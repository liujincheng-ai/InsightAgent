"""Run the frozen InsightAgent V1 benchmark against the InsightAgent SSE API."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .metrics import score_record, summarize_records
from .schemas import file_sha256, load_dataset, validate_v1_pair

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
                event = json.loads(data)
            except json.JSONDecodeError:
                event = {"type": "unparsed", "content": data}
            events.append(event)
    return events


def parse_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract final answer, tools, SQL and citations without discarding events."""

    answer = ""
    tools: list[str] = []
    sql: list[str] = []
    sql_executed = False
    pending_sql = False
    sources: list[Any] = []
    for event in events:
        event_type = event.get("type")
        if event_type == "final":
            answer = str(event.get("content", ""))
            sources.extend(event.get("citations", []) or [])
        if event_type == "step.meta":
            action = str(event.get("action", ""))
            if action and action not in tools:
                tools.append(action)
            if action == "sql_query":
                pending_sql = True
                action_input = event.get("action_input", "")
                try:
                    parsed = json.loads(action_input)
                    candidate = parsed.get("sql") or parsed.get("query")
                except (json.JSONDecodeError, AttributeError, TypeError):
                    candidate = action_input
                if candidate:
                    sql.append(str(candidate))
        if event_type == "step.chunk" and pending_sql:
            observation = str(event.get("content", ""))
            failure_markers = ("预执行校验失败", "数据库未执行", "error", "Error")
            if observation and not any(
                marker in observation for marker in failure_markers
            ):
                sql_executed = True
            pending_sql = False
    raw_trajectory = json.dumps(events, ensure_ascii=False, separators=(",", ":"))
    return {
        "actual_answer": answer,
        "actual_tools": tools,
        "actual_sql": sql,
        "sql_executed": sql_executed,
        "actual_sources": sources,
        "raw_trajectory": raw_trajectory,
    }


def evaluate_case(
    case: dict[str, Any],
    *,
    endpoint: str,
    model: str,
    temperature: float,
    timeout: float,
    transport: JsonTransport = _post_sse,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run one case in a fresh conversation and always return a record."""

    conv_uid = f"day5-{case['id']}-{uuid.uuid4()}"
    if case["type"] == "rag":
        ext_info = {"knowledge_space_name": "汽车配件企业制度库"}
    elif case["type"] in {
        "sales_diagnosis",
        "customer_loss",
        "dealer_health",
        "integrated",
    }:
        ext_info = {
            "database_name": "insight_agent",
            "database_type": "postgresql",
            "knowledge_space_name": "汽车配件企业制度库",
        }
    else:
        ext_info = {
            "database_name": "insight_agent",
            "database_type": "postgresql",
        }
    payload = {
        "conv_uid": conv_uid,
        "user_input": case["question"],
        "chat_mode": "chat_react_agent",
        "model_name": model,
        "temperature": temperature,
        "max_new_tokens": 4000,
        "select_param": "",
        "ext_info": ext_info,
    }
    started = time.perf_counter()
    error: str | None = None
    events: list[dict[str, Any]] = []
    try:
        events = transport(endpoint, payload, timeout)
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
    latency = round(time.perf_counter() - started, 3)
    actual["error"] = error
    verdict = score_record(case, actual)
    record = {
        "id": case["id"],
        "type": case["type"],
        "question": case["question"],
        "expected_facts": case["expected_facts"],
        "expected_tool": case.get("expected_tool"),
        "expected_documents": case.get("expected_documents", []),
        "expected_sections": case.get("expected_sections", []),
        "numeric_tolerance": case["numeric_tolerance"],
        **actual,
        "latency_seconds": latency,
        "model": model,
        "temperature": temperature,
        "conversation_id": conv_uid,
        "token_usage": None,
        "estimated_cost_cny": None,
        **verdict,
        "manual_review": {
            "required": case["grading"] == "deterministic_and_manual",
            "reviewer": None,
            "decision": None,
            "reason": None,
        },
    }
    return record, events


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_summary_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "type",
        "pass_fail",
        "failure_category",
        "failure_reason",
        "latency_seconds",
        "model",
        "conversation_id",
        "actual_tools",
        "actual_sql",
        "actual_answer",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["actual_tools"] = json.dumps(row["actual_tools"], ensure_ascii=False)
            row["actual_sql"] = json.dumps(row["actual_sql"], ensure_ascii=False)
            writer.writerow(row)


def run(args: argparse.Namespace, transport: JsonTransport = _post_sse) -> int:
    dataset_dir = Path(args.dataset_dir)
    paths = {
        "dev": dataset_dir / "v1_dev.json",
        "test": dataset_dir / "v1_test.json",
    }
    datasets = {name: load_dataset(path) for name, path in paths.items()}
    errors = validate_v1_pair(datasets["dev"], datasets["test"])
    if errors:
        raise ValueError("数据集校验失败:\n- " + "\n- ".join(errors))
    selected = [args.split] if args.split != "all" else ["dev", "test"]
    cases = [
        {**case, "split": split}
        for split in selected
        for case in datasets[split]["cases"]
    ]
    case_ids = getattr(args, "case_id", None)
    if case_ids:
        requested = set(case_ids)
        cases = [case for case in cases if case["id"] in requested]
        found = {case["id"] for case in cases}
        missing = sorted(requested - found)
        if missing:
            raise ValueError("未找到指定评测 ID: " + ", ".join(missing))
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} {case['question']}", flush=True)
        record, events = evaluate_case(
            case,
            endpoint=args.endpoint,
            model=args.model,
            temperature=args.temperature,
            timeout=args.timeout,
            transport=transport,
        )
        record["split"] = case["split"]
        records.append(record)
        raw_payload = {"case": case, "record": record, "events": events}
        with (raw_dir / f"{case['id']}.json").open("w", encoding="utf-8") as stream:
            json.dump(raw_payload, stream, ensure_ascii=False, indent=2)
    summary = summarize_records(records)
    with (output_dir / "records.json").open("w", encoding="utf-8") as stream:
        json.dump(records, stream, ensure_ascii=False, indent=2)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    _write_summary_csv(output_dir / "summary.csv", records)
    manifest = {
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": args.split,
        "model": args.model,
        "temperature": args.temperature,
        "endpoint": args.endpoint,
        "timeout_seconds": args.timeout,
        "database": "insight_agent",
        "knowledge_base": "汽车配件企业制度库",
        "prompt_version": "insight-agent-day4-working-tree",
        "data_version": "v1-529e9fc1",
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "git_dirty": bool(_git_value("status", "--porcelain")),
        "dataset_sha256": {name: file_sha256(path) for name, path in paths.items()},
        "case_count": len(cases),
        "raw_trace_preserved": True,
        "token_and_cost_note": "API 未返回可审计计费 Token；未估算成本。",
        "summary": summary,
    }
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--case-id",
        action="append",
        help="只运行指定任务 ID；可重复传入。默认运行所选 split 的全部任务。",
    )
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:5670/api/v1/chat/react-agent"
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(Path(__file__).resolve().parent / "dataset"),
    )
    parser.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
