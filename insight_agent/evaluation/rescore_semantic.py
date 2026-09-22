"""Recompute Week 1 derived verdicts while preserving model events and answers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .run_semantic_eval import _write_csv
from .semantic_metrics import score_semantic_case, summarize_semantic_records

SCORER_VERSION = "week1-semantic-v2-unit-normalized"


def rescore(result_dir: str | Path) -> dict[str, Any]:
    directory = Path(result_dir)
    records_path = directory / "records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    refreshed: list[dict[str, Any]] = []
    for record in records:
        raw_path = directory / "raw" / f"{record['id']}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        events_before = json.dumps(raw["events"], ensure_ascii=False, sort_keys=True)
        actual = {
            key: record.get(key)
            for key in (
                "actual_answer",
                "actual_tools",
                "actual_sql",
                "sql_executed",
                "actual_sources",
                "raw_trajectory",
                "error",
            )
        }
        verdict = score_semantic_case(raw["case"], actual, raw["events"])
        updated = {**record, **verdict}
        updated["pass_fail"] = "pass" if verdict["passed"] else "fail"
        raw["record"] = updated
        assert events_before == json.dumps(
            raw["events"], ensure_ascii=False, sort_keys=True
        )
        raw_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        refreshed.append(updated)
    summary = summarize_semantic_records(refreshed)
    records_path.write_text(
        json.dumps(refreshed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (directory / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(directory / "summary.csv", refreshed)
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"] = summary
    manifest["rescore"] = {
        "scorer_version": SCORER_VERSION,
        "rescored_at_utc": datetime.now(timezone.utc).isoformat(),
        "immutable_fields": ["events", "actual_answer", "actual_sql"],
        "reason": (
            "Normalize decimal ratios vs percent and separate strict result-set "
            "from evidence-bound answer facts."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir")
    args = parser.parse_args()
    print(json.dumps(rescore(args.result_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
