"""Read-only PostgreSQL access used by InsightAgent business tools.

The Web datasource and a business tool have different lifecycles.  This module
therefore opens a short-lived connection for one deterministic query and never
accepts SQL from an LLM.  Tool queries are constants in application code and
all values are passed as DB-API parameters.
"""

from __future__ import annotations

import os
from typing import Any, Protocol, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor


class ReadOnlyQueryExecutor(Protocol):
    """Minimal interface that keeps business logic easy to unit test."""

    def fetch_all(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        """Execute a fixed read-only query and return mapping rows."""


class PostgresReadOnlyExecutor:
    """Execute fixed queries with the dedicated least-privilege account."""

    def __init__(self) -> None:
        self._host = os.getenv("INSIGHT_TOOL_DB_HOST", "localhost")
        self._port = int(os.getenv("INSIGHT_TOOL_DB_PORT", "5432"))
        self._database = os.getenv("INSIGHT_TOOL_DB_NAME", "insight_agent")
        self._user = os.getenv("INSIGHT_TOOL_DB_USER", "insight_readonly")
        # Do not put this value in config files, logs, observations, or tests.
        self._password = os.getenv("INSIGHT_TOOL_DB_PASSWORD")

    def fetch_all(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        if not self._password:
            raise RuntimeError("INSIGHT_TOOL_DB_PASSWORD 未配置")
        try:
            with psycopg2.connect(
                host=self._host,
                port=self._port,
                dbname=self._database,
                user=self._user,
                password=self._password,
                connect_timeout=10,
                application_name="insight_agent_sales_diagnosis",
            ) as connection:
                connection.set_session(readonly=True, autocommit=True)
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, tuple(params))
                    return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as exc:
            # The original driver exception can include connection details; only
            # return its class to the Agent so credentials and host internals do
            # not leak into an Observation.
            raise RuntimeError(f"数据库只读查询失败: {type(exc).__name__}") from exc
