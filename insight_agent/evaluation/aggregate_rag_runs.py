"""Aggregate non-overwriting Week 3 run directories into a comparison table."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def aggregate(input_dir: Path, *, prefix: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted(input_dir.glob("*/run_manifest.json")):
        if prefix and not manifest_path.parent.name.startswith(prefix):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary = manifest.get("summary", {})
        retrieval = summary.get("retrieval", {})
        answer = summary.get("answer", {})
        rows.append(
            {
                "run_id": manifest.get("run_id"),
                "mode": manifest.get("mode"),
                "retriever": manifest.get("retriever"),
                "chunk_size": manifest.get("chunk_size"),
                "chunk_overlap": manifest.get("chunk_overlap"),
                "top_k": manifest.get("top_k"),
                "query_strategy": manifest.get("query_strategy", "single"),
                "split": manifest.get("split"),
                "model": manifest.get("model"),
                "document_hit_at_k": retrieval.get("document_hit_at_k"),
                "section_hit_at_k": retrieval.get("section_hit_at_k"),
                "gold_source_coverage_at_k": retrieval.get("gold_source_coverage_at_k"),
                "mrr": retrieval.get("mrr"),
                "retrieval_latency": retrieval.get("average_retrieval_latency_seconds"),
                "answer_fact_accuracy": answer.get("answer_fact_accuracy"),
                "citation_precision": answer.get("citation_precision"),
                "no_answer_accuracy": answer.get("no_answer_accuracy"),
                "fabricated_citations": answer.get("fabricated_citation_count"),
                "pass_rate": answer.get("pass_rate"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--prefix")
    args = parser.parse_args()
    rows = aggregate(Path(args.input_dir), prefix=args.prefix)
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"结果目录非空，拒绝覆盖: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = sorted(
        rows,
        key=lambda item: (
            -(item["document_hit_at_k"] or 0),
            -(item["mrr"] or 0),
            -(item["section_hit_at_k"] or 0),
            item["retrieval_latency"] or float("inf"),
        ),
    )
    payload = {
        "run_count": len(rows),
        "best_retrieval": ranked[0] if ranked else None,
        "runs": rows,
    }
    (output_dir / "comparison.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if rows:
        with (output_dir / "comparison.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
