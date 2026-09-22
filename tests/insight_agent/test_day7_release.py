from __future__ import annotations

from pathlib import Path

import pytest

from insight_agent.database.db_connection import DatabaseConfig
from insight_agent.database.provision_readonly import provision_readonly_role


def test_database_owner_password_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHT_DB_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="INSIGHT_DB_PASSWORD"):
        DatabaseConfig.from_environment()


def test_database_config_reads_runtime_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSIGHT_DB_HOST", "db.internal")
    monkeypatch.setenv("INSIGHT_DB_PORT", "5544")
    monkeypatch.setenv("INSIGHT_DB_NAME", "business")
    monkeypatch.setenv("INSIGHT_DB_USER", "owner")
    monkeypatch.setenv("INSIGHT_DB_PASSWORD", "runtime-only")

    config = DatabaseConfig.from_environment()

    assert config.host == "db.internal"
    assert config.port == 5544
    assert config.database == "business"
    assert config.user == "owner"
    assert config.password == "runtime-only"
    assert "runtime-only" not in config.safe_summary()


def test_readonly_role_name_rejects_sql_tokens() -> None:
    with pytest.raises(ValueError, match="字母、数字和下划线"):
        provision_readonly_role("reader; DROP ROLE owner", "not-logged")


def test_insightagent_welcome_copy_and_prompt_are_present() -> None:
    root = Path(__file__).resolve().parents[2]
    welcome = (root / "web/new-components/chat/ChatWelcome.tsx").read_text(
        encoding="utf-8"
    )
    page = (root / "web/new-components/chat/ChatPage.tsx").read_text(encoding="utf-8")
    home_page = (root / "web/pages/index.tsx").read_text(encoding="utf-8")

    assert "InsightAgent" in welcome
    assert "企业经营数据与知识协同分析智能体" in welcome
    assert "2026 年第二季度华东区域刹车系统" in welcome
    assert "inputRef.current.setValue(suggestion.prompt)" in page
    assert "华东销售下滑诊断" in home_page
    assert "Evidence-first analytics" in home_page
    assert "DB-GPT" not in home_page
    assert "if (example.fillOnly)" in home_page
    assert "setQuery(translatedQuery)" in home_page
