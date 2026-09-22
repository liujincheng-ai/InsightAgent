from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from insight_agent.tools.sales_diagnosis import (
    SalesDiagnosisService,
    sales_diagnosis_tool,
)


class FakeExecutor:
    def __init__(self, no_data: bool = False, raises: bool = False) -> None:
        self.calls: list[tuple[str, Sequence[Any]]] = []
        self.no_data = no_data
        self.raises = raises

    def fetch_all(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        if self.raises:
            raise RuntimeError("数据库只读查询失败: OperationalError")
        if "national_current" not in query and "GROUP BY" not in query:
            if self.no_data:
                return [
                    {
                        "current_sales": 0,
                        "previous_sales": 0,
                        "prior_year_sales": 0,
                        "current_gross_profit": 0,
                        "previous_gross_profit": 0,
                    }
                ]
            return [
                {
                    "current_sales": 900,
                    "previous_sales": 1200,
                    "prior_year_sales": 1000,
                    "current_gross_profit": 180,
                    "previous_gross_profit": 300,
                }
            ]
        if "GROUP BY p.product_name" in query:
            return [
                {
                    "dimension_name": "制动片",
                    "current_sales": 300,
                    "previous_sales": 600,
                },
                {
                    "dimension_name": "制动盘",
                    "current_sales": 500,
                    "previous_sales": 550,
                },
            ]
        if "GROUP BY s.channel" in query:
            return [
                {
                    "dimension_name": "经销商",
                    "current_sales": 400,
                    "previous_sales": 800,
                }
            ]
        return [{"current_sales": 5000, "previous_sales": 4900}]


def test_sales_diagnosis_returns_deterministic_metrics_and_evidence() -> None:
    executor = FakeExecutor()
    result = SalesDiagnosisService(executor).diagnose("华东", "刹车系统", "2026Q2", 2)

    assert result["status"] == "success"
    assert result["error"] is None
    assert result["data"]["sales"] is result["sales"]
    assert result["sales"] == {
        "current": 900.0,
        "previous_quarter": 1200.0,
        "prior_year_same_quarter": 1000.0,
        "qoq_change_amount": -300.0,
        "qoq_change_rate": -0.25,
        "yoy_change_amount": -100.0,
        "yoy_change_rate": -0.1,
    }
    assert result["gross_margin"]["change_percentage_points"] == -5.0
    assert result["top_decline_products"][0]["name"] == "制动片"
    assert result["top_decline_products"][0]["decline_contribution_rate"] == 1.0
    assert result["channel_contributions"][0]["name"] == "经销商"
    assert {item["id"] for item in result["evidence"]} == {
        "sales_summary",
        "product_contribution",
        "channel_contribution",
        "national_category_trend",
    }


def test_sales_diagnosis_uses_parameters_and_expected_quarter_windows() -> None:
    executor = FakeExecutor()
    SalesDiagnosisService(executor).diagnose("华东", "刹车系统", "2026Q2")

    summary_sql, summary_params = executor.calls[0]
    assert "%s" in summary_sql
    assert "华东" not in summary_sql and "刹车系统" not in summary_sql
    assert list(summary_params[0:6]) == [
        date(2026, 4, 1),
        date(2026, 7, 1),
        date(2026, 1, 1),
        date(2026, 4, 1),
        date(2025, 4, 1),
        date(2025, 7, 1),
    ]
    assert list(summary_params[-2:]) == [date(2025, 4, 1), date(2026, 7, 1)]


def test_sales_diagnosis_returns_no_data_without_guessing() -> None:
    result = SalesDiagnosisService(FakeExecutor(no_data=True)).diagnose(
        "华东", "不存在品类", "2026Q2"
    )
    assert result["status"] == "no_data"
    assert result["data"] is None


def test_sales_diagnosis_rejects_invalid_business_input() -> None:
    service = SalesDiagnosisService(FakeExecutor())
    invalid_quarter = service.diagnose("华东", "刹车系统", "2026-Q2")
    invalid_top_n = service.diagnose("华东", "刹车系统", "2026Q2", 21)

    assert invalid_quarter["error"]["code"] == "invalid_input"
    assert invalid_top_n["error"]["code"] == "invalid_input"


def test_sales_diagnosis_returns_sanitized_database_error() -> None:
    result = SalesDiagnosisService(FakeExecutor(raises=True)).diagnose(
        "华东", "刹车系统", "2026Q2"
    )
    assert result["status"] == "error"
    assert result["error"] == {
        "code": "database_error",
        "message": "数据库只读查询失败: OperationalError",
    }


def test_sales_diagnosis_is_a_native_dbgpt_function_tool() -> None:
    assert getattr(sales_diagnosis_tool, "_tool").name == "sales_diagnosis_tool"
