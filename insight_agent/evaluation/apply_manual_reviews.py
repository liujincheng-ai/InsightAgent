"""Apply explicit human review decisions to one frozen Day 5 run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .metrics import summarize_records
from .rescore import _write_csv


def apply_reviews(output_dir: Path) -> dict[str, Any]:
    review_path = output_dir / "manual_reviews.json"
    review_doc = json.loads(review_path.read_text(encoding="utf-8"))
    reviews = review_doc["reviews"]
    raw_files = sorted((output_dir / "raw").glob("*.json"))
    records: list[dict[str, Any]] = []
    required_ids: set[str] = set()
    for path in raw_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = payload["record"]
        manual = record.get("manual_review", {})
        if manual.get("required"):
            required_ids.add(record["id"])
            review = reviews.get(record["id"])
            if not review or review.get("decision") not in {"pass", "fail"}:
                raise ValueError(f"缺少人工复核: {record['id']}")
            record["deterministic_passed"] = bool(record["passed"])
            manual.update(
                {
                    "reviewer": review_doc["reviewer"],
                    "decision": review["decision"],
                    "reason": review["reason"],
                }
            )
            record["manual_review"] = manual
            if review["decision"] == "fail":
                record["passed"] = False
                record["pass_fail"] = "fail"
                if not record.get("failure_category"):
                    record["failure_category"] = "manual_integrated_quality"
                    record["failure_reason"] = "人工复核未通过"
        payload["record"] = record
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        records.append(record)
    extra = set(reviews) - required_ids
    missing = required_ids - set(reviews)
    if missing or extra:
        raise ValueError(
            f"人工复核 ID 不一致，missing={sorted(missing)}, extra={sorted(extra)}"
        )
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
    manifest["manual_review"] = {
        "completed": True,
        "reviewed_cases": len(required_ids),
        "reviewer": review_doc["reviewer"],
        "rubric": review_doc["rubric"],
        "artifact": "manual_reviews.json",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(apply_reviews(args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
