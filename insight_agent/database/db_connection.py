"""Shared PostgreSQL connection settings for local InsightAgent scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
from psycopg2.extensions import connection


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection configuration with local-demo defaults."""

    host: str = "localhost"
    port: int = 5432
    database: str = "insight_agent"
    user: str = "insight"
    password: str = ""

    @classmethod
    def from_environment(cls) -> "DatabaseConfig":
        """Build configuration from optional INSIGHT_DB_* overrides."""
        password = os.getenv("INSIGHT_DB_PASSWORD")
        if not password:
            raise RuntimeError("INSIGHT_DB_PASSWORD 未配置")
        return cls(
            host=os.getenv("INSIGHT_DB_HOST", cls.host),
            port=int(os.getenv("INSIGHT_DB_PORT", str(cls.port))),
            database=os.getenv("INSIGHT_DB_NAME", cls.database),
            user=os.getenv("INSIGHT_DB_USER", cls.user),
            password=password,
        )

    def safe_summary(self) -> str:
        """Return a log-safe connection identity without a password."""
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


def connect(config: DatabaseConfig | None = None) -> connection:
    """Open a PostgreSQL connection without logging credentials."""
    config = config or DatabaseConfig.from_environment()
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
        connect_timeout=10,
        application_name="insight_agent_day1",
    )
