"""Rebuild the four InsightAgent tables and bulk-load generated CSV data."""

from __future__ import annotations

import argparse
from pathlib import Path

from .db_connection import DatabaseConfig, connect

TABLE_FILES = [
    ("dim_region", "dim_region.csv"),
    ("dim_product", "dim_product.csv"),
    ("dim_customer", "dim_customer.csv"),
    ("fact_sales", "fact_sales.csv"),
]


def load_dataset(schema_path: Path, data_dir: Path) -> dict[str, int]:
    """Execute schema and COPY all CSV files in one transaction."""
    missing = [name for _, name in TABLE_FILES if not (data_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing generated CSV files: {', '.join(missing)}")

    config = DatabaseConfig.from_environment()
    print(f"Connecting to {config.safe_summary()}")
    connection = connect(config)
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_path.read_text(encoding="utf-8"))
                for table, file_name in TABLE_FILES:
                    csv_path = data_dir / file_name
                    with csv_path.open("r", encoding="utf-8", newline="") as file:
                        cursor.copy_expert(
                            f"COPY {table} FROM STDIN "
                            "WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')",
                            file,
                        )
                cursor.execute("ANALYZE;")

        counts: dict[str, int] = {}
        with connection.cursor() as cursor:
            for table, _ in TABLE_FILES:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
        return counts
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=base_dir / "schema.sql")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=base_dir.parent / "data" / "raw",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = load_dataset(args.schema, args.data_dir)
    for table, count in counts.items():
        print(f"{table}: {count:,}")


if __name__ == "__main__":
    main()
