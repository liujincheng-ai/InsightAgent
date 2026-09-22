from __future__ import annotations

from typing import Any, Sequence

from insight_agent.tools.customer_loss_analysis import (
    CustomerLossAnalysisService,
    customer_loss_analysis_tool,
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
            "customer_name": "A客户",
            "customer_level": "A",
            "channel": "经销商",
            "previous_sales": 1000,
            "current_sales": 0,
        },
        {
            "customer_id": 2,
            "customer_name": "B客户",
            "customer_level": "B",
            "channel": "电商",
            "previous_sales": 800,
            "current_sales": 300,
        },
        {
            "customer_id": 3,
            "customer_name": "新客户",
            "customer_level": "C",
            "channel": "直营网点",
            "previous_sales": 0,
            "current_sales": 200,
        },
        {
            "customer_id": 4,
            "customer_name": "稳定客户",
            "customer_level": "B",
            "channel": "汽修连锁",
            "previous_sales": 500,
            "current_sales": 520,
        },
    ]


def test_customer_loss_returns_ranked_warnings_and_evidence() -> None:
    result = CustomerLossAnalysisService(FakeExecutor()).analyze(
        "华东", "刹车系统", "2026Q2"
    )

    assert result["status"] == "success"
    assert result["baseline_quarter"] == "2026Q1"
    assert result["data"]["summary"]["risk_customer_count"] == 2
    assert result["data"]["summary"]["new_customer_count"] == 1
    assert result["data"]["risk_customers"][0]["customer_name"] == "A客户"
    assert result["data"]["risk_customers"][0]["risk_status"] == "suspected_churn"
    assert result["data"]["risk_customers"][0]["is_core_a_customer"] is True
    assert "不代表客户已确认流失" in result["data"]["interpretation"]
    assert result["evidence"][1]["sections"] == ["1.2", "2.1", "2.2", "3.1"]


def test_customer_loss_uses_fixed_parameterized_sql_and_quarter_scope() -> None:
    executor = FakeExecutor()
    CustomerLossAnalysisService(executor).analyze("华东", "刹车系统", "2026Q2")

    query, params = executor.calls[0]
    assert "%s" in query
    assert "华东" not in query and "刹车系统" not in query
    assert list(params[4:6]) == ["华东", "刹车系统"]
    assert "ORDER BY c.customer_name" in query


def test_customer_loss_respects_threshold_and_top_n() -> None:
    result = CustomerLossAnalysisService(FakeExecutor()).analyze(
        "华东", "刹车系统", "2026Q2", decline_threshold=0.7, top_n=1
    )
    assert result["data"]["summary"]["risk_customer_count"] == 1
    assert len(result["data"]["risk_customers"]) == 1


def test_customer_loss_returns_no_data_without_guessing() -> None:
    result = CustomerLossAnalysisService(FakeExecutor(rows=[])).analyze(
        "华东", "未知品类", "2026Q2"
    )
    assert result["status"] == "no_data"
    assert result["data"] is None


def test_customer_loss_rejects_invalid_inputs() -> None:
    service = CustomerLossAnalysisService(FakeExecutor())
    assert service.analyze("", "刹车系统", "2026Q2")["error"]["code"] == "invalid_input"
    assert (
        service.analyze("华东", "刹车系统", "bad")["error"]["code"] == "invalid_input"
    )
    assert (
        service.analyze("华东", "刹车系统", "2026Q2", 0)["error"]["code"]
        == "invalid_input"
    )
    assert (
        service.analyze("华东", "刹车系统", "2026Q2", top_n=21)["error"]["code"]
        == "invalid_input"
    )


def test_customer_loss_returns_sanitized_database_error() -> None:
    result = CustomerLossAnalysisService(FakeExecutor(raises=True)).analyze(
        "华东", "刹车系统", "2026Q2"
    )
    assert result["error"] == {
        "code": "database_error",
        "message": "数据库只读查询失败: OperationalError",
    }


def test_customer_loss_is_a_native_dbgpt_function_tool() -> None:
    native_tool = getattr(customer_loss_analysis_tool, "_tool")
    assert native_tool.name == "customer_loss_analysis_tool"
    assert "decline_threshold" in native_tool.args
