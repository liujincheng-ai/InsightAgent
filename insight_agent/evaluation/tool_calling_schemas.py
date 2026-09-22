"""Contracts and validators for the frozen Week 2 Tool Calling dataset."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

TOOL_NAMES = {
    "sales_diagnosis_tool",
    "customer_loss_analysis_tool",
    "dealer_health_analysis_tool",
}
ROUTING_LABELS = TOOL_NAMES | {"sql_query"}
CASE_TYPE_COUNTS = {
    "sales_diagnosis": 10,
    "customer_loss": 10,
    "dealer_health": 10,
    "no_business_tool": 5,
    "combination": 5,
}
SPLIT_COUNTS = {"dev": 24, "test": 12, "challenge": 4}
REQUIRED_FIELDS = {
    "id",
    "split",
    "case_type",
    "question",
    "expected_calls",
    "tags",
}


def load_tool_calling_dataset(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_tool_calling_dataset(dataset: dict[str, Any]) -> list[str]:
    """Validate quotas, split isolation and expected call contracts."""

    errors: list[str] = []
    if dataset.get("dataset_status") != "frozen-before-model-run":
        errors.append("dataset_status 必须为 frozen-before-model-run")
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return [*errors, "cases 必须是数组"]
    if len(cases) != 40:
        errors.append(f"数据集必须包含 40 条，实际 {len(cases)} 条")
    ids: set[str] = set()
    questions: set[str] = set()
    for index, case in enumerate(cases, start=1):
        label = (
            case.get("id", f"第 {index} 条")
            if isinstance(case, dict)
            else f"第 {index} 条"
        )
        if not isinstance(case, dict):
            errors.append(f"第 {index} 条不是对象")
            continue
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            errors.append(f"{label} 缺少字段: {', '.join(sorted(missing))}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"第 {index} 条 id 无效")
        elif case_id in ids:
            errors.append(f"id 重复: {case_id}")
        else:
            ids.add(case_id)
        question = case.get("question")
        if not isinstance(question, str) or not question.strip():
            errors.append(f"{label} question 无效")
        elif question in questions:
            errors.append(f"问题重复: {label}")
        else:
            questions.add(question)
        if case.get("split") not in SPLIT_COUNTS:
            errors.append(f"{label} split 无效")
        if case.get("case_type") not in CASE_TYPE_COUNTS:
            errors.append(f"{label} case_type 无效")
        expected_calls = case.get("expected_calls")
        if not isinstance(expected_calls, list) or not expected_calls:
            errors.append(f"{label} expected_calls 必须是非空数组")
            continue
        for call in expected_calls:
            if not isinstance(call, dict) or not {"tool", "arguments"} <= set(call):
                errors.append(f"{label} expected_calls 包含无效项")
                continue
            if call.get("tool") not in ROUTING_LABELS:
                errors.append(f"{label} 包含未知 Tool: {call.get('tool')}")
            if not isinstance(call.get("arguments"), dict):
                errors.append(f"{label} arguments 必须是对象")
        expected_tools = [call.get("tool") for call in expected_calls]
        case_type = case.get("case_type")
        if case_type == "no_business_tool" and expected_tools != ["sql_query"]:
            errors.append(f"{label} no_business_tool 必须只期望 sql_query")
        if case_type == "combination" and len(expected_tools) < 2:
            errors.append(f"{label} combination 至少需要两个 Tool")
        if case_type not in {"no_business_tool", "combination"}:
            expected = {
                "sales_diagnosis": "sales_diagnosis_tool",
                "customer_loss": "customer_loss_analysis_tool",
                "dealer_health": "dealer_health_analysis_tool",
            }.get(case_type)
            if expected_tools != [expected]:
                errors.append(f"{label} 期望 Tool 应为 {expected}")
    type_counts = Counter(case.get("case_type") for case in cases)
    if dict(type_counts) != CASE_TYPE_COUNTS:
        errors.append(f"类型配额应为 {CASE_TYPE_COUNTS}，实际 {dict(type_counts)}")
    split_counts = Counter(case.get("split") for case in cases)
    if dict(split_counts) != SPLIT_COUNTS:
        errors.append(f"Split 配额应为 {SPLIT_COUNTS}，实际 {dict(split_counts)}")
    return errors


def select_tool_calling_cases(
    dataset: dict[str, Any], split: str
) -> list[dict[str, Any]]:
    if split == "all":
        return list(dataset["cases"])
    return [case for case in dataset["cases"] if case["split"] == split]
