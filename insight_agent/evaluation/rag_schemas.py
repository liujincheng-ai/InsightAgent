"""Contracts for the frozen Week 3 retrieval and citation benchmark."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

CASE_TYPE_COUNTS = {
    "single_document": 15,
    "multi_document": 10,
    "exact_clause": 10,
    "no_answer": 5,
}
SPLIT_COUNTS = {"dev": 24, "test": 12, "challenge": 4}
REQUIRED_FIELDS = {
    "id",
    "split",
    "case_type",
    "question",
    "gold_sources",
    "expected_facts",
    "unacceptable_conclusions",
    "should_answer",
    "tags",
}


def load_rag_dataset(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_rag_dataset(dataset: dict[str, Any]) -> list[str]:
    """Validate quotas, source contracts and frozen split isolation."""

    errors: list[str] = []
    if dataset.get("dataset_status") not in {
        "frozen-before-model-run",
        "frozen-before-final-run",
    }:
        errors.append("dataset_status 必须表示模型运行前或最终运行前冻结")
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return [*errors, "cases 必须是数组"]
    if len(cases) != 40:
        errors.append(f"数据集必须包含 40 条，实际 {len(cases)} 条")
    ids: set[str] = set()
    questions: set[str] = set()
    for index, case in enumerate(cases, start=1):
        label = (
            case.get("id", f"第 {index} 条") if isinstance(case, dict) else str(index)
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
        case_type = case.get("case_type")
        if case_type not in CASE_TYPE_COUNTS:
            errors.append(f"{label} case_type 无效")
        sources = case.get("gold_sources")
        facts = case.get("expected_facts")
        should_answer = case.get("should_answer")
        if not isinstance(sources, list) or not isinstance(facts, list):
            errors.append(f"{label} gold_sources/expected_facts 必须是数组")
            continue
        for source in sources:
            if not isinstance(source, dict) or not {"document", "section"} <= set(
                source
            ):
                errors.append(f"{label} 包含无效 Gold 来源")
        for fact in facts:
            if (
                not isinstance(fact, dict)
                or not isinstance(fact.get("name"), str)
                or not isinstance(fact.get("accepted_values"), list)
                or not fact.get("accepted_values")
            ):
                errors.append(f"{label} 包含无效 expected_fact")
        if case_type == "no_answer":
            if should_answer is not False or sources or facts:
                errors.append(
                    f"{label} 无答案题必须无 Gold 来源和事实，"
                    "并设置 should_answer=false"
                )
        elif should_answer is not True or not sources or not facts:
            errors.append(f"{label} 可回答题必须提供 Gold 来源和事实")
        if (
            case_type == "single_document"
            and len({s.get("document") for s in sources}) != 1
        ):
            errors.append(f"{label} 单文档题必须只涉及一份文档")
        if (
            case_type == "multi_document"
            and len({s.get("document") for s in sources}) < 2
        ):
            errors.append(f"{label} 多文档题必须涉及至少两份文档")
    type_counts = Counter(case.get("case_type") for case in cases)
    if dict(type_counts) != CASE_TYPE_COUNTS:
        errors.append(f"类型配额应为 {CASE_TYPE_COUNTS}，实际 {dict(type_counts)}")
    split_counts = Counter(case.get("split") for case in cases)
    if dict(split_counts) != SPLIT_COUNTS:
        errors.append(f"Split 配额应为 {SPLIT_COUNTS}，实际 {dict(split_counts)}")
    return errors


def select_rag_cases(dataset: dict[str, Any], split: str) -> list[dict[str, Any]]:
    if split == "all":
        return list(dataset["cases"])
    return [case for case in dataset["cases"] if case["split"] == split]
