"""Shared fixtures for CLI tests."""

import click.testing
import pytest


@pytest.fixture()
def isolated_dbgpt_home(tmp_path, monkeypatch):
    """Isolate DBGPT_HOME to a temp directory."""
    home = tmp_path / "dbgpt"
    home.mkdir()
    monkeypatch.setenv("DBGPT_HOME", str(home))
    import dbgpt.cli._config as _cfg

    monkeypatch.setattr(_cfg, "_DBGPT_HOME", home)
    monkeypatch.setattr(_cfg, "_CONFIGS_DIR", home / "configs")
    monkeypatch.setattr(_cfg, "_ACTIVE_CONFIG", home / "config.toml")
    return home


@pytest.fixture()
def cli_runner():
    """Return a Click test runner."""
    return click.testing.CliRunner(mix_stderr=False)
