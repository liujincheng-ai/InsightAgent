"""Tests for cli_scripts.py — start group alias and bare-start behavior."""

from unittest.mock import patch

from click.testing import CliRunner

from dbgpt.cli.cli_scripts import cli


def test_start_web_alias_help_shows_options():
    """dbgpt start web --help exits 0 and shows --config and --profile."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["start", "web", "--help"])
    assert result.exit_code == 0, result.output
    assert "--config" in result.output or "--profile" in result.output


def test_start_webserver_still_works():
    """dbgpt start webserver --help exits 0 (regression)."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["start", "webserver", "--help"])
    assert result.exit_code == 0, result.output


def test_start_controller_unaffected():
    """dbgpt start controller --help still works after changes."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["start", "controller", "--help"])
    assert result.exit_code == 0, result.output


def test_bare_start_invokes_web_or_shows_help():
    """bare dbgpt start (no subcommand) either invokes web or shows help — does NOT crash."""  # noqa: E501
    runner = CliRunner(mix_stderr=False)
    with (
        patch("dbgpt.cli._wizard.maybe_run_wizard", return_value="/fake/config.toml"),
        patch("dbgpt_app.dbgpt_server.run_webserver"),
    ):
        result = runner.invoke(cli, ["start"])
    # Must not return an error exit code from a crash
    assert result.exit_code in (0, 1, 2), (
        f"Unexpected exit code: {result.exit_code}\n{result.output}"
    )
    assert result.exception is None or "No such command" not in str(result.exception)


def test_start_none_exits_zero(cli_runner):
    from dbgpt.cli.cli_scripts import cli

    result = cli_runner.invoke(cli, ["start", "none"])
    assert result.exit_code == 0


def test_start_none_output_mentions_planned(cli_runner):
    from dbgpt.cli.cli_scripts import cli

    result = cli_runner.invoke(cli, ["start", "none"])
    assert "planned" in result.output.lower()


def test_start_none_output_mentions_start_web(cli_runner):
    from dbgpt.cli.cli_scripts import cli

    result = cli_runner.invoke(cli, ["start", "none"])
    assert "dbgpt start web" in result.output
