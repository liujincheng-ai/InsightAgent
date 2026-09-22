"""Smoke tests for CLI test infrastructure — verifies fixture isolation."""

import os
from pathlib import Path


def test_isolated_dbgpt_home_is_not_real_home(isolated_dbgpt_home):
    """Verify that isolated_dbgpt_home does NOT point to the real ~/.dbgpt."""
    real_home = Path.home() / ".dbgpt"
    assert isolated_dbgpt_home != real_home, (
        f"isolated_dbgpt_home should not be the real home: {real_home}"
    )


def test_isolated_dbgpt_home_env_var(isolated_dbgpt_home):
    """Verify DBGPT_HOME env var is set to the isolated path."""
    env_home = os.environ.get("DBGPT_HOME")
    assert env_home is not None, "DBGPT_HOME env var should be set"
    assert env_home == str(isolated_dbgpt_home), (
        f"DBGPT_HOME ({env_home}) should match isolated_dbgpt_home ({isolated_dbgpt_home})"  # noqa: E501
    )


def test_isolated_dbgpt_home_patches_config_module(isolated_dbgpt_home):
    """Verify _config module constants are patched to isolated temp path."""
    import dbgpt.cli._config as _cfg

    assert _cfg._DBGPT_HOME == isolated_dbgpt_home, (
        f"_config._DBGPT_HOME ({_cfg._DBGPT_HOME}) should equal isolated home"
    )
    assert _cfg._CONFIGS_DIR == isolated_dbgpt_home / "configs", (
        "_config._CONFIGS_DIR should be under isolated home"
    )
    assert _cfg._ACTIVE_CONFIG == isolated_dbgpt_home / "config.toml", (
        "_config._ACTIVE_CONFIG should be under isolated home"
    )


def test_cli_runner_returns_click_runner(cli_runner):
    """Verify cli_runner fixture returns a CliRunner instance."""
    import click.testing

    assert isinstance(cli_runner, click.testing.CliRunner)
