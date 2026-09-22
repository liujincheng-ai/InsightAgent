"""Load and select the small, auditable InsightAgent business semantic layer.

The layer deliberately contains definitions and decision rules rather than benchmark
answers.  Selection is deterministic and question-driven so unrelated definitions do
not consume prompt space.  ``INSIGHT_SEMANTIC_PROFILE`` provides an ablation switch:
``baseline``, ``comments``, ``glossary`` or ``combined`` (the default).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SEMANTIC_DIR = Path(__file__).resolve().parent
VALID_PROFILES = {"baseline", "comments", "glossary", "combined"}


@dataclass(frozen=True)
class SemanticDecision:
    """Selected prompt context and ambiguity handling for one question."""

    profile: str
    context: str
    requires_clarification: bool
    clarification_questions: tuple[str, ...]


@lru_cache(maxsize=1)
def _load_glossary() -> dict[str, Any]:
    with (SEMANTIC_DIR / "business_glossary.yaml").open(encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream)
    if not isinstance(loaded, dict):
        raise ValueError("business_glossary.yaml 顶层必须是对象")
    return loaded


def get_semantic_profile(value: str | None = None) -> str:
    """Return a validated semantic ablation profile."""

    profile = (
        (value or os.getenv("INSIGHT_SEMANTIC_PROFILE", "combined")).strip().lower()
    )
    if profile not in VALID_PROFILES:
        raise ValueError(
            "INSIGHT_SEMANTIC_PROFILE 必须是 baseline/comments/glossary/combined"
        )
    return profile


def _matches(question: str, terms: list[str]) -> bool:
    normalized = re.sub(r"\s+", "", question).lower()
    return any(re.sub(r"\s+", "", str(term)).lower() in normalized for term in terms)


def _selected_metrics(question: str, glossary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        definition
        for definition in glossary.get("metrics", [])
        if _matches(question, definition.get("triggers", []))
    ]


def _schema_lines(question: str, glossary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in glossary.get("schema_semantics", []):
        if _matches(question, item.get("triggers", [])):
            lines.append(str(item["definition"]))
    return lines


def _ambiguity_questions(question: str, glossary: dict[str, Any]) -> list[str]:
    normalized = re.sub(r"\s+", "", question)
    questions: list[str] = []
    for rule in glossary.get("ambiguity_rules", []):
        if not _matches(question, rule.get("triggers", [])):
            continue
        explicit_markers = rule.get("resolved_by", [])
        if not any(str(marker) in normalized for marker in explicit_markers):
            questions.append(str(rule["question"]))
    return questions


def build_semantic_context(
    question: str, profile: str | None = None
) -> SemanticDecision:
    """Select only relevant schema and metric definitions for a SQL question."""

    selected_profile = get_semantic_profile(profile)
    if selected_profile == "baseline":
        return SemanticDecision(selected_profile, "- 不注入新增业务语义。", False, ())

    glossary = _load_glossary()
    sections: list[str] = []
    if selected_profile in {"comments", "combined"}:
        schema_lines = _schema_lines(question, glossary)
        if schema_lines:
            sections.append(
                "### 相关 Schema 语义\n" + "\n".join(f"- {x}" for x in schema_lines)
            )

    ambiguity = _ambiguity_questions(question, glossary)
    if selected_profile in {"glossary", "combined"}:
        metrics = _selected_metrics(question, glossary)
        if metrics:
            metric_lines = []
            for item in metrics:
                metric_lines.append(
                    f"- {item['name']}：{item['definition']}；SQL 口径：{item['sql']}；"
                    f"单位：{item['unit']}。"
                )
            sections.append("### 相关指标词典\n" + "\n".join(metric_lines))
        if ambiguity:
            sections.append(
                "### 高风险歧义\n- 当前问题缺少关键口径，禁止静默假设；"
                "不要执行 SQL，直接 terminate 并逐项询问：" + "；".join(ambiguity)
            )

    context = "\n\n".join(sections) or "- 当前问题没有命中需额外注入的语义定义。"
    return SemanticDecision(
        selected_profile,
        context,
        bool(ambiguity and selected_profile in {"glossary", "combined"}),
        tuple(ambiguity),
    )
