"""Run the frozen 20-case Week 4 Agent reliability benchmark."""

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

from .reliability_metrics import (
    score_reliability_case,
    summarize_reliability_records,
)
from .reliability_schemas import (
    load_reliability_dataset,
    select_reliability_cases,
    validate_reliability_dataset,
)
from .run_eval import _post_sse
from .schemas import file_sha256


def _ext_info(case: dict[str, Any], profile: str, max_steps: int | None):
    if case["mode"] == "database":
        ext_info: dict[str, Any] = {
            "database_name": "insight_agent",
            "database_type": "postgresql",
        }
    elif case["mode"] == "knowledge":
        ext_info = {"knowledge_space_name": "汽车配件企业制度库"}
    else:
        ext_info = {
            "database_name": "insight_agent",
            "database_type": "postgresql",
            "knowledge_space_name": "汽车配件企业制度库",
        }
    ext_info.update(
        {
            "reliability_case_id": case["id"],
            "reliability_profile": profile,
        }
    )
    if max_steps is not None:
        ext_info["reliability_max_steps"] = max_steps
    return ext_info


def run(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_reliability_dataset(dataset_path)
    errors = validate_reliability_dataset(dataset)
    if errors:
        raise ValueError("Week 4 数据集校验失败:\n- " + "\n- ".join(errors))
    cases = select_reliability_cases(dataset, args.split)
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
                f"week4-{args.profile}-{args.repeat_index}-{case['id']}-"
                f"{uuid.uuid4()}"
            ),
            "user_input": case["question"],
            "chat_mode": "chat_react_agent",
            "model_name": args.model,
            "temperature": args.temperature,
            "max_new_tokens": 4000,
            "select_param": "",
            "ext_info": _ext_info(case, args.profile, args.max_steps),
        }
        started = time.perf_counter()
        events: list[dict[str, Any]] = []
        transport_error = None
        try:
            events = _post_sse(args.endpoint, payload, args.timeout)
        except (TimeoutError, urllib.error.URLError, OSError, ValueError) as error:
            transport_error = f"{type(error).__name__}: {error}"
        verdict = score_reliability_case(
            case,
            events,
            profile=args.profile,
            transport_error=transport_error,
        )
        final_answer = next(
            (
                str(event.get("content") or "")
                for event in reversed(events)
                if event.get("type") == "final"
            ),
            "",
        )
        record = {
            "id": case["id"],
            "split": case["split"],
            "case_type": case["case_type"],
            "mode": case["mode"],
            "question": case["question"],
            "expected_initial_tool": case["expected_initial_tool"],
            "expected_failure_type": case["expected_failure_type"],
            "expected_recovery_action": case["expected_recovery_action"],
            "expected_completion": case["expected_completion"],
            "expected_max_steps": case["max_steps"],
            "actual_answer": final_answer,
            "transport_error": transport_error,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "profile": args.profile,
            "model": args.model,
            "temperature": args.temperature,
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
    summary = summarize_reliability_records(records)
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
        "profile": args.profile,
        "model": args.model,
        "temperature": args.temperature,
        "repeat_index": args.repeat_index,
        "split": args.split,
        "case_count": len(cases),
        "max_steps_override": args.max_steps,
        "dataset_version": dataset.get("version"),
        "dataset_sha256": file_sha256(dataset_path),
        "baseline_commit": dataset.get("baseline_commit"),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "fault_injection": "isolated request-local ToolPack outcomes",
        "raw_trace_preserved": True,
        "summary": summary,
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
        "mode",
        "pass_fail",
        "actual_initial_tool",
        "actual_failure_type",
        "actual_recovery_action",
        "actual_completion",
        "step_count",
        "terminated",
        "circuit_breaker_triggered",
        "post_breaker_calls",
        "blind_retry_non_retryable",
        "latency_seconds",
        "failed_checks",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["failed_checks"] = ",".join(record.get("failed_checks") or [])
            writer.writerow(row)


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=("baseline", "after"), required=True
    )
    parser.add_argument(
        "--split", choices=("dev", "test", "challenge", "all"), default="dev"
    )
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--repeat-index", type=int, default=1)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--timeout", type=float, default=150.0)
    parser.add_argument("--case-id", action="append")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v1/chat/react-agent"
    )
    parser.add_argument(
        "--dataset",
        default=str(
            root
            / "insight_agent"
            / "evaluation"
            / "dataset"
            / "failure_cases.json"
        ),
    )
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
