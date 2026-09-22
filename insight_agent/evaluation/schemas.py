"""Dataset and result contracts for the frozen InsightAgent V1 benchmark."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

CASE_COUNTS = {
    "text_to_sql": 8,
    "rag": 6,
    "sales_diagnosis": 3,
    "customer_loss": 3,
    "dealer_health": 3,
    "integrated": 7,
}
TOOL_BY_TYPE = {
    "sales_diagnosis": "sales_diagnosis_tool",
    "customer_loss": "customer_loss_analysis_tool",
    "dealer_health": "dealer_health_analysis_tool",
}
REQUIRED_CASE_FIELDS = {
    "id",
    "type",
    "question",
    "expected_facts",
    "numeric_tolerance",
    "grading",
}


def load_dataset(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 benchmark dataset."""

    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def file_sha256(path: str | Path) -> str:
    """Return a stable fingerprint used by the run manifest."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dataset(
    dataset: dict[str, Any], *, expected_size: int | None = None
) -> list[str]:
    """Validate one dev/test dataset without mutating it."""

    errors: list[str] = []
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return ["cases 必须是数组"]
    if expected_size is not None and len(cases) != expected_size:
        errors.append(f"cases 必须包含 {expected_size} 条，实际 {len(cases)} 条")
    if dataset.get("dataset_status") != "frozen-before-model-run":
        errors.append("dataset_status 必须为 frozen-before-model-run")
    seen: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"第 {index} 条任务不是对象")
            continue
        case_id = case.get("id", f"第 {index} 条")
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            errors.append(f"{case_id} 缺少字段: {', '.join(sorted(missing))}")
        if not isinstance(case.get("id"), str) or not case.get("id"):
            errors.append(f"第 {index} 条任务 id 无效")
        elif case_id in seen:
            errors.append(f"任务 id 重复: {case_id}")
        else:
            seen.add(case_id)
        case_type = case.get("type")
        if case_type not in CASE_COUNTS:
            errors.append(f"{case_id} type 无效: {case_type}")
        if not isinstance(case.get("question"), str) or not case.get("question"):
            errors.append(f"{case_id} question 无效")
        facts = case.get("expected_facts")
        if not isinstance(facts, list) or not facts:
            errors.append(f"{case_id} expected_facts 必须是非空数组")
        else:
            for fact in facts:
                if not isinstance(fact, dict) or not {"name", "value"} <= set(fact):
                    errors.append(f"{case_id} 包含无效 expected_fact")
                    break
        expected_tool = case.get("expected_tool")
        required_tool = TOOL_BY_TYPE.get(case_type)
        if required_tool and expected_tool != required_tool:
            errors.append(f"{case_id} expected_tool 必须为 {required_tool}")
        if case_type == "integrated" and not expected_tool:
            errors.append(f"{case_id} 综合任务必须声明 expected_tool")
        documents = case.get("expected_documents", [])
        sections = case.get("expected_sections", [])
        if case_type in {"rag", "integrated"}:
            if not documents or not sections:
                errors.append(f"{case_id} 必须声明制度文档和章节")
        if not isinstance(case.get("numeric_tolerance"), (int, float)):
            errors.append(f"{case_id} numeric_tolerance 必须是数字")
        if case.get("grading") not in {"deterministic", "deterministic_and_manual"}:
            errors.append(f"{case_id} grading 无效")
        if case_type == "text_to_sql" and not case.get("gold_sql"):
            errors.append(f"{case_id} 必须保存 gold_sql")
    return errors


def validate_v1_pair(
    dev: dict[str, Any], test: dict[str, Any]
) -> list[str]:
    """Validate the 20/10 split and the required 30-case composition."""

    errors = validate_dataset(dev, expected_size=20)
    errors.extend(validate_dataset(test, expected_size=10))
    dev_ids = {case.get("id") for case in dev.get("cases", [])}
    test_ids = {case.get("id") for case in test.get("cases", [])}
    overlap = sorted(dev_ids & test_ids)
    if overlap:
        errors.append(f"dev/test id 重复: {', '.join(overlap)}")
    all_cases = [*dev.get("cases", []), *test.get("cases", [])]
    counts = Counter(case.get("type") for case in all_cases)
    if dict(counts) != CASE_COUNTS:
        errors.append(f"30 条类型配额应为 {CASE_COUNTS}，实际为 {dict(counts)}")
    questions = [case.get("question") for case in all_cases]
    if len(set(questions)) != len(questions):
        errors.append("30 条任务存在重复问题")
    return errors
