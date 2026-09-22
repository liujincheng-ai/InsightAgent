"""Aggregate comparable Week 4 reliability runs by profile."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

METRICS = (
    "pass_rate",
    "failure_recovery_rate",
    "termination_rate",
    "failure_type_accuracy",
    "recovery_action_accuracy",
    "completion_accuracy",
    "non_retryable_blind_retry_rate",
    "repeated_call_rate",
    "duplicate_failure_call_rate",
    "average_steps",
    "p95_steps",
    "average_latency_seconds",
    "p95_latency_seconds",
)


def aggregate(run_dirs: list[Path]) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        manifest = json.loads((run_dir / "run_manifest.json").read_text("utf-8"))
        summary = json.loads((run_dir / "summary.json").read_text("utf-8"))
        runs.append(
            {
                "run_id": manifest["run_id"],
                "profile": manifest["profile"],
                "model": manifest["model"],
                "repeat_index": manifest["repeat_index"],
                "dataset_sha256": manifest["dataset_sha256"],
                **{name: summary.get(name) for name in METRICS},
            }
        )
    hashes = {item["dataset_sha256"] for item in runs}
    models = {item["model"] for item in runs}
    if len(hashes) != 1:
        raise ValueError("不能聚合不同数据集指纹的运行")
    if len(models) != 1:
        raise ValueError("Before/After 必须使用相同模型")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[run["profile"]].append(run)
    profiles: dict[str, Any] = {}
    for profile, profile_runs in sorted(grouped.items()):
        metrics: dict[str, Any] = {}
        for name in METRICS:
            values = [float(item[name] or 0.0) for item in profile_runs]
            metrics[name] = {
                "mean": round(statistics.mean(values), 6),
                "stdev": (
                    round(statistics.stdev(values), 6)
                    if len(values) > 1
                    else 0.0
                ),
            }
        profiles[profile] = {
            "run_count": len(profile_runs),
            "metrics": metrics,
        }
    comparison: dict[str, Any] = {}
    if {"baseline", "after"} <= set(profiles):
        for name in METRICS:
            before = profiles["baseline"]["metrics"][name]["mean"]
            after = profiles["after"]["metrics"][name]["mean"]
            comparison[name] = {
                "baseline": before,
                "after": after,
                "delta": round(after - before, 6),
            }
    return {
        "dataset_sha256": next(iter(hashes)) if hashes else None,
        "model": next(iter(models)) if models else None,
        "runs": sorted(
            runs, key=lambda item: (item["profile"], item["repeat_index"])
        ),
        "profiles": profiles,
        "comparison": comparison,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "aggregate.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output_dir / "runs.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        fields = list(result["runs"][0]) if result["runs"] else []
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["runs"])
    (output_dir / "report.md").write_text(_markdown(result), encoding="utf-8")


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Week 4 Agent 可靠性重复运行汇总",
        "",
        f"数据集 SHA-256：`{result['dataset_sha256']}`",
        "",
        "| Profile | Runs | Recovery | Termination | Repeat | Steps | Latency |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for profile, data in result["profiles"].items():
        metrics = data["metrics"]
        lines.append(
            "| {profile} | {runs} | {recovery:.2%} | {termination:.2%} | "
            "{repeat:.2%} | {steps:.2f} | {latency:.2f}s |".format(
                profile=profile,
                runs=data["run_count"],
                recovery=metrics["failure_recovery_rate"]["mean"],
                termination=metrics["termination_rate"]["mean"],
                repeat=metrics["repeated_call_rate"]["mean"],
                steps=metrics["average_steps"]["mean"],
                latency=metrics["average_latency_seconds"]["mean"],
            )
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    write_outputs(
        aggregate([Path(path) for path in arguments.run_dir]),
        Path(arguments.output_dir),
    )
