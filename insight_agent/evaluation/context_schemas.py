"""Schemas and validation for the Week 5 long-context frozen set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VALID_SPLITS = {"dev", "test", "challenge"}
VALID_MODES = {"database", "rag", "integrated"}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_long_context_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_long_context_dataset(data)
    if errors:
        raise ValueError("第五周长链数据集校验失败:\n- " + "\n- ".join(errors))
    return data


def validate_long_context_dataset(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = data.get("cases")
    if not isinstance(cases, list):
        return ["cases 必须是数组"]
    if len(cases) != 20:
        errors.append(f"冻结集必须为 20 题，实际为 {len(cases)}")

    ids: set[str] = set()
    split_counts = {name: 0 for name in VALID_SPLITS}
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}.id 缺失")
        elif case_id in ids:
            errors.append(f"重复 ID: {case_id}")
        else:
            ids.add(case_id)
        split = case.get("split")
        if split not in VALID_SPLITS:
            errors.append(f"{prefix}.split 非法: {split}")
        else:
            split_counts[split] += 1
        if case.get("mode") not in VALID_MODES:
            errors.append(f"{prefix}.mode 非法: {case.get('mode')}")
        turns = case.get("turns")
        if (
            not isinstance(turns, list)
            or not turns
            or not all(isinstance(turn, str) and turn.strip() for turn in turns)
        ):
            errors.append(f"{prefix}.turns 必须是非空字符串数组")
        facts = case.get("expected_facts", [])
        if not isinstance(facts, list):
            errors.append(f"{prefix}.expected_facts 必须是数组")
        for fact_index, fact in enumerate(facts):
            if not isinstance(fact, dict) or "accepted_values" not in fact:
                errors.append(
                    f"{prefix}.expected_facts[{fact_index}] 缺少 accepted_values"
                )

    expected_counts = {"dev": 12, "test": 6, "challenge": 2}
    if split_counts != expected_counts:
        errors.append(f"split 数量必须为 {expected_counts}，实际为 {split_counts}")
    return errors
