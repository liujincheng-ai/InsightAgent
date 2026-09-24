"""Week 1 semantic-layer, dataset and deterministic scorer tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from insight_agent.agent.domain_policy import (
    build_database_agent_prompt,
    validate_insight_sql,
)
from insight_agent.evaluation.semantic_metrics import (
    extract_actual_tables,
    result_matches,
    score_semantic_case,
)
from insight_agent.evaluation.semantic_schemas import (
    load_semantic_datasets,
    validate_semantic_datasets,
)
from insight_agent.semantic import build_semantic_context, get_semantic_profile

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "insight_agent" / "evaluation" / "dataset"


def _canonical_sha256(path: Path) -> str:
    """Hash dataset content independently of the checkout's line endings."""
    canonical_bytes = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical_bytes).hexdigest()


def test_semantic_dataset_has_frozen_18_8_4_contract() -> None:
    datasets = load_semantic_datasets(DATASET_DIR)
    assert validate_semantic_datasets(datasets) == []
    assert {split: len(dataset["cases"]) for split, dataset in datasets.items()} == {
        "dev": 18,
        "test": 8,
        "challenge": 4,
    }
    assert sum(len(dataset["cases"]) for dataset in datasets.values()) == 30


def test_semantic_dataset_fingerprints_are_frozen() -> None:
    expected = {
        "sql_semantic_dev.json": (
            "a912a70918cfcd838f77903895ca3dcc93bd29f09e099768edd3102fc5a23728"
        ),
        "sql_semantic_test.json": (
            "2d35eedb8000de6cb073bd23d91d7e6de70cf300fba5061a7509910c5f7cd647"
        ),
        "sql_semantic_challenge.json": (
            "562ad043ad7bb0c8550b189de56d5e13fddb94a9fd8dc162738e61da7dc49b4d"
        ),
    }
    for filename, digest in expected.items():
        assert _canonical_sha256(DATASET_DIR / filename) == digest


def test_profiles_isolate_schema_and_glossary_content() -> None:
    question = "华东刹车系统 2026 Q2 的销售额和毛利率是多少？"
    baseline = build_semantic_context(question, "baseline").context
    comments = build_semantic_context(question, "comments").context
    glossary = build_semantic_context(question, "glossary").context
    combined = build_semantic_context(question, "combined").context
    assert "不注入新增业务语义" in baseline
    assert "fact_sales.region_id" in comments
    assert "SUM(fact_sales.sales_amount)" not in comments
    assert "SUM(fact_sales.sales_amount)" in glossary
    assert "fact_sales.region_id" not in glossary
    assert "SUM(fact_sales.sales_amount)" in combined
    assert "fact_sales.region_id" in combined


def test_high_risk_ambiguity_requires_clarification_before_sql() -> None:
    decision = build_semantic_context("华东最近表现怎么样？", "combined")
    assert decision.requires_clarification
    assert len(decision.clarification_questions) == 2
    prompt = build_database_agent_prompt(
        "fact_sales", "华东最近表现怎么样？", "combined"
    )
    assert "不得执行 sql_query" in prompt
    assert "请确认要比较销售额、销量、毛利率还是其他指标" in prompt
    assert "请确认具体时间范围" in prompt


def test_invalid_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="INSIGHT_SEMANTIC_PROFILE"):
        get_semantic_profile("unknown")


def test_markdown_result_comparison_rejects_day7_wrong_denominator() -> None:
    gold = {
        "columns": ["channel", "decline_amount", "contribution_pct"],
        "rows": [["经销商", 395312.25, 74.8917]],
    }
    wrong = extract_actual_tables(
        [],
        "| channel | decline_amount | contribution_pct |\n"
        "| --- | --- | --- |\n| 经销商 | 395312.25 | 73.99 |",
    )
    correct = extract_actual_tables(
        [],
        "| channel | decline_amount | contribution_pct |\n"
        "| --- | --- | --- |\n| 经销商 | 395312.25 | 74.8917 |",
    )
    assert not result_matches(gold, wrong, 0.02)
    assert result_matches(gold, correct, 0.02)


def test_answer_fact_completeness_is_separate_from_sql_result() -> None:
    case = {
        "requires_clarification": False,
        "numeric_tolerance": 0.02,
        "gold_result": {
            "columns": ["q1_margin_pct", "q2_margin_pct", "change_pp"],
            "rows": [[28.91, 26.13, -2.78]],
        },
    }
    table = (
        "| q1_margin_pct | q2_margin_pct | change_pp |\n| --- | --- | --- |\n"
        "| 28.91 | 26.13 | -2.78 |"
    )
    events = [{"type": "step.chunk", "content": table}]
    actual = {
        "actual_answer": "毛利率下降 2.78 个百分点。",
        "actual_sql": ["SELECT ..."],
        "sql_executed": True,
        "error": None,
    }
    verdict = score_semantic_case(case, actual, events)
    assert verdict["components"]["result_set"]
    assert not verdict["components"]["answer_facts"]
    assert verdict["failure_category"] == "answer_fact_completeness"


def test_views_are_read_only_semantic_aggregations() -> None:
    sql = (ROOT / "insight_agent" / "database" / "views.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE OR REPLACE VIEW insight_quarterly_sales" in sql
    assert "SUM(f.gross_profit) / NULLIF(SUM(f.sales_amount), 0)" in sql
    apply_code = (ROOT / "insight_agent" / "database" / "apply_views.py").read_text(
        encoding="utf-8"
    )
    assert "GRANT SELECT ON insight_quarterly_sales" in apply_code
    assert "sql.Identifier(role_name)" in apply_code


def test_week1_delivery_documents_disclose_metrics_and_failures() -> None:
    required = {
        "WEEK1.md": "Text-to-SQL 语义正确性",
        "WEEK1_PROGRESS.md": "27/30",
        "WEEK1_ACCEPTANCE_REPORT.md": "三个最终失败",
        "WEEK1_INTERVIEW_GUIDE_DETAILED.md": "三个失败怎么回答",
        "RESUME_PRIVATE_AGENT_LATEST.md": "私企 Agent 开发岗",
        "RESUME_ENTERPRISE_AI_LATEST.md": "央国企 AI 岗",
    }
    for filename, marker in required.items():
        content = (ROOT / "insight_agent" / filename).read_text(encoding="utf-8")
        assert marker in content

    evaluation_doc = ROOT / "docs" / "evaluation" / "week1_text2sql.md"
    assert "严格结果集" in evaluation_doc.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("question", "sql", "message"),
    [
        (
            "华东 2026 Q2 销量最高的品类是哪一个？",
            "SELECT SUM(f.sales_amount) FROM fact_sales f JOIN dim_region r "
            "ON r.region_id=f.region_id JOIN dim_product p ON p.product_id="
            "f.product_id WHERE r.region_name='华东' AND 2026=2026",
            "销量必须使用 SUM(quantity)",
        ),
        (
            "华东刹车系统 2026 Q2 毛利率是多少？",
            "SELECT SUM(f.gross_profit),SUM(f.sales_amount) FROM fact_sales f "
            "JOIN dim_region r ON r.region_id=f.region_id JOIN dim_product p ON "
            "p.product_id=f.product_id WHERE r.region_name='华东' AND "
            "p.category='刹车系统' AND 2026=2026",
            "毛利率必须使用",
        ),
        (
            "2026 Q2 各区域有多少家活跃经销商？",
            "SELECT r.region_name,COUNT(f.customer_id) FROM fact_sales f JOIN "
            "dim_region r ON r.region_id=f.region_id WHERE f.channel='经销商' "
            "AND 2026=2026 GROUP BY r.region_name",
            "COUNT(DISTINCT customer_id)",
        ),
    ],
)
def test_semantic_preflight_rejects_executable_but_wrong_sql(
    question: str, sql: str, message: str
) -> None:
    result = validate_insight_sql(sql, question)
    assert not result.valid
    assert any(message in error for error in result.errors)
