from __future__ import annotations

import json
from pathlib import Path

import pytest

from dbgpt.agent.core.context.budget import ContextBudgetConfig
from dbgpt.agent.core.context.manager import ContextManager
from dbgpt.agent.core.context.storage import (
    ToolResultBudgetConfig,
    ToolResultStorage,
    set_current_storage,
)
from dbgpt_app.openapi.api_v1.tools.sql_query import make_sql_query
from insight_agent.agent.domain_policy import validate_insight_sql
from insight_agent.evaluation.context_profiler import (
    parse_events,
    score_case,
    summarize_records,
)
from insight_agent.evaluation.context_schemas import (
    load_long_context_dataset,
    validate_long_context_dataset,
)
from insight_agent.evaluation.cost_calculator import (
    estimate_cost,
    estimate_text_tokens,
)

DATASET = (
    Path(__file__).resolve().parents[2]
    / "insight_agent"
    / "evaluation"
    / "dataset"
    / "long_context_test.json"
)


def test_week5_dataset_is_frozen_and_partitioned() -> None:
    dataset = load_long_context_dataset(DATASET)
    assert len(dataset["cases"]) == 20
    assert sum(case["split"] == "dev" for case in dataset["cases"]) == 12
    assert sum(case["split"] == "test" for case in dataset["cases"]) == 6
    assert sum(case["split"] == "challenge" for case in dataset["cases"]) == 2


def test_week5_dataset_rejects_duplicate_ids() -> None:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    dataset["cases"][1]["id"] = dataset["cases"][0]["id"]
    assert any("重复 ID" in error for error in validate_long_context_dataset(dataset))


def test_context_profiler_uses_last_status_before_step() -> None:
    events = [
        {"type": "context.status", "used": 1000, "ratio": 0.8},
        {
            "type": "context.status",
            "used": 600,
            "ratio": 0.5,
            "compact_layer": "layer2",
        },
        {"type": "step.start", "step": 1},
        {"type": "step.meta", "action": "sql_query", "thought": "查询"},
        {"type": "step.chunk", "content": "Observation"},
        {"type": "step.done", "step": 1},
        {"type": "final", "content": "销售额为 100 元", "citations": []},
    ]
    actual = parse_events(events, "测试问题")
    question_tokens = estimate_text_tokens("测试问题")
    assert actual["estimated_input_tokens_before_compaction"] == (
        1000 + question_tokens
    )
    assert actual["estimated_input_tokens"] == 600 + question_tokens
    assert actual["context_layers"] == {"layer2": 1}


def test_score_case_checks_fact_tool_and_citation() -> None:
    case = {
        "expected_facts": [
            {
                "name": "sales",
                "kind": "numeric",
                "accepted_values": [1087378.79],
                "tolerance": 0.01,
            }
        ],
        "expected_tools": ["sales_diagnosis_tool"],
        "expected_documents": ["经销商分级与考核管理制度"],
        "expected_sections": ["4.2"],
        "expected_completion": "success",
    }
    actual = {
        "actual_answer": "销售额 1,087,378.79 元，参见制度 4.2 节。",
        "actual_tools": ["sales_diagnosis_tool"],
        "actual_citations": [{"document": "经销商分级与考核管理制度"}],
        "context_overflow_present": False,
    }
    verdict = score_case(case, actual)
    assert verdict["pass_fail"] is True


def test_cost_is_labelled_as_estimate() -> None:
    cost = estimate_cost(
        "deepseek-v4-flash", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost["kind"] == "estimated_not_provider_usage"
    assert cost["total_cost_usd"] == pytest.approx(1.5)
    assert cost["total_cost_cny"] == pytest.approx(10.5)


def test_summarize_records_keeps_quality_and_cost_separate() -> None:
    record = {
        "pass_fail": True,
        "facts_passed": 2,
        "facts_total": 2,
        "citation_checks_passed": 1,
        "citation_checks_total": 1,
        "estimated_input_tokens": 100,
        "estimated_output_tokens": 20,
        "latency_seconds": 1.5,
        "cost_estimate": {"total_cost_cny": 0.01},
        "tool_result_chars": 200,
        "persisted_output_present": True,
        "context_overflow_present": False,
        "context_layers": {"layer1": 1},
        "transport_error": None,
    }
    summary = summarize_records([record])
    assert summary["task_pass_rate"] == 1.0
    assert summary["key_fact_retention"] == 1.0
    assert summary["citation_accuracy"] == 1.0
    assert summary["estimated_total_cost_cny"] == 0.01
    assert summary["context_layer_counts"] == {"layer1": 1}


def test_context_manager_retains_model_name_for_layer3() -> None:
    manager = ContextManager(
        config=ContextBudgetConfig(max_context_tokens=1000),
        model_name="deepseek-v4-flash",
    )
    assert manager.model_name == "deepseek-v4-flash"


def test_tool_storage_enforces_rolling_turn_budget(tmp_path: Path) -> None:
    storage = ToolResultStorage(
        str(tmp_path),
        config=ToolResultBudgetConfig(
            default_result_size=1000,
            turn_budget=10,
            preview_size=4,
        ),
    )
    storage.begin_turn()
    first, first_path = storage.maybe_persist_for_turn("123456", "tool", "first")
    second, second_path = storage.maybe_persist_for_turn("abcdef", "tool", "second")
    assert first == "123456" and first_path is None
    assert "<persisted-output>" in second
    assert second_path and Path(second_path).read_text(encoding="utf-8") == "abcdef"


def test_tool_storage_rejects_sibling_prefix_path(tmp_path: Path) -> None:
    storage_dir = tmp_path / "safe"
    sibling = tmp_path / "safe-evil"
    sibling.mkdir()
    secret = sibling / "secret.txt"
    secret.write_text("not allowed", encoding="utf-8")
    storage = ToolResultStorage(str(storage_dir))
    assert storage.read_persisted(str(secret)) is None


def test_large_sql_result_is_fully_persisted_and_only_topn_is_inline(
    tmp_path: Path,
) -> None:
    class LargeConnector:
        def run(self, _sql: str):
            columns = [("id",), ("value",)]
            rows = [(index, f"value-{index}") for index in range(60)]
            return [columns, *rows]

    storage = ToolResultStorage(str(tmp_path), preview_size=100)
    set_current_storage(storage)
    try:
        query = make_sql_query(
            {"database_name": "generic_db", "user_input": "列出数据"},
            LargeConnector(),
        )
        payload = json.loads(query("SELECT id, value FROM demo"))
    finally:
        set_current_storage(None)

    content = payload["chunks"][0]["content"]
    assert "共 60 行" in content
    assert "value-9" in content
    assert "value-10" not in content
    assert "<persisted-output>" in content
    files = list(tmp_path.glob("*.txt"))
    assert len(files) == 1
    full_result = files[0].read_text(encoding="utf-8")
    assert "value-59" in full_result


def test_full_trace_request_rejects_sql_limit() -> None:
    result = validate_insight_sql(
        "SELECT c.customer_name, SUM(f.sales_amount) AS sales "
        "FROM fact_sales f JOIN dim_customer c ON f.customer_id=c.customer_id "
        "WHERE EXTRACT(YEAR FROM f.sale_date)=2026 "
        "AND EXTRACT(QUARTER FROM f.sale_date)=2 "
        "GROUP BY c.customer_name ORDER BY sales DESC LIMIT 10",
        "列出 2026Q2 全部客户，回答只总结前10名，但完整查询结果必须可追溯。",
    )
    assert not result.valid
    assert any("SQL 不得 LIMIT" in error for error in result.errors)


def test_full_trace_request_rejects_window_rank_topn_filter() -> None:
    result = validate_insight_sql(
        "WITH base AS (SELECT r.region_name, p.category, f.channel, "
        "SUM(f.sales_amount) AS sales_amount FROM fact_sales f "
        "JOIN dim_region r ON f.region_id=r.region_id "
        "JOIN dim_product p ON f.product_id=p.product_id "
        "WHERE EXTRACT(YEAR FROM f.sale_date)=2026 "
        "AND EXTRACT(QUARTER FROM f.sale_date)=2 "
        "GROUP BY r.region_name,p.category,f.channel), ranked AS ("
        "SELECT *, ROW_NUMBER() OVER (ORDER BY sales_amount) AS rn FROM base) "
        "SELECT * FROM ranked WHERE rn <= 10",
        "列出 2026Q2 全部组合，回答只展示最低10个，完整结果需要可追溯。",
    )
    assert not result.valid
    assert any("SQL 不得 LIMIT" in error for error in result.errors)
