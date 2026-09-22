"""Build a transparent Week 5 baseline/optimized comparison with supplements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .context_profiler import summarize_records


def _load_records(run_dir: Path) -> list[dict[str, Any]]:
    return json.loads((run_dir / "records.json").read_text(encoding="utf-8"))


def _aggregate(
    primary_dir: Path, supplement_dirs: list[Path]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    records = {item["id"]: item for item in _load_records(primary_dir)}
    replacements: dict[str, str] = {}
    for supplement_dir in supplement_dirs:
        for item in _load_records(supplement_dir):
            if item["id"] not in records:
                raise ValueError(f"补跑用例不在主评测集中: {item['id']}")
            records[item["id"]] = item
            replacements[item["id"]] = str(supplement_dir)
    ordered = sorted(records.values(), key=lambda item: item["id"])
    return ordered, replacements


def _reduction(before: float, after: float) -> float:
    return round((before - after) / before, 6) if before else 0.0


def build_comparison(
    baseline_records: list[dict[str, Any]],
    optimized_records: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline = summarize_records(baseline_records)
    optimized = summarize_records(optimized_records)
    input_reduction = _reduction(
        baseline["average_estimated_input_tokens"],
        optimized["average_estimated_input_tokens"],
    )
    cost_reduction = _reduction(
        baseline["estimated_average_cost_cny"],
        optimized["estimated_average_cost_cny"],
    )
    citation_drop = round(
        baseline["citation_accuracy"] - optimized["citation_accuracy"], 6
    )
    passed_drop = baseline["passed"] - optimized["passed"]
    checks = {
        "input_token_reduction_at_least_15pct": input_reduction >= 0.15,
        "estimated_cost_reduction_at_least_10pct": cost_reduction >= 0.10,
        "task_pass_drop_at_most_one_case": passed_drop <= 1,
        "key_fact_retention_at_least_95pct": (optimized["key_fact_retention"] >= 0.95),
        "citation_accuracy_drop_at_most_5pp": citation_drop <= 0.05,
        "no_context_overflow": optimized["context_overflow_count"] == 0,
        "no_transport_error": optimized["transport_error_count"] == 0,
    }
    return {
        "baseline": baseline,
        "optimized": optimized,
        "deltas": {
            "input_token_reduction": input_reduction,
            "estimated_cost_reduction": cost_reduction,
            "citation_accuracy_drop": citation_drop,
            "passed_case_drop": passed_drop,
        },
        "acceptance_checks": checks,
        "accepted": all(checks.values()),
    }


def _markdown(comparison: dict[str, Any], provenance: dict[str, Any]) -> str:
    before = comparison["baseline"]
    after = comparison["optimized"]
    delta = comparison["deltas"]
    pass_delta = after["passed"] - before["passed"]
    fact_delta = after["key_fact_retention"] - before["key_fact_retention"]
    citation_delta = after["citation_accuracy"] - before["citation_accuracy"]
    latency_delta = after["average_latency_seconds"] - before["average_latency_seconds"]
    lines = [
        "# 第五周上下文优化对比报告",
        "",
        "> token 与费用均为本地估算，不是模型供应商账单；补跑替换及原因见文末。",
        "",
        "| 指标 | 基线 | 优化后 | 变化 |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| 任务通过 | {before['passed']}/20 | {after['passed']}/20 | "
            f"{pass_delta:+d} |"
        ),
        (
            f"| 关键事实保持率 | {before['key_fact_retention']:.2%} | "
            f"{after['key_fact_retention']:.2%} | {fact_delta:+.2%} |"
        ),
        (
            f"| 引用准确率 | {before['citation_accuracy']:.2%} | "
            f"{after['citation_accuracy']:.2%} | {citation_delta:+.2%} |"
        ),
        (
            "| 平均估算输入 token | "
            f"{before['average_estimated_input_tokens']:.2f} | "
            f"{after['average_estimated_input_tokens']:.2f} | "
            f"{-delta['input_token_reduction']:.2%} |"
        ),
        (
            "| 平均估算成本（元） | "
            f"{before['estimated_average_cost_cny']:.6f} | "
            f"{after['estimated_average_cost_cny']:.6f} | "
            f"{-delta['estimated_cost_reduction']:.2%} |"
        ),
        (
            f"| 平均延迟（秒） | {before['average_latency_seconds']:.3f} | "
            f"{after['average_latency_seconds']:.3f} | {latency_delta:+.3f} |"
        ),
        (
            f"| 上下文溢出 | {before['context_overflow_count']} | "
            f"{after['context_overflow_count']} | — |"
        ),
        "",
        "## 验收判定",
        "",
    ]
    for name, passed in comparison["acceptance_checks"].items():
        lines.append(f"- {'通过' if passed else '未通过'}：`{name}`")
    lines.extend(
        [
            "",
            f"**最终判定：{'通过' if comparison['accepted'] else '未通过'}。**",
            "",
            "## 补跑替换记录",
            "",
            "补跑只替换网络异常、无证据占位输出或已由确定性单测修复的呈现缺口；",
            "主评测原始目录和补跑目录均保留，不覆盖原始结果。",
            "",
            "```json",
            json.dumps(provenance, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--baseline-supplement", type=Path, action="append", default=[])
    parser.add_argument("--optimized-dir", type=Path, required=True)
    parser.add_argument(
        "--optimized-supplement", type=Path, action="append", default=[]
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    baseline_records, baseline_replacements = _aggregate(
        args.baseline_dir, args.baseline_supplement
    )
    optimized_records, optimized_replacements = _aggregate(
        args.optimized_dir, args.optimized_supplement
    )
    comparison = build_comparison(baseline_records, optimized_records)
    provenance = {
        "baseline_primary": str(args.baseline_dir),
        "baseline_replacements": baseline_replacements,
        "optimized_primary": str(args.optimized_dir),
        "optimized_replacements": optimized_replacements,
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "baseline_records.json").write_text(
        json.dumps(baseline_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "optimized_records.json").write_text(
        json.dumps(optimized_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "comparison.json").write_text(
        json.dumps(
            {**comparison, "provenance": provenance}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (args.output_dir / "第五周_优化对比报告.md").write_text(
        _markdown(comparison, provenance), encoding="utf-8"
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0 if comparison["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
