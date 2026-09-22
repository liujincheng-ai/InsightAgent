"""Run the frozen 40-case Week 2 Tool Calling benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insight_agent.tools import TOOL_CALLING_PROFILES

from .run_eval import _post_sse, parse_events
from .schemas import file_sha256
from .tool_calling_metrics import (
    extract_tool_calls,
    score_tool_calling_case,
    summarize_tool_calling_records,
)
from .tool_calling_schemas import (
    load_tool_calling_dataset,
    select_tool_calling_cases,
    validate_tool_calling_dataset,
)


def run(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_tool_calling_dataset(dataset_path)
    errors = validate_tool_calling_dataset(dataset)
    if errors:
        raise ValueError("Tool Calling 数据集校验失败:\n- " + "\n- ".join(errors))
    cases = select_tool_calling_cases(dataset, args.split)
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in cases}
        if missing:
            raise ValueError("未找到指定评测 ID: " + ", ".join(sorted(missing)))
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} {case['question']}", flush=True)
        payload = {
            "conv_uid": (
                f"week2-{args.profile}-{args.repeat_index}-{case['id']}-{uuid.uuid4()}"
            ),
            "user_input": case["question"],
            "chat_mode": "chat_react_agent",
            "model_name": args.model,
            "temperature": args.temperature,
            "max_new_tokens": 4000,
            "select_param": "",
            "ext_info": {
                "database_name": "insight_agent",
                "database_type": "postgresql",
                "tool_calling_profile": args.profile,
            },
        }
        started = time.perf_counter()
        events: list[dict[str, Any]] = []
        transport_error = None
        try:
            events = _post_sse(args.endpoint, payload, args.timeout)
        except (TimeoutError, urllib.error.URLError, OSError, ValueError) as exc:
            transport_error = f"{type(exc).__name__}: {exc}"
        parsed = parse_events(events)
        calls = extract_tool_calls(events)
        verdict = score_tool_calling_case(case, calls, transport_error=transport_error)
        record = {
            "id": case["id"],
            "split": case["split"],
            "case_type": case["case_type"],
            "question": case["question"],
            "tags": case["tags"],
            "expected_calls": case["expected_calls"],
            "actual_calls": calls,
            "actual_answer": parsed["actual_answer"],
            "transport_error": transport_error,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "model": args.model,
            "temperature": args.temperature,
            "profile": args.profile,
            "repeat_index": args.repeat_index,
            **verdict,
        }
        records.append(record)
        (raw_dir / f"{case['id']}.json").write_text(
            json.dumps(
                {"case": case, "record": record, "events": events},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    summary = summarize_tool_calling_records(records)
    (output_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(output_dir / "summary.csv", records)
    manifest = {
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "temperature": args.temperature,
        "profile": args.profile,
        "repeat_index": args.repeat_index,
        "split": args.split,
        "case_count": len(cases),
        "dataset_sha256": file_sha256(dataset_path),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "rule_router_enabled": False,
        "forced_domain_gate_enabled": False,
        "domain_recovery_enabled": False,
        "raw_trace_preserved": True,
        "summary": summary,
        "comparison_rule": (
            "Only runs with identical model, dataset hash, split and temperature "
            "are directly comparable. Test/challenge must not guide tuning."
        ),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "split",
        "case_type",
        "pass_fail",
        "failure_category",
        "selection_exact",
        "order_correct",
        "argument_schema_valid",
        "argument_semantic_correct",
        "execution_success",
        "latency_seconds",
        "expected_tools",
        "actual_tools",
        "actual_answer",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["expected_tools"] = json.dumps(
                row["expected_tools"], ensure_ascii=False
            )
            row["actual_tools"] = json.dumps(row["actual_tools"], ensure_ascii=False)
            writer.writerow(row)


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split", choices=("dev", "test", "challenge", "all"), default="dev"
    )
    parser.add_argument("--profile", choices=TOOL_CALLING_PROFILES, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--repeat-index", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--case-id", action="append")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v1/chat/react-agent"
    )
    parser.add_argument(
        "--dataset",
        default=str(
            Path(__file__).resolve().parent / "dataset" / "tool_selection_test.json"
        ),
    )
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
