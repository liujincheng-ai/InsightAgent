"""sql_query tool — read-only SQL query against the selected database."""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from dbgpt.agent.core.context.storage import get_current_storage
from dbgpt.agent.resource.tool.base import tool
from dbgpt_app.insight_agent.sql_error import (
    classify_preflight_error,
    classify_sql_error,
)
from insight_agent.agent.domain_policy import (
    is_insight_database,
    validate_insight_sql,
    validate_read_only_sql,
)

logger = logging.getLogger(__name__)


def make_sql_query(react_state: Dict[str, Any], database_connector: Optional[Any]):
    @tool(
        description=(
            "对用户选择的数据库执行 SQL 查询（仅支持 SELECT）。"
            '参数: {"sql": "SELECT 语句"}'
        )
    )
    def sql_query(sql: str) -> str:
        """Execute a read-only SQL query against the selected database."""
        started_at = time.monotonic()
        database_name = str(react_state.get("database_name") or "")
        question = str(react_state.get("user_input") or "")
        diagnostics = react_state.setdefault("diagnostics", [])

        def _failure_payload(
            error_info: Any,
            *,
            source: str,
            failed_sql: str,
            details: Any = None,
        ) -> str:
            failure_count = int(react_state.get("sql_failure_count", 0)) + 1
            if not error_info.retryable:
                failure_count = 2
            react_state["sql_failure_count"] = failure_count
            react_state["last_failed_sql"] = " ".join(failed_sql.lower().split())
            retryable = bool(error_info.retryable and failure_count < 2)
            remaining = 1 if retryable else 0
            next_action = "retry_sql" if retryable else "terminate"
            payload = {
                "status": "error",
                "error_code": error_info.error_code,
                "error_source": source,
                "retryable": retryable,
                "retry_budget_remaining": remaining,
                "next_action": next_action,
                "safe_summary": error_info.safe_summary,
                "chunks": [
                    {
                        "output_type": "text",
                        "content": (
                            f"[{error_info.error_code}] {error_info.safe_summary} "
                            + (
                                "你只可修正 SQL 后再调用一次 sql_query；"
                                "不得重复原 SQL。"
                                if retryable
                                else "本次查询不得继续重试，请说明失败并终止。"
                            )
                        ),
                    }
                ],
            }
            if details is not None:
                payload["validation_errors"] = details
            return json.dumps(payload, ensure_ascii=False)

        def _record(status: str, **extra: Any) -> None:
            entry = {
                "tool": "sql_query",
                "status": status,
                "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
            }
            entry.update(extra)
            diagnostics.append(entry)
            logger.info(
                "InsightAgent sql_query status=%s database=%s duration_ms=%s",
                status,
                database_name or "<none>",
                entry["duration_ms"],
            )

        if database_connector is None:
            _record("no_database")
            return json.dumps(
                {
                    "chunks": [
                        {
                            "output_type": "text",
                            "content": "未选择数据库，请先在左侧面板选择一个数据源。",
                        }
                    ]
                },
                ensure_ascii=False,
            )

        # Focused InsightAgent questions are designed to be answered by one
        # semantically complete query.  Once a validated query succeeds, block
        # exploratory follow-up queries and force the next ReAct round to turn
        # the existing result into a final answer.  This keeps Q4/Q6/Q8 from
        # drifting into redundant multi-step analysis.
        if is_insight_database(database_name) and react_state.get(
            "successful_sql_calls", 0
        ):
            _record("blocked_after_success")
            return json.dumps(
                {
                    "error_code": "SQL_RESULT_ALREADY_SUFFICIENT",
                    "retryable": False,
                    "next_action": "terminate",
                    "chunks": [
                        {
                            "output_type": "text",
                            "content": (
                                "已有一次通过语义校验的查询结果，禁止继续查询。"
                                "请立即使用此前结果执行 terminate，并给出最终中文答案。"
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )

        if (
            is_insight_database(database_name)
            and int(react_state.get("sql_failure_count", 0)) >= 2
        ):
            _record("retry_budget_exhausted")
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "SQL_RETRY_LIMIT_REACHED",
                    "retryable": False,
                    "retry_budget_remaining": 0,
                    "next_action": "terminate",
                    "chunks": [
                        {
                            "output_type": "text",
                            "content": (
                                "SQL 首次尝试及一次修正均失败，禁止继续查询，"
                                "请说明失败并终止。"
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )

        sql_stripped = sql.strip().rstrip(";")
        normalized_sql = " ".join(sql_stripped.lower().split())
        if (
            is_insight_database(database_name)
            and react_state.get("last_failed_sql") == normalized_sql
        ):
            react_state["sql_failure_count"] = 2
            _record("duplicate_failed_sql")
            return json.dumps(
                {
                    "status": "error",
                    "error_code": "SQL_RETRY_LIMIT_REACHED",
                    "retryable": False,
                    "retry_budget_remaining": 0,
                    "next_action": "terminate",
                    "chunks": [
                        {
                            "output_type": "text",
                            "content": (
                                "修正时重复提交了相同失败 SQL，重试预算已耗尽，"
                                "请说明失败并终止。"
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
        validation = (
            validate_insight_sql(sql_stripped, question)
            if is_insight_database(database_name)
            else validate_read_only_sql(sql_stripped)
        )
        if not validation.valid:
            _record("validation_failed", validation_errors=list(validation.errors))
            return _failure_payload(
                classify_preflight_error(validation.errors),
                source="preflight",
                failed_sql=sql_stripped,
                details=list(validation.errors),
            )

        if is_insight_database(database_name):
            logger.info(
                "InsightAgent semantic SQL preflight passed for question_chars=%d",
                len(question),
            )

        try:
            result = database_connector.run(sql_stripped)
            if not result:
                _record("empty")
                return json.dumps(
                    {
                        "chunks": [
                            {"output_type": "text", "content": "查询返回空结果。"}
                        ]
                    },
                    ensure_ascii=False,
                )

            columns = result[0]
            col_names = [str(c[0]) if isinstance(c, tuple) else str(c) for c in columns]
            rows = result[1:]

            header = "| " + " | ".join(col_names) + " |"
            separator = "| " + " | ".join(["---"] * len(col_names)) + " |"
            all_md_rows = [
                "| " + " | ".join(str(v) for v in row) + " |" for row in rows
            ]
            full_table = "\n".join([header, separator] + all_md_rows)

            # Persist the complete result before reducing what enters the model
            # context.  The context receives schema, total count, Top-N rows and
            # a readable file reference; no truncated text is presented as the
            # complete result.
            MAX_SQL_OUTPUT_CHARS = 20_000
            TOP_N_ROWS = 10
            oversized = len(rows) > 50 or len(full_table) > MAX_SQL_OUTPUT_CHARS
            table = full_table
            persisted_path: Optional[str] = None
            if oversized:
                storage = get_current_storage()
                persisted_message = ""
                if storage is not None:
                    persisted_message, persisted_path = storage.maybe_persist(
                        content=full_table,
                        tool_name="sql_query",
                        tool_call_id=f"sql_query_full_{uuid.uuid4().hex}",
                        threshold=0,
                    )
                top_rows = all_md_rows[:TOP_N_ROWS]
                table = "\n".join([header, separator] + top_rows)
                table += (
                    f"\n\n结果摘要：字段 {', '.join(col_names)}；"
                    f"共 {len(rows)} 行；上表仅展示前 {min(TOP_N_ROWS, len(rows))} 行。"
                )
                if persisted_path:
                    table += f"\n\n{persisted_message}"
                else:
                    table += "\n\n完整结果未能落盘，本回答不得将预览误称为完整结果。"

            _record(
                "success",
                row_count=len(rows),
                full_result_persisted=bool(persisted_path),
            )
            if is_insight_database(database_name):
                react_state["successful_sql_calls"] = (
                    int(react_state.get("successful_sql_calls", 0)) + 1
                )
                react_state["last_sql_result"] = {
                    "columns": col_names,
                    "rows": [list(row) for row in rows[:50]],
                    "row_count": len(rows),
                }
            return json.dumps(
                {
                    "status": "success",
                    "next_action": "terminate",
                    "instruction": (
                        "查询结果已经足以回答当前问题；下一轮必须 terminate，"
                        "不得追加 SQL 查询。"
                    ),
                    "chunks": [{"output_type": "markdown", "content": table}],
                },
                ensure_ascii=False,
            )
        except Exception as e:
            _record("execution_failed", error_type=type(e).__name__)
            return _failure_payload(
                classify_sql_error(e), source="database", failed_sql=sql_stripped
            )

    return sql_query
