"""Trace extraction and metrics for Week 2 Tool Calling evaluation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from insight_agent.tools.argument_schemas import (
    CustomerLossArgs,
    DealerHealthArgs,
    SalesDiagnosisArgs,
)

ROUTING_TOOLS = {
    "sales_diagnosis_tool",
    "customer_loss_analysis_tool",
    "dealer_health_analysis_tool",
    "sql_query",
}
SCHEMA_BY_TOOL = {
    "sales_diagnosis_tool": SalesDiagnosisArgs,
    "customer_loss_analysis_tool": CustomerLossArgs,
    "dealer_health_analysis_tool": DealerHealthArgs,
}


def extract_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract ordered calls, arguments and observations from SSE events."""

    calls: list[dict[str, Any]] = []
    by_step: dict[str, dict[str, Any]] = {}
    for event in events:
        event_type = event.get("type")
        step_id = str(event.get("id") or "")
        if event_type == "step.meta":
            action = str(event.get("action") or "")
            if not action or action == "terminate":
                continue
            action_input = event.get("action_input")
            arguments, parse_error = _parse_arguments(action_input)
            call = {
                "tool": action,
                "arguments": arguments,
                "argument_parse_error": parse_error,
                "observation": "",
                "execution_success": False,
                "_completion_seen": False,
            }
            calls.append(call)
            if step_id:
                by_step[step_id] = call
        elif event_type == "step.chunk" and step_id in by_step:
            content = event.get("content")
            text = (
                content
                if isinstance(content, str)
                else json.dumps(content, ensure_ascii=False, default=str)
            )
            call = by_step[step_id]
            call["observation"] += text
        elif event_type == "step.done" and step_id in by_step:
            call = by_step[step_id]
            call["_completion_seen"] = True
            call["execution_success"] = _observation_succeeded(
                call["observation"], str(event.get("status") or "done")
            )
    for call in calls:
        if call["observation"] and not call["_completion_seen"]:
            call["execution_success"] = _observation_succeeded(
                call["observation"], "done"
            )
        call.pop("_completion_seen", None)
        call["schema_valid"], call["normalized_arguments"] = _validate_arguments(
            call["tool"], call["arguments"]
        )
    return calls


def score_tool_calling_case(
    case: dict[str, Any],
    calls: list[dict[str, Any]],
    *,
    transport_error: str | None = None,
) -> dict[str, Any]:
    expected_calls = case["expected_calls"]
    expected_tools = [call["tool"] for call in expected_calls]
    actual_tools = [call["tool"] for call in calls]
    selection_exact = Counter(expected_tools) == Counter(actual_tools)
    order_correct = expected_tools == actual_tools
    expected_counter = Counter(expected_tools)
    actual_counter = Counter(actual_tools)
    missing_calls = list((expected_counter - actual_counter).elements())
    extra_calls = list((actual_counter - expected_counter).elements())
    argument_schema_valid = bool(calls) and all(call["schema_valid"] for call in calls)
    semantic_results: list[bool] = []
    actual_by_tool: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in calls:
        actual_by_tool[call["tool"]].append(call)
    expected_seen: Counter[str] = Counter()
    for expected in expected_calls:
        tool_name = expected["tool"]
        occurrence = expected_seen[tool_name]
        expected_seen[tool_name] += 1
        candidates = actual_by_tool.get(tool_name, [])
        if occurrence >= len(candidates):
            semantic_results.append(False)
            continue
        semantic_results.append(
            _arguments_match(
                tool_name,
                expected["arguments"],
                candidates[occurrence]["normalized_arguments"],
            )
        )
    argument_semantic_correct = bool(semantic_results) and all(semantic_results)
    execution_success = bool(calls) and all(call["execution_success"] for call in calls)
    combination_order_required = case["case_type"] == "combination"
    passed = bool(
        not transport_error
        and selection_exact
        and argument_schema_valid
        and argument_semantic_correct
        and execution_success
        and (order_correct or not combination_order_required)
    )
    failure_category = None
    if transport_error:
        failure_category = "transport_error"
    elif not selection_exact:
        failure_category = "tool_selection"
    elif combination_order_required and not order_correct:
        failure_category = "tool_order"
    elif not argument_schema_valid:
        failure_category = "argument_schema"
    elif not argument_semantic_correct:
        failure_category = "argument_semantics"
    elif not execution_success:
        failure_category = "execution"
    return {
        "passed": passed,
        "pass_fail": "pass" if passed else "fail",
        "selection_exact": selection_exact,
        "order_correct": order_correct,
        "argument_schema_valid": argument_schema_valid,
        "argument_semantic_correct": argument_semantic_correct,
        "execution_success": execution_success,
        "missing_calls": missing_calls,
        "extra_calls": extra_calls,
        "failure_category": failure_category,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
    }


def summarize_tool_calling_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(records)
    if not total:
        return {"total": 0}
    tool_stats = {tool: {"tp": 0, "fp": 0, "fn": 0} for tool in sorted(ROUTING_TOOLS)}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    actual_call_count = 0
    extra_call_count = 0
    for record in records:
        expected_set = set(record["expected_tools"])
        actual_set = set(record["actual_tools"])
        for tool in tool_stats:
            if tool in expected_set and tool in actual_set:
                tool_stats[tool]["tp"] += 1
            elif tool not in expected_set and tool in actual_set:
                tool_stats[tool]["fp"] += 1
            elif tool in expected_set and tool not in actual_set:
                tool_stats[tool]["fn"] += 1
        if len(record["expected_tools"]) == 1:
            expected_label = record["expected_tools"][0]
            actual_label = (
                record["actual_tools"][0]
                if len(record["actual_tools"]) == 1
                else ("none" if not record["actual_tools"] else "multiple")
            )
            confusion[expected_label][actual_label] += 1
        actual_call_count += len(record["actual_tools"])
        extra_call_count += len(record["extra_calls"])
    per_tool = {}
    for tool, counts in tool_stats.items():
        precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
        recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
        f1 = _ratio(2 * precision * recall, precision + recall)
        per_tool[tool] = {
            **counts,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    summary = {
        "total": total,
        "passed": sum(record["passed"] for record in records),
        "pass_rate": _ratio(sum(record["passed"] for record in records), total),
        "tool_selection_accuracy": _average(records, "selection_exact"),
        "argument_validity": _average(records, "argument_schema_valid"),
        "argument_semantic_accuracy": _average(records, "argument_semantic_correct"),
        "execution_success": _average(records, "execution_success"),
        "combination_order_accuracy": _average(
            [r for r in records if r["case_type"] == "combination"],
            "order_correct",
        ),
        "unnecessary_call_rate": _ratio(extra_call_count, actual_call_count),
        "extra_call_count": extra_call_count,
        "actual_call_count": actual_call_count,
        "per_tool": per_tool,
        "confusion_matrix": {
            expected: dict(counts) for expected, counts in sorted(confusion.items())
        },
        "failure_categories": dict(
            Counter(record["failure_category"] or "pass" for record in records)
        ),
    }
    business_recalls = {
        tool: per_tool[tool]["recall"]
        for tool in (
            "sales_diagnosis_tool",
            "customer_loss_analysis_tool",
            "dealer_health_analysis_tool",
        )
    }
    summary["acceptance"] = {
        "tool_selection_accuracy_gte_90": summary["tool_selection_accuracy"]
        >= 0.9,
        "each_business_tool_recall_gte_80": all(
            value >= 0.8 for value in business_recalls.values()
        ),
        "argument_validity_gte_95": summary["argument_validity"] >= 0.95,
        "unnecessary_call_rate_lte_5": summary["unnecessary_call_rate"] <= 0.05,
    }
    summary["acceptance"]["live_metrics_passed"] = all(
        summary["acceptance"].values()
    )
    return summary


def _parse_arguments(value: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(value, dict):
        return dict(value), None
    if not isinstance(value, str):
        return {}, "Action Input 不是 JSON 对象"
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return {}, f"JSONDecodeError: {exc}"
    if not isinstance(parsed, dict):
        return {}, "Action Input 不是 JSON 对象"
    return parsed, None


def _validate_arguments(
    tool_name: str, arguments: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    if tool_name == "sql_query":
        sql = arguments.get("sql") or arguments.get("query")
        valid = isinstance(sql, str) and sql.strip().lower().startswith(
            ("select", "with")
        )
        return valid, {"sql": sql} if sql else {}
    schema = SCHEMA_BY_TOOL.get(tool_name)
    if schema is None:
        return False, {}
    try:
        model = schema.model_validate(arguments)
    except Exception:
        return False, arguments
    return True, model.model_dump()


def _arguments_match(
    tool_name: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> bool:
    if tool_name == "sql_query":
        sql = actual.get("sql")
        return expected.get("sql") == "__READ_ONLY_SELECT__" and isinstance(sql, str)
    for key, value in expected.items():
        actual_value = actual.get(key)
        if isinstance(value, (int, float)) and isinstance(actual_value, (int, float)):
            if abs(float(value) - float(actual_value)) > 1e-9:
                return False
        elif actual_value != value:
            return False
    return True


def _observation_succeeded(observation: str, status: str) -> bool:
    if status.lower() not in {"done", "success", "completed"}:
        return False
    if not observation:
        return False
    lowered = observation.lower()
    failure_markers = (
        '"status": "error"',
        '"status":"error"',
        '"status": "blocked"',
        '"status":"blocked"',
        "invalid_arguments",
        "action_input_validation_failed",
        "sql_action_input_schema_error",
        "[syntax_error]",
        "[permission_error]",
        "[database_error]",
        "[timeout_error]",
        "execution error",
        "数据库未执行",
        "预执行校验失败",
        "预检提示",
    )
    return not any(marker in lowered for marker in failure_markers)


def _average(records: list[dict[str, Any]], key: str) -> float | None:
    if not records:
        return None
    return round(sum(bool(record[key]) for record in records) / len(records), 6)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)
