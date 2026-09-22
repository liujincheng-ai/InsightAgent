"""Deterministic customer purchase-loss warning analysis for InsightAgent."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from dbgpt.agent.resource.tool.base import tool

from .argument_schemas import CustomerLossArgs
from .db import PostgresReadOnlyExecutor, ReadOnlyQueryExecutor
from .metrics import money, parse_quarter, rate, safe_rate

_MAX_TOP_N = 20

_CUSTOMER_COMPARISON_SQL = """
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_level,
    c.channel,
    COALESCE(SUM(s.sales_amount) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS current_sales,
    COALESCE(SUM(s.sales_amount) FILTER (
        WHERE s.sale_date >= %s AND s.sale_date < %s
    ), 0) AS previous_sales
FROM fact_sales AS s
JOIN dim_customer AS c ON c.customer_id = s.customer_id
JOIN dim_region AS r ON r.region_id = s.region_id
JOIN dim_product AS p ON p.product_id = s.product_id
WHERE r.region_name = %s
  AND p.category = %s
  AND s.sale_date >= %s
  AND s.sale_date < %s
GROUP BY c.customer_id, c.customer_name, c.customer_level, c.channel
ORDER BY c.customer_name
"""


@dataclass
class CustomerLossAnalysisService:
    """Compare customer purchases with the immediately preceding quarter."""

    executor: ReadOnlyQueryExecutor

    def analyze(
        self,
        region: str,
        category: str,
        current_quarter: str,
        decline_threshold: float = 0.5,
        top_n: int = 10,
    ) -> dict[str, Any]:
        try:
            region = _non_empty(region, "区域")
            category = _non_empty(category, "品类")
            windows = parse_quarter(current_quarter)
            threshold = _validate_threshold(decline_threshold)
            _validate_top_n(top_n)
        except ValueError as exc:
            return _error("invalid_input", str(exc))

        current_start, current_end, previous_start, previous_end, _, _ = windows
        try:
            rows = self.executor.fetch_all(
                _CUSTOMER_COMPARISON_SQL,
                [
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    region,
                    category,
                    previous_start,
                    current_end,
                ],
            )
        except RuntimeError as exc:
            return _error("database_error", str(exc))

        if not rows:
            return _no_data(region, category, current_quarter)

        total_current = sum(
            (Decimal(str(row.get("current_sales") or 0)) for row in rows),
            Decimal("0"),
        )
        total_previous = sum(
            (Decimal(str(row.get("previous_sales") or 0)) for row in rows),
            Decimal("0"),
        )
        total_decline = max(total_previous - total_current, Decimal("0"))
        classified = [_classify_customer(row, threshold, total_decline) for row in rows]
        risk_customers = [
            customer
            for customer in classified
            if customer["risk_status"] in {"suspected_churn", "significant_decline"}
        ]
        risk_customers.sort(
            key=lambda item: (-item["decline_amount"], item["customer_name"])
        )

        return {
            "status": "success",
            "error": None,
            "region": region,
            "category": category,
            "current_quarter": current_quarter.strip(),
            "baseline_quarter": _quarter_label(previous_start),
            "units": {"sales": "CNY", "rates": "decimal"},
            "data": {
                "decline_threshold": rate(threshold),
                "summary": {
                    "current_sales": money(total_current),
                    "previous_sales": money(total_previous),
                    "net_decline_amount": money(total_decline),
                    "risk_customer_count": len(risk_customers),
                    "suspected_churn_count": sum(
                        item["risk_status"] == "suspected_churn" for item in classified
                    ),
                    "significant_decline_count": sum(
                        item["risk_status"] == "significant_decline"
                        for item in classified
                    ),
                    "new_customer_count": sum(
                        item["risk_status"] == "new_customer" for item in classified
                    ),
                },
                "risk_customers": risk_customers[:top_n],
                "interpretation": (
                    "结果仅表示停止采购或大幅下滑预警，不代表客户已确认流失；"
                    "须按制度核对沟通、库存、价格和售后事实。"
                ),
            },
            "evidence": [
                {
                    "id": "customer_quarter_comparison",
                    "scope": {
                        "region": region,
                        "category": category,
                        "date_range": (
                            f"{previous_start.isoformat()} 至 "
                            f"{current_end.isoformat()}（结束日期不含）"
                        ),
                    },
                },
                {
                    "id": "customer_loss_policy",
                    "document": "重点客户流失预警办法.md",
                    "sections": ["1.2", "2.1", "2.2", "3.1"],
                },
            ],
        }


def _classify_customer(
    row: dict[str, Any], threshold: Decimal, total_decline: Decimal
) -> dict[str, Any]:
    current = Decimal(str(row.get("current_sales") or 0))
    previous = Decimal(str(row.get("previous_sales") or 0))
    decline = previous - current
    decline_ratio = safe_rate(decline, previous)
    if previous > 0 and current == 0:
        risk_status = "suspected_churn"
    elif previous > 0 and current > 0 and decline / previous >= threshold:
        risk_status = "significant_decline"
    elif previous == 0 and current > 0:
        risk_status = "new_customer"
    else:
        risk_status = "stable_or_growing"
    level = str(row.get("customer_level") or "")
    return {
        "customer_id": row.get("customer_id"),
        "customer_name": str(row.get("customer_name") or ""),
        "customer_level": level,
        "channel": str(row.get("channel") or ""),
        "previous_sales": money(previous),
        "current_sales": money(current),
        "decline_amount": money(max(decline, Decimal("0"))),
        "decline_rate": rate(decline_ratio if decline > 0 else 0.0),
        "decline_contribution_rate": rate(
            safe_rate(max(decline, Decimal("0")), total_decline)
        ),
        "is_core_a_customer": level == "A",
        "risk_status": risk_status,
    }


def _validate_threshold(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("decline_threshold 必须是大于 0 且不超过 1 的数字")
    threshold = Decimal(str(value))
    if not Decimal("0") < threshold <= Decimal("1"):
        raise ValueError("decline_threshold 必须是大于 0 且不超过 1 的数字")
    return threshold


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
    "customer_loss_analysis_tool",
    description=(
        "比较明确区域和品类的当前季度与上一季度客户采购，识别停止采购或超过阈值"
        "下滑的客户，计算客户下降贡献并标记 A 级客户。适用于客户流失预警、风险"
        "客户名单和客户下降影响；不用于整体销售归因、经销商健康评分或确认客户已流失。"
    ),
    args_schema=CustomerLossArgs,
    validate_args=True,
)
def customer_loss_analysis_tool(
    region: str,
    category: str,
    current_quarter: str,
    decline_threshold: float = 0.5,
    top_n: int = 10,
) -> dict[str, Any]:
    """Return deterministic customer purchase-loss warnings."""

    return CustomerLossAnalysisService(PostgresReadOnlyExecutor()).analyze(
        region, category, current_quarter, decline_threshold, top_n
    )
