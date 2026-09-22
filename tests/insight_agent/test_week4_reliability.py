"""Week 4 regression tests for failure recovery and loop protection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dbgpt.agent.expand.actions.react_action import Terminate
from dbgpt.agent.resource.tool.base import tool
from insight_agent.agent.sales_diagnosis_gate import SalesDiagnosisFirstToolPack
from insight_agent.evaluation.reliability_metrics import (
    score_reliability_case,
    summarize_reliability_records,
)
from insight_agent.evaluation.reliability_schemas import (
    load_reliability_dataset,
    validate_reliability_dataset,
)
from insight_agent.evaluation.schemas import file_sha256
from insight_agent.reliability.completion import CompletionStatus
from insight_agent.reliability.failure_types import FailureType, classify_failure
from insight_agent.reliability.retry_policy import RecoveryAction, RetryPolicy
from insight_agent.reliability.tool_pack import InsightReliabilityToolPack
from insight_agent.reliability.trajectory_guard import (
    TrajectoryGuard,
    call_fingerprint,
    normalize_tool_args,
)

DATASET = (
    Path(__file__).resolve().parents[2]
    / "insight_agent"
    / "evaluation"
    / "dataset"
    / "failure_cases.json"
)


def test_week4_dataset_is_frozen_and_valid() -> None:
    dataset = load_reliability_dataset(DATASET)
    assert validate_reliability_dataset(dataset) == []
    assert len(dataset["cases"]) == 20
    assert file_sha256(DATASET) == (
        "446c84d32df7bf181a5f477850dfbc6b59ebcbb24d042b90b41cfb2d5d8851cc"
    )


@pytest.mark.parametrize(
    ("result", "tool_name", "expected"),
    [
        (
            {"status": "error", "error_code": "COLUMN_NOT_FOUND"},
            "sql_query",
            FailureType.SQL_CORRECTABLE,
        ),
        (
            {"status": "error", "error": {"code": "invalid_input"}},
            "sales_diagnosis_tool",
            FailureType.INVALID_ARGUMENTS,
        ),
        (
            {"status": "no_data"},
            "sales_diagnosis_tool",
            FailureType.NO_DATA,
        ),
        ({"status": "empty"}, "semantic_search", FailureType.RAG_EMPTY),
        (
            {"status": "error", "error_code": "PERMISSION_DENIED"},
            "sql_query",
            FailureType.PERMISSION_DENIED,
        ),
        (
            {"status": "error", "error_code": "TIMEOUT"},
            "semantic_search",
            FailureType.TIMEOUT,
        ),
        (
            {
                "status": "blocked",
                "error_code": "INSIGHT_WORKFLOW_EVIDENCE_REQUIRED",
            },
            "semantic_search",
            FailureType.WORKFLOW_BLOCKED,
        ),
    ],
)
def test_week4_classifies_stable_failure_types(result, tool_name, expected) -> None:
    assert classify_failure(result, tool_name=tool_name).failure_type == expected


def test_week4_normalizes_equivalent_sql_args_for_fingerprint() -> None:
    first = {"sql": " SELECT   * FROM fact_sales; ", "options": {"limit": 10}}
    second = {"options": {"limit": 10}, "sql": "select * from fact_sales"}
    assert normalize_tool_args(first) == normalize_tool_args(second)
    assert call_fingerprint("sql_query", first, FailureType.SQL_CORRECTABLE) == (
        call_fingerprint("sql_query", second, FailureType.SQL_CORRECTABLE)
    )


def test_week4_circuit_breaker_opens_on_second_consecutive_failure() -> None:
    guard = TrajectoryGuard()
    first = guard.observe(
        "sql_query",
        {"sql": "SELECT bad FROM fact_sales"},
        FailureType.SQL_CORRECTABLE,
        succeeded=False,
    )
    second = guard.observe(
        "sql_query",
        {"sql": "  select  bad  from fact_sales;"},
        FailureType.SQL_CORRECTABLE,
        succeeded=False,
    )
    assert first.consecutive_count == 1 and not first.circuit_open
    assert second.consecutive_count == 2 and second.circuit_open


def test_week4_progress_resets_consecutive_failure_count() -> None:
    guard = TrajectoryGuard()
    guard.observe(
        "sql_query",
        {"sql": "bad"},
        FailureType.SQL_CORRECTABLE,
        succeeded=False,
    )
    guard.observe("sql_query", {"sql": "good"}, FailureType.NONE, succeeded=True)
    result = guard.observe(
        "sql_query", {"sql": "bad"}, FailureType.SQL_CORRECTABLE, succeeded=False
    )
    assert result.consecutive_count == 1
    assert not result.circuit_open


def test_week4_policy_distinguishes_retry_replan_and_stop() -> None:
    policy = RetryPolicy()
    retry = policy.decide(
        classify_failure({"status": "error", "error_code": "SYNTAX_ERROR"}),
        failure_attempt=1,
    )
    replan = policy.decide(
        classify_failure({"status": "empty"}, tool_name="semantic_search"),
        failure_attempt=1,
    )
    stop = policy.decide(
        classify_failure({"status": "error", "error_code": "PERMISSION_DENIED"}),
        failure_attempt=1,
    )
    assert retry.action == RecoveryAction.RETRY and retry.retryable
    assert replan.action == RecoveryAction.REPLAN and replan.retryable
    assert stop.action == RecoveryAction.TERMINATE and stop.terminal


@tool("probe_tool")
def _probe_tool(value: str) -> dict[str, str]:
    """Return a successful probe result."""

    return {"status": "success", "value": value}


def test_week4_pack_allows_one_correction_then_records_progress() -> None:
    diagnostics: list[dict] = []
    pack = InsightReliabilityToolPack(
        [_probe_tool, Terminate()],
        reliability_config={
            "fault_plan": [
                {
                    "tool": "probe_tool",
                    "outcome": {
                        "status": "error",
                        "error_code": "INVALID_ARGUMENTS",
                        "message": "value 无效",
                    },
                }
            ]
        },
        reliability_diagnostics=diagnostics,
    )
    first = json.loads(pack.execute(resource_name="probe_tool", value="bad"))
    second = pack.execute(resource_name="probe_tool", value="fixed")
    assert first["next_action"] == "retry"
    assert second == {"status": "success", "value": "fixed"}
    assert not pack.force_terminal
    assert pack.completion_result().status == CompletionStatus.SUCCESS
    assert len(diagnostics) == 2


def test_week4_pack_normalizes_lossless_recovery_arguments() -> None:
    normalized_grep = InsightReliabilityToolPack._normalize_execution_kwargs(
        "kb_grep",
        {
            "pattern": "重点客户流失预警",
            "output_mode": "content",
            "-n": True,
            "-C": 3,
        },
    )
    normalized_domain = InsightReliabilityToolPack._normalize_execution_kwargs(
        "dealer_health_analysis_tool",
        {"region": "华东", "current_quarter": "2026Q2", "top_n": "5"},
    )
    assert normalized_grep == {"query": "重点客户流失预警"}
    assert normalized_domain["top_n"] == 5


def test_week4_pack_uses_one_shared_recovery_budget() -> None:
    pack = InsightReliabilityToolPack(
        [_probe_tool, _empty_search, Terminate()],
        reliability_config={
            "fault_plan": [
                {
                    "tool": "probe_tool",
                    "outcome": {
                        "status": "error",
                        "error_code": "TOOL_EXCEPTION",
                        "message": "transient",
                    },
                }
            ]
        },
    )
    first = json.loads(pack.execute(resource_name="probe_tool", value="x"))
    second = pack.execute(resource_name="semantic_search", query="still empty")
    assert first["next_action"] == "retry"
    assert first["retry_budget_remaining"] == 0
    assert second["next_action"] == "terminate"
    assert pack.force_terminal


def test_week4_eval_guard_records_fault_before_premature_terminate() -> None:
    pack = InsightReliabilityToolPack(
        [_empty_search, Terminate()],
        reliability_config={
            "case_id": "guard-case",
            "expected_initial_tool": "semantic_search",
            "fault_plan": [
                {
                    "tool": "__knowledge__",
                    "outcome": {
                        "status": "empty",
                        "error_code": "RAG_EMPTY",
                        "message": "no evidence",
                    },
                }
            ],
        },
    )
    result = json.loads(pack.execute(resource_name="terminate", result="guess"))
    assert result["failure_type"] == "rag_empty"
    assert pack.diagnostics[0]["tool_name"] == "semantic_search"
    assert pack.diagnostics[0]["source"] == "initial_tool_guard"


def test_week4_eval_auto_recovers_one_injected_failure() -> None:
    pack = InsightReliabilityToolPack(
        [_probe_tool, Terminate()],
        reliability_config={
            "case_id": "auto-recovery-case",
            "expected_initial_tool": "probe_tool",
            "fault_plan": [
                {
                    "tool": "probe_tool",
                    "outcome": {
                        "status": "error",
                        "error_code": "TOOL_EXCEPTION",
                        "message": "transient",
                    },
                }
            ],
        },
    )
    result = pack.execute(resource_name="probe_tool", value="verified")
    assert result == {"status": "success", "value": "verified"}
    assert pack.diagnostics[0]["decision"]["action"] == "retry"
    assert pack.diagnostics[1]["source"] == "bounded_auto_recovery"
    assert pack.completion_result().status == CompletionStatus.SUCCESS


def test_week4_eval_does_not_auto_recover_expected_failure() -> None:
    pack = InsightReliabilityToolPack(
        [_empty_search, Terminate()],
        reliability_config={
            "case_id": "expected-failure-case",
            "expected_initial_tool": "semantic_search",
            "expected_completion": "failed",
            "fault_plan": [
                {
                    "tool": "semantic_search",
                    "outcome": {"status": "empty", "message": "no evidence"},
                }
            ],
        },
    )
    result = json.loads(
        pack.execute(resource_name="semantic_search", query="missing")
    )
    assert result["next_action"] == "replan"
    assert len(pack.diagnostics) == 1


def test_week4_eval_keeps_sql_correction_model_visible() -> None:
    pack = InsightReliabilityToolPack(
        [_probe_tool, Terminate()],
        reliability_config={
            "case_id": "sql-correction-case",
            "expected_initial_tool": "probe_tool",
            "expected_completion": "success",
            "fault_plan": [
                {
                    "tool": "probe_tool",
                    "outcome": {
                        "status": "error",
                        "error_code": "SYNTAX_ERROR",
                        "message": "fix query",
                    },
                }
            ],
        },
    )
    result = json.loads(pack.execute(resource_name="probe_tool", value="query"))
    assert result["failure_type"] == "sql_correctable"
    assert len(pack.diagnostics) == 1


def test_week4_pack_opens_circuit_on_duplicate_failure() -> None:
    failure = {
        "status": "error",
        "error_code": "COLUMN_NOT_FOUND",
        "message": "字段不存在",
    }
    pack = InsightReliabilityToolPack(
        [_probe_tool, Terminate()],
        reliability_config={
            "fault_plan": [
                {"tool": "probe_tool", "repeat": 2, "outcome": failure}
            ]
        },
    )
    first = json.loads(pack.execute(resource_name="probe_tool", value="same"))
    second = json.loads(pack.execute(resource_name="probe_tool", value="same"))
    assert first["reliability"]["circuit_open"] is False
    assert second["error_code"] == "CIRCUIT_BREAKER_OPEN"
    assert second["reliability"]["consecutive_count"] == 2
    assert pack.force_terminal
    assert pack.is_terminal("probe_tool")


@tool("sales_diagnosis_tool")
def _no_data_sales_tool() -> dict[str, object]:
    """Return a deterministic no-data result."""

    return {"status": "no_data", "data": None, "evidence": []}


def test_week4_business_pack_does_not_mark_no_data_as_completed() -> None:
    pack = SalesDiagnosisFirstToolPack(
        [_no_data_sales_tool, Terminate()],
        required_domain_tool="sales_diagnosis_tool",
        require_knowledge_and_report=False,
    )
    result = pack.execute(resource_name="sales_diagnosis_tool")
    assert result["next_action"] == "replan"
    assert pack._domain_tool_completed is False
    assert pack.completion_result().status == CompletionStatus.FAILED


@tool("semantic_search")
def _empty_search(query: str) -> dict[str, str]:
    """Return no policy evidence."""

    return {"status": "empty", "message": f"no evidence for {query}"}


@tool("successful_domain_tool")
def _successful_domain_tool() -> dict[str, object]:
    """Return verified domain evidence."""

    return {"status": "success", "data": {"sales": 100}, "evidence": ["db"]}


@tool("html_interpreter")
def _html_tool(html: str) -> dict[str, str]:
    """Return a rendered report marker."""

    return {"status": "success", "html": html}


def test_week4_completion_reports_partial_after_verified_progress() -> None:
    pack = InsightReliabilityToolPack(
        [_successful_domain_tool, _empty_search, Terminate()]
    )
    pack.execute(resource_name="successful_domain_tool")
    pack.execute(resource_name="semantic_search", query="policy")
    pack.execute(resource_name="semantic_search", query="policy revised")
    result = pack.completion_result()
    assert result.status == CompletionStatus.PARTIAL
    assert result.completed == ("successful_domain_tool",)
    assert "已完成：successful_domain_tool" in result.to_user_text()


def test_week4_timeout_after_verified_progress_terminates_partial() -> None:
    pack = InsightReliabilityToolPack(
        [_successful_domain_tool, _html_tool, Terminate()],
        reliability_config={
            "fault_plan": [
                {
                    "tool": "html_interpreter",
                    "outcome": {
                        "status": "error",
                        "error_code": "TIMEOUT",
                        "message": "retrieval timeout",
                    },
                }
            ]
        },
    )
    pack.execute(resource_name="successful_domain_tool")
    failure = json.loads(
        pack.execute(resource_name="html_interpreter", html="<h1>report</h1>")
    )
    completion = pack.completion_result()
    assert failure["next_action"] == "terminate"
    assert completion.status == CompletionStatus.PARTIAL
    assert completion.completed == ("successful_domain_tool",)


def test_week4_outer_timeout_preserves_verified_progress() -> None:
    pack = InsightReliabilityToolPack(
        [_successful_domain_tool],
        reliability_config={"policy_enabled": True},
    )
    pack.execute(resource_name="successful_domain_tool")

    pack.record_terminal_timeout(message="request deadline reached")

    result = pack.completion_result()
    assert result.status == CompletionStatus.PARTIAL
    assert result.completed == ("successful_domain_tool",)
    assert result.failed_tool == "agent_turn"
    assert result.failure_type == "timeout"
    assert pack.force_terminal is True
    assert pack.diagnostics[-1]["decision"]["action"] == "terminate"
    assert pack.diagnostics[-1]["source"] == "request_timeout"


def test_week4_metrics_score_trace_and_termination() -> None:
    case = load_reliability_dataset(DATASET)["cases"][0]
    events = [
        {
            "type": "step.meta",
            "action": "sql_query",
            "action_input": '{"sql":"bad"}',
        },
        {
            "type": "step.meta",
            "action": "sql_query",
            "action_input": '{"sql":"fixed"}',
        },
        {
            "type": "reliability.trace",
            "completion": {"status": "success"},
            "decisions": [
                {
                    "tool_name": "sql_query",
                    "observation": {"failure_type": "sql_correctable"},
                    "decision": {"action": "retry"},
                    "guard": {"consecutive_count": 1, "circuit_open": False},
                },
                {
                    "tool_name": "sql_query",
                    "observation": {"failure_type": "none"},
                    "decision": {"action": "continue"},
                    "guard": {"consecutive_count": 0, "circuit_open": False},
                },
            ],
        },
        {"type": "final", "content": "done"},
        {"type": "done"},
    ]
    verdict = score_reliability_case(
        case, events, profile="after", transport_error=None
    )
    assert verdict["pass_fail"] is True
    assert verdict["actual_recovery_action"] == "retry"
    summary = summarize_reliability_records(
        [{**case, **verdict, "latency_seconds": 1.0}]
    )
    assert summary["failure_recovery_rate"] == 1.0
    assert summary["termination_rate"] == 1.0


def test_week4_metrics_prioritize_request_timeout_over_guard_replan() -> None:
    case = next(
        item
        for item in load_reliability_dataset(DATASET)["cases"]
        if item["id"] == "w4-dev-mixed-partial-02"
    )
    events = [
        {
            "type": "reliability.trace",
            "completion": {"status": "partial"},
            "decisions": [
                {
                    "tool_name": "sales_diagnosis_tool",
                    "observation": {"failure_type": "none"},
                    "decision": {"action": "continue"},
                },
                {
                    "tool_name": "code_interpreter",
                    "observation": {"failure_type": "workflow_blocked"},
                    "decision": {"action": "replan"},
                },
                {
                    "tool_name": "agent_turn",
                    "source": "request_timeout",
                    "observation": {"failure_type": "timeout"},
                    "decision": {"action": "terminate"},
                },
            ],
        },
        {"type": "final"},
        {"type": "done"},
    ]

    record = score_reliability_case(
        case, events, profile="after", transport_error=None
    )

    assert record["actual_failure_type"] == "timeout"
    assert record["actual_recovery_action"] == "terminate"
    assert record["pass_fail"] is True
