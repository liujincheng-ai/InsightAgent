"""Deterministic retrieval and answer metrics for Week 3."""

from __future__ import annotations

import re
from statistics import mean
from typing import Any, Iterable


def normalize_text(value: Any) -> str:
    text = str(value or "").casefold()
    return re.sub(r"[\s`*_《》〈〉\[\]（）()，,。；;：:、\-]+", "", text)


def source_key(document: str, section: str) -> tuple[str, str]:
    return normalize_text(document), normalize_text(section)


def score_retrieval_case(
    case: dict[str, Any], results: list[dict[str, Any]], *, top_k: int
) -> dict[str, Any]:
    gold = {
        source_key(item["document"], item["section"])
        for item in case.get("gold_sources", [])
    }
    ranked_pairs = [
        source_key(item.get("document", ""), item.get("section", ""))
        for item in results[:top_k]
    ]
    ranked_docs = [pair[0] for pair in ranked_pairs]
    gold_docs = {pair[0] for pair in gold}
    first_rank = None
    for index, pair in enumerate(ranked_pairs, start=1):
        if pair in gold or pair[0] in gold_docs:
            first_rank = index
            break
    matched_sources = gold.intersection(ranked_pairs)
    return {
        "document_hit_at_k": None
        if not gold
        else bool(gold_docs.intersection(ranked_docs)),
        "section_hit_at_k": None if not gold else bool(matched_sources),
        "gold_source_coverage_at_k": (
            None if not gold else len(matched_sources) / len(gold)
        ),
        "reciprocal_rank": 0.0 if first_rank is None else 1.0 / first_rank,
        "first_relevant_rank": first_rank,
        "retrieved_count": len(results),
    }


def summarize_retrieval_records(
    records: list[dict[str, Any]], *, top_k: int
) -> dict[str, Any]:
    answerable = [item for item in records if item.get("should_answer")]
    latencies = [float(item["retrieval_latency_seconds"]) for item in records]
    return {
        "case_count": len(records),
        "answerable_case_count": len(answerable),
        "top_k": top_k,
        "document_hit_at_k": _average(answerable, "document_hit_at_k"),
        "section_hit_at_k": _average(answerable, "section_hit_at_k"),
        "gold_source_coverage_at_k": _average(answerable, "gold_source_coverage_at_k"),
        "mrr": _average(answerable, "reciprocal_rank"),
        "average_retrieval_latency_seconds": round(mean(latencies), 4)
        if latencies
        else None,
        "p95_retrieval_latency_seconds": _percentile(latencies, 0.95),
    }


def fact_accuracy(case: dict[str, Any], answer: str) -> tuple[float | None, list[str]]:
    expected = case.get("expected_facts", [])
    if not expected:
        return None, []
    normalized = normalize_text(answer)
    missing: list[str] = []
    for fact in expected:
        variants = [normalize_text(item) for item in fact["accepted_values"]]
        if not any(variant and variant in normalized for variant in variants):
            missing.append(fact["name"])
    return (len(expected) - len(missing)) / len(expected), missing


def summarize_answer_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [item for item in records if item.get("should_answer")]
    no_answer = [item for item in records if not item.get("should_answer")]
    latencies = [float(item["generation_latency_seconds"]) for item in records]
    citations = [
        claim for item in answerable for claim in item.get("citation_verdicts", [])
    ]
    return {
        "case_count": len(records),
        "answer_fact_accuracy": _average(answerable, "answer_fact_accuracy"),
        "citation_precision": _average(citations, "supported"),
        "no_answer_accuracy": _average(no_answer, "no_answer_correct"),
        "fabricated_citation_count": sum(
            int(item.get("fabricated_citation_count", 0)) for item in records
        ),
        "unacceptable_conclusion_count": sum(
            len(item.get("unacceptable_conclusions_found", [])) for item in records
        ),
        "average_generation_latency_seconds": round(mean(latencies), 3)
        if latencies
        else None,
        "pass_rate": _average(records, "pass_fail"),
    }


def _average(records: Iterable[dict[str, Any]], key: str) -> float | None:
    values = [float(item[key]) for item in records if item.get(key) is not None]
    return None if not values else round(sum(values) / len(values), 4)


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * quantile + 0.5)))
    return round(ordered[index], 4)
