"""Recompute derived scores from immutable Day 5 raw result files."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import score_record, summarize_records
from .run_eval import parse_events


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "split",
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


def rescore(output_dir: Path) -> dict[str, Any]:
    """Update records and summaries while leaving event arrays unchanged."""

    raw_files = sorted((output_dir / "raw").glob("*.json"))
    if not raw_files:
        raise FileNotFoundError(f"没有原始结果: {output_dir / 'raw'}")
    records: list[dict[str, Any]] = []
    for path in raw_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        case = payload["case"]
        record = payload["record"]
        reparsed = parse_events(payload.get("events", []))
        record.update(reparsed)
        verdict = score_record(case, record)
        record.update(verdict)
        payload["record"] = record
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        records.append(record)
    records.sort(key=lambda item: (item.get("split", ""), item["id"]))
    summary = summarize_records(records)
    (output_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(output_dir / "summary.csv", records)
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"] = summary
    manifest["scoring_version"] = "day5-v1.1-whitespace-normalized"
    manifest["rescored_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["rescore_note"] = (
        "仅修正文本事实空白归一化；模型事件、答案、Tool、SQL、引用与延迟未变。"
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(rescore(args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
