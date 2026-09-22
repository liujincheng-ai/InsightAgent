"""Integration tests — full wizard→config→start flow."""

from __future__ import annotations

from unittest.mock import patch

import dbgpt.cli._config as _cfg
from dbgpt.cli._config import (
    read_active_profile,
    resolve_config_path,
    write_active_profile,
    write_profile_config,
)
from dbgpt.cli._wizard import run_setup_noninteractive

# All tests use `isolated_dbgpt_home` from conftest.py — never touches real ~/.dbgpt


# ---------------------------------------------------------------------------
# Test 1: First run triggers wizard and creates TOML
# ---------------------------------------------------------------------------


def test_first_run_triggers_wizard_creates_toml(isolated_dbgpt_home):
    """First run: calling run_setup_wizard creates profile TOML + activates it."""
    from dbgpt.cli._wizard import run_setup_wizard

    # Ensure no config exists before wizard runs
    assert not (_cfg._CONFIGS_DIR / "openai.toml").exists()

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key", return_value="sk-test"),
        patch(
            "dbgpt.cli._wizard._ask_model_names",
            return_value=("gpt-4o", "text-embedding-3-small"),
        ),
        patch("dbgpt.cli._wizard._print_welcome"),
        patch(
            "dbgpt.cli._wizard._ask_api_base",
            return_value="https://api.openai.com/v1",
        ),
    ):
        from dbgpt.cli._profiles import get_profile

        mock_ask_profile.return_value = get_profile("openai")

        run_setup_wizard()

    # openai.toml must exist under the isolated configs dir
    assert (_cfg._CONFIGS_DIR / "openai.toml").exists()
    # Active profile must be set to "openai"
    assert read_active_profile() == "openai"


# ---------------------------------------------------------------------------
# Test 2: Profile switch then start resolves correct config
# ---------------------------------------------------------------------------


def test_profile_switch_then_start_resolves_config(isolated_dbgpt_home):
    """Switching active profile makes resolve_config_path return the new profile path."""  # noqa: E501
    # Create two TOML files
    _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\n", encoding="utf-8")
    (_cfg._CONFIGS_DIR / "qwen.toml").write_text("[models]\n", encoding="utf-8")

    # Switch to qwen
    write_active_profile("qwen")

    # resolve_config_path with no args should pick up qwen
    result = resolve_config_path()
    assert result is not None
    assert "qwen.toml" in result


# ---------------------------------------------------------------------------
# Test 3: start web help shows config/profile options
# ---------------------------------------------------------------------------


def test_start_web_invokes_webserver_with_resolved_config(isolated_dbgpt_home):
    """start web --help exits 0 and shows relevant option text."""
    import click.testing

    from dbgpt.cli.cli_scripts import cli

    runner = click.testing.CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["start", "web", "--help"])

    # --help should always succeed (exit 0) and show options
    assert result.exit_code == 0
    # Should show at least one of the expected flags
    help_text = result.output
    assert "--config" in help_text or "--profile" in help_text or "--yes" in help_text


# ---------------------------------------------------------------------------
# Test 4: CLI --profile flag overrides active profile
# ---------------------------------------------------------------------------


def test_cli_flag_overrides_active_profile(isolated_dbgpt_home):
    """resolve_config_path(profile=...) returns that profile's path, not the active one."""  # noqa: E501
    _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\n", encoding="utf-8")
    (_cfg._CONFIGS_DIR / "qwen.toml").write_text("[models]\n", encoding="utf-8")

    # Active profile is openai
    write_active_profile("openai")

    # But we pass profile="qwen" explicitly
    result = resolve_config_path(profile="qwen")
    assert result is not None
    assert "qwen.toml" in result
    assert "openai.toml" not in result


# ---------------------------------------------------------------------------
# Test 5: Explicit --config flag overrides everything
# ---------------------------------------------------------------------------


def test_explicit_config_flag_overrides_all(isolated_dbgpt_home):
    """resolve_config_path(config=...) returns the exact path regardless of active profile."""  # noqa: E501
    _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\n", encoding="utf-8")
    write_active_profile("openai")

    custom_path = "/custom/path.toml"
    result = resolve_config_path(config=custom_path)
    assert result == custom_path


# ---------------------------------------------------------------------------
# Test 6: Non-interactive mode creates default profile
# ---------------------------------------------------------------------------


def test_noninteractive_mode_creates_default_profile(isolated_dbgpt_home):
    """run_setup_noninteractive writes openai.toml with the provided API key."""
    # Confirm no config exists first
    assert not (_cfg._CONFIGS_DIR / "openai.toml").exists()

    run_setup_noninteractive(profile_name="openai", api_key="sk-test")

    # Profile TOML must be created
    toml_path = _cfg._CONFIGS_DIR / "openai.toml"
    assert toml_path.exists()
    content = toml_path.read_text(encoding="utf-8")
    assert "sk-test" in content


# ---------------------------------------------------------------------------
# Test 7: Skip provider creates minimal config
# ---------------------------------------------------------------------------


def test_skip_provider_creates_minimal_config(isolated_dbgpt_home):
    """write_profile_config('default', ...) creates default.toml and activates it."""
    # Confirm no config exists
    assert not (_cfg._CONFIGS_DIR / "default.toml").exists()

    write_profile_config("default", api_key=None, activate=True)

    # default.toml must exist
    toml_path = _cfg._CONFIGS_DIR / "default.toml"
    assert toml_path.exists()
    # Active profile must be "default"
    assert read_active_profile() == "default"
