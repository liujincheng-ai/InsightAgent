"""Validate Day 1 database invariants and freeze the computed Gold Truth."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from psycopg2.extras import RealDictCursor

from .db_connection import connect
from .generate_data import (
    END_DATE,
    FACT_ROW_COUNT,
    RANDOM_SEED,
    SPECIAL_EAST_DEALERS,
    START_DATE,
)


def _percent_change(current: Decimal, baseline: Decimal) -> float:
    return float((current / baseline - 1) * 100)


def _hash_files(data_dir: Path) -> tuple[dict[str, str], str]:
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(data_dir.glob("*.csv"))
    }
    if len(hashes) != 4:
        raise AssertionError(f"Expected 4 generated CSV files, found {len(hashes)}")
    source = "\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes))
    return hashes, hashlib.sha256(source.encode("utf-8")).hexdigest()


def collect_validation(data_dir: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    connection = connect()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM dim_region) AS regions,
                    (SELECT COUNT(*) FROM dim_product) AS products,
                    (SELECT COUNT(*) FROM dim_customer) AS customers,
                    (SELECT COUNT(*) FROM fact_sales) AS sales,
                    (SELECT MIN(sale_date) FROM fact_sales) AS min_date,
                    (SELECT MAX(sale_date) FROM fact_sales) AS max_date
                """
            )
            counts = dict(cursor.fetchone())
            checks["counts_and_range"] = {
                key: value.isoformat() if hasattr(value, "isoformat") else value
                for key, value in counts.items()
            }
            assert counts["regions"] == 5
            assert counts["products"] == 36
            assert counts["customers"] == 150
            assert counts["sales"] == FACT_ROW_COUNT
            assert counts["min_date"] == START_DATE
            assert counts["max_date"] == END_DATE

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE
                        f.sale_date IS NULL OR f.region_id IS NULL
                        OR f.product_id IS NULL OR f.customer_id IS NULL
                        OR f.channel IS NULL OR f.quantity IS NULL
                        OR f.unit_price IS NULL OR f.discount_rate IS NULL
                        OR f.sales_amount IS NULL OR f.cost_amount IS NULL
                        OR f.gross_profit IS NULL
                    ) AS null_rows,
                    COUNT(*) FILTER (WHERE ABS(
                        f.sales_amount
                        - ROUND(f.quantity * f.unit_price * (1 - f.discount_rate), 2)
                    ) > 0.01) AS invalid_sales_formula,
                    COUNT(*) FILTER (WHERE ABS(
                        f.gross_profit - (f.sales_amount - f.cost_amount)
                    ) > 0.01) AS invalid_profit_formula,
                    COUNT(*) FILTER (WHERE f.sale_date < %s OR f.sale_date > %s)
                        AS out_of_range_rows,
                    COUNT(*) FILTER (WHERE
                        c.region_id <> f.region_id OR c.channel <> f.channel
                    )
                        AS dimension_mismatch_rows
                FROM fact_sales f
                JOIN dim_customer c USING (customer_id)
                """,
                (START_DATE, END_DATE),
            )
            integrity = dict(cursor.fetchone())
            checks["integrity"] = integrity
            assert all(value == 0 for value in integrity.values())

            cursor.execute(
                """
                SELECT
                    SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ) AS current_sales,
                    SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-01-01'
                          AND f.sale_date < DATE '2026-04-01'
                    ) AS qoq_sales,
                    SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2025-04-01'
                          AND f.sale_date < DATE '2025-07-01'
                    ) AS yoy_sales,
                    AVG(f.discount_rate) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ) AS current_discount,
                    AVG(f.discount_rate) FILTER (
                        WHERE f.sale_date >= DATE '2026-01-01'
                          AND f.sale_date < DATE '2026-04-01'
                    ) AS qoq_discount,
                    SUM(f.gross_profit) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ) / NULLIF(SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ), 0) AS current_margin,
                    SUM(f.gross_profit) FILTER (
                        WHERE f.sale_date >= DATE '2026-01-01'
                          AND f.sale_date < DATE '2026-04-01'
                    ) / NULLIF(SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-01-01'
                          AND f.sale_date < DATE '2026-04-01'
                    ), 0) AS qoq_margin
                FROM fact_sales f
                JOIN dim_region r USING (region_id)
                JOIN dim_product p USING (product_id)
                WHERE r.region_name = '华东' AND p.category = '刹车系统'
                """
            )
            metrics = dict(cursor.fetchone())
            qoq_change = _percent_change(metrics["current_sales"], metrics["qoq_sales"])
            yoy_change = _percent_change(metrics["current_sales"], metrics["yoy_sales"])
            discount_change_pp = float(
                (metrics["current_discount"] - metrics["qoq_discount"]) * 100
            )
            margin_change_pp = float(
                (metrics["current_margin"] - metrics["qoq_margin"]) * 100
            )
            assert -35 <= qoq_change <= -25, qoq_change
            assert -30 <= yoy_change <= -20, yoy_change
            assert 3 <= discount_change_pp <= 5, discount_change_pp
            assert margin_change_pp < 0, margin_change_pp

            cursor.execute(
                """
                WITH channel_sales AS (
                    SELECT
                        f.channel,
                        SUM(f.sales_amount) FILTER (
                            WHERE f.sale_date >= DATE '2026-04-01'
                              AND f.sale_date < DATE '2026-07-01'
                        ) AS current_sales,
                        SUM(f.sales_amount) FILTER (
                            WHERE f.sale_date >= DATE '2026-01-01'
                              AND f.sale_date < DATE '2026-04-01'
                        ) AS baseline_sales
                    FROM fact_sales f
                    JOIN dim_region r USING (region_id)
                    JOIN dim_product p USING (product_id)
                    WHERE r.region_name = '华东' AND p.category = '刹车系统'
                    GROUP BY f.channel
                )
                SELECT channel, current_sales, baseline_sales
                FROM channel_sales
                ORDER BY baseline_sales - current_sales DESC
                """
            )
            channels = [dict(row) for row in cursor.fetchall()]
            total_decline = sum(
                row["baseline_sales"] - row["current_sales"] for row in channels
            )
            dealer = next(row for row in channels if row["channel"] == "经销商")
            dealer_contribution = float(
                (dealer["baseline_sales"] - dealer["current_sales"]) / total_decline
            )
            assert dealer_contribution >= 0.5, dealer_contribution

            cursor.execute(
                """
                WITH customer_sales AS (
                SELECT
                    c.customer_name,
                    c.customer_level,
                    c.channel,
                    COALESCE(SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ), 0) AS current_sales,
                    COALESCE(SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-01-01'
                          AND f.sale_date < DATE '2026-04-01'
                    ), 0) AS baseline_sales
                FROM fact_sales f
                JOIN dim_region r USING (region_id)
                JOIN dim_product p USING (product_id)
                JOIN dim_customer c USING (customer_id)
                WHERE r.region_name = '华东' AND p.category = '刹车系统'
                GROUP BY c.customer_name, c.customer_level, c.channel
                )
                SELECT *
                FROM customer_sales
                ORDER BY baseline_sales - current_sales DESC
                LIMIT 10
                """
            )
            customers = [dict(row) for row in cursor.fetchall()]
            top_three_names = [row["customer_name"] for row in customers[:3]]
            assert set(top_three_names) == set(SPECIAL_EAST_DEALERS), top_three_names

            cursor.execute(
                """
                SELECT
                    SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2026-04-01'
                          AND f.sale_date < DATE '2026-07-01'
                    ) AS current_sales,
                    SUM(f.sales_amount) FILTER (
                        WHERE f.sale_date >= DATE '2025-04-01'
                          AND f.sale_date < DATE '2025-07-01'
                    ) AS yoy_sales
                FROM fact_sales f
                JOIN dim_region r USING (region_id)
                JOIN dim_product p USING (product_id)
                WHERE r.region_name = '华南' AND p.category = '刹车系统'
                """
            )
            south = dict(cursor.fetchone())
            south_yoy_change = _percent_change(
                south["current_sales"], south["yoy_sales"]
            )
            assert south_yoy_change > 0, south_yoy_change

        csv_hashes, fingerprint = _hash_files(data_dir)
        return {
            "dataset_version": "v1",
            "random_seed": RANDOM_SEED,
            "status": "verified",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "synthetic_data_notice": (
                "This dataset is fully synthetic and contains no real company "
                "or personal information."
            ),
            "row_counts": checks["counts_and_range"],
            "integrity_checks": checks["integrity"],
            "scenario": {
                "id": "east_china_brake_q2_decline",
                "period": "2026Q2",
                "qoq_comparison_period": "2026Q1",
                "yoy_comparison_period": "2025Q2",
                "region": "华东",
                "category": "刹车系统",
            },
            "expected_metrics": {
                "current_sales": round(float(metrics["current_sales"]), 2),
                "qoq_sales_change_pct": round(qoq_change, 4),
                "yoy_sales_change_pct": round(yoy_change, 4),
                "average_discount_change_pp": round(discount_change_pp, 4),
                "gross_margin_change_pp": round(margin_change_pp, 4),
                "dealer_decline_contribution_pct": round(dealer_contribution * 100, 4),
                "south_china_brake_yoy_change_pct": round(south_yoy_change, 4),
            },
            "expected_primary_channel": "经销商",
            "expected_top_decline_customers": top_three_names,
            "top_customer_evidence": [
                {
                    "customer_name": row["customer_name"],
                    "customer_level": row["customer_level"],
                    "channel": row["channel"],
                    "baseline_sales": round(float(row["baseline_sales"]), 2),
                    "current_sales": round(float(row["current_sales"]), 2),
                    "decline_amount": round(
                        float(row["baseline_sales"] - row["current_sales"]), 2
                    ),
                }
                for row in customers[:5]
            ],
            "csv_sha256": csv_hashes,
            "dataset_fingerprint": fingerprint,
            "validation_result": "all_checks_passed",
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=repo_root / "insight_agent" / "data" / "raw",
    )
    parser.add_argument(
        "--gold-output",
        type=Path,
        default=repo_root / "insight_agent" / "data" / "gold" / "anomaly_ledger.json",
    )
    parser.add_argument("--evidence-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = collect_validation(args.data_dir)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.gold_output.parent.mkdir(parents=True, exist_ok=True)
    args.gold_output.write_text(payload, encoding="utf-8")
    if args.evidence_output:
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
