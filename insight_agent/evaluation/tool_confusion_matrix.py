"""Aggregate repeated Week 2 runs and render Tool confusion matrices."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def aggregate(run_dirs: list[Path]) -> dict[str, Any]:
    runs = []
    matrices: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    for run_dir in run_dirs:
        manifest = json.loads((run_dir / "run_manifest.json").read_text("utf-8"))
        summary = json.loads((run_dir / "summary.json").read_text("utf-8"))
        profile = manifest["profile"]
        runs.append(
            {
                "run_id": manifest["run_id"],
                "profile": profile,
                "model": manifest["model"],
                "repeat_index": manifest["repeat_index"],
                "dataset_sha256": manifest["dataset_sha256"],
                "total": summary["total"],
                "tool_selection_accuracy": summary["tool_selection_accuracy"],
                "argument_validity": summary["argument_validity"],
                "argument_semantic_accuracy": summary["argument_semantic_accuracy"],
                "execution_success": summary["execution_success"],
                "unnecessary_call_rate": summary["unnecessary_call_rate"],
                "pass_rate": summary["pass_rate"],
            }
        )
        for expected, actuals in summary["confusion_matrix"].items():
            matrices[profile][expected].update(actuals)
    hashes = {run["dataset_sha256"] for run in runs}
    models = {run["model"] for run in runs}
    if len(hashes) != 1:
        raise ValueError("不能聚合不同数据集指纹的运行")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[run["profile"]].append(run)
    profiles = {}
    metric_names = (
        "tool_selection_accuracy",
        "argument_validity",
        "argument_semantic_accuracy",
        "execution_success",
        "unnecessary_call_rate",
        "pass_rate",
    )
    for profile, profile_runs in sorted(grouped.items()):
        metrics = {}
        for name in metric_names:
            values = [float(run[name]) for run in profile_runs]
            metrics[name] = {
                "mean": round(statistics.mean(values), 6),
                "stdev": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
            }
        total = sum(int(run["total"]) for run in profile_runs)
        selected = round(
            sum(
                float(run["tool_selection_accuracy"]) * int(run["total"])
                for run in profile_runs
            )
        )
        metrics["tool_selection_accuracy"]["wilson_95"] = _wilson(selected, total)
        profiles[profile] = {
            "run_count": len(profile_runs),
            "metrics": metrics,
            "confusion_matrix": {
                expected: dict(actuals)
                for expected, actuals in sorted(matrices[profile].items())
            },
        }
    return {
        "dataset_sha256": next(iter(hashes)) if hashes else None,
        "models": sorted(models),
        "runs": sorted(runs, key=lambda item: (item["profile"], item["repeat_index"])),
        "profiles": profiles,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
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
        "# Week 2 Tool Calling 重复运行汇总",
        "",
        f"数据集 SHA-256：`{result['dataset_sha256']}`",
        "",
        "| Profile | Runs | Selection Mean | Stdev | 95% CI | Arg Valid | "
        "Execution | Extra Call |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for profile, data in result["profiles"].items():
        metrics = data["metrics"]
        low, high = metrics["tool_selection_accuracy"]["wilson_95"]
        lines.append(
            (
                "| {profile} | {runs} | {selection:.2%} | {stdev:.2%} | "
                "{low:.2%}–{high:.2%} | {args:.2%} | {execution:.2%} | "
                "{extra:.2%} |"
            ).format(
                profile=profile,
                runs=data["run_count"],
                selection=metrics["tool_selection_accuracy"]["mean"],
                stdev=metrics["tool_selection_accuracy"]["stdev"],
                low=low,
                high=high,
                args=metrics["argument_validity"]["mean"],
                execution=metrics["execution_success"]["mean"],
                extra=metrics["unnecessary_call_rate"]["mean"],
            )
        )
        labels = sorted(
            set(data["confusion_matrix"])
            | {actual for row in data["confusion_matrix"].values() for actual in row}
        )
        lines.extend(["", f"## {profile} 混淆矩阵", ""])
        lines.append("| Expected \\ Actual | " + " | ".join(labels) + " |")
        lines.append("|---|" + "---:|" * len(labels))
        for expected in labels:
            row = data["confusion_matrix"].get(expected, {})
            lines.append(
                f"| {expected} | "
                + " | ".join(str(row.get(actual, 0)) for actual in labels)
                + " |"
            )
    return "\n".join(lines) + "\n"


def _wilson(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = proportion + z * z / (2 * total)
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    )
    return [
        round((centre - margin) / denominator, 6),
        round((centre + margin) / denominator, 6),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    write_outputs(
        aggregate([Path(path) for path in args.run_dir]), Path(args.output_dir)
    )
