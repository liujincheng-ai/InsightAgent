"""Run and score the frozen Week 5 long-context benchmark against the SSE API."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from .context_schemas import file_sha256, load_long_context_dataset
from .cost_calculator import estimate_cost, estimate_text_tokens

JsonTransport = Callable[[str, dict[str, Any], float], list[dict[str, Any]]]


def _post_sse(
    url: str, payload: dict[str, Any], timeout: float
) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    events: list[dict[str, Any]] = []
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                events.append({"type": "unparsed", "content": data})
    return events


def _normalise(text: str) -> str:
    return re.sub(r"[\s,，。；;：:%％（）()\-]", "", (text or "").lower())


def _fact_matches(fact: dict[str, Any], text: str) -> bool:
    values = fact.get("accepted_values", [])
    if fact.get("kind") != "numeric":
        normalised = _normalise(text)
        return any(_normalise(str(value)) in normalised for value in values)

    numbers = [
        float(item.replace(",", ""))
        for item in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", text)
    ]
    tolerance = float(fact.get("tolerance", 0.02))
    for expected in values:
        expected_number = float(expected)
        for actual in numbers:
            absolute = max(0.01, abs(expected_number) * tolerance)
            if math.isclose(actual, expected_number, abs_tol=absolute):
                return True
            # Permit decimal/percentage representation when explicitly numeric.
            if math.isclose(actual / 100, expected_number, abs_tol=absolute):
                return True
            if math.isclose(actual, expected_number / 100, abs_tol=absolute):
                return True
    return False


def _context_metrics(events: list[dict[str, Any]], question: str) -> dict[str, Any]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") == "context.status":
            if event.get("compact_layer") in (None, "none"):
                if current:
                    groups.append(current)
                current = [event]
            elif current:
                current.append(event)
        elif event.get("type") == "step.start" and current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    question_tokens = estimate_text_tokens(question)
    before = sum(int(group[0].get("used") or 0) + question_tokens for group in groups)
    effective = sum(
        int(group[-1].get("used") or 0) + question_tokens for group in groups
    )
    layers = Counter(
        str(status.get("compact_layer"))
        for group in groups
        for status in group
        if status.get("compact_layer")
    )
    return {
        "llm_round_count": len(groups),
        "estimated_input_tokens_before_compaction": before,
        "estimated_input_tokens": effective,
        "estimated_tokens_saved": max(0, before - effective),
        "context_layers": dict(sorted(layers.items())),
        "max_context_ratio": max(
            (float(status.get("ratio") or 0) for group in groups for status in group),
            default=0.0,
        ),
        "context_status_present": bool(groups),
    }


def parse_events(events: list[dict[str, Any]], question: str) -> dict[str, Any]:
    answers = [
        str(event.get("content") or "")
        for event in events
        if event.get("type") == "final"
    ]
    answer = answers[-1] if answers else ""
    tools: list[str] = []
    observations: list[str] = []
    output_text: list[str] = [answer]
    citations: list[dict[str, Any]] = []
    step_count = 0
    for event in events:
        event_type = event.get("type")
        if event_type == "step.meta":
            action = str(event.get("action") or "")
            if action:
                tools.append(action)
            output_text.extend(
                str(event.get(key) or "")
                for key in ("thought", "action_intention", "action_reason")
            )
        elif event_type == "step.chunk":
            content = str(event.get("content") or "")
            observations.append(content)
        elif event_type == "step.done":
            step_count += 1
        elif event_type == "final":
            citations.extend(event.get("citations") or [])

    raw_text = json.dumps(events, ensure_ascii=False, separators=(",", ":"))
    context = _context_metrics(events, question)
    return {
        "actual_answer": answer,
        "actual_tools": tools,
        "actual_citations": citations,
        "step_count": step_count,
        "tool_result_chars": sum(len(item) for item in observations),
        "raw_event_chars": len(raw_text),
        "persisted_output_present": "<persisted-output>" in raw_text,
        "context_overflow_present": any(
            marker in raw_text.lower()
            for marker in (
                "context_too_long",
                "context_length_exceeded",
                "maximum context length",
            )
        ),
        "estimated_output_tokens": estimate_text_tokens("\n".join(output_text)),
        **context,
    }


def score_case(case: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    evidence_text = "\n".join(
        [
            actual["actual_answer"],
            json.dumps(actual["actual_citations"], ensure_ascii=False),
        ]
    )
    fact_checks = {
        str(fact.get("name") or index): _fact_matches(fact, evidence_text)
        for index, fact in enumerate(case.get("expected_facts", []), start=1)
    }
    expected_tools = case.get("expected_tools", [])
    tool_checks = {tool: tool in actual["actual_tools"] for tool in expected_tools}
    raw_citations = _normalise(
        json.dumps(actual["actual_citations"], ensure_ascii=False)
        + actual["actual_answer"]
    )
    document_checks = {
        doc: _normalise(doc) in raw_citations
        for doc in case.get("expected_documents", [])
    }
    section_checks = {
        section: _normalise(section) in raw_citations
        for section in case.get("expected_sections", [])
    }

    expected_completion = case.get("expected_completion", "success")
    answer_norm = _normalise(actual["actual_answer"])
    if expected_completion == "no_data":
        completion_ok = any(
            marker in answer_norm
            for marker in ("无数据", "没有数据", "未查询到", "证据不足")
        )
    elif expected_completion == "clarification":
        completion_ok = any(
            marker in answer_norm for marker in ("请明确", "需要明确", "请提供", "澄清")
        )
    elif expected_completion == "partial":
        completion_ok = (
            "部分" in actual["actual_answer"] or "未完成" in actual["actual_answer"]
        )
    else:
        completion_ok = bool(actual["actual_answer"]) and not any(
            marker in actual["actual_answer"]
            for marker in ("任务执行失败", "系统暂时无法", "Traceback")
        )

    citation_total = len(document_checks) + len(section_checks)
    citation_passed = sum(document_checks.values()) + sum(section_checks.values())
    facts_total = len(fact_checks)
    facts_passed = sum(fact_checks.values())
    passed = (
        all(fact_checks.values())
        and all(tool_checks.values())
        and all(document_checks.values())
        and all(section_checks.values())
        and completion_ok
        and not actual["context_overflow_present"]
    )
    return {
        "fact_checks": fact_checks,
        "tool_checks": tool_checks,
        "document_checks": document_checks,
        "section_checks": section_checks,
        "facts_passed": facts_passed,
        "facts_total": facts_total,
        "citation_checks_passed": citation_passed,
        "citation_checks_total": citation_total,
        "completion_ok": completion_ok,
        "pass_fail": passed,
        "failed_checks": [
            name
            for name, checks in (
                ("facts", fact_checks),
                ("tools", tool_checks),
                ("documents", document_checks),
                ("sections", section_checks),
            )
            if not all(checks.values())
        ]
        + ([] if completion_ok else ["completion"])
        + ([] if not actual["context_overflow_present"] else ["context_overflow"]),
    }


def _ext_info(case: dict[str, Any], profile: str) -> dict[str, Any]:
    result: dict[str, Any] = {"context_profile": profile}
    if case["mode"] in {"database", "integrated"}:
        result.update({"database_name": "insight_agent", "database_type": "postgresql"})
    if case["mode"] in {"rag", "integrated"}:
        result["knowledge_space_name"] = "汽车配件企业制度库"
    return result


def evaluate_case(
    case: dict[str, Any],
    *,
    endpoint: str,
    model: str,
    profile: str,
    temperature: float,
    timeout: float,
    transport: JsonTransport = _post_sse,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conv_uid = f"week5-{case['id']}-{uuid.uuid4()}"
    all_events: list[dict[str, Any]] = []
    latency = 0.0
    transport_error: str | None = None
    for turn_index, question in enumerate(case["turns"], start=1):
        payload = {
            "conv_uid": conv_uid,
            "user_input": question,
            "chat_mode": "chat_react_agent",
            "model_name": model,
            "temperature": temperature,
            "max_new_tokens": 4000,
            "select_param": "",
            "ext_info": _ext_info(case, profile),
        }
        started = time.perf_counter()
        try:
            events = transport(endpoint, payload, timeout)
        except (TimeoutError, urllib.error.URLError, OSError, ValueError) as exc:
            events = []
            transport_error = f"{type(exc).__name__}: {exc}"
        latency += time.perf_counter() - started
        all_events.append({"type": "benchmark.turn", "turn": turn_index})
        all_events.extend(events)
        if transport_error:
            break

    joined_question = "\n".join(case["turns"])
    actual = parse_events(all_events, joined_question)
    verdict = score_case(case, actual)
    cost = estimate_cost(
        model,
        input_tokens=actual["estimated_input_tokens"],
        output_tokens=actual["estimated_output_tokens"],
    )
    record = {
        "id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "mode": case["mode"],
        "turns": case["turns"],
        "profile": profile,
        "model": model,
        "temperature": temperature,
        "conversation_id": conv_uid,
        "transport_error": transport_error,
        "latency_seconds": round(latency, 3),
        "cost_estimate": cost,
        **actual,
        **verdict,
    }
    return record, all_events


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(records)
    facts_total = sum(item["facts_total"] for item in records)
    citations_total = sum(item["citation_checks_total"] for item in records)
    layer_counts: Counter[str] = Counter()
    for record in records:
        layer_counts.update(record["context_layers"])
    return {
        "case_count": count,
        "passed": sum(bool(item["pass_fail"]) for item in records),
        "task_pass_rate": round(
            sum(bool(item["pass_fail"]) for item in records) / count, 6
        )
        if count
        else 0.0,
        "key_fact_retention": round(
            sum(item["facts_passed"] for item in records) / facts_total, 6
        )
        if facts_total
        else 1.0,
        "citation_accuracy": round(
            sum(item["citation_checks_passed"] for item in records) / citations_total,
            6,
        )
        if citations_total
        else 1.0,
        "average_estimated_input_tokens": round(
            mean(item["estimated_input_tokens"] for item in records), 2
        )
        if records
        else 0.0,
        "average_estimated_output_tokens": round(
            mean(item["estimated_output_tokens"] for item in records), 2
        )
        if records
        else 0.0,
        "average_latency_seconds": round(
            mean(item["latency_seconds"] for item in records), 3
        )
        if records
        else 0.0,
        "p95_latency_seconds": round(
            sorted(item["latency_seconds"] for item in records)[
                max(0, math.ceil(count * 0.95) - 1)
            ],
            3,
        )
        if records
        else 0.0,
        "estimated_total_cost_cny": round(
            sum(item["cost_estimate"]["total_cost_cny"] for item in records), 6
        ),
        "estimated_average_cost_cny": round(
            mean(item["cost_estimate"]["total_cost_cny"] for item in records), 8
        )
        if records
        else 0.0,
        "average_tool_result_chars": round(
            mean(item["tool_result_chars"] for item in records), 2
        )
        if records
        else 0.0,
        "persistence_rate": round(
            sum(bool(item["persisted_output_present"]) for item in records) / count, 6
        )
        if count
        else 0.0,
        "context_overflow_count": sum(
            bool(item["context_overflow_present"]) for item in records
        ),
        "context_layer_counts": dict(sorted(layer_counts.items())),
        "transport_error_count": sum(bool(item["transport_error"]) for item in records),
    }


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "split",
        "category",
        "pass_fail",
        "estimated_input_tokens",
        "estimated_output_tokens",
        "latency_seconds",
        "step_count",
        "tool_result_chars",
        "persisted_output_present",
        "context_layers",
        "failed_checks",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["context_layers"] = json.dumps(
                row["context_layers"], ensure_ascii=False
            )
            row["failed_checks"] = json.dumps(row["failed_checks"], ensure_ascii=False)
            writer.writerow(row)


def run(args: argparse.Namespace, transport: JsonTransport = _post_sse) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_long_context_dataset(dataset_path)
    cases = [
        case
        for case in dataset["cases"]
        if args.split == "all" or case["split"] == args.split
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
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} {case['turns'][0]}", flush=True)
        record, events = evaluate_case(
            case,
            endpoint=args.endpoint,
            model=args.model,
            profile=args.profile,
            temperature=args.temperature,
            timeout=args.timeout,
            transport=transport,
        )
        records.append(record)
        payload = {"case": case, "record": record, "events": events}
        (raw_dir / f"{case['id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = summarize_records(records)
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
        "dataset": str(dataset_path),
        "dataset_sha256": file_sha256(dataset_path),
        "dataset_status": dataset.get("dataset_status"),
        "case_count": len(cases),
        "split": args.split,
        "model": args.model,
        "profile": args.profile,
        "temperature": args.temperature,
        "endpoint": args.endpoint,
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "raw_trace_preserved": True,
        "token_note": (
            "React API 未暴露 Provider usage；输入 Token 来自 context.status，"
            "输出 Token 依据 DeepSeek 官方字符比例估算。"
        ),
        "summary": summary,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default=str(
            Path(__file__).resolve().parent / "dataset" / "long_context_test.json"
        ),
    )
    parser.add_argument(
        "--split", choices=("dev", "test", "challenge", "all"), default="dev"
    )
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--profile", choices=("baseline", "balanced", "aggressive"), required=True
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v1/chat/react-agent"
    )
    parser.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
