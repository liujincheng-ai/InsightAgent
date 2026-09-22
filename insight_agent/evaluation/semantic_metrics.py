"""Deterministic result and answer scoring for the Week 1 SQL benchmark."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable

NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def _tables(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in str(text).splitlines()]
    tables: list[dict[str, Any]] = []
    index = 0
    while index + 1 < len(lines):
        if not (lines[index].startswith("|") and lines[index + 1].startswith("|")):
            index += 1
            continue
        separator = [cell.strip() for cell in lines[index + 1].strip("|").split("|")]
        if not separator or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            index += 1
            continue
        columns = [cell.strip() for cell in lines[index].strip("|").split("|")]
        rows: list[list[Any]] = []
        index += 2
        while index < len(lines) and lines[index].startswith("|"):
            cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
            rows.append([_coerce(cell) for cell in cells])
            index += 1
        tables.append({"columns": columns, "rows": rows})
    return tables


def _coerce(value: str) -> Any:
    normalized = value.replace(",", "").strip()
    if normalized.lower() in {"null", "none", "无数据", "n/a", ""}:
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?%?", normalized):
        number = float(normalized.rstrip("%"))
        return int(number) if number.is_integer() and "." not in normalized else number
    return value.strip()


def extract_actual_tables(
    events: list[dict[str, Any]], answer: str
) -> list[dict[str, Any]]:
    """Extract Markdown result tables without trusting model-written SQL text."""

    content = [
        str(event.get("content", ""))
        for event in events
        if event.get("type") == "step.chunk"
    ]
    content.append(answer)
    tables: list[dict[str, Any]] = []
    for item in content:
        tables.extend(_tables(item))
    return tables


def _value_matches(expected: Any, actual: Any, tolerance: float) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        expected_number = float(expected)
        actual_number = float(actual)
        if abs(expected_number - actual_number) <= tolerance:
            return True
        # SQL commonly returns a decimal ratio while the Gold result and final
        # business answer use percent.  Treat these as unit-normalized values.
        return (
            abs(expected_number) > 1
            and abs(actual_number) <= 1
            and abs(expected_number - actual_number * 100) <= tolerance
        )
    return (
        "".join(str(expected).split()).lower() == "".join(str(actual).split()).lower()
    )


def _row_contains(expected: list[Any], actual: list[Any], tolerance: float) -> bool:
    """Return whether each Gold value has a distinct matching actual cell."""

    remaining = list(range(len(actual)))
    for expected_value in expected:
        found = next(
            (
                pos
                for pos in remaining
                if _value_matches(expected_value, actual[pos], tolerance)
            ),
            None,
        )
        if found is None:
            return False
        remaining.remove(found)
    return True


def result_matches(
    gold_result: dict[str, Any], actual_tables: list[dict[str, Any]], tolerance: float
) -> bool:
    gold_rows = gold_result.get("rows", [])
    for table in actual_tables:
        unmatched = list(table.get("rows", []))
        matched_all = True
        for gold_row in gold_rows:
            match_index = next(
                (
                    idx
                    for idx, row in enumerate(unmatched)
                    if _row_contains(gold_row, row, tolerance)
                ),
                None,
            )
            if match_index is None:
                matched_all = False
                break
            unmatched.pop(match_index)
        if matched_all:
            return True
    return False


def _answer_contains(value: Any, answer: str, tolerance: float) -> bool:
    if value is None:
        return any(
            marker in answer for marker in ("无数据", "没有记录", "未查询到", "NULL")
        )
    if isinstance(value, (int, float)):
        numbers = [float(token.replace(",", "")) for token in NUMBER_RE.findall(answer)]
        return any(abs(number - float(value)) <= tolerance for number in numbers)
    return "".join(str(value).split()).lower() in "".join(answer.split()).lower()


def score_semantic_case(
    case: dict[str, Any], actual: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    answer = str(actual.get("actual_answer", ""))
    if case.get("requires_clarification"):
        terms = case.get("expected_clarification_terms", [])
        clarification_passed = bool(answer) and all(term in answer for term in terms)
        no_sql_passed = not actual.get("actual_sql")
        components = {
            "runtime": bool(answer) and not actual.get("error"),
            "clarification": clarification_passed,
            "no_sql_before_clarification": no_sql_passed,
        }
        passed = all(components.values())
        return {
            "passed": passed,
            "components": components,
            "failure_category": None if passed else "ambiguity_handling",
            "actual_tables": [],
        }

    tables = extract_actual_tables(events, answer)
    tolerance = float(case.get("numeric_tolerance", 0.02))
    result_passed = result_matches(case["gold_result"], tables, tolerance)
    gold_values = [value for row in case["gold_result"]["rows"] for value in row]
    answer_passed = all(
        _answer_contains(value, answer, tolerance) for value in gold_values
    )
    components = {
        "runtime": bool(answer) and not actual.get("error"),
        "sql_executed": bool(actual.get("sql_executed")),
        "result_set": result_passed,
        "answer_facts": answer_passed,
        "semantic_evidence": result_passed or answer_passed,
    }
    passed = all(
        components[key]
        for key in ("runtime", "sql_executed", "semantic_evidence", "answer_facts")
    )
    priority = (
        ("runtime", "runtime_or_timeout"),
        ("sql_executed", "sql_generation_or_execution"),
        ("semantic_evidence", "sql_semantic_result"),
        ("answer_facts", "answer_fact_completeness"),
    )
    failure = next(
        (category for key, category in priority if not components[key]), None
    )
    return {
        "passed": passed,
        "components": components,
        "failure_category": failure,
        "actual_tables": tables,
    }


def summarize_semantic_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    entries = list(records)
    sql_entries = [item for item in entries if not item.get("requires_clarification")]
    ambiguity = [item for item in entries if item.get("requires_clarification")]

    def ratio(items: list[dict[str, Any]], key: str) -> float | None:
        if not items:
            return None
        return round(
            sum(bool(item.get("components", {}).get(key)) for item in items)
            / len(items),
            4,
        )

    tags: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in entries:
        for tag in item.get("semantic_tags", []):
            tags[tag].append(item)
    failures = Counter(
        item.get("failure_category") for item in entries if not item.get("passed")
    )
    return {
        "total": len(entries),
        "passed": sum(bool(item.get("passed")) for item in entries),
        "pass_rate": round(
            sum(bool(item.get("passed")) for item in entries) / len(entries), 4
        )
        if entries
        else None,
        "sql_execution_success": ratio(sql_entries, "sql_executed"),
        "result_set_accuracy": ratio(sql_entries, "result_set"),
        "answer_fact_accuracy": ratio(sql_entries, "answer_facts"),
        "ambiguity_handling_accuracy": ratio(ambiguity, "clarification"),
        "no_sql_before_clarification_rate": ratio(
            ambiguity, "no_sql_before_clarification"
        ),
        "by_semantic_tag": {
            tag: {
                "total": len(items),
                "passed": sum(bool(item.get("passed")) for item in items),
                "pass_rate": round(
                    sum(bool(item.get("passed")) for item in items) / len(items), 4
                ),
            }
            for tag, items in sorted(tags.items())
        },
        "failure_categories": {
            str(key): value for key, value in sorted(failures.items())
        },
    }
