"""Contracts for the frozen Week 4 Agent reliability benchmark."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

CASE_TYPE_COUNTS = {
    "sql_correctable": 3,
    "no_data": 3,
    "rag_empty": 3,
    "invalid_arguments": 3,
    "permission_denied": 2,
    "tool_exception": 2,
    "timeout": 2,
    "mixed_partial": 2,
}
SPLIT_COUNTS = {"dev": 12, "test": 6, "challenge": 2}
MODES = {"database", "knowledge", "integrated"}
RECOVERY_ACTIONS = {"retry", "replan", "terminate"}
COMPLETION_STATUSES = {"success", "failed", "partial"}
REQUIRED_FIELDS = {
    "id",
    "split",
    "case_type",
    "mode",
    "question",
    "expected_initial_tool",
    "expected_failure_type",
    "expected_recovery_action",
    "expected_completion",
    "max_steps",
    "fault_plan",
    "tags",
}


def load_reliability_dataset(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_reliability_dataset(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if dataset.get("dataset_status") != "frozen-before-model-run":
        errors.append("dataset_status 必须是 frozen-before-model-run")
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return [*errors, "cases 必须是数组"]
    if len(cases) != 20:
        errors.append(f"数据集必须包含 20 条，实际 {len(cases)} 条")
    ids: set[str] = set()
    questions: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"第 {index} 条不是对象")
            continue
        label = str(case.get("id") or f"第 {index} 条")
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            errors.append(f"{label} 缺少字段: {', '.join(sorted(missing))}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{label} id 无效")
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
        if case.get("mode") not in MODES:
            errors.append(f"{label} mode 无效")
        if case.get("expected_recovery_action") not in RECOVERY_ACTIONS:
            errors.append(f"{label} expected_recovery_action 无效")
        if case.get("expected_completion") not in COMPLETION_STATUSES:
            errors.append(f"{label} expected_completion 无效")
        if not isinstance(case.get("max_steps"), int) or case.get("max_steps", 0) < 1:
            errors.append(f"{label} max_steps 无效")
        plan = case.get("fault_plan")
        if not isinstance(plan, list) or not plan:
            errors.append(f"{label} fault_plan 必须是非空数组")
            continue
        for step in plan:
            if (
                not isinstance(step, dict)
                or not isinstance(step.get("tool"), str)
                or "outcome" not in step
            ):
                errors.append(f"{label} 包含无效 fault_plan")
                break
    type_counts = Counter(case.get("case_type") for case in cases)
    if dict(type_counts) != CASE_TYPE_COUNTS:
        errors.append(f"类型配额应为 {CASE_TYPE_COUNTS}，实际 {dict(type_counts)}")
    split_counts = Counter(case.get("split") for case in cases)
    if dict(split_counts) != SPLIT_COUNTS:
        errors.append(f"Split 配额应为 {SPLIT_COUNTS}，实际 {dict(split_counts)}")
    return errors


def select_reliability_cases(
    dataset: dict[str, Any], split: str
) -> list[dict[str, Any]]:
    if split == "all":
        return list(dataset["cases"])
    return [case for case in dataset["cases"] if case["split"] == split]


def reliability_case_by_id(
    dataset: dict[str, Any], case_id: str
) -> dict[str, Any] | None:
    return next(
        (
            case
            for case in dataset.get("cases", [])
            if case.get("id") == case_id
        ),
        None,
    )
