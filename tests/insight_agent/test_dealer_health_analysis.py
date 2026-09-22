from __future__ import annotations

from typing import Any, Sequence

from insight_agent.tools.dealer_health_analysis import (
    DealerHealthAnalysisService,
    dealer_health_analysis_tool,
)


class FakeExecutor:
    def __init__(
        self, rows: list[dict[str, Any]] | None = None, raises: bool = False
    ) -> None:
        self.rows = rows if rows is not None else _rows()
        self.raises = raises
        self.calls: list[tuple[str, Sequence[Any]]] = []

    def fetch_all(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        if self.raises:
            raise RuntimeError("数据库只读查询失败: OperationalError")
        return self.rows


def _rows() -> list[dict[str, Any]]:
    return [
        {
            "customer_id": 1,
            "customer_name": "高风险经销商",
            "customer_level": "A",
            "current_sales": 60,
            "previous_sales": 100,
            "prior_year_sales": 90,
            "current_gross_profit": 9,
            "previous_gross_profit": 28,
            "current_active_days": 2,
            "previous_active_days": 10,
            "current_average_discount": 0.16,
        },
        {
            "customer_id": 2,
            "customer_name": "健康经销商",
            "customer_level": "B",
            "current_sales": 120,
            "previous_sales": 100,
            "prior_year_sales": 110,
            "current_gross_profit": 36,
            "previous_gross_profit": 28,
            "current_active_days": 12,
            "previous_active_days": 10,
            "current_average_discount": 0.08,
        },
    ]


def test_dealer_health_returns_ranked_scores_and_deductions() -> None:
    result = DealerHealthAnalysisService(FakeExecutor()).analyze("华东", "2026Q2")

    assert result["status"] == "success"
    assert result["baseline_quarter"] == "2026Q1"
    assert result["data"]["dealer_count"] == 2
    assert result["data"]["risk_counts"] == {"high": 1, "medium": 0, "low": 1}
    risky = result["data"]["dealers"][0]
    assert risky["dealer_name"] == "高风险经销商"
    assert risky["component_scores"] == {
        "sales_change": 0,
        "purchase_activity": 5,
        "discount": 0,
        "gross_margin": 0,
    }
    assert risky["health_score"] == 5
    assert risky["risk_level"] == "high"
    assert len(risky["deductions"]) == 4


def test_dealer_health_uses_weighted_margin_and_line_average_discount() -> None:
    result = DealerHealthAnalysisService(FakeExecutor()).analyze("华东", "2026Q2")
    healthy = result["data"]["dealers"][1]

    assert healthy["gross_margin"]["current"] == 0.3
    assert healthy["average_discount_rate"] == 0.08
    assert healthy["health_score"] == 100
    assert healthy["deductions"] == []


def test_dealer_health_sql_is_parameterized_and_dealer_only() -> None:
    executor = FakeExecutor()
    DealerHealthAnalysisService(executor).analyze("华东", "2026Q2")

    query, params = executor.calls[0]
    assert "%s" in query and "华东" not in query
    assert "c.channel = '经销商'" in query
    assert params[-1] == "华东"


def test_dealer_health_top_n_keeps_deterministic_risk_order() -> None:
    result = DealerHealthAnalysisService(FakeExecutor()).analyze(
        "华东", "2026Q2", top_n=1
    )
    assert result["data"]["dealer_count"] == 2
    assert [item["dealer_name"] for item in result["data"]["dealers"]] == [
        "高风险经销商"
    ]


def test_dealer_health_returns_no_data_without_guessing() -> None:
    result = DealerHealthAnalysisService(FakeExecutor(rows=[])).analyze(
        "未知区域", "2026Q2"
    )
    assert result["status"] == "no_data"
    assert result["data"] is None


def test_dealer_health_rejects_invalid_inputs() -> None:
    service = DealerHealthAnalysisService(FakeExecutor())
    assert service.analyze("", "2026Q2")["error"]["code"] == "invalid_input"
    assert service.analyze("华东", "2026-Q2")["error"]["code"] == "invalid_input"
    assert service.analyze("华东", "2026Q2", 21)["error"]["code"] == "invalid_input"


def test_dealer_health_returns_sanitized_database_error() -> None:
    result = DealerHealthAnalysisService(FakeExecutor(raises=True)).analyze(
        "华东", "2026Q2"
    )
    assert result["error"] == {
        "code": "database_error",
        "message": "数据库只读查询失败: OperationalError",
    }


def test_dealer_health_is_a_native_dbgpt_function_tool() -> None:
    native_tool = getattr(dealer_health_analysis_tool, "_tool")
    assert native_tool.name == "dealer_health_analysis_tool"
    assert set(native_tool.args) == {"region", "current_quarter", "top_n"}
