"""Recompute Week 3 answer metrics from preserved model outputs without rerunning."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .citation_check import score_structured_answer
from .rag_metrics import summarize_answer_records, summarize_retrieval_records
from .rag_schemas import load_rag_dataset

SCORE_FIELDS = {
    "structured_answer",
    "answer_fact_accuracy",
    "missing_facts",
    "citation_verdicts",
    "fabricated_citation_count",
    "unacceptable_conclusions_found",
    "no_answer_correct",
    "pass_fail",
    "failure_category",
}


def rescore(source_dir: Path, output_dir: Path, dataset_path: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads((source_dir / "records.json").read_text(encoding="utf-8"))
    dataset = load_rag_dataset(dataset_path)
    cases = {case["id"]: case for case in dataset["cases"]}
    rescored: list[dict[str, Any]] = []
    for original in records:
        record = {
            key: value for key, value in original.items() if key not in SCORE_FIELDS
        }
        case = cases[record["id"]]
        record.update(
            score_structured_answer(
                case,
                record["raw_answer"],
                retrieved=record["retrieved"],
            )
        )
        rescored.append(record)
    source_manifest = json.loads(
        (source_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    top_k = int(source_manifest["top_k"])
    summary = {
        "retrieval": summarize_retrieval_records(rescored, top_k=top_k),
        "answer": summarize_answer_records(rescored),
    }
    manifest = {
        **source_manifest,
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rescore_of": source_dir.name,
        "model_rerun": False,
        "summary": summary,
    }
    (output_dir / "records.json").write_text(
        json.dumps(rescored, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir")
    parser.add_argument("output_dir")
    parser.add_argument(
        "--dataset",
        default=str(root / "insight_agent/evaluation/dataset/rag_test.json"),
    )
    args = parser.parse_args()
    summary = rescore(Path(args.source_dir), Path(args.output_dir), Path(args.dataset))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
