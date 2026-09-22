"""Scoring and aggregation for the Week 4 reliability benchmark."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any


def _action_sequence(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "step.meta":
            continue
        action = str(event.get("action") or "").strip()
        if action:
            actions.append(
                {
                    "action": action,
                    "action_input": event.get("action_input"),
                }
            )
    return actions


def _trace_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (
            event
            for event in reversed(events)
            if event.get("type") == "reliability.trace"
        ),
        None,
    )


def _primary_failure_index(decisions: list[dict[str, Any]]) -> int | None:
    """Select the benchmark fault without hiding earlier guard events."""

    for index, item in enumerate(decisions):
        observation = item.get("observation") or {}
        if item.get("injected") and observation.get("failure_type") not in {
            None,
            "none",
        }:
            return index
    for index, item in enumerate(decisions):
        observation = item.get("observation") or {}
        if item.get("source") == "request_timeout" and observation.get(
            "failure_type"
        ) not in {None, "none"}:
            return index
    for index, item in enumerate(decisions):
        observation = item.get("observation") or {}
        if observation.get("failure_type") not in {None, "none"}:
            return index
    return None


def _observed_recovery_action(
    decisions: list[dict[str, Any]], *, profile: str
) -> str | None:
    failure_index = _primary_failure_index(decisions)
    if failure_index is None:
        return None
    failure = decisions[failure_index]
    if profile == "after":
        decision = failure.get("decision") or {}
        return str(decision.get("action") or "") or None
    failed_tool = failure.get("tool_name")
    for item in decisions[failure_index + 1 :]:
        next_tool = item.get("tool_name")
        if next_tool == "terminate":
            return "terminate"
        if next_tool:
            return "retry" if next_tool == failed_tool else "replan"
    return "terminate"


def score_reliability_case(
    case: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    profile: str,
    transport_error: str | None,
) -> dict[str, Any]:
    actions = _action_sequence(events)
    trace = _trace_event(events)
    decisions = list((trace or {}).get("decisions") or [])
    completion = dict((trace or {}).get("completion") or {})
    decision_actions = [
        {
            "action": item.get("tool_name"),
            "action_input": item.get("normalized_args"),
        }
        for item in decisions
        if item.get("tool_name")
    ]
    scored_actions = decision_actions or actions
    first_action = next(
        (
            item["action"]
            for item in scored_actions
            if item["action"] not in {"terminate", "todowrite"}
        ),
        None,
    )
    failure_index = _primary_failure_index(decisions)
    actual_failure_type = None
    if failure_index is not None:
        actual_failure_type = (decisions[failure_index].get("observation") or {}).get(
            "failure_type"
        )
    actual_recovery_action = _observed_recovery_action(
        decisions, profile=profile
    )
    actual_completion = completion.get("status")
    final_seen = any(event.get("type") == "final" for event in events)
    done_seen = any(event.get("type") == "done" for event in events)
    step_count = sum(
        item["action"] != "terminate" for item in scored_actions
    )
    within_budget = step_count <= int(case["max_steps"])
    terminated = final_seen and done_seen and within_budget and transport_error is None
    circuit_indexes = [
        index
        for index, item in enumerate(decisions)
        if (item.get("guard") or {}).get("circuit_open") is True
    ]
    first_circuit = circuit_indexes[0] if circuit_indexes else None
    post_breaker_calls = 0
    if first_circuit is not None:
        post_breaker_calls = sum(
            item.get("tool_name") != "terminate"
            for item in decisions[first_circuit + 1 :]
        )
    duplicate_failure_calls = sum(
        int((item.get("guard") or {}).get("consecutive_count") or 0) >= 2
        for item in decisions
    )
    blind_retry = False
    if failure_index is not None and actual_failure_type in {
        "permission_denied",
        "unknown",
    }:
        blind_retry = any(
            item.get("tool_name") != "terminate"
            for item in decisions[failure_index + 1 :]
        )
    instrumentation_present = trace is not None
    checks = {
        "instrumentation_present": instrumentation_present,
        "initial_tool_correct": first_action == case["expected_initial_tool"],
        "failure_type_correct": actual_failure_type
        == case["expected_failure_type"],
        "recovery_action_correct": actual_recovery_action
        == case["expected_recovery_action"],
        "completion_correct": actual_completion == case["expected_completion"],
        "termination_within_budget": terminated,
        "no_post_breaker_call": post_breaker_calls == 0,
        "no_blind_retry": not blind_retry,
    }
    return {
        "actual_actions": scored_actions,
        "sse_actions": actions,
        "actual_initial_tool": first_action,
        "actual_failure_type": actual_failure_type,
        "actual_recovery_action": actual_recovery_action,
        "actual_completion": actual_completion,
        "step_count": step_count,
        "terminated": terminated,
        "within_step_budget": within_budget,
        "circuit_breaker_triggered": bool(circuit_indexes),
        "duplicate_failure_calls": duplicate_failure_calls,
        "post_breaker_calls": post_breaker_calls,
        "blind_retry_non_retryable": blind_retry,
        "reliability_trace": trace,
        **checks,
        "pass_fail": all(checks.values()),
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def _rate(records: list[dict[str, Any]], key: str) -> float:
    return (
        sum(bool(item.get(key)) for item in records) / len(records)
        if records
        else 0.0
    )


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def summarize_reliability_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    recoverable = [
        item for item in records if item.get("expected_completion") == "success"
    ]
    non_retryable = [
        item
        for item in records
        if item.get("expected_failure_type") in {"permission_denied", "unknown"}
    ]
    total_tool_calls = sum(len(item.get("actual_actions") or []) for item in records)
    post_breaker_calls = sum(item.get("post_breaker_calls", 0) for item in records)
    duplicate_calls = sum(
        item.get("duplicate_failure_calls", 0) for item in records
    )
    return {
        "case_count": len(records),
        "pass_rate": _rate(records, "pass_fail"),
        "failure_recovery_rate": _rate(recoverable, "completion_correct"),
        "termination_rate": _rate(records, "termination_within_budget"),
        "failure_type_accuracy": _rate(records, "failure_type_correct"),
        "recovery_action_accuracy": _rate(records, "recovery_action_correct"),
        "completion_accuracy": _rate(records, "completion_correct"),
        "non_retryable_blind_retry_rate": (
            sum(item.get("blind_retry_non_retryable", False) for item in non_retryable)
            / len(non_retryable)
            if non_retryable
            else 0.0
        ),
        "repeated_call_rate": (
            post_breaker_calls / total_tool_calls if total_tool_calls else 0.0
        ),
        "duplicate_failure_call_rate": (
            duplicate_calls / total_tool_calls if total_tool_calls else 0.0
        ),
        "circuit_breaker_trigger_count": sum(
            item.get("circuit_breaker_triggered", False) for item in records
        ),
        "average_steps": (
            sum(item.get("step_count", 0) for item in records) / len(records)
            if records
            else 0.0
        ),
        "p95_steps": _p95([float(item.get("step_count", 0)) for item in records]),
        "average_latency_seconds": (
            sum(item.get("latency_seconds", 0.0) for item in records) / len(records)
            if records
            else 0.0
        ),
        "p95_latency_seconds": _p95(
            [float(item.get("latency_seconds", 0.0)) for item in records]
        ),
        "completion_counts": dict(
            Counter(item.get("actual_completion") for item in records)
        ),
        "failed_case_ids": [
            item["id"] for item in records if not item.get("pass_fail")
        ],
    }
