from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

from insight_agent.evaluation.schemas import file_sha256
from insight_agent.evaluation.tool_calling_metrics import (
    extract_tool_calls,
    score_tool_calling_case,
    summarize_tool_calling_records,
)
from insight_agent.evaluation.tool_calling_schemas import (
    CASE_TYPE_COUNTS,
    SPLIT_COUNTS,
    load_tool_calling_dataset,
    select_tool_calling_cases,
    validate_tool_calling_dataset,
)
from insight_agent.tools import build_business_tools
from insight_agent.tools.customer_loss_analysis import customer_loss_analysis_tool
from insight_agent.tools.dealer_health_analysis import dealer_health_analysis_tool
from insight_agent.tools.sales_diagnosis import sales_diagnosis_tool

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "insight_agent" / "evaluation" / "dataset" / "tool_selection_test.json"
DATASET_SHA256 = "996e11265a0bd9efaa3a4a3bf56267a9b94964f24102e1ce0d93602d67521603"


def test_week2_dataset_is_frozen_and_has_required_quotas() -> None:
    dataset = load_tool_calling_dataset(DATASET)

    assert validate_tool_calling_dataset(dataset) == []
    assert file_sha256(DATASET) == DATASET_SHA256
    assert {
        split: len(select_tool_calling_cases(dataset, split)) for split in SPLIT_COUNTS
    } == SPLIT_COUNTS
    assert sum(CASE_TYPE_COUNTS.values()) == 40


def test_ablation_profiles_keep_names_stable_and_add_boundaries_incrementally() -> None:
    baseline = {tool.name: tool for tool in build_business_tools("baseline")}
    positive = {tool.name: tool for tool in build_business_tools("positive")}
    boundary = {tool.name: tool for tool in build_business_tools("boundary")}

    assert (
        set(baseline)
        == set(positive)
        == set(boundary)
        == {
            "sales_diagnosis_tool",
            "customer_loss_analysis_tool",
            "dealer_health_analysis_tool",
        }
    )
    assert "不用于客户流失名单" not in positive["sales_diagnosis_tool"].description
    assert "不用于客户流失名单" in boundary["sales_diagnosis_tool"].description
    assert baseline["sales_diagnosis_tool"].args["current_quarter"].constraints == {}
    assert boundary["sales_diagnosis_tool"].args["current_quarter"].constraints == {
        "pattern": r"^20\d{2}Q[1-4]$"
    }
    assert boundary["customer_loss_analysis_tool"].args[
        "decline_threshold"
    ].constraints == {"exclusiveMinimum": 0, "maximum": 1}


def test_boundary_prompt_exposes_enum_pattern_and_numeric_ranges() -> None:
    tool = {item.name: item for item in build_business_tools("boundary")}[
        "customer_loss_analysis_tool"
    ]
    prompt, _ = asyncio.run(tool.get_prompt(lang="zh"))

    assert '"enum": ["华东", "华南", "华北"]' in prompt
    assert '"pattern": "^20\\\\d{2}Q[1-4]$"' in prompt
    assert '"exclusiveMinimum": 0' in prompt
    assert '"maximum": 1' in prompt


def test_invalid_schema_arguments_never_construct_database_executor(
    monkeypatch,
) -> None:
    def fail_if_called():
        raise AssertionError("database executor must not be constructed")

    sales_module = importlib.import_module("insight_agent.tools.sales_diagnosis")
    loss_module = importlib.import_module("insight_agent.tools.customer_loss_analysis")
    health_module = importlib.import_module(
        "insight_agent.tools.dealer_health_analysis"
    )
    monkeypatch.setattr(sales_module, "PostgresReadOnlyExecutor", fail_if_called)
    monkeypatch.setattr(loss_module, "PostgresReadOnlyExecutor", fail_if_called)
    monkeypatch.setattr(health_module, "PostgresReadOnlyExecutor", fail_if_called)

    results = [
        sales_diagnosis_tool("华中", "刹车系统", "2026Q2", 5),
        customer_loss_analysis_tool("华东", "刹车系统", "2026-Q2", 0.5, 10),
        dealer_health_analysis_tool("华东", "2026Q2", 21),
    ]

    assert all(result["status"] == "error" for result in results)
    assert all(result["error"]["code"] == "invalid_arguments" for result in results)
    assert all(result["error"]["retryable"] is True for result in results)


def test_trace_metrics_score_selection_arguments_execution_and_extra_calls() -> None:
    case = {
        "id": "case",
        "case_type": "sales_diagnosis",
        "expected_calls": [
            {
                "tool": "sales_diagnosis_tool",
                "arguments": {
                    "region": "华东",
                    "category": "刹车系统",
                    "current_quarter": "2026Q2",
                    "top_n": 5,
                },
            }
        ],
    }
    events = _successful_call_events(
        "sales_diagnosis_tool",
        {
            "region": "华东",
            "category": "刹车系统",
            "current_quarter": "2026Q2",
            "top_n": 5,
        },
    )
    calls = extract_tool_calls(events)
    verdict = score_tool_calling_case(case, calls)

    assert verdict["passed"]
    assert verdict["selection_exact"]
    assert verdict["argument_schema_valid"]
    assert verdict["argument_semantic_correct"]
    assert verdict["execution_success"]

    extra_calls = calls + extract_tool_calls(
        _successful_call_events(
            "dealer_health_analysis_tool",
            {"region": "华东", "current_quarter": "2026Q2", "top_n": 10},
            step_id="step-2",
        )
    )
    failed = score_tool_calling_case(case, extra_calls)
    assert not failed["passed"]
    assert failed["failure_category"] == "tool_selection"
    assert failed["extra_calls"] == ["dealer_health_analysis_tool"]


def test_summary_reports_confusion_matrix_and_per_tool_recall() -> None:
    records = [
        {
            "passed": True,
            "case_type": "sales_diagnosis",
            "selection_exact": True,
            "order_correct": True,
            "argument_schema_valid": True,
            "argument_semantic_correct": True,
            "execution_success": True,
            "expected_tools": ["sales_diagnosis_tool"],
            "actual_tools": ["sales_diagnosis_tool"],
            "extra_calls": [],
            "failure_category": None,
        },
        {
            "passed": False,
            "case_type": "customer_loss",
            "selection_exact": False,
            "order_correct": False,
            "argument_schema_valid": True,
            "argument_semantic_correct": False,
            "execution_success": True,
            "expected_tools": ["customer_loss_analysis_tool"],
            "actual_tools": ["sales_diagnosis_tool"],
            "extra_calls": ["sales_diagnosis_tool"],
            "failure_category": "tool_selection",
        },
    ]
    summary = summarize_tool_calling_records(records)

    assert summary["tool_selection_accuracy"] == 0.5
    assert summary["per_tool"]["customer_loss_analysis_tool"]["recall"] == 0.0
    assert summary["confusion_matrix"]["customer_loss_analysis_tool"] == {
        "sales_diagnosis_tool": 1
    }
    assert summary["unnecessary_call_rate"] == 0.5


def test_api_has_isolated_tool_calling_evaluation_mode() -> None:
    api = (
        ROOT
        / "packages"
        / "dbgpt-app"
        / "src"
        / "dbgpt_app"
        / "openapi"
        / "api_v1"
        / "agentic_data_api.py"
    ).read_text(encoding="utf-8")

    assert "is_tool_calling_evaluation = bool(tool_calling_profile)" in api
    assert "build_business_tools(tool_calling_profile)" in api
    assert "[*business_eval_tools, sql_query_tool, Terminate()]" in api
    assert "就不得使用 sql_query，必须调用对应业务 Tool" in api
    assert "{{{{ action_space }}}}" in api
    assert "{{{{ action_space_names }}}}" in api
    assert "严禁在同一个 Action Input 后追加第二组 Action" in api
    assert "系统不会\n预先指定业务 Tool，也不会在漏调后自动恢复" in api


def test_trace_metrics_treat_sql_validation_and_preflight_errors_as_failures() -> None:
    for observation in (
        '{"error_code":"ACTION_INPUT_VALIDATION_FAILED"}',
        "[SYNTAX_ERROR] SQL 有误。预检提示：需要显式计算贡献率",
    ):
        events = [
            {
                "type": "step.meta",
                "id": "step-1",
                "action": "sql_query",
                "action_input": '{"sql":"SELECT 1"}',
            },
            {"type": "step.chunk", "id": "step-1", "content": observation},
            {"type": "step.done", "id": "step-1", "status": "done"},
        ]

        assert extract_tool_calls(events)[0]["execution_success"] is False


def test_trace_metrics_count_hallucinated_tool_as_an_extra_call() -> None:
    events = [
        {
            "type": "step.meta",
            "id": "step-1",
            "action": "sales_diagnosis",
            "action_input": '{"region":"华东"}',
        },
        {
            "type": "step.chunk",
            "id": "step-1",
            "content": "Tool execute failed! No tool found for execution",
        },
        {"type": "step.done", "id": "step-1", "status": "failed"},
    ]
    calls = extract_tool_calls(events)

    assert calls[0]["tool"] == "sales_diagnosis"
    assert calls[0]["schema_valid"] is False
    assert calls[0]["execution_success"] is False


def _successful_call_events(
    tool: str, arguments: dict, *, step_id: str = "step-1"
) -> list[dict]:
    import json

    return [
        {
            "type": "step.meta",
            "id": step_id,
            "action": tool,
            "action_input": json.dumps(arguments, ensure_ascii=False),
        },
        {
            "type": "step.chunk",
            "id": step_id,
            "content": '{"status":"success","data":{}}',
        },
        {"type": "step.done", "id": step_id, "status": "done"},
    ]
