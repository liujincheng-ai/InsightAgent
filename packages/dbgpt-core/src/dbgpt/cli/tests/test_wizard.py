"""Tests for _wizard.py — model config step and skip/default flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dbgpt.cli._profiles import get_profile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log_ask(*return_values):
    """Return a mock _log whose .ask() yields values in sequence."""
    mock_log = MagicMock()
    mock_log.ask.side_effect = list(return_values)
    return mock_log


# ---------------------------------------------------------------------------
# _ask_model_names
# ---------------------------------------------------------------------------


def test_ask_model_names_returns_defaults_on_enter():
    """User presses Enter → default values from spec returned."""
    from dbgpt.cli._wizard import _ask_model_names

    spec = get_profile("openai")

    mock_log = _make_log_ask("gpt-4o", "text-embedding-3-small")
    with patch("dbgpt.cli._wizard._log", mock_log):
        llm, emb = _ask_model_names(spec)

    assert llm == "gpt-4o"
    assert emb == "text-embedding-3-small"
    mock_log.ask.assert_any_call("LLM model name", default="gpt-4o")
    mock_log.ask.assert_any_call(
        "Embedding model name", default="text-embedding-3-small"
    )


def test_ask_model_names_returns_custom_values():
    """User types custom model names → returned as-is."""
    from dbgpt.cli._wizard import _ask_model_names

    spec = get_profile("openai")

    mock_log = _make_log_ask("my-custom-llm", "my-custom-emb")
    with patch("dbgpt.cli._wizard._log", mock_log):
        llm, emb = _ask_model_names(spec)

    assert llm == "my-custom-llm"
    assert emb == "my-custom-emb"


# ---------------------------------------------------------------------------
# run_setup_wizard — model names integration
# ---------------------------------------------------------------------------


def test_run_setup_wizard_calls_ask_model_names(isolated_dbgpt_home):
    """run_setup_wizard passes llm_model/embedding_model to write_profile_config."""
    from dbgpt.cli._wizard import run_setup_wizard

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key", return_value="sk-test"),
        patch(
            "dbgpt.cli._wizard._ask_api_base", return_value="https://api.openai.com/v1"
        ),
        patch(
            "dbgpt.cli._wizard._ask_model_names",
            return_value=("gpt-4o", "text-embedding-3-small"),
        ) as mock_model,
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "openai.toml",
        ) as mock_write,
        patch("dbgpt.cli._wizard._print_welcome"),
    ):
        spec = get_profile("openai")
        mock_ask_profile.return_value = spec

        run_setup_wizard()

        mock_model.assert_called_once_with(spec)
        mock_write.assert_called_once_with(
            "openai",
            api_key="sk-test",
            activate=True,
            llm_model="gpt-4o",
            embedding_model="text-embedding-3-small",
            api_base="https://api.openai.com/v1",
            embedding_api_key=None,
        )


# ---------------------------------------------------------------------------
# Default (formerly skip) flow
# ---------------------------------------------------------------------------


def test_default_profile_bypasses_all_prompts(isolated_dbgpt_home):
    """default spec → _ask_api_key and _ask_model_names never called."""
    from dbgpt.cli._wizard import run_setup_wizard

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key") as mock_api_key,
        patch("dbgpt.cli._wizard._ask_model_names") as mock_model,
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "default.toml",
        ),
        patch("dbgpt.cli._wizard._print_welcome"),
    ):
        mock_ask_profile.return_value = get_profile("default")

        run_setup_wizard()

        mock_api_key.assert_not_called()
        mock_model.assert_not_called()


# ---------------------------------------------------------------------------
# run_setup_noninteractive — unchanged
# ---------------------------------------------------------------------------


def test_run_setup_noninteractive_unchanged(isolated_dbgpt_home):
    """run_setup_noninteractive does NOT call _ask_model_names."""
    from dbgpt.cli._wizard import run_setup_noninteractive

    with (
        patch("dbgpt.cli._wizard._ask_model_names") as mock_model,
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "openai.toml",
        ),
    ):
        run_setup_noninteractive("openai", "sk-xxx")

        mock_model.assert_not_called()


# ---------------------------------------------------------------------------
# Custom profile — api_base
# ---------------------------------------------------------------------------


def test_custom_profile_asks_api_base(isolated_dbgpt_home):
    """custom spec → _ask_api_base is called and result passed to write_profile_config."""  # noqa: E501
    from dbgpt.cli._wizard import run_setup_wizard

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key", return_value="sk-custom"),
        patch(
            "dbgpt.cli._wizard._ask_api_base", return_value="https://my.proxy.com/v1"
        ) as mock_api_base,
        patch(
            "dbgpt.cli._wizard._ask_model_names",
            return_value=("gpt-4o", "text-embedding-3-small"),
        ),
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "custom.toml",
        ) as mock_write,
        patch("dbgpt.cli._wizard._print_welcome"),
    ):
        spec = get_profile("custom")
        mock_ask_profile.return_value = spec

        run_setup_wizard()

        mock_api_base.assert_called_once_with(spec)
        mock_write.assert_called_once_with(
            "custom",
            api_key="sk-custom",
            activate=True,
            llm_model="gpt-4o",
            embedding_model="text-embedding-3-small",
            api_base="https://my.proxy.com/v1",
            embedding_api_key=None,
        )


def test_openai_profile_asks_api_base(isolated_dbgpt_home):
    """openai spec → _ask_api_base IS called (users often use proxies)."""
    from dbgpt.cli._wizard import run_setup_wizard

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key", return_value="sk-openai"),
        patch(
            "dbgpt.cli._wizard._ask_api_base",
            return_value="https://api.openai.com/v1",
        ) as mock_api_base,
        patch(
            "dbgpt.cli._wizard._ask_model_names",
            return_value=("gpt-4o", "text-embedding-3-small"),
        ),
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "openai.toml",
        ) as mock_write,
        patch("dbgpt.cli._wizard._print_welcome"),
    ):
        spec = get_profile("openai")
        mock_ask_profile.return_value = spec

        run_setup_wizard()

        mock_api_base.assert_called_once_with(spec)
        mock_write.assert_called_once_with(
            "openai",
            api_key="sk-openai",
            activate=True,
            llm_model="gpt-4o",
            embedding_model="text-embedding-3-small",
            api_base="https://api.openai.com/v1",
            embedding_api_key=None,
        )


def test_kimi_profile_does_not_ask_api_base(isolated_dbgpt_home):
    """kimi spec → _ask_api_base is NOT called."""
    from dbgpt.cli._wizard import run_setup_wizard

    with (
        patch("dbgpt.cli._wizard._ask_profile") as mock_ask_profile,
        patch("dbgpt.cli._wizard._ask_api_key", return_value="sk-test"),
        patch("dbgpt.cli._wizard._ask_api_base") as mock_api_base,
        patch(
            "dbgpt.cli._wizard._ask_model_names",
            return_value=("kimi-k2", "text-embedding-v3"),
        ),
        patch("dbgpt.cli._wizard._ask_embedding_api_key", return_value="ds-key"),
        patch(
            "dbgpt.cli._wizard.write_profile_config",
            return_value=isolated_dbgpt_home / "configs" / "kimi.toml",
        ),
        patch("dbgpt.cli._wizard._print_welcome"),
    ):
        mock_ask_profile.return_value = get_profile("kimi")

        run_setup_wizard()

        mock_api_base.assert_not_called()
