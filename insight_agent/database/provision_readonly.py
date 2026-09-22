"""Provision the least-privilege PostgreSQL role used by InsightAgent tools."""

from __future__ import annotations

import os

from psycopg2 import sql

from .db_connection import connect


def provision_readonly_role(role_name: str, password: str) -> None:
    """Create or update a login role and grant read-only access to business data."""

    if not role_name.replace("_", "").isalnum():
        raise ValueError("INSIGHT_TOOL_DB_USER 只能包含字母、数字和下划线")
    if not password:
        raise RuntimeError("INSIGHT_TOOL_DB_PASSWORD 未配置")

    connection = connect()
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
            if cursor.fetchone():
                cursor.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(role_name), sql.Literal(password)
                    )
                )
            else:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(role_name), sql.Literal(password)
                    )
                )
            cursor.execute(
                sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(
                    sql.Identifier(role_name)
                )
            )
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE insight_agent TO {}").format(
                    sql.Identifier(role_name)
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(role_name)
                )
            )
            cursor.execute(
                sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                    sql.Identifier(role_name)
                )
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT SELECT ON TABLES TO {}"
                ).format(sql.Identifier(role_name))
            )
    finally:
        connection.close()


def main() -> None:
    role_name = os.getenv("INSIGHT_TOOL_DB_USER", "insight_readonly")
    password = os.getenv("INSIGHT_TOOL_DB_PASSWORD", "")
    provision_readonly_role(role_name, password)
    print(f"Read-only role ready: {role_name}")


if __name__ == "__main__":
    main()
