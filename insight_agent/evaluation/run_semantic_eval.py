"""Run the frozen 30-case Week 1 Text-to-SQL semantic benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insight_agent.semantic import get_semantic_profile

from .run_eval import _post_sse, parse_events
from .schemas import file_sha256
from .semantic_metrics import score_semantic_case, summarize_semantic_records
from .semantic_schemas import load_semantic_datasets, validate_semantic_datasets


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "split",
        "pass_fail",
        "failure_category",
        "latency_seconds",
        "actual_sql",
        "actual_answer",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["actual_sql"] = json.dumps(row["actual_sql"], ensure_ascii=False)
            writer.writerow(row)


def run(args: argparse.Namespace) -> int:
    profile = get_semantic_profile(args.profile)
    os.environ["INSIGHT_SEMANTIC_PROFILE"] = profile
    dataset_dir = Path(args.dataset_dir)
    datasets = load_semantic_datasets(dataset_dir)
    errors = validate_semantic_datasets(datasets)
    if errors:
        raise ValueError("语义数据集校验失败:\n- " + "\n- ".join(errors))
    selected = list(datasets) if args.split == "all" else [args.split]
    cases = [
        {**case, "split": split}
        for split in selected
        for case in datasets[split]["cases"]
    ]
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
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case['id']} {case['question']}", flush=True)
        payload = {
            "conv_uid": f"week1-{profile}-{case['id']}-{uuid.uuid4()}",
            "user_input": case["question"],
            "chat_mode": "chat_react_agent",
            "model_name": args.model,
            "temperature": args.temperature,
            "max_new_tokens": 4000,
            "select_param": "",
            "ext_info": {
                "database_name": "insight_agent",
                "database_type": "postgresql",
                "semantic_profile": profile,
            },
        }
        started = time.perf_counter()
        error = None
        events: list[dict[str, Any]] = []
        try:
            events = _post_sse(args.endpoint, payload, args.timeout)
            actual = parse_events(events)
        except (TimeoutError, urllib.error.URLError, OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            actual = {
                "actual_answer": "",
                "actual_tools": [],
                "actual_sql": [],
                "sql_executed": False,
                "actual_sources": [],
                "raw_trajectory": "",
            }
        actual["error"] = error
        verdict = score_semantic_case(case, actual, events)
        record = {
            "id": case["id"],
            "split": case["split"],
            "question": case["question"],
            "semantic_tags": case["semantic_tags"],
            "requires_clarification": case["requires_clarification"],
            "gold_result": case.get("gold_result"),
            **actual,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "model": args.model,
            "temperature": args.temperature,
            "profile": profile,
            **verdict,
            "pass_fail": "pass" if verdict["passed"] else "fail",
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
    summary = summarize_semantic_records(records)
    (output_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(output_dir / "summary.csv", records)
    paths = {split: dataset_dir / f"sql_semantic_{split}.json" for split in selected}
    manifest = {
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "temperature": args.temperature,
        "semantic_profile": profile,
        "split": args.split,
        "case_count": len(cases),
        "dataset_sha256": {k: file_sha256(v) for k, v in paths.items()},
        "raw_trace_preserved": True,
        "summary": summary,
        "comparison_rule": (
            "Only runs with identical model, dataset hashes and parameters are "
            "direct Before/After comparisons."
        ),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split", choices=("dev", "test", "challenge", "all"), default="dev"
    )
    parser.add_argument(
        "--profile",
        choices=("baseline", "comments", "glossary", "combined"),
        required=True,
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--case-id", action="append")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v1/chat/react-agent"
    )
    parser.add_argument(
        "--dataset-dir", default=str(Path(__file__).resolve().parent / "dataset")
    )
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
