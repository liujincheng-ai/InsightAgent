"""Deterministic sales-decline diagnosis for the InsightAgent demo."""
# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbgpt.agent.resource.tool.base import tool

from .argument_schemas import SalesDiagnosisArgs
from .db import PostgresReadOnlyExecutor, ReadOnlyQueryExecutor
from .metrics import money, parse_quarter, rate, safe_rate

_MAX_TOP_N = 20

_SUMMARY_SQL = """
SELECT
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS current_sales,
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS previous_sales,
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS prior_year_sales,
    COALESCE(SUM(s.gross_profit) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS current_gross_profit,
    COALESCE(SUM(s.gross_profit) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS previous_gross_profit
FROM fact_sales AS s
JOIN dim_region AS r ON r.region_id = s.region_id
JOIN dim_product AS p ON p.product_id = s.product_id
WHERE r.region_name = %s
  AND p.category = %s
  AND s.sale_date >= %s
  AND s.sale_date < %s
"""

_CONTRIBUTION_SQL = """
SELECT
    {dimension} AS dimension_name,
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS current_sales,
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS previous_sales
FROM fact_sales AS s
JOIN dim_region AS r ON r.region_id = s.region_id
JOIN dim_product AS p ON p.product_id = s.product_id
WHERE r.region_name = %s
  AND p.category = %s
  AND s.sale_date >= %s
  AND s.sale_date < %s
GROUP BY {dimension}
ORDER BY (COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0)
          - COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0)) ASC,
         {dimension}
LIMIT %s
"""

_NATIONAL_SQL = """
SELECT
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS current_sales,
    COALESCE(SUM(s.sales_amount) FILTER (WHERE s.sale_date >= %s AND s.sale_date < %s), 0) AS previous_sales
FROM fact_sales AS s
JOIN dim_product AS p ON p.product_id = s.product_id
WHERE p.category = %s
  AND s.sale_date >= %s
  AND s.sale_date < %s
"""


@dataclass
class SalesDiagnosisService:
    """Run a bounded sequence of fixed aggregate queries."""

    executor: ReadOnlyQueryExecutor

    def diagnose(
        self, region: str, category: str, current_quarter: str, top_n: int = 5
    ) -> dict[str, Any]:
        region = _non_empty(region, "区域")
        category = _non_empty(category, "品类")
        if (
            isinstance(top_n, bool)
            or not isinstance(top_n, int)
            or not 1 <= top_n <= _MAX_TOP_N
        ):
            return _error("invalid_input", f"top_n 必须是 1 到 {_MAX_TOP_N} 的整数")
        try:
            windows = parse_quarter(current_quarter)
        except ValueError as exc:
            return _error("invalid_input", str(exc))
        (
            current_start,
            current_end,
            previous_start,
            previous_end,
            prior_year_start,
            prior_year_end,
        ) = windows
        scope_start, scope_end = min(previous_start, prior_year_start), current_end
        try:
            summary_rows = self.executor.fetch_all(
                _SUMMARY_SQL,
                [
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    prior_year_start,
                    prior_year_end,
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    region,
                    category,
                    scope_start,
                    scope_end,
                ],
            )
            if not summary_rows:
                return _no_data(region, category, current_quarter)
            summary = summary_rows[0]
            current_sales = money(summary.get("current_sales"))
            previous_sales = money(summary.get("previous_sales"))
            prior_year_sales = money(summary.get("prior_year_sales"))
            if current_sales == previous_sales == prior_year_sales == 0:
                return _no_data(region, category, current_quarter)
            product_rows = self._contributions(
                "p.product_name",
                region,
                category,
                current_start,
                current_end,
                previous_start,
                previous_end,
                scope_start,
                scope_end,
                top_n,
            )
            channel_rows = self._contributions(
                "s.channel",
                region,
                category,
                current_start,
                current_end,
                previous_start,
                previous_end,
                scope_start,
                scope_end,
                top_n,
            )
            national_rows = self.executor.fetch_all(
                _NATIONAL_SQL,
                [
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    category,
                    previous_start,
                    current_end,
                ],
            )
        except RuntimeError as exc:
            return _error("database_error", str(exc))

        current_margin = safe_rate(
            summary.get("current_gross_profit", 0), current_sales
        )
        previous_margin = safe_rate(
            summary.get("previous_gross_profit", 0), previous_sales
        )
        national = national_rows[0] if national_rows else {}
        national_current = money(national.get("current_sales"))
        national_previous = money(national.get("previous_sales"))
        decline_amount = max(previous_sales - current_sales, 0)
        result = {
            "status": "success",
            "error": None,
            "region": region,
            "category": category,
            "current_quarter": current_quarter.strip(),
            "units": {
                "sales": "CNY",
                "rates": "decimal",
                "gross_margin_change": "percentage_points",
            },
            "sales": {
                "current": current_sales,
                "previous_quarter": previous_sales,
                "prior_year_same_quarter": prior_year_sales,
                "qoq_change_amount": money(current_sales - previous_sales),
                "qoq_change_rate": rate(
                    safe_rate(current_sales - previous_sales, previous_sales)
                ),
                "yoy_change_amount": money(current_sales - prior_year_sales),
                "yoy_change_rate": rate(
                    safe_rate(current_sales - prior_year_sales, prior_year_sales)
                ),
            },
            "gross_margin": {
                "current": rate(current_margin),
                "previous_quarter": rate(previous_margin),
                "change_percentage_points": rate(
                    (current_margin - previous_margin) * 100
                    if current_margin is not None and previous_margin is not None
                    else None
                ),
            },
            "top_decline_products": _format_contributions(product_rows, decline_amount),
            "channel_contributions": _format_contributions(
                channel_rows, decline_amount
            ),
            "regional_vs_national": {
                "region_qoq_change_rate": rate(
                    safe_rate(current_sales - previous_sales, previous_sales)
                ),
                "national_qoq_change_rate": rate(
                    safe_rate(national_current - national_previous, national_previous)
                ),
                "national_current_sales": national_current,
                "national_previous_sales": national_previous,
            },
            "evidence": [
                {
                    "id": "sales_summary",
                    "scope": _scope(region, category, previous_start, current_end),
                },
                {
                    "id": "product_contribution",
                    "scope": _scope(region, category, previous_start, current_end),
                },
                {
                    "id": "channel_contribution",
                    "scope": _scope(region, category, previous_start, current_end),
                },
                {
                    "id": "national_category_trend",
                    "scope": _scope("全国", category, previous_start, current_end),
                },
            ],
        }
        result["data"] = {
            key: result[key]
            for key in (
                "sales",
                "gross_margin",
                "top_decline_products",
                "channel_contributions",
                "regional_vs_national",
            )
        }
        return result

    def _contributions(
        self,
        dimension: str,
        region: str,
        category: str,
        current_start: Any,
        current_end: Any,
        previous_start: Any,
        previous_end: Any,
        scope_start: Any,
        scope_end: Any,
        top_n: int,
    ) -> list[dict[str, Any]]:
        query = _CONTRIBUTION_SQL.format(dimension=dimension)
        return self.executor.fetch_all(
            query,
            [
                current_start,
                current_end,
                previous_start,
                previous_end,
                region,
                category,
                scope_start,
                scope_end,
                current_start,
                current_end,
                previous_start,
                previous_end,
                top_n,
            ],
        )


def _format_contributions(
    rows: list[dict[str, Any]], total_decline: float
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        current_sales = money(row.get("current_sales"))
        previous_sales = money(row.get("previous_sales"))
        change_amount = money(current_sales - previous_sales)
        if change_amount >= 0:
            continue
        result.append(
            {
                "name": str(row.get("dimension_name", "")),
                "current_sales": current_sales,
                "previous_sales": previous_sales,
                "qoq_change_amount": change_amount,
                "decline_contribution_rate": rate(
                    safe_rate(-change_amount, total_decline)
                ),
            }
        )
    return result


def _scope(region: str, category: str, start: Any, end: Any) -> dict[str, str]:
    return {
        "region": region,
        "category": category,
        "date_range": f"{start.isoformat()} 至 {end.isoformat()}（结束日期不含）",
    }


def _non_empty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}必须是非空文本")
    return value.strip()


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {"code": code, "message": message},
        "data": None,
        "evidence": [],
    }


def _no_data(region: str, category: str, current_quarter: str) -> dict[str, Any]:
    return {
        "status": "no_data",
        "error": None,
        "region": region,
        "category": category,
        "current_quarter": current_quarter,
        "data": None,
        "evidence": [],
    }


@tool(
    "sales_diagnosis_tool",
    description=(
        "诊断明确区域、汽车配件品类和季度的销售变化原因，返回环比、同比、加权"
        "毛利率、产品贡献、渠道贡献和全国趋势。适用于销售下滑归因、增长归因和"
        "渠道贡献分析；不用于客户流失名单、经销商健康评分或普通销售额查询。"
    ),
    args_schema=SalesDiagnosisArgs,
    validate_args=True,
)
def sales_diagnosis_tool(
    region: str, category: str, current_quarter: str, top_n: int = 5
) -> dict[str, Any]:
    """Diagnose a regional category's sales decline with fixed read-only SQL."""

    try:
        region = _non_empty(region, "区域")
        category = _non_empty(category, "品类")
    except ValueError as exc:
        return _error("invalid_input", str(exc))
    return SalesDiagnosisService(PostgresReadOnlyExecutor()).diagnose(
        region, category, current_quarter, top_n
    )
