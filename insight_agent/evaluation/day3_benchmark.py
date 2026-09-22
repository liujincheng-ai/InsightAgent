"""Contracts and summary metrics for the initial Day 3 benchmark."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable

REQUIRED_CASE_FIELDS = {"id", "type", "question", "expected_facts", "tolerance"}
VALID_CASE_TYPES = {"sql", "rag", "tool", "integrated"}


def validate_dataset(dataset: dict[str, Any]) -> list[str]:
    """Return immutable-contract errors for a Day 3 benchmark dataset."""

    errors: list[str] = []
    cases = dataset.get("cases")
    if not isinstance(cases, list) or len(cases) != 15:
        return ["cases 必须恰好包含 15 条任务"]
    seen_ids: set[str] = set()
    counts: Counter[str] = Counter()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"第 {index} 条任务不是对象")
            continue
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            errors.append(
                f"{case.get('id', index)} 缺少字段: {', '.join(sorted(missing))}"
            )
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"第 {index} 条任务 id 无效")
        elif case_id in seen_ids:
            errors.append(f"任务 id 重复: {case_id}")
        else:
            seen_ids.add(case_id)
        case_type = case.get("type")
        if case_type not in VALID_CASE_TYPES:
            errors.append(f"{case_id} type 无效: {case_type}")
        else:
            counts[case_type] += 1
        if (
            case_type in {"tool", "integrated"}
            and case.get("expected_tool") != "sales_diagnosis_tool"
        ):
            errors.append(f"{case_id} 必须声明 sales_diagnosis_tool")
        if case_type in {"rag", "integrated"} and not case.get("expected_sources"):
            errors.append(f"{case_id} 必须声明制度来源")
    expected_counts = {"sql": 5, "rag": 4, "tool": 3, "integrated": 3}
    if dict(counts) != expected_counts:
        errors.append(f"任务类型数量必须为 {expected_counts}，实际为 {dict(counts)}")
    return errors


def summarize_records(
    records: Iterable[dict[str, Any]],
) -> dict[str, float | int | None]:
    """Summarize raw runs without hiding failed or missing observations."""

    entries = list(records)
    if not entries:
        return {
            "total": 0,
            "pass_rate": None,
            "sql_execution_success_rate": None,
            "expected_tool_call_rate": None,
            "rag_document_hit_rate": None,
            "integrated_task_pass_rate": None,
            "average_latency_seconds": None,
            "estimated_cost_cny": 0.0,
        }

    def fraction(predicate: Any, population: list[dict[str, Any]]) -> float | None:
        return (
            round(
                sum(bool(predicate(item)) for item in population) / len(population), 4
            )
            if population
            else None
        )

    sql = [item for item in entries if item.get("type") == "sql"]
    tool_expected = [item for item in entries if item.get("expected_tool")]
    rag = [item for item in entries if item.get("type") in {"rag", "integrated"}]
    integrated = [item for item in entries if item.get("type") == "integrated"]
    latencies = [
        float(item["latency_seconds"])
        for item in entries
        if isinstance(item.get("latency_seconds"), (int, float))
    ]
    costs = [
        float(item["estimated_cost_cny"])
        for item in entries
        if isinstance(item.get("estimated_cost_cny"), (int, float))
    ]
    return {
        "total": len(entries),
        "pass_rate": fraction(lambda item: item.get("passed"), entries),
        "sql_execution_success_rate": fraction(
            lambda item: item.get("sql_executed"), sql
        ),
        "expected_tool_call_rate": fraction(
            lambda item: item.get("expected_tool") in item.get("actual_tools", []),
            tool_expected,
        ),
        "rag_document_hit_rate": fraction(
            lambda item: item.get("expected_sources") == item.get("actual_sources"), rag
        ),
        "integrated_task_pass_rate": fraction(
            lambda item: item.get("passed"), integrated
        ),
        "average_latency_seconds": round(mean(latencies), 3) if latencies else None,
        "estimated_cost_cny": round(sum(costs), 4),
    }
