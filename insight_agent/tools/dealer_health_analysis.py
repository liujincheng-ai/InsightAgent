"""Deterministic dealer health scoring for the InsightAgent demo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from dbgpt.agent.resource.tool.base import tool

from .argument_schemas import DealerHealthArgs
from .db import PostgresReadOnlyExecutor, ReadOnlyQueryExecutor
from .metrics import (
    activity_score,
    change_rate,
    discount_score,
    gross_margin_score,
    health_risk_level,
    money,
    parse_quarter,
    percentage_point_change,
    rate,
    safe_rate,
    sales_change_score,
)

_MAX_TOP_N = 20
_RISK_ORDER = {"high": 0, "medium": 1, "low": 2}

_DEALER_HEALTH_SQL = """
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_level,
    COALESCE(SUM(s.sales_amount) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS current_sales,
    COALESCE(SUM(s.sales_amount) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS previous_sales,
    COALESCE(SUM(s.sales_amount) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS prior_year_sales,
    COALESCE(SUM(s.gross_profit) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS current_gross_profit,
    COALESCE(SUM(s.gross_profit) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS previous_gross_profit,
    COUNT(DISTINCT s.sale_date) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ) AS current_active_days,
    COUNT(DISTINCT s.sale_date) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ) AS previous_active_days,
    AVG(s.discount_rate) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ) AS current_average_discount
FROM dim_customer AS c
JOIN dim_region AS r ON r.region_id = c.region_id
LEFT JOIN fact_sales AS s
  ON s.customer_id = c.customer_id
 AND s.sale_date >= %s
 AND s.sale_date < %s
WHERE r.region_name = %s
  AND c.channel = '经销商'
GROUP BY c.customer_id, c.customer_name, c.customer_level
ORDER BY c.customer_name
"""


@dataclass
class DealerHealthAnalysisService:
    """Apply a transparent four-component score to a region's dealers."""

    executor: ReadOnlyQueryExecutor

    def analyze(
        self, region: str, current_quarter: str, top_n: int = 10
    ) -> dict[str, Any]:
        try:
            region = _non_empty(region, "区域")
            windows = parse_quarter(current_quarter)
            _validate_top_n(top_n)
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
        try:
            rows = self.executor.fetch_all(
                _DEALER_HEALTH_SQL,
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
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    current_start,
                    current_end,
                    prior_year_start,
                    current_end,
                    region,
                ],
            )
        except RuntimeError as exc:
            return _error("database_error", str(exc))

        if not rows:
            return _no_data(region, current_quarter)

        dealers = [_score_dealer(row) for row in rows]
        dealers.sort(
            key=lambda item: (
                _RISK_ORDER[item["risk_level"]],
                item["health_score"],
                -item["sales"]["current"],
                item["dealer_name"],
            )
        )
        return {
            "status": "success",
            "error": None,
            "region": region,
            "current_quarter": current_quarter.strip(),
            "baseline_quarter": _quarter_label(previous_start),
            "units": {
                "sales": "CNY",
                "rates": "decimal",
                "gross_margin_change": "percentage_points",
                "health_score": "points_0_to_100",
            },
            "data": {
                "scoring_version": "insight-agent-v1-demo",
                "dealer_count": len(dealers),
                "risk_counts": {
                    level: sum(item["risk_level"] == level for item in dealers)
                    for level in ("high", "medium", "low")
                },
                "dealers": dealers[:top_n],
                "interpretation": (
                    "健康度分段是 InsightAgent V1 可解释演示规则，不是行业标准；"
                    "风险结果用于调查优先级，不替代客户核验或等级调整审批。"
                ),
            },
            "evidence": [
                {
                    "id": "dealer_health_metrics",
                    "scope": {
                        "region": region,
                        "channel": "经销商",
                        "date_range": (
                            f"{prior_year_start.isoformat()} 至 "
                            f"{current_end.isoformat()}（结束日期不含）"
                        ),
                    },
                },
                {
                    "id": "dealer_policy",
                    "document": "经销商分级与考核管理制度.md",
                    "sections": ["3.1", "3.2", "4.2"],
                },
                {
                    "id": "discount_policy",
                    "document": "汽车配件价格与折扣管理办法.md",
                    "sections": ["2.2", "3.1", "4.2"],
                },
            ],
        }


def _score_dealer(row: dict[str, Any]) -> dict[str, Any]:
    current_sales = Decimal(str(row.get("current_sales") or 0))
    previous_sales = Decimal(str(row.get("previous_sales") or 0))
    prior_year_sales = Decimal(str(row.get("prior_year_sales") or 0))
    current_profit = Decimal(str(row.get("current_gross_profit") or 0))
    previous_profit = Decimal(str(row.get("previous_gross_profit") or 0))
    current_days = int(row.get("current_active_days") or 0)
    previous_days = int(row.get("previous_active_days") or 0)
    average_discount = row.get("current_average_discount")
    current_margin = safe_rate(current_profit, current_sales)
    previous_margin = safe_rate(previous_profit, previous_sales)

    components = {
        "sales_change": sales_change_score(current_sales, previous_sales),
        "purchase_activity": activity_score(current_days, previous_days),
        "discount": discount_score(average_discount),
        "gross_margin": gross_margin_score(current_margin, previous_margin),
    }
    score = sum(components.values())
    return {
        "dealer_id": row.get("customer_id"),
        "dealer_name": str(row.get("customer_name") or ""),
        "customer_level": str(row.get("customer_level") or ""),
        "sales": {
            "current": money(current_sales),
            "previous_quarter": money(previous_sales),
            "prior_year_same_quarter": money(prior_year_sales),
            "qoq_change_rate": rate(change_rate(current_sales, previous_sales)),
            "yoy_change_rate": rate(change_rate(current_sales, prior_year_sales)),
        },
        "activity": {
            "current_purchase_days": current_days,
            "previous_purchase_days": previous_days,
            "change_days": current_days - previous_days,
            "retention_rate": rate(safe_rate(current_days, previous_days)),
        },
        "average_discount_rate": rate(average_discount),
        "gross_margin": {
            "current": rate(current_margin),
            "previous_quarter": rate(previous_margin),
            "change_percentage_points": rate(
                percentage_point_change(current_margin, previous_margin)
            ),
        },
        "component_scores": components,
        "health_score": score,
        "risk_level": health_risk_level(score),
        "deductions": _deductions(components),
    }


def _deductions(components: dict[str, int]) -> list[dict[str, Any]]:
    maximums = {
        "sales_change": 40,
        "purchase_activity": 20,
        "discount": 20,
        "gross_margin": 20,
    }
    reasons = {
        "sales_change": "季度销售变化未达到满分区间",
        "purchase_activity": "活跃采购天数较基准期不足",
        "discount": "订单行平均折扣超过 8% 标准范围",
        "gross_margin": "加权毛利率较上一季度下降",
    }
    return [
        {
            "component": name,
            "score": score,
            "max_score": maximums[name],
            "deducted_points": maximums[name] - score,
            "reason": reasons[name],
        }
        for name, score in components.items()
        if score < maximums[name]
    ]


def _validate_top_n(value: Any) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_TOP_N
    ):
        raise ValueError(f"top_n 必须是 1 到 {_MAX_TOP_N} 的整数")


def _non_empty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}必须是非空文本")
    return value.strip()


def _quarter_label(start: Any) -> str:
    return f"{start.year}Q{((start.month - 1) // 3) + 1}"


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {"code": code, "message": message},
        "data": None,
        "evidence": [],
    }


def _no_data(region: str, current_quarter: str) -> dict[str, Any]:
    return {
        "status": "no_data",
        "error": None,
        "region": region,
        "current_quarter": current_quarter,
        "data": None,
        "evidence": [],
    }


@tool(
    "dealer_health_analysis_tool",
    description=(
        "按销售变化、采购活跃天数、订单行平均折扣和加权毛利率四项规则，计算明确"
        "区域经销商在指定季度的 0 到 100 健康分、风险等级和扣分原因。适用于经销商"
        "健康度、风险排序和干预优先级；不用于具体品类销售归因或普通客户流失名单。"
    ),
    args_schema=DealerHealthArgs,
    validate_args=True,
)
def dealer_health_analysis_tool(
    region: str, current_quarter: str, top_n: int = 10
) -> dict[str, Any]:
    """Return deterministic and explainable dealer health scores."""

    return DealerHealthAnalysisService(PostgresReadOnlyExecutor()).analyze(
        region, current_quarter, top_n
    )
