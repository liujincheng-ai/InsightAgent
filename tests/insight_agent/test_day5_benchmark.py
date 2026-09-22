from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from insight_agent.evaluation.metrics import score_record, summarize_records
from insight_agent.evaluation.run_eval import evaluate_case, parse_events, run
from insight_agent.evaluation.schemas import (
    CASE_COUNTS,
    file_sha256,
    load_dataset,
    validate_v1_pair,
)

ROOT = Path(__file__).parents[2] / "insight_agent" / "evaluation"


def _datasets() -> tuple[dict, dict]:
    return (
        load_dataset(ROOT / "dataset" / "v1_dev.json"),
        load_dataset(ROOT / "dataset" / "v1_test.json"),
    )


def test_v1_dataset_has_frozen_20_10_split_and_exact_type_counts() -> None:
    dev, test = _datasets()
    assert validate_v1_pair(dev, test) == []
    assert len(dev["cases"]) == 20
    assert len(test["cases"]) == 10
    counts = {
        case_type: sum(
            case["type"] == case_type for case in [*dev["cases"], *test["cases"]]
        )
        for case_type in CASE_COUNTS
    }
    assert counts == CASE_COUNTS


def test_dataset_hash_is_stable_and_nonempty() -> None:
    path = ROOT / "dataset" / "v1_test.json"
    assert len(file_sha256(path)) == 64
    assert file_sha256(path) == file_sha256(path)


def test_parse_events_preserves_tool_sql_answer_and_citations() -> None:
    events = [
        {
            "type": "step.meta",
            "action": "sql_query",
            "action_input": '{"sql":"SELECT 1"}',
        },
        {
            "type": "final",
            "content": "结果为 1",
            "citations": [{"document": "制度.md", "section": "4.2"}],
        },
    ]
    parsed = parse_events(events)
    assert parsed["actual_tools"] == ["sql_query"]
    assert parsed["actual_sql"] == ["SELECT 1"]
    assert parsed["sql_executed"] is False
    assert parsed["actual_answer"] == "结果为 1"
    assert parsed["actual_sources"] == [{"document": "制度.md", "section": "4.2"}]
    assert '"step.meta"' in parsed["raw_trajectory"]


def test_parse_events_distinguishes_sql_attempt_from_successful_observation() -> None:
    failed = parse_events(
        [
            {"type": "step.meta", "action": "sql_query", "action_input": "SELECT 1"},
            {"type": "step.chunk", "content": "SQL 预执行校验失败，数据库未执行"},
        ]
    )
    succeeded = parse_events(
        [
            {"type": "step.meta", "action": "sql_query", "action_input": "SELECT 1"},
            {"type": "step.chunk", "content": "| value |\n| 1 |"},
        ]
    )
    assert failed["actual_sql"] == ["SELECT 1"]
    assert failed["sql_executed"] is False
    assert succeeded["sql_executed"] is True


def test_score_record_handles_rate_representation_and_failure_reason() -> None:
    case = {
        "type": "sales_diagnosis",
        "expected_facts": [
            {
                "name": "qoq",
                "kind": "numeric",
                "value": -0.3268,
                "accepted_values": [-32.68],
                "tolerance": 0.001,
            }
        ],
        "numeric_tolerance": 0.01,
        "expected_tool": "sales_diagnosis_tool",
    }
    passed = score_record(
        case,
        {
            "actual_answer": "环比 -32.68%",
            "raw_trajectory": "",
            "actual_tools": ["sales_diagnosis_tool"],
            "actual_sources": [],
            "error": None,
        },
    )
    assert passed["passed"] is True
    failed = score_record(
        case,
        {
            "actual_answer": "环比 -32.68%",
            "raw_trajectory": "",
            "actual_tools": [],
            "actual_sources": [],
            "error": None,
        },
    )
    assert failed["failure_category"] == "tool_selection"


def test_text_fact_matching_normalizes_human_readable_whitespace() -> None:
    case = {
        "type": "rag",
        "expected_facts": [{"name": "period", "value": "30 天"}],
        "numeric_tolerance": 0.01,
    }
    verdict = score_record(
        case,
        {
            "actual_answer": "设置 30天整改观察期",
            "raw_trajectory": "",
            "actual_tools": [],
            "actual_sources": [],
            "error": None,
        },
    )
    assert verdict["components"]["facts"] is True


def test_summary_keeps_failures_in_denominator() -> None:
    records = [
        {
            "type": "text_to_sql",
            "passed": True,
            "components": {"facts": True, "sql_executed": True},
            "latency_seconds": 1.0,
        },
        {
            "type": "text_to_sql",
            "passed": False,
            "components": {"facts": False, "sql_executed": False},
            "failure_category": "sql_generation_or_execution",
            "latency_seconds": 3.0,
        },
    ]
    summary = summarize_records(records)
    assert summary["total"] == 2
    assert summary["pass_rate"] == 0.5
    assert summary["sql_execution_success_rate"] == 0.5
    assert summary["average_latency_seconds"] == 2.0


def test_evaluate_case_closes_failure_without_dropping_record() -> None:
    case = {
        "id": "case-1",
        "type": "rag",
        "question": "问题",
        "expected_facts": [{"name": "fact", "value": "答案"}],
        "expected_documents": ["制度"],
        "expected_sections": ["1.1"],
        "numeric_tolerance": 0.01,
        "grading": "deterministic_and_manual",
    }

    def broken_transport(_url: str, _payload: dict, _timeout: float) -> list[dict]:
        raise TimeoutError("deadline")

    record, events = evaluate_case(
        case,
        endpoint="http://example.invalid",
        model="test-model",
        temperature=0,
        timeout=1,
        transport=broken_transport,
    )
    assert events == []
    assert record["pass_fail"] == "fail"
    assert record["failure_category"] == "runtime_or_timeout"
    assert "TimeoutError" in record["error"]


def test_evaluate_case_isolates_resources_by_task_type() -> None:
    captured: list[dict] = []

    def transport(_url: str, payload: dict, _timeout: float) -> list[dict]:
        captured.append(payload)
        return [{"type": "final", "content": "答案"}]

    base_case = {
        "id": "case-resource",
        "question": "问题",
        "expected_facts": [{"name": "fact", "value": "答案"}],
        "numeric_tolerance": 0.01,
        "grading": "deterministic",
    }
    for case_type in ("text_to_sql", "rag", "sales_diagnosis", "integrated"):
        case = {**base_case, "type": case_type}
        if case_type == "text_to_sql":
            case["gold_sql"] = "SELECT 1"
        if case_type in {"rag", "integrated"}:
            case["expected_documents"] = ["制度"]
            case["expected_sections"] = ["1.1"]
        if case_type in {"sales_diagnosis", "integrated"}:
            case["expected_tool"] = "sales_diagnosis_tool"
        evaluate_case(
            case,
            endpoint="http://example.invalid",
            model="test-model",
            temperature=0,
            timeout=1,
            transport=transport,
        )
    assert set(captured[0]["ext_info"]) == {"database_name", "database_type"}
    assert set(captured[1]["ext_info"]) == {"knowledge_space_name"}
    assert set(captured[2]["ext_info"]) == {
        "database_name",
        "database_type",
        "knowledge_space_name",
    }
    assert set(captured[3]["ext_info"]) == {
        "database_name",
        "database_type",
        "knowledge_space_name",
    }


def test_run_refuses_to_overwrite_nonempty_results(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")
    args = argparse.Namespace(
        dataset_dir=str(ROOT / "dataset"),
        split="dev",
        output_dir=str(output),
        endpoint="http://example.invalid",
        model="test-model",
        temperature=0.0,
        timeout=1.0,
    )
    with pytest.raises(FileExistsError):
        run(args, transport=lambda *_args: [])
    assert (output / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_run_writes_raw_records_summary_csv_and_manifest(tmp_path: Path) -> None:
    source_dev, source_test = _datasets()
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "v1_dev.json").write_text(
        json.dumps(source_dev, ensure_ascii=False), encoding="utf-8"
    )
    (dataset_dir / "v1_test.json").write_text(
        json.dumps(source_test, ensure_ascii=False), encoding="utf-8"
    )
    output = tmp_path / "results"

    def transport(_url: str, payload: dict, _timeout: float) -> list[dict]:
        return [{"type": "final", "content": f"模拟结果 {payload['user_input']}"}]

    args = argparse.Namespace(
        dataset_dir=str(dataset_dir),
        split="test",
        output_dir=str(output),
        endpoint="http://example.invalid",
        model="test-model",
        temperature=0.0,
        timeout=1.0,
    )
    assert run(args, transport=transport) == 0
    assert len(list((output / "raw").glob("*.json"))) == 10
    assert (output / "records.json").is_file()
    assert (output / "summary.json").is_file()
    assert (output / "summary.csv").is_file()
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_count"] == 10
    assert manifest["raw_trace_preserved"] is True
