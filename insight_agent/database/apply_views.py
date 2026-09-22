"""Create Week 1 semantic views and grant the configured read-only role."""

from __future__ import annotations

import os
from pathlib import Path

from psycopg2 import sql

from .db_connection import connect


def apply_semantic_views(role_name: str) -> None:
    if not role_name.replace("_", "").isalnum():
        raise ValueError("INSIGHT_TOOL_DB_USER 只能包含字母、数字和下划线")
    statements = (Path(__file__).resolve().parent / "views.sql").read_text(
        encoding="utf-8"
    )
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(statements)
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT ON insight_quarterly_sales, "
                    "insight_quarterly_customer_sales TO {}"
                ).format(sql.Identifier(role_name))
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    role_name = os.getenv("INSIGHT_TOOL_DB_USER", "insight_readonly")
    apply_semantic_views(role_name)
    print(f"Week 1 semantic views ready for read-only role: {role_name}")


if __name__ == "__main__":
    main()
