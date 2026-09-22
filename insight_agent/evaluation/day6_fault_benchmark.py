"""Run the Day 6 bounded SQL-recovery comparison against local PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dbgpt_app.openapi.api_v1.tools.sql_query import make_sql_query
from insight_agent.database.db_connection import connect


@dataclass(frozen=True)
class FaultCase:
    id: str
    expected_error: str
    faulty_sql: str
    corrected_sql: str | None
    injected_error: BaseException | None = None


CASES = (
    FaultCase(
        "syntax",
        "SYNTAX_ERROR",
        "SELECT * FROM fact_sales WHERE (",
        "SELECT COUNT(*) AS row_count FROM fact_sales",
    ),
    FaultCase(
        "table_not_found",
        "TABLE_NOT_FOUND",
        "SELECT * FROM missing_sales_table",
        "SELECT COUNT(*) AS row_count FROM fact_sales",
    ),
    FaultCase(
        "column_not_found",
        "COLUMN_NOT_FOUND",
        "SELECT missing_amount FROM fact_sales",
        "SELECT SUM(sales_amount) AS sales_amount FROM fact_sales",
    ),
    FaultCase(
        "missing_group_by",
        "SYNTAX_ERROR",
        "SELECT region_id, SUM(sales_amount) FROM fact_sales",
        "SELECT region_id, SUM(sales_amount) FROM fact_sales GROUP BY region_id",
    ),
    FaultCase(
        "type_or_date",
        "TYPE_OR_DATE_ERROR",
        "SELECT DATE '2026-13-01'",
        "SELECT DATE '2026-06-30' AS valid_date",
    ),
    FaultCase(
        "ambiguous_column",
        "AMBIGUOUS_COLUMN",
        (
            "SELECT customer_id FROM fact_sales f "
            "JOIN dim_customer c ON c.customer_id = f.customer_id LIMIT 1"
        ),
        (
            "SELECT f.customer_id FROM fact_sales f "
            "JOIN dim_customer c ON c.customer_id = f.customer_id LIMIT 1"
        ),
    ),
    FaultCase(
        "permission_denied",
        "PERMISSION_DENIED",
        "DELETE FROM fact_sales",
        None,
    ),
    FaultCase(
        "timeout",
        "TIMEOUT",
        "SELECT COUNT(*) FROM fact_sales",
        "SELECT COUNT(*) AS row_count FROM fact_sales",
        TimeoutError("statement timeout at host=10.0.0.8 password=hidden"),
    ),
    FaultCase(
        "unknown",
        "UNKNOWN_SQL_ERROR",
        "SELECT COUNT(*) FROM fact_sales",
        None,
        RuntimeError(r"unrecognized driver failure at C:\private\db.conf"),
    ),
)


class PostgresConnector:
    """Adapt a DB-API connection to InsightAgent's connector result shape."""

    def __init__(self, injected_error: BaseException | None = None) -> None:
        self._injected_error = injected_error
        self._injected = False

    def run(self, sql: str) -> list[Any]:
        if self._injected_error is not None and not self._injected:
            self._injected = True
            raise self._injected_error
        with connect() as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [(item.name,) for item in (cursor.description or ())]
                rows = cursor.fetchall() if cursor.description else []
                return [columns, *rows]


def _run_mode(case: FaultCase, *, retry_enabled: bool) -> dict[str, Any]:
    state = {
        "database_name": "insight_agent",
        "user_input": "Day 6 SQL 主动故障测试",
    }
    connector = PostgresConnector(case.injected_error)
    sql_query = make_sql_query(state, connector)
    first = json.loads(sql_query(case.faulty_sql))
    attempts = [first]
    if retry_enabled and first.get("retryable") and case.corrected_sql:
        attempts.append(json.loads(sql_query(case.corrected_sql)))
    final = attempts[-1]
    serialized = json.dumps(attempts, ensure_ascii=False)
    return {
        "attempt_count": len(attempts),
        "first_error": first.get("error_code"),
        "first_source": first.get("error_source"),
        "classification_correct": first.get("error_code") == case.expected_error,
        "final_execution_success": final.get("status") == "success",
        "safe_observation": all(
            marker not in serialized
            for marker in ("hidden", "10.0.0.8", r"C:\private")
        ),
        "attempts": attempts,
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()
    records: list[dict[str, Any]] = []
    for case in CASES:
        baseline = _run_mode(case, retry_enabled=False)
        recovered = _run_mode(case, retry_enabled=True)
        record = {
            "case": asdict(case) | {"injected_error": repr(case.injected_error)},
            "baseline": baseline,
            "day6": recovered,
        }
        records.append(record)
        (raw_dir / f"{case.id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    retryable = [
        item for item in records if item["baseline"]["attempts"][0].get("retryable")
    ]
    summary = {
        "total_cases": len(records),
        "classification_accuracy": sum(
            item["day6"]["classification_correct"] for item in records
        )
        / len(records),
        "safe_observation_rate": sum(
            item["day6"]["safe_observation"] for item in records
        )
        / len(records),
        "baseline_final_execution_success_rate": sum(
            item["baseline"]["final_execution_success"] for item in records
        )
        / len(records),
        "day6_retryable_final_execution_success_rate": sum(
            item["day6"]["final_execution_success"] for item in retryable
        )
        / len(retryable),
        "average_sql_attempts": sum(
            item["day6"]["attempt_count"] for item in records
        )
        / len(records),
        "non_retryable_cases": [
            item["case"]["id"]
            for item in records
            if not item["baseline"]["attempts"][0].get("retryable")
        ],
        "failed_after_retry": [
            item["case"]["id"]
            for item in retryable
            if not item["day6"]["final_execution_success"]
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "id",
                "expected_error",
                "classification_correct",
                "baseline_success",
                "day6_success",
                "day6_attempts",
                "safe_observation",
            ),
        )
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    "id": item["case"]["id"],
                    "expected_error": item["case"]["expected_error"],
                    "classification_correct": item["day6"][
                        "classification_correct"
                    ],
                    "baseline_success": item["baseline"][
                        "final_execution_success"
                    ],
                    "day6_success": item["day6"]["final_execution_success"],
                    "day6_attempts": item["day6"]["attempt_count"],
                    "safe_observation": item["day6"]["safe_observation"],
                }
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
