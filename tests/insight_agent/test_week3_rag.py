from __future__ import annotations

from pathlib import Path

from insight_agent.evaluation.citation_check import score_structured_answer
from insight_agent.evaluation.rag_metrics import (
    score_retrieval_case,
    summarize_retrieval_records,
)
from insight_agent.evaluation.rag_retrieval import build_chunks, decompose_query
from insight_agent.evaluation.rag_schemas import (
    CASE_TYPE_COUNTS,
    SPLIT_COUNTS,
    load_rag_dataset,
    validate_rag_dataset,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "insight_agent/evaluation/dataset/rag_test.json"
KNOWLEDGE = ROOT / "insight_agent/knowledge"
DISTRACTORS = ROOT / "insight_agent/evaluation/fixtures/rag_distractors"


def test_week3_dataset_is_frozen_and_valid() -> None:
    dataset = load_rag_dataset(DATASET)
    assert validate_rag_dataset(dataset) == []
    assert dataset["case_type_counts"] == CASE_TYPE_COUNTS
    assert len(dataset["cases"]) == sum(CASE_TYPE_COUNTS.values())
    assert sum(SPLIT_COUNTS.values()) == 40


def test_experimental_corpus_keeps_formal_and_distractor_documents_separate() -> None:
    formal = {path.name for path in KNOWLEDGE.glob("*.md")}
    distractors = {path.name for path in DISTRACTORS.glob("*.md")}
    assert len(formal) == 6
    assert len(distractors) == 4
    assert formal.isdisjoint(distractors)
    assert any(
        "已废止" in path.read_text(encoding="utf-8")
        for path in DISTRACTORS.glob("*.md")
    )


def test_chunk_builder_preserves_stable_citation_metadata() -> None:
    chunks = build_chunks([KNOWLEDGE, DISTRACTORS], chunk_size=256, chunk_overlap=50)
    assert chunks
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(chunk.metadata.get("document") for chunk in chunks)
    assert all(chunk.metadata.get("section") for chunk in chunks)
    assert {chunk.metadata.get("source_kind") for chunk in chunks} == {
        "policy",
        "distractor",
    }
    old = [chunk for chunk in chunks if "旧版" in chunk.metadata["document"]]
    assert old and all(chunk.metadata["status"] == "obsolete" for chunk in old)


def test_multi_intent_query_is_decomposed_without_model_calls() -> None:
    queries = decompose_query(
        "重点客户达到橙色预警并提出13%折扣诉求时，谁负责处置，折扣由谁审批？"
    )
    assert queries[0].startswith("重点客户达到橙色预警")
    assert "折扣由谁审批" in queries
    assert len(queries) == len(set(queries))


def test_retrieval_metrics_distinguish_document_and_section_hits() -> None:
    case = {
        "gold_sources": [
            {"document": "制度A.md", "section": "4.2"},
            {"document": "制度B.md", "section": "3.1"},
        ]
    }
    results = [
        {"document": "制度A.md", "section": "4.1"},
        {"document": "制度B.md", "section": "3.1"},
    ]
    verdict = score_retrieval_case(case, results, top_k=5)
    assert verdict["document_hit_at_k"] is True
    assert verdict["section_hit_at_k"] is True
    assert verdict["gold_source_coverage_at_k"] == 0.5
    assert verdict["reciprocal_rank"] == 1.0


def test_retrieval_summary_reports_mrr_and_latency() -> None:
    summary = summarize_retrieval_records(
        [
            {
                "should_answer": True,
                "document_hit_at_k": True,
                "section_hit_at_k": True,
                "gold_source_coverage_at_k": 1.0,
                "reciprocal_rank": 1.0,
                "retrieval_latency_seconds": 0.1,
            },
            {
                "should_answer": True,
                "document_hit_at_k": False,
                "section_hit_at_k": False,
                "gold_source_coverage_at_k": 0.0,
                "reciprocal_rank": 0.0,
                "retrieval_latency_seconds": 0.3,
            },
        ],
        top_k=5,
    )
    assert summary["document_hit_at_k"] == 0.5
    assert summary["mrr"] == 0.5
    assert summary["average_retrieval_latency_seconds"] == 0.2


def test_citation_checker_accepts_supported_claim() -> None:
    case = {
        "should_answer": True,
        "gold_sources": [{"document": "制度.md", "section": "4.2"}],
        "expected_facts": [
            {"name": "threshold", "accepted_values": ["超过15%还须总经理批准"]}
        ],
        "unacceptable_conclusions": [],
    }
    raw = """{
      "answer":"超过15%还须总经理批准。",
      "insufficient_evidence":false,
      "claims":[{"claim":"超过15%还须总经理批准","source_document":"制度.md","section":"4.2","evidence":"超过15%还须总经理批准"}]
    }"""
    verdict = score_structured_answer(case, raw)
    assert verdict["pass_fail"] is True
    assert verdict["fabricated_citation_count"] == 0
    assert verdict["citation_verdicts"][0]["supported"] is True


def test_citation_checker_rejects_unsupported_source() -> None:
    case = {
        "should_answer": True,
        "gold_sources": [{"document": "正式制度.md", "section": "4.2"}],
        "expected_facts": [{"name": "limit", "accepted_values": ["8%"]}],
        "unacceptable_conclusions": [],
    }
    raw = """{
      "answer":"标准折扣为8%。",
      "insufficient_evidence":false,
      "claims":[{"claim":"标准折扣为8%","source_document":"旧版.md","section":"2.1","evidence":"8%"}]
    }"""
    verdict = score_structured_answer(case, raw)
    assert verdict["pass_fail"] is False
    assert verdict["fabricated_citation_count"] == 1
    assert verdict["failure_category"] == "citation_not_supporting_claim"


def test_no_answer_requires_explicit_refusal_without_citations() -> None:
    case = {
        "should_answer": False,
        "gold_sources": [],
        "expected_facts": [],
        "unacceptable_conclusions": ["住宿费上限为500元"],
    }
    accepted = score_structured_answer(
        case,
        '{"answer":"现有制度未规定该事项，证据不足。","insufficient_evidence":true,"claims":[]}',
    )
    invented = score_structured_answer(
        case,
        '{"answer":"住宿费上限为500元。","insufficient_evidence":false,"claims":[]}',
    )
    assert accepted["pass_fail"] is True
    assert accepted["no_answer_correct"] is True
    assert invented["pass_fail"] is False
    assert invented["failure_category"] == "no_answer_hallucination"
