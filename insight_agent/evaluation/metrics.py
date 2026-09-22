"""Deterministic scoring and aggregation for the InsightAgent V1 benchmark."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any, Iterable

NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def _numeric_values(text: str) -> list[float]:
    values: list[float] = []
    for token in NUMBER_RE.findall(text):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def score_facts(
    expected_facts: list[dict[str, Any]],
    evidence_text: str,
    default_tolerance: float,
) -> tuple[bool, list[dict[str, Any]]]:
    """Score text and numeric facts against answer plus raw trajectory."""

    numeric_values = _numeric_values(evidence_text)
    details: list[dict[str, Any]] = []
    for fact in expected_facts:
        kind = fact.get("kind", "text")
        expected = fact["value"]
        if kind == "numeric":
            accepted = [expected, *fact.get("accepted_values", [])]
            tolerance = float(fact.get("tolerance", default_tolerance))
            matched = any(
                abs(actual - float(candidate)) <= tolerance
                for actual in numeric_values
                for candidate in accepted
            )
        else:
            accepted = [str(expected), *map(str, fact.get("accepted_values", []))]
            normalized_evidence = "".join(evidence_text.split())
            matched = any(
                "".join(candidate.split()) in normalized_evidence
                for candidate in accepted
            )
        details.append(
            {
                "name": fact["name"],
                "expected": expected,
                "matched": matched,
            }
        )
    return all(item["matched"] for item in details), details


def score_record(case: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    """Apply explicit component rules and return an auditable verdict."""

    evidence_text = "\n".join(
        str(actual.get(key, "")) for key in ("actual_answer", "raw_trajectory")
    )
    facts_passed, fact_results = score_facts(
        case["expected_facts"], evidence_text, case["numeric_tolerance"]
    )
    expected_tool = case.get("expected_tool")
    tool_passed = not expected_tool or expected_tool in actual.get("actual_tools", [])
    expected_documents = case.get("expected_documents", [])
    expected_sections = case.get("expected_sections", [])
    source_text = "\n".join(
        [evidence_text, *map(str, actual.get("actual_sources", []))]
    )
    normalized_source = "".join(source_text.split())
    documents_passed = all(
        "".join(doc.split()) in normalized_source for doc in expected_documents
    )
    sections_passed = documents_passed and all(
        section in source_text for section in expected_sections
    )
    sql_passed = case["type"] != "text_to_sql" or bool(
        actual.get("sql_executed", bool(actual.get("actual_sql")))
    )
    runtime_passed = not actual.get("error") and bool(actual.get("actual_answer"))
    components = {
        "facts": facts_passed,
        "tool": tool_passed,
        "documents": documents_passed,
        "sections": sections_passed,
        "sql_executed": sql_passed,
        "runtime": runtime_passed,
    }
    passed = all(components.values())
    failure_reason = None
    failure_category = None
    if not passed:
        priority = [
            ("runtime", "runtime_or_timeout"),
            ("tool", "tool_selection"),
            ("sql_executed", "sql_generation_or_execution"),
            ("documents", "rag_document_retrieval"),
            ("sections", "rag_section_or_citation"),
            ("facts", "answer_fact_accuracy"),
        ]
        for component, category in priority:
            if not components[component]:
                failure_category = category
                failure_reason = f"主要失败项: {component}"
                break
    return {
        "passed": passed,
        "pass_fail": "pass" if passed else "fail",
        "components": components,
        "fact_results": fact_results,
        "failure_category": failure_category,
        "failure_reason": failure_reason,
    }


def summarize_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate all cases while keeping failures in every denominator."""

    entries = list(records)
    if not entries:
        return {
            "total": 0,
            "passed": 0,
            "pass_rate": None,
            "by_type": {},
            "failure_categories": {},
            "average_latency_seconds": None,
        }

    def ratio(items: list[dict[str, Any]], predicate: Any) -> float | None:
        if not items:
            return None
        return round(sum(bool(predicate(item)) for item in items) / len(items), 4)

    by_type: dict[str, dict[str, Any]] = {}
    for case_type in sorted({item["type"] for item in entries}):
        subset = [item for item in entries if item["type"] == case_type]
        by_type[case_type] = {
            "total": len(subset),
            "passed": sum(bool(item.get("passed")) for item in subset),
            "pass_rate": ratio(subset, lambda item: item.get("passed")),
        }
    tool_cases = [item for item in entries if item.get("expected_tool")]
    rag_cases = [item for item in entries if item.get("expected_documents")]
    sql_cases = [item for item in entries if item["type"] == "text_to_sql"]
    integrated = [item for item in entries if item["type"] == "integrated"]
    latencies = [
        float(item["latency_seconds"])
        for item in entries
        if isinstance(item.get("latency_seconds"), (int, float))
    ]
    failure_categories = Counter(
        item.get("failure_category") for item in entries if not item.get("passed")
    )
    return {
        "total": len(entries),
        "passed": sum(bool(item.get("passed")) for item in entries),
        "pass_rate": ratio(entries, lambda item: item.get("passed")),
        "sql_execution_success_rate": ratio(
            sql_cases, lambda item: item.get("components", {}).get("sql_executed")
        ),
        "answer_fact_accuracy": ratio(
            entries, lambda item: item.get("components", {}).get("facts")
        ),
        "expected_tool_call_rate": ratio(
            tool_cases, lambda item: item.get("components", {}).get("tool")
        ),
        "rag_document_hit_rate": ratio(
            rag_cases, lambda item: item.get("components", {}).get("documents")
        ),
        "citation_section_accuracy": ratio(
            rag_cases, lambda item: item.get("components", {}).get("sections")
        ),
        "integrated_task_pass_rate": ratio(
            integrated, lambda item: item.get("passed")
        ),
        "average_latency_seconds": round(mean(latencies), 3) if latencies else None,
        "by_type": by_type,
        "failure_categories": {
            str(key): value for key, value in sorted(failure_categories.items())
        },
        "estimated_cost_cny": None,
        "cost_note": "服务端未返回可审计计费 Token，V1 不推算费用。",
    }
