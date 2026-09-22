"""Regression tests for the Day 2 InsightAgent fixes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dbgpt.agent.expand.actions.react_action import (
    normalize_common_tool_args,
    parse_strict_action_input,
)
from dbgpt.agent.resource import tool
from dbgpt.agent.resource.pack import ResourcePack
from dbgpt_app.openapi.api_v1.agentic_data_api import (
    _extract_search_candidate,
    _extract_sql_candidate,
    _is_insight_integrated_request,
)
from dbgpt_app.openapi.api_v1.citation_followup import (
    build_citation_followup_answer,
    is_citation_followup,
)
from dbgpt_app.openapi.api_v1.tools.sql_query import make_sql_query
from insight_agent.agent.domain_policy import (
    build_database_agent_prompt,
    build_integrated_business_prompt,
    format_focused_domain_answer,
    format_integrated_business_answer,
    validate_insight_sql,
    validate_read_only_sql,
)
from insight_agent.agent.sales_diagnosis_gate import (
    SalesDiagnosisFirstToolPack,
    focused_domain_tool_args,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "insight_agent" / "evaluation" / "dataset"


def test_day2_evaluation_contract_is_immutable() -> None:
    expected = {
        "day2_text_to_sql.json": (
            "c8642a4e7ce53ec9bbe7b96168a1b69efd74907843b8066c5f683b5676e5d83d"
        ),
        "day2_rag.json": (
            "180a18903960dbc39d882697f3ae02d29fdfd3407c7e72fc17b8d55a41343e48"
        ),
    }
    for filename, digest in expected.items():
        content = (DATASET_DIR / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == digest


def test_q3_sql_requires_2026_product_join_and_defined_aliases() -> None:
    question = "华东 Q2 哪个汽车配件品类下降最多？"
    broken = """
        SELECT p.category, SUM(f.sales_amount)
        FROM fact_sales f
        JOIN dim_region r ON f.region_id = r.region_id
        WHERE r.region_name = '华东' AND EXTRACT(YEAR FROM f.sale_date) = 2025
        GROUP BY p.category
    """
    result = validate_insight_sql(broken, question)
    assert not result.valid
    assert any("未在 FROM/JOIN 中定义的别名: p" in item for item in result.errors)
    assert "产品或品类分析必须连接 dim_product" in result.errors
    assert any("2026 Q2" in item for item in result.errors)

    fixed = """
        SELECT p.category,
               SUM(CASE WHEN f.sale_date >= DATE '2026-01-01'
                         AND f.sale_date < DATE '2026-04-01'
                        THEN f.sales_amount ELSE 0 END) AS q1_sales,
               SUM(CASE WHEN f.sale_date >= DATE '2026-04-01'
                         AND f.sale_date < DATE '2026-07-01'
                        THEN f.sales_amount ELSE 0 END) AS q2_sales
        FROM fact_sales f
        JOIN dim_region r ON f.region_id = r.region_id
        JOIN dim_product p ON f.product_id = p.product_id
        WHERE r.region_name = '华东'
        GROUP BY p.category
    """
    assert validate_insight_sql(fixed, question).valid


def test_q10_sql_requires_full_business_scope() -> None:
    question = "华东刹车系统经销商渠道 2026 年销售下降从哪个月开始？"
    incomplete = """
        SELECT DATE_TRUNC('month', sale_date), SUM(sales_amount)
        FROM fact_sales
        WHERE channel = '经销商' AND EXTRACT(YEAR FROM sale_date) = 2026
        GROUP BY 1
    """
    result = validate_insight_sql(incomplete, question)
    assert not result.valid
    assert "缺少业务范围约束: 华东" in result.errors
    assert "缺少业务范围约束: 刹车系统" in result.errors
    assert "区域分析必须连接 dim_region" in result.errors
    assert "产品或品类分析必须连接 dim_product" in result.errors

    fixed = """
        SELECT DATE_TRUNC('month', f.sale_date), SUM(f.sales_amount)
        FROM fact_sales f
        JOIN dim_region r ON f.region_id = r.region_id
        JOIN dim_product p ON f.product_id = p.product_id
        WHERE r.region_name = '华东'
          AND p.category = '刹车系统'
          AND f.channel = '经销商'
          AND f.sale_date >= DATE '2026-01-01'
          AND f.sale_date < DATE '2027-01-01'
        GROUP BY 1
    """
    assert validate_insight_sql(fixed, question).valid


def test_sql_tool_does_not_execute_when_preflight_fails() -> None:
    class RecordingConnector:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def run(self, sql: str):
            self.queries.append(sql)
            return [[("value",)], (1,)]

    connector = RecordingConnector()
    state = {
        "database_name": "insight_agent",
        "user_input": "华东刹车系统经销商渠道 2026 年销售下降从哪个月开始？",
    }
    sql_query = make_sql_query(state, connector)
    payload = json.loads(
        sql_query(
            "SELECT DATE_TRUNC('month', sale_date), SUM(sales_amount) "
            "FROM fact_sales WHERE channel = '经销商' "
            "AND EXTRACT(YEAR FROM sale_date) = 2026 GROUP BY 1"
        )
    )
    assert payload["error_code"] in {
        "COLUMN_NOT_FOUND",
        "TYPE_OR_DATE_ERROR",
    }
    assert payload["error_source"] == "preflight"
    assert payload["retryable"] is True
    assert connector.queries == []
    assert state["diagnostics"][0]["status"] == "validation_failed"


def test_sql_tool_requires_terminate_after_first_success() -> None:
    class RecordingConnector:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def run(self, sql: str):
            self.queries.append(sql)
            return [[("value",)], (1,)]

    connector = RecordingConnector()
    state = {
        "database_name": "insight_agent",
        "user_input": "2026 年每月销售趋势是什么？",
    }
    sql_query = make_sql_query(state, connector)
    valid_sql = (
        "SELECT DATE_TRUNC('month', sale_date), SUM(sales_amount) "
        "FROM fact_sales WHERE sale_date >= DATE '2026-01-01' "
        "AND sale_date < DATE '2027-01-01' GROUP BY 1"
    )

    first = json.loads(sql_query(valid_sql))
    second = json.loads(sql_query(valid_sql))

    assert first["status"] == "success"
    assert first["next_action"] == "terminate"
    assert second["error_code"] == "SQL_RESULT_ALREADY_SUFFICIENT"
    assert second["retryable"] is False
    assert len(connector.queries) == 1
    assert state["diagnostics"][-1]["status"] == "blocked_after_success"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE fact_sales SET quantity = 0",
        "SELECT 1; DELETE FROM fact_sales",
        "WITH removed AS (DELETE FROM fact_sales RETURNING *) SELECT * FROM removed",
    ],
)
def test_read_only_sql_validation_fails_closed(sql: str) -> None:
    assert not validate_read_only_sql(sql).valid


def test_strict_sql_action_input_rejects_malformed_or_extra_fields() -> None:
    with pytest.raises(ValueError, match="INVALID_JSON"):
        parse_strict_action_input("sql_query", '{"sql": "SELECT 1"')
    with pytest.raises(ValueError, match="SCHEMA_ERROR"):
        parse_strict_action_input("sql_query", {"sql": "SELECT 1", "unexpected": True})
    assert parse_strict_action_input("sql_query", '{"sql": "SELECT 1"}') == {
        "sql": "SELECT 1"
    }
    assert parse_strict_action_input("kb_grep", "not json") is None


def test_kb_cat_file_alias_is_normalized_to_path() -> None:
    assert normalize_common_tool_args(
        "kb_cat", {"file": "经销商分级与考核管理制度.md"}
    ) == {"path": "经销商分级与考核管理制度.md"}
    assert normalize_common_tool_args("kb_cat", {"path": "制度.md"}) == {
        "path": "制度.md"
    }


def test_database_prompt_uses_focused_tool_surface_and_selected_semantics() -> None:
    prompt = build_database_agent_prompt(
        "- 数据库名: insight_agent\n- 可用表: fact_sales, dim_region, dim_product",
        "经销商渠道销售下降从哪个月开始？",
    )
    assert "sql_query 或 terminate" in prompt
    assert "不委派子任务" in prompt
    assert "交易渠道以 fact_sales.channel 为准" in prompt
    assert "SUM(fact_sales.sales_amount)" in prompt
    assert "最多修正一次" in prompt
    assert "## 数据范围" in prompt
    assert "销售额（CNY）" in prompt


def test_integrated_prompt_requires_native_sales_tool_before_rag() -> None:
    prompt = build_integrated_business_prompt(
        "分析华东刹车系统经销商渠道下降并结合制度提出改进建议，生成报告"
    )
    assert "第一项数据动作" in prompt
    assert "sales_diagnosis_tool" in prompt
    assert "不得通过 `execute_tool` 间接调用" in prompt
    assert "《经销商分级与考核管理制度》的 4.2 节" in prompt
    assert "HTML 报告渲染前，不得 terminate" in prompt


def test_integrated_prompt_does_not_force_dealer_policy_for_unrelated_report() -> None:
    prompt = build_integrated_business_prompt(
        "分析华南照明系统销售变化并结合产品质量制度生成报告"
    )
    assert "sales_diagnosis_tool" in prompt
    assert "不得固定引用无关文件或章节" in prompt
    assert "经销商分级与考核管理制度》的 4.2 节" not in prompt


def test_integrated_prompt_preserves_explicit_document_and_section() -> None:
    prompt = build_integrated_business_prompt(
        "评估华东 2026Q2 经销商健康度，再引用《汽车配件价格与折扣管理办法》"
        "3.1 节解释折扣扣分依据。"
    )
    assert "dealer_health_analysis_tool" in prompt
    assert "《汽车配件价格与折扣管理办法》 3.1 节" in prompt
    assert "不得用其他制度替换用户指定依据" in prompt
    assert "经销商评分引用《经销商分级与考核管理制度》" not in prompt


def test_day4_prompt_routes_each_focused_question_to_one_domain_tool() -> None:
    cases = [
        (
            "华东刹车系统 2026 Q2 的同比、环比和主要下降渠道是什么？",
            "sales_diagnosis_tool",
        ),
        (
            "哪些 A 级客户对华东刹车系统销售下滑影响最大？",
            "customer_loss_analysis_tool",
        ),
        (
            "2026 Q2 华东哪些经销商风险最高，具体扣分项是什么？",
            "dealer_health_analysis_tool",
        ),
    ]
    for question, expected_tool in cases:
        prompt = build_integrated_business_prompt(question)
        assert f"第一项数据动作必须直接调用 `{expected_tool}`" in prompt
        assert "不强制检索制度或生成 HTML" in prompt


def test_day4_routing_ignores_database_and_knowledge_ui_prefixes() -> None:
    prompt = build_integrated_business_prompt(
        "[Database: insight_agent] [Knowledge: 汽车配件企业制度库] "
        "哪些 A 级客户对华东刹车系统销售下滑影响最大？"
    )
    assert "customer_loss_analysis_tool" in prompt
    assert "不强制检索制度或生成 HTML" in prompt
    assert '"current_quarter":"<YYYYQn>"' in prompt
    assert "不得把 `current_quarter` 改成 `period`" in prompt
    assert "最新完整季度 `2026Q2`" in prompt
    assert "比较基准是上一季度 `2026Q1`" in prompt

    from jinja2 import Template

    assert "customer_loss_analysis_tool" in Template(prompt).render()


def test_day4_toolpack_allows_only_selected_domain_tool_first() -> None:
    calls: list[str] = []

    @tool("sales_diagnosis_tool")
    def sales_tool() -> dict[str, str]:
        """Return sales facts."""
        calls.append("sales")
        return {"status": "success"}

    @tool("customer_loss_analysis_tool")
    def customer_tool() -> dict[str, str]:
        """Return customer warnings."""
        calls.append("customer")
        return {"status": "success"}

    @tool("dealer_health_analysis_tool")
    def dealer_tool() -> dict[str, str]:
        """Return dealer scores."""
        calls.append("dealer")
        return {"status": "success"}

    from dbgpt.agent.expand.actions.react_action import Terminate

    pack = SalesDiagnosisFirstToolPack(
        [sales_tool, customer_tool, dealer_tool, Terminate()],
        required_domain_tool="customer_loss_analysis_tool",
        require_knowledge_and_report=False,
    )
    blocked = pack.execute(resource_name="sales_diagnosis_tool")
    assert blocked["error_code"] == "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED"
    assert calls == []
    assert (
        pack.execute(resource_name="customer_loss_analysis_tool")["status"] == "success"
    )
    assert calls == ["customer"]
    assert pack.is_terminal("terminate") is True


def test_integrated_toolpack_requires_all_explicit_domain_tools() -> None:
    calls: list[str] = []

    @tool("sales_diagnosis_tool")
    def sales_tool() -> dict[str, str]:
        """Return sales facts."""
        calls.append("sales")
        return {"status": "success"}

    @tool("customer_loss_analysis_tool")
    def customer_tool() -> dict[str, str]:
        """Return customer warnings."""
        calls.append("customer")
        return {"status": "success"}

    from dbgpt.agent.expand.actions.react_action import Terminate

    pack = SalesDiagnosisFirstToolPack(
        [sales_tool, customer_tool, Terminate()],
        required_domain_tool="customer_loss_analysis_tool",
        required_domain_tools=[
            "customer_loss_analysis_tool",
            "sales_diagnosis_tool",
        ],
        require_knowledge_and_report=False,
    )
    assert pack.execute(resource_name="customer_loss_analysis_tool")["status"] == (
        "success"
    )
    assert pack.is_terminal("terminate") is False
    assert pack.execute(resource_name="sales_diagnosis_tool")["status"] == "success"
    assert calls == ["customer", "sales"]
    assert set(pack.domain_results) == {
        "customer_loss_analysis_tool",
        "sales_diagnosis_tool",
    }
    assert pack.is_terminal("terminate") is True


def test_insight_integrated_request_uses_selected_resources_not_tool_mode() -> None:
    connector = object()
    assert _is_insight_integrated_request(
        connector, "汽车配件企业制度库", "insight_agent"
    )
    assert not _is_insight_integrated_request(
        None, "汽车配件企业制度库", "insight_agent"
    )
    assert not _is_insight_integrated_request(connector, None, "insight_agent")
    assert not _is_insight_integrated_request(connector, "制度库", "other_database")


def test_day6_recovers_only_a_lone_sql_mapping() -> None:
    sql = "SELECT SUM(sales_amount) FROM fact_sales"
    assert _extract_sql_candidate(json.dumps({"sql": sql})) == sql
    assert _extract_sql_candidate(repr({"sql": sql})) == sql
    assert _extract_sql_candidate("{'sql': 'SELECT 1', 'extra': true}") is None
    assert _extract_sql_candidate("__import__('os').system('whoami')") is None


def test_day6_recovers_only_a_lone_search_mapping() -> None:
    query = "重点安全类产品 7 天内缺货 紧急补货"
    assert _extract_search_candidate(json.dumps({"query": query})) == query
    assert _extract_search_candidate(repr({"query": query})) == query
    assert _extract_search_candidate('{"query":"x","top_k":5}') is None
    assert _extract_search_candidate("__import__('os').system('whoami')") is None


@pytest.mark.parametrize(
    ("question", "tool_name", "expected"),
    [
        (
            "华东刹车系统 2026 Q2 的同比和环比？",
            "sales_diagnosis_tool",
            {
                "region": "华东",
                "category": "刹车系统",
                "current_quarter": "2026Q2",
                "top_n": 5,
            },
        ),
        (
            "哪些 A 级客户对华东刹车系统销售下滑影响最大？",
            "customer_loss_analysis_tool",
            {
                "region": "华东",
                "category": "刹车系统",
                "current_quarter": "2026Q2",
                "decline_threshold": 0.5,
                "top_n": 10,
            },
        ),
        (
            "2026 Q2 华东哪些经销商风险最高？",
            "dealer_health_analysis_tool",
            {"region": "华东", "current_quarter": "2026Q2", "top_n": 10},
        ),
    ],
)
def test_focused_domain_tool_args(
    question: str, tool_name: str, expected: dict[str, object]
) -> None:
    assert focused_domain_tool_args(question, tool_name) == expected


def test_focused_domain_tool_args_fails_closed_without_scope() -> None:
    result = focused_domain_tool_args(
        "哪些客户下降最多？", "customer_loss_analysis_tool"
    )
    assert result is None


def test_focused_sales_answer_uses_verified_observation() -> None:
    answer = format_focused_domain_answer(
        "sales_diagnosis_tool",
        {
            "status": "success",
            "region": "华东",
            "category": "刹车系统",
            "current_quarter": "2026Q2",
            "baseline_quarter": "2026Q1",
            "data": {
                "sales": {
                    "current": 1087378.79,
                    "qoq_change_rate": -0.3268,
                    "yoy_change_rate": -0.2927,
                },
                "channel_contributions": [
                    {
                        "name": "经销商",
                        "qoq_change_amount": -395312.25,
                        "decline_contribution_rate": 0.7489,
                    }
                ],
            },
        },
    )
    assert answer is not None
    assert "1,087,378.79" in answer
    assert "-32.68%" in answer
    assert "-29.27%" in answer
    assert "经销商" in answer and "74.89%" in answer


def test_integrated_answer_is_bound_to_domain_and_policy_evidence() -> None:
    result = {
        "status": "success",
        "region": "华东",
        "category": "刹车系统",
        "current_quarter": "2026Q2",
        "baseline_quarter": "2026Q1",
        "data": {
            "sales": {
                "current": 1087378.79,
                "qoq_change_rate": -0.3268,
                "yoy_change_rate": -0.2927,
            },
            "channel_contributions": [
                {
                    "name": "经销商",
                    "qoq_change_amount": -395312.25,
                    "decline_contribution_rate": 0.7489,
                }
            ],
        },
    }
    answer = format_integrated_business_answer(
        "sales_diagnosis_tool",
        result,
        "《经销商分级与考核管理制度》第3.2节、第4.2节",
        "生成经营分析报告",
    )
    assert answer is not None
    assert "2026Q2" in answer and "2026Q1" in answer and "2025Q2" in answer
    assert "-32.68%" in answer and "-29.27%" in answer
    assert "客户" in answer and "经销商" in answer and "风险" in answer
    assert "经销商分级与考核管理制度" in answer
    assert "3.2" in answer and "4.2" in answer
    assert "数据事实" in answer and "管理建议" in answer


def test_focused_customer_answer_filters_a_level_and_keeps_warning() -> None:
    answer = format_focused_domain_answer(
        "customer_loss_analysis_tool",
        {
            "status": "success",
            "region": "华东",
            "category": "刹车系统",
            "current_quarter": "2026Q2",
            "baseline_quarter": "2026Q1",
            "data": {
                "summary": {"net_decline_amount": 100, "risk_customer_count": 2},
                "risk_customers": [
                    {
                        "customer_name": "A级客户",
                        "is_core_a_customer": True,
                        "decline_amount": 80,
                        "decline_rate": 0.8,
                        "decline_contribution_rate": 0.8,
                    },
                    {
                        "customer_name": "B级客户",
                        "is_core_a_customer": False,
                        "decline_amount": 20,
                        "decline_rate": 0.6,
                        "decline_contribution_rate": 0.2,
                    },
                ],
            },
        },
        "哪些 A 级客户影响最大？",
    )
    assert answer is not None
    assert "A级客户" in answer and "B级客户" not in answer
    assert "不代表客户已确认流失" in answer


def test_focused_dealer_answer_exposes_scores_and_deductions() -> None:
    answer = format_focused_domain_answer(
        "dealer_health_analysis_tool",
        {
            "status": "success",
            "region": "华东",
            "current_quarter": "2026Q2",
            "baseline_quarter": "2026Q1",
            "data": {
                "dealers": [
                    {
                        "dealer_name": "华东核心经销商一号",
                        "health_score": 62,
                        "risk_level": "medium",
                        "component_scores": {
                            "sales_change": 12,
                            "purchase_activity": 20,
                            "discount": 14,
                            "gross_margin": 16,
                        },
                        "deductions": [
                            {"component": "sales_change", "deducted_points": 28}
                        ],
                    }
                ]
            },
        },
    )
    assert answer is not None
    assert "62/100" in answer and "销售变化 12/40" in answer
    assert "sales_change 扣 28 分" in answer
    assert "V1 演示规则" in answer


def test_integrated_toolpack_requires_diagnosis_before_rag_and_termination() -> None:
    calls: list[str] = []

    @tool("sales_diagnosis_tool")
    def sales_diagnosis_tool() -> dict[str, str]:
        """Return the mandatory sales diagnostic observation."""
        calls.append("sales")
        return {"status": "success"}

    @tool("semantic_search")
    def semantic_search() -> str:
        """Return the policy evidence."""
        calls.append("knowledge")
        return "制度证据"

    @tool("html_interpreter")
    def html_interpreter() -> str:
        """Render the business report."""
        calls.append("html")
        return "报告"

    from dbgpt.agent.expand.actions.react_action import Terminate

    pack = SalesDiagnosisFirstToolPack(
        [sales_diagnosis_tool, semantic_search, html_interpreter, Terminate()]
    )
    before_diagnosis = pack.execute(resource_name="semantic_search")
    assert before_diagnosis["error_code"] == "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED"
    assert calls == []
    assert pack.is_terminal("terminate") is False

    assert pack.execute(resource_name="sales_diagnosis_tool")["status"] == "success"
    before_knowledge = pack.execute(resource_name="html_interpreter")
    assert before_knowledge["error_code"] == "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED"
    assert pack.execute(resource_name="semantic_search") == "制度证据"
    assert pack.execute(resource_name="code_interpreter")["error_code"] == (
        "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED"
    )
    assert pack.execute(resource_name="html_interpreter") == "报告"
    assert pack.is_terminal("terminate") is True

    # The guard survives the outer Agent resource pack used by ToolAction.
    assert SalesDiagnosisFirstToolPack.from_resource(ResourcePack([pack])) == [pack]


def _view_message(source: str, section: str, answer: str) -> SimpleNamespace:
    payload = {
        "type": "react-agent",
        "final_content": f"{answer}，来自《{source}》{section}。",
        "citations": [
            {
                "index": 1,
                "id": source,
                "sourceName": source,
                "excerpt": f"## {section}\n这是支持回答的制度正文。",
                "score": 0.9,
                "path": source,
                "url": None,
            }
        ],
    }
    return SimpleNamespace(type="view", content=json.dumps(payload, ensure_ascii=False))


def test_citation_followup_is_built_from_three_prior_rounds() -> None:
    question = "以上三个答案分别来自哪份制度、哪个章节？"
    assert is_citation_followup(question)
    messages = [
        _view_message(
            "经销商分级与考核管理制度.md", "4.2 A级经销商连续下降处置", "措施"
        ),
        _view_message("重点客户流失预警办法.md", "3.3 责任分工", "责任人"),
        _view_message("汽车配件价格与折扣管理办法.md", "4.2 超标准折扣审批", "审批"),
        SimpleNamespace(type="human", content=question),
    ]
    answer = build_citation_followup_answer(messages)
    assert answer is not None
    assert len(answer.citations) == 3
    assert "经销商分级与考核管理制度.md》— 4.2" in answer.content
    assert "重点客户流失预警办法.md》— 3.3" in answer.content
    assert "汽车配件价格与折扣管理办法.md》— 4.2" in answer.content


def test_citation_followup_extracts_sections_from_realistic_retrieval_text() -> None:
    messages = [
        _view_message(
            "经销商分级与考核管理制度.md",
            "4.2 A级经销商连续下降处置",
            "连续下降处置措施",
        ),
        _view_message("重点客户流失预警办法.md", "3.3 责任分工", "责任分工"),
        SimpleNamespace(
            type="view",
            content=json.dumps(
                {
                    "type": "react-agent",
                    "final_content": "超过标准折扣时必须履行分级审批，不得拆单。",
                    "citations": [
                        {
                            "sourceName": "汽车配件价格与折扣管理办法.md",
                            "excerpt": (
                                '1: "制度-4.1 申请信息": 申请材料。\n'
                                '1: "制度-4.2 超标准折扣审批": 分级审批。'
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        ),
    ]

    answer = build_citation_followup_answer(messages)

    assert answer is not None
    assert "汽车配件价格与折扣管理办法.md》— 4.2 超标准折扣审批" in answer.content


def test_citation_followup_recovers_document_from_generic_source_label() -> None:
    messages = [
        SimpleNamespace(
            type="view",
            content=json.dumps(
                {
                    "type": "react-agent",
                    "final_content": (
                        "根据《启明汽车配件销售有限公司 "
                        "经销商分级与考核管理制度》第4.2节回答。"
                    ),
                    "citations": [
                        {
                            "sourceName": "Knowledge Base",
                            "excerpt": (
                                '"启明汽车配件销售有限公司 '
                                "经销商分级与考核管理制度-4. 下降处置-"
                                '4.2 A级经销商连续下降处置": 正文'
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        ),
        _view_message("重点客户流失预警办法.md", "3.3 责任分工", "责任分工"),
        _view_message("汽车配件价格与折扣管理办法.md", "4.2 超标准折扣审批", "审批"),
    ]

    answer = build_citation_followup_answer(messages)

    assert answer is not None
    assert "经销商分级与考核管理制度.md》— 4.2" in answer.content


def test_citation_followup_prefers_primary_section_over_supplement() -> None:
    first_round = SimpleNamespace(
        type="view",
        content=json.dumps(
            {
                "type": "react-agent",
                "final_content": (
                    "根据《经销商分级与考核管理制度》第 4.2 节回答。"
                    "补充说明见第 3.2 节连续下降预警。"
                ),
                "citations": [
                    {
                        "sourceName": "Knowledge Base",
                        "excerpt": (
                            '"启明汽车配件销售有限公司 经销商分级与考核管理制度-'
                            '4. 下降处置-4.2 A级经销商连续下降处置": 正文'
                        ),
                    },
                    {
                        "sourceName": "Knowledge Base",
                        "excerpt": (
                            '"启明汽车配件销售有限公司 经销商分级与考核管理制度-'
                            '3. 预警-3.2 连续下降预警": 补充正文'
                        ),
                    },
                ],
            },
            ensure_ascii=False,
        ),
    )
    answer = build_citation_followup_answer(
        [
            first_round,
            _view_message("重点客户流失预警办法.md", "3.3 责任分工", "责任"),
            _view_message(
                "汽车配件价格与折扣管理办法.md",
                "4.2 超标准折扣审批",
                "审批",
            ),
        ]
    )

    assert answer is not None
    assert "经销商分级与考核管理制度.md》— 4.2" in answer.content
    assert "经销商分级与考核管理制度.md》— 3.2" not in answer.content


def test_citation_followup_uses_persisted_primary_section() -> None:
    messages = [
        SimpleNamespace(
            type="view",
            content=json.dumps(
                {
                    "final_content": "审批制度见引用。",
                    "citations": [
                        {
                            "sourceName": "汽车配件价格与折扣管理办法.md",
                            "excerpt": "4.1 申请信息\n4.2 超标准折扣审批",
                            "primarySection": "4.2",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        ),
        _view_message("重点客户流失预警办法.md", "3.3 责任分工", "责任"),
        _view_message("经销商分级与考核管理制度.md", "4.2 下降处置", "处置"),
    ]

    answer = build_citation_followup_answer(messages)

    assert answer is not None
    assert "汽车配件价格与折扣管理办法.md》— 4.2" in answer.content
