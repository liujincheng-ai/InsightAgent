"""Claim-to-citation checks for structured Week 3 answers."""

from __future__ import annotations

import json
import re
from typing import Any

from .rag_metrics import fact_accuracy, normalize_text, source_key

INSUFFICIENT_TERMS = ("证据不足", "制度未规定", "无法从现有制度", "没有足够证据")
NEGATION_TERMS = ("不", "不是", "不能", "不得", "禁止", "并非", "不可", "未")


def parse_structured_answer(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    candidate = fenced.group(1) if fenced else text
    if not candidate.startswith("{"):
        match = re.search(r"\{.*\}", candidate, flags=re.S)
        candidate = match.group(0) if match else ""
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return {
            "answer": raw,
            "claims": [],
            "insufficient_evidence": False,
            "parse_error": True,
        }
    return {
        "answer": str(parsed.get("answer") or ""),
        "claims": parsed.get("claims")
        if isinstance(parsed.get("claims"), list)
        else [],
        "insufficient_evidence": bool(parsed.get("insufficient_evidence")),
        "parse_error": False,
    }


def score_structured_answer(
    case: dict[str, Any],
    raw: str,
    *,
    retrieved: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parsed = parse_structured_answer(raw)
    answer = parsed["answer"] or raw
    accuracy, missing = fact_accuracy(case, answer)
    gold = {
        source_key(item["document"], item["section"])
        for item in case.get("gold_sources", [])
    }
    expected_terms = {
        normalize_text(value)
        for fact in case.get("expected_facts", [])
        for value in fact.get("accepted_values", [])
    }
    retrieved_by_source: dict[tuple[str, str], list[str]] = {}
    for item in retrieved or []:
        pair = source_key(item.get("document", ""), item.get("section", ""))
        retrieved_by_source.setdefault(pair, []).append(
            normalize_text(item.get("content", ""))
        )
    verdicts: list[dict[str, Any]] = []
    fabricated = 0
    for claim in parsed["claims"]:
        if not isinstance(claim, dict):
            fabricated += 1
            continue
        pair = source_key(claim.get("source_document", ""), claim.get("section", ""))
        claim_text = normalize_text(claim.get("claim", ""))
        evidence_text = normalize_text(claim.get("evidence", ""))
        source_valid = (
            pair in retrieved_by_source if retrieved is not None else pair in gold
        )
        gold_aligned = pair in gold
        if retrieved is not None:
            source_chunks = retrieved_by_source.get(pair, [])
            content_supported = bool(evidence_text) and any(
                evidence_text in content for content in source_chunks
            )
        else:
            content_supported = any(
                term and (term in claim_text or term in evidence_text)
                for term in expected_terms
            )
        supported = source_valid and content_supported
        if not source_valid:
            fabricated += 1
        verdicts.append(
            {
                "claim": claim.get("claim"),
                "document": claim.get("source_document"),
                "section": claim.get("section"),
                "source_valid": source_valid,
                "gold_aligned": gold_aligned,
                "content_supported": content_supported,
                "supported": supported,
            }
        )
    normalized_answer = normalize_text(answer)
    unacceptable = [
        value
        for value in case.get("unacceptable_conclusions", [])
        if _contains_unnegated(normalized_answer, normalize_text(value))
    ]
    if case["should_answer"]:
        no_answer_correct = None
        passed = (
            not parsed["parse_error"]
            and accuracy == 1.0
            and bool(verdicts)
            and all(item["supported"] for item in verdicts)
            and not unacceptable
        )
    else:
        has_insufficient_phrase = any(term in answer for term in INSUFFICIENT_TERMS)
        no_answer_correct = (
            parsed["insufficient_evidence"]
            and has_insufficient_phrase
            and not parsed["claims"]
            and not unacceptable
        )
        passed = not parsed["parse_error"] and no_answer_correct
    return {
        "structured_answer": parsed,
        "answer_fact_accuracy": accuracy,
        "missing_facts": missing,
        "citation_verdicts": verdicts,
        "fabricated_citation_count": fabricated,
        "unacceptable_conclusions_found": unacceptable,
        "no_answer_correct": no_answer_correct,
        "pass_fail": bool(passed),
        "failure_category": _failure_category(
            parsed, accuracy, verdicts, unacceptable, no_answer_correct
        ),
    }


def _contains_unnegated(answer: str, conclusion: str) -> bool:
    if not conclusion:
        return False
    start = 0
    while True:
        index = answer.find(conclusion, start)
        if index < 0:
            return False
        prefix = answer[max(0, index - 32) : index]
        if not any(term in prefix for term in NEGATION_TERMS):
            return True
        start = index + len(conclusion)


def _failure_category(
    parsed: dict[str, Any],
    accuracy: float | None,
    verdicts: list[dict[str, Any]],
    unacceptable: list[str],
    no_answer_correct: bool | None,
) -> str | None:
    if parsed["parse_error"]:
        return "structured_output_parse"
    if no_answer_correct is False:
        return "no_answer_hallucination"
    if accuracy is not None and accuracy < 1.0:
        return "answer_fact_accuracy"
    if not verdicts and no_answer_correct is None:
        return "citation_missing"
    if any(not item["supported"] for item in verdicts):
        return "citation_not_supporting_claim"
    if unacceptable:
        return "unacceptable_conclusion"
    return None
