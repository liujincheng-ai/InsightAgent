from __future__ import annotations

import json
from pathlib import Path

from insight_agent.evaluation.day3_benchmark import summarize_records, validate_dataset

ROOT = Path(__file__).resolve().parents[2]


def test_day3_dataset_is_frozen_and_has_the_planned_mix() -> None:
    dataset = json.loads(
        (
            ROOT / "insight_agent" / "evaluation" / "dataset" / "day3_initial.json"
        ).read_text(encoding="utf-8")
    )
    assert dataset["dataset_status"] == "frozen-before-pro-run"
    assert validate_dataset(dataset) == []


def test_day3_summary_keeps_failure_and_latency_metrics() -> None:
    summary = summarize_records(
        [
            {
                "type": "sql",
                "passed": True,
                "sql_executed": True,
                "latency_seconds": 2.0,
                "estimated_cost_cny": 0.1,
            },
            {
                "type": "tool",
                "passed": False,
                "expected_tool": "sales_diagnosis_tool",
                "actual_tools": [],
                "latency_seconds": 4.0,
                "estimated_cost_cny": 0.2,
            },
            {
                "type": "integrated",
                "passed": True,
                "expected_tool": "sales_diagnosis_tool",
                "actual_tools": ["sales_diagnosis_tool"],
                "expected_sources": ["制度"],
                "actual_sources": ["制度"],
                "latency_seconds": 6.0,
                "estimated_cost_cny": 0.3,
            },
        ]
    )
    assert summary["total"] == 3
    assert summary["pass_rate"] == 0.6667
    assert summary["expected_tool_call_rate"] == 0.5
    assert summary["integrated_task_pass_rate"] == 1.0
    assert summary["average_latency_seconds"] == 4.0
