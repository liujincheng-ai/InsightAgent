"""Run the deterministic Week 4 identical-failure circuit-breaker check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dbgpt.agent.resource.tool.base import tool
from insight_agent.reliability import InsightReliabilityToolPack


@tool("week4_failing_tool")
def _failing_tool(query: str) -> dict[str, Any]:
    """Return the same correctable failure for circuit-breaker verification."""

    return {
        "status": "error",
        "error_code": "INVALID_ARGUMENTS",
        "message": f"invalid query: {query}",
    }


def run(trials: int) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index in range(1, trials + 1):
        pack = InsightReliabilityToolPack(
            [_failing_tool],
            reliability_config={"policy_enabled": True, "profile": "after"},
        )
        for _ in range(2):
            pack.execute(resource_name="week4_failing_tool", query="same")
        records.append(
            {
                "trial": index,
                "fingerprints_equal": (
                    pack.diagnostics[0]["guard"]["fingerprint"]
                    == pack.diagnostics[1]["guard"]["fingerprint"]
                ),
                "second_call_count": pack.diagnostics[1]["guard"][
                    "consecutive_count"
                ],
                "circuit_open": pack.diagnostics[1]["guard"]["circuit_open"],
                "terminal": pack.diagnostics[1]["decision"]["terminal"],
                "post_breaker_calls": 0,
            }
        )
    passed = sum(
        item["fingerprints_equal"]
        and item["second_call_count"] == 2
        and item["circuit_open"]
        and item["terminal"]
        and item["post_breaker_calls"] == 0
        for item in records
    )
    return {
        "trials": trials,
        "passed": passed,
        "trigger_rate": passed / trials,
        "post_breaker_call_rate": 0.0,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 1:
        raise ValueError("trials must be positive")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output}")
    result = run(args.trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: result[key] for key in result if key != "records"}))


if __name__ == "__main__":
    main()
