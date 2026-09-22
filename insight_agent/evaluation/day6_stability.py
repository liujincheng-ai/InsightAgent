"""Run the Day 6 main demo five times and apply an explicit stability rubric."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from insight_agent.evaluation.run_eval import _post_sse, evaluate_case

QUESTION = (
    "分析 2026 年第二季度华东区域刹车系统配件销售下滑的主要因素，"
    "并结合经销商管理制度提出改进建议，生成带图表和引用依据的经营分析报告。"
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _rubric(record: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, bool]:
    trajectory = json.dumps(events, ensure_ascii=False)
    answer = str(record.get("actual_answer") or "")
    tools = set(record.get("actual_tools") or [])
    sources = json.dumps(record.get("actual_sources") or [], ensure_ascii=False)
    return {
        "plan_present": any(
            event.get("type") == "plan.update"
            or (
                event.get("type") == "step.meta"
                and event.get("action") == "todowrite"
            )
            for event in events
        ),
        "correct_time_scope": (
            _contains_any(trajectory, ("2026Q2", "2026 Q2"))
            and _contains_any(trajectory, ("2026Q1", "2026 Q1"))
            and _contains_any(trajectory, ("2025Q2", "2025 Q2", "同比"))
        ),
        "correct_domain_tool": "sales_diagnosis_tool" in tools,
        "qoq_and_yoy_present": (
            _contains_any(answer, ("-32.68%", "-0.3268"))
            and _contains_any(answer, ("-29.27%", "-0.2927"))
        ),
        "customer_and_dealer_risk": (
            "客户" in trajectory and "经销商" in trajectory and "风险" in trajectory
        ),
        "correct_policy": (
            "经销商分级与考核管理制度" in sources
            and _contains_any(trajectory, ("4.2", "3.2"))
        ),
        "facts_separated_from_advice": (
            _contains_any(trajectory, ("数据事实", "事实"))
            and _contains_any(trajectory, ("管理建议", "改进建议", "建议"))
        ),
        "visual_report": any(
            event.get("type") == "step.chunk"
            and event.get("output_type") == "html"
            for event in events
        ),
        "normal_termination": (
            any(event.get("type") == "final" for event in events)
            and any(event.get("type") == "done" for event in events)
            and bool(answer)
            and "未完成" not in answer
        ),
    }


def run(
    output_dir: Path,
    *,
    model: str,
    endpoint: str,
    timeout: float,
    runs: int = 5,
    start_index: int = 1,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()
    records = []
    for offset in range(runs):
        index = start_index + offset
        case = {
            "id": f"day6-main-demo-{index:02d}",
            "type": "integrated",
            "question": QUESTION,
            "expected_facts": [
                {
                    "name": "qoq",
                    "kind": "numeric",
                    "value": -32.68,
                    "accepted_values": [-0.3268],
                    "tolerance": 0.02,
                },
                {
                    "name": "yoy",
                    "kind": "numeric",
                    "value": -29.27,
                    "accepted_values": [-0.2927],
                    "tolerance": 0.02,
                },
            ],
            "expected_tool": "sales_diagnosis_tool",
            "expected_documents": ["经销商分级与考核管理制度"],
            "expected_sections": ["4.2"],
            "numeric_tolerance": 0.01,
            "grading": "deterministic_and_manual",
        }
        print(f"[{offset + 1}/{runs}] {QUESTION}", flush=True)
        record, events = evaluate_case(
            case,
            endpoint=endpoint,
            model=model,
            temperature=0.0,
            timeout=timeout,
            transport=_post_sse,
        )
        rubric = _rubric(record, events)
        record["rubric"] = rubric
        record["stability_passed"] = all(rubric.values())
        records.append(record)
        (raw_dir / f"{case['id']}.json").write_text(
            json.dumps(
                {"case": case, "record": record, "events": events},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    passed = sum(item["stability_passed"] for item in records)
    summary = {
        "total": len(records),
        "passed": passed,
        "pass_rate": passed / len(records),
        "acceptance_threshold": max(1, runs - 1),
        "accepted": passed >= max(1, runs - 1),
        "criteria_pass_counts": {
            name: sum(item["rubric"][name] for item in records)
            for name in records[0]["rubric"]
        },
        "average_latency_seconds": round(
            sum(float(item["latency_seconds"]) for item in records) / len(records),
            3,
        ),
    }
    (output_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("id", "passed", *records[0]["rubric"].keys()),
        )
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    "id": item["id"],
                    "passed": item["stability_passed"],
                    **item["rubric"],
                }
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:5670/api/v1/chat/react-agent",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--start-index", type=int, default=1)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.output_dir,
                model=args.model,
                endpoint=args.endpoint,
                timeout=args.timeout,
                runs=args.runs,
                start_index=args.start_index,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
