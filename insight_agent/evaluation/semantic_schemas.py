"""Contracts for the frozen Week 1 SQL semantic benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import load_dataset

SPLIT_COUNTS = {"dev": 18, "test": 8, "challenge": 4}


def load_semantic_datasets(dataset_dir: str | Path) -> dict[str, dict[str, Any]]:
    directory = Path(dataset_dir)
    return {
        split: load_dataset(directory / f"sql_semantic_{split}.json")
        for split in SPLIT_COUNTS
    }


def validate_semantic_datasets(datasets: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    questions: set[str] = set()
    tag_set: set[str] = set()
    for split, expected_count in SPLIT_COUNTS.items():
        dataset = datasets.get(split, {})
        cases = dataset.get("cases")
        if dataset.get("dataset_status") != "frozen-before-model-run":
            errors.append(f"{split}: dataset_status 无效")
        if dataset.get("split") != split:
            errors.append(f"{split}: split 字段无效")
        if not isinstance(cases, list) or len(cases) != expected_count:
            errors.append(f"{split}: 应包含 {expected_count} 题")
            continue
        for case in cases:
            case_id = case.get("id")
            question = case.get("question")
            if not case_id or case_id in ids:
                errors.append(f"{split}: ID 缺失或重复 {case_id}")
            ids.add(case_id)
            if not question or question in questions:
                errors.append(f"{split}: 问题缺失或重复 {question}")
            questions.add(question)
            tags = case.get("semantic_tags")
            if not isinstance(tags, list) or not tags:
                errors.append(f"{case_id}: semantic_tags 缺失")
            else:
                tag_set.update(tags)
            if case.get("requires_clarification"):
                if case.get("gold_sql") or not case.get("expected_clarification_terms"):
                    errors.append(f"{case_id}: 歧义题契约无效")
            elif not case.get("gold_sql") or not isinstance(
                case.get("gold_result"), dict
            ):
                errors.append(f"{case_id}: 必须包含 Gold SQL 和 Gold result")
            if not isinstance(case.get("numeric_tolerance"), (int, float)):
                errors.append(f"{case_id}: numeric_tolerance 无效")
    required_classes = {
        "time",
        "join",
        "join_duplicate",
        "sales_vs_quantity",
        "weighted_margin",
        "contribution",
        "no_data",
        "ambiguity",
        "fact_completeness",
    }
    missing = required_classes - tag_set
    if missing:
        errors.append("缺少语义错误类型: " + ", ".join(sorted(missing)))
    if len(ids) != 30:
        errors.append(f"总题数必须为 30，实际 {len(ids)}")
    return errors
