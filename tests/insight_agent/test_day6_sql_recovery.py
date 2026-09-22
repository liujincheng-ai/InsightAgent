"""Day 6 regression tests for bounded SQL recovery and safe observations."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from dbgpt_app.insight_agent.sql_error import (
    classify_sql_error,
    sanitize_sql_error,
)
from dbgpt_app.openapi.api_v1.tools.sql_query import make_sql_query
from insight_agent.agent.domain_policy import (
    format_verified_sql_answer,
    validate_insight_sql,
)


class DriverError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DriverError('syntax error at or near "FROM"', "42601"), "SYNTAX_ERROR"),
        (DriverError('relation "missing" does not exist', "42P01"), "TABLE_NOT_FOUND"),
        (DriverError('column "missing" does not exist', "42703"), "COLUMN_NOT_FOUND"),
        (
            DriverError("invalid input syntax for type date", "22007"),
            "TYPE_OR_DATE_ERROR",
        ),
        (
            DriverError('column reference "id" is ambiguous', "42702"),
            "AMBIGUOUS_COLUMN",
        ),
        (
            DriverError("must appear in the GROUP BY clause", "42803"),
            "SYNTAX_ERROR",
        ),
        (
            DriverError("permission denied for table fact_sales", "42501"),
            "PERMISSION_DENIED",
        ),
        (TimeoutError("statement timeout"), "TIMEOUT"),
        (RuntimeError("driver returned an unfamiliar failure"), "UNKNOWN_SQL_ERROR"),
    ],
)
def test_day6_classifies_eight_sql_error_types(
    error: BaseException, expected: str
) -> None:
    assert classify_sql_error(error).error_code == expected


def test_day6_sql_error_sanitizer_removes_connection_details() -> None:
    raw = (
        "postgresql://alice:secret@db.internal:5432/insight "
        "password=hunter2 host=10.0.0.8 user=alice "
        "C:\\Users\\alice\\project\\config.toml LINE 1: SELECT * FROM secret"
    )
    sanitized = sanitize_sql_error(raw)
    assert "secret" not in sanitized
    assert "hunter2" not in sanitized
    assert "10.0.0.8" not in sanitized
    assert "alice\\project" not in sanitized
    assert "SELECT *" not in sanitized


@pytest.mark.parametrize(
    "sql",
    [
        """
        SELECT r.region_name, t.q1_sales
        FROM (SELECT fs.region_id, SUM(fs.sales_amount) q1_sales
              FROM fact_sales fs GROUP BY fs.region_id) t
        JOIN dim_region r ON r.region_id = t.region_id
        """,
        """
        WITH t AS (
            SELECT fs.region_id, SUM(fs.sales_amount) q1_sales
            FROM fact_sales fs GROUP BY fs.region_id
        )
        SELECT r.region_name, t.q1_sales
        FROM t JOIN dim_region r ON r.region_id = t.region_id
        """,
        """
        SELECT dim_region.region_name, SUM(fact_sales.sales_amount)
        FROM fact_sales JOIN dim_region
          ON fact_sales.region_id = dim_region.region_id
        GROUP BY dim_region.region_name
        """,
        """
        SELECT public.dim_region.region_name, SUM(public.fact_sales.sales_amount)
        FROM public.fact_sales JOIN public.dim_region
          ON public.fact_sales.region_id = public.dim_region.region_id
        GROUP BY public.dim_region.region_name
        """,
    ],
)
def test_day6_alias_preflight_accepts_valid_join_shapes(sql: str) -> None:
    result = validate_insight_sql(
        sql,
        "2026 年第二季度哪个区域销售额环比下降最多？",
    )
    assert not any("未在 FROM/JOIN 中定义的别名" in item for item in result.errors)


def test_day6_sql_tool_allows_only_one_corrective_attempt() -> None:
    class FailingConnector:
        calls = 0

        def run(self, _sql: str):
            self.calls += 1
            raise DriverError("syntax error", "42601")

    state = {"database_name": "insight_agent", "user_input": "查询 2026 年销售额"}
    connector = FailingConnector()
    query = make_sql_query(state, connector)

    first = json.loads(query("SELECT amount FROM first_attempt"))
    second = json.loads(query("SELECT amount FROM corrected_attempt"))
    third = json.loads(query("SELECT amount FROM third_attempt"))

    assert first["error_code"] == "SYNTAX_ERROR"
    assert first["retryable"] is True
    assert first["retry_budget_remaining"] == 1
    assert second["retryable"] is False
    assert second["retry_budget_remaining"] == 0
    assert third["error_code"] == "SQL_RETRY_LIMIT_REACHED"
    assert connector.calls == 2


def test_day6_duplicate_failed_sql_exhausts_retry_budget_without_execution() -> None:
    class FailingConnector:
        calls = 0

        def run(self, _sql: str):
            self.calls += 1
            raise DriverError('column "bad" does not exist', "42703")

    state = {"database_name": "insight_agent", "user_input": "查询 2026 年销售额"}
    connector = FailingConnector()
    query = make_sql_query(state, connector)
    sql = "SELECT bad FROM fact_sales"

    assert json.loads(query(sql))["retryable"] is True
    duplicate = json.loads(query("  SELECT   bad FROM fact_sales;  "))

    assert duplicate["error_code"] == "SQL_RETRY_LIMIT_REACHED"
    assert connector.calls == 1


def test_day6_permission_failure_cannot_be_retried() -> None:
    class PermissionConnector:
        calls = 0

        def run(self, _sql: str):
            self.calls += 1
            raise DriverError("permission denied password=do-not-leak", "42501")

    state = {"database_name": "insight_agent", "user_input": "查询 2026 年销售额"}
    connector = PermissionConnector()
    query = make_sql_query(state, connector)

    first = json.loads(query("SELECT amount FROM protected_view"))
    blocked = json.loads(query("SELECT amount FROM another_view"))

    assert first["error_code"] == "PERMISSION_DENIED"
    assert first["retryable"] is False
    assert "do-not-leak" not in json.dumps(first, ensure_ascii=False)
    assert blocked["error_code"] == "SQL_RETRY_LIMIT_REACHED"
    assert connector.calls == 1


def test_day6_verified_sql_presenter_keeps_observation_numbers() -> None:
    answer = format_verified_sql_answer(
        "华东 2026 Q2 销售额的环比和同比是多少？",
        {
            "columns": ["q2_2026_sales", "q1_2026_sales", "q2_2025_sales"],
            "rows": [[15228822.09, 15727133.31, 14952425.25]],
            "row_count": 1,
        },
    )

    assert answer is not None
    assert "15,228,822.09" in answer
    assert "-3.17%" in answer
    assert "1.85%" in answer
    assert "15,288,822.09" not in answer


def test_day6_verified_sql_presenter_accepts_compact_period_aliases() -> None:
    answer = format_verified_sql_answer(
        "华东区域 2026 Q2 销售额是多少？环比和同比分别是多少？",
        {
            "columns": ["q2_2026", "q1_2026", "q2_2025"],
            "rows": [[15228822.09, 15727133.31, 14952425.25]],
        },
    )
    assert answer is not None
    assert "15,228,822.09" in answer
    assert "-3.17%" in answer and "1.85%" in answer


def test_week5_verified_sql_presenter_calculates_weighted_metric_changes() -> None:
    answer = format_verified_sql_answer(
        "比较 2026Q2 与 2026Q1 折扣率和加权毛利率变化",
        {
            "columns": [
                "period",
                "avg_line_discount_rate",
                "weighted_gross_margin",
            ],
            "rows": [
                ["Q1_2026", Decimal("0.0669"), Decimal("0.2891")],
                ["Q2_2026", Decimal("0.1087"), Decimal("0.2613")],
            ],
        },
    )
    assert answer is not None
    assert "+4.1800 个百分点" in answer
    assert "-2.7800 个百分点" in answer
    assert "总毛利除以总销售额" in answer


def test_day6_channel_contribution_requires_explicit_denominator() -> None:
    question = "华东刹车系统 2026Q2 销售下降主要来自哪个渠道？给出贡献率。"
    missing_rate = validate_insight_sql(
        "SELECT f.channel, SUM(f.sales_amount) AS q2_sales "
        "FROM fact_sales f JOIN dim_region r ON f.region_id=r.region_id "
        "JOIN dim_product p ON f.product_id=p.product_id "
        "WHERE r.region_name='华东' AND p.category='刹车系统' "
        "AND f.sale_date>=DATE '2026-04-01' GROUP BY f.channel",
        question,
    )
    assert not missing_rate.valid
    assert any("贡献率必须在 SQL 中显式计算" in item for item in missing_rate.errors)

    with_rate = validate_insight_sql(
        "SELECT f.channel, SUM(f.sales_amount) AS q2_sales, "
        "0.7489 AS contribution_rate FROM fact_sales f "
        "JOIN dim_region r ON f.region_id=r.region_id "
        "JOIN dim_product p ON f.product_id=p.product_id "
        "WHERE r.region_name='华东' AND p.category='刹车系统' "
        "AND f.sale_date>=DATE '2026-04-01' GROUP BY f.channel",
        question,
    )
    assert with_rate.valid


@pytest.mark.parametrize(
    ("question", "result", "expected"),
    [
        (
            "比较华东与华南销售额环比变化率。",
            {
                "columns": ["region_name", "q2_sales", "q1_sales"],
                "rows": [
                    ["华东", 1087378.79, 1615224.29],
                    ["华南", 1761223.1, 1608329.54],
                ],
            },
            ("华东：环比 -32.68%", "华南：环比 9.51%"),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["q1_margin_pct", "q2_margin_pct"],
                "rows": [[28.9089938, 26.1250856]],
            },
            ("变化：-2.78 个百分点",),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["q1_gross_margin_pct", "q2_gross_margin_pct"],
                "rows": [[28.9089938, 26.1250856]],
            },
            ("变化：-2.78 个百分点",),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["q2_margin", "q1_margin"],
                "rows": [[26.1250856, 28.9089938]],
            },
            ("变化：-2.78 个百分点",),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["period", "gross_margin"],
                "rows": [["2026 Q2", 0.261250856], ["2026 Q1", 0.289089938]],
            },
            ("2026 Q1 加权毛利率：28.91%", "变化：-2.78 个百分点"),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["qtr", "sales_amt", "gross_profit", "gross_margin"],
                "rows": [
                    [1, 1615224.29, 466945.09, Decimal("0.289089938")],
                    [2, 1087378.79, 284078.64, Decimal("0.261250856")],
                ],
            },
            ("2026 Q1 加权毛利率：28.91%", "变化：-2.78 个百分点"),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["q1_gp", "q1_sales", "q2_gp", "q2_sales"],
                "rows": [[466945.09, 1615224.29, 284078.64, 1087378.79]],
            },
            ("2026 Q1 加权毛利率：28.91%", "变化：-2.78 个百分点"),
        ),
        (
            "加权毛利率变化了多少个百分点？",
            {
                "columns": ["q1_sales", "q1_profit", "q2_sales", "q2_profit"],
                "rows": [[1615224.29, 466945.09, 1087378.79, 284078.64]],
            },
            ("2026 Q1 加权毛利率：28.91%", "变化：-2.78 个百分点"),
        ),
        (
            "销售下降主要来自哪个渠道？给出贡献率。",
            {
                "columns": ["channel", "diff"],
                "rows": [
                    ["经销商", -395312.25],
                    ["直营网点", -76919.69],
                    ["电商", -41283.32],
                    ["汽修连锁", -20760.53],
                    ["大客户直供", 6430.29],
                ],
            },
            ("经销商", "395,312.25", "74.89%"),
        ),
        (
            "销售下降主要来自哪个渠道？给出贡献率。",
            {
                "columns": ["channel", "q2_sales", "q1_sales"],
                "rows": [
                    ["经销商", 324352.47, 719664.72],
                    ["直营网点", 187501.18, 264420.87],
                    ["电商", 153562.73, 194846.05],
                    ["汽修连锁", 246296.67, 267057.2],
                    ["大客户直供", 175665.74, 169235.45],
                ],
            },
            ("经销商", "395,312.25", "74.89%"),
        ),
        (
            "哪个品类销售额环比下降最多？下降比例是多少？",
            {
                "columns": ["category", "q2_sales", "q1_sales", "change_amount"],
                "rows": [["刹车系统", 1087378.79, 1615224.29, -527845.5]],
            },
            ("刹车系统", "环比变化率：-32.68%", "降幅：32.68%"),
        ),
        (
            "销售下降主要来自哪个渠道？给出贡献率。",
            {
                "columns": ["channel", "change_amount"],
                "rows": [
                    ["经销商", -395312.25],
                    ["直营网点", -76919.69],
                    ["电商", -41283.32],
                    ["汽修连锁", -20760.53],
                    ["大客户直供", 6430.29],
                ],
            },
            ("经销商", "395,312.25", "74.89%"),
        ),
        (
            "下降金额最大的客户是谁？",
            {
                "columns": ["customer_name", "decline_amount"],
                "rows": [["华东核心经销商三号", -158586.31]],
            },
            ("华东核心经销商三号下降 158,586.31 元",),
        ),
        (
            "下降金额最大的客户是谁？",
            {
                "columns": ["customer_name", "q2_sales", "q1_sales", "change_amount"],
                "rows": [["华东核心经销商三号", 15235.94, 173822.25, -158586.31]],
            },
            ("华东核心经销商三号下降 158,586.31 元",),
        ),
    ],
)
def test_day6_verified_sql_presenter_derives_requested_metrics(
    question: str, result: dict, expected: tuple[str, ...]
) -> None:
    answer = format_verified_sql_answer(question, result)
    assert answer is not None
    assert all(item in answer for item in expected)
