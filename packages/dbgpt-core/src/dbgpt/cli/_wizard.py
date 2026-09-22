"""First-run setup wizard for InsightAgent CLI.

Provides :func:`run_setup_wizard` (interactive) and
:func:`run_setup_noninteractive` (``--yes`` / CI mode).

Interactive flow::

    Welcome to InsightAgent! 🎉

    Which LLM provider would you like to use?

      ● OpenAI          OpenAI or OpenAI API proxy
      ○ Kimi            Moonshot AI
      ○ Qwen            DashScope API
      ○ MiniMax         abab series
      ○ Z.AI            zhipu.ai API
      ○ Custom          Any OpenAI compatible endpoint
      ○ Skip for now    Use OpenAI defaults

    Enter your OPENAI_API_KEY: ****
    ✔ Config saved → ~/.dbgpt/configs/openai.toml

For profiles with a separate embedding key (e.g. Kimi uses MOONSHOT_API_KEY
for LLM but DASHSCOPE_API_KEY for embeddings), the wizard will prompt for
both keys.
"""

from __future__ import annotations

import os
from typing import Optional

from dbgpt.cli._config import (
    resolve_config_path,
    write_profile_config,
)
from dbgpt.cli._profiles import ProfileSpec, get_profile, list_profiles
from dbgpt.util.console.console import CliLogger

_log = CliLogger()

# ---------------------------------------------------------------------------
# Provider display metadata (description only)
# ---------------------------------------------------------------------------

_PROVIDER_META = {
    "openai": "OpenAI or OpenAI API proxy",
    "kimi": "Moonshot AI",
    "qwen": "DashScope API",
    "minimax": "MiniMax API",
    "glm": "zhipu.ai API",
    "custom": "Any OpenAI compatible endpoint",
    "default": "Use OpenAI defaults",
}

_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "kimi": "Kimi",
    "qwen": "Qwen",
    "minimax": "MiniMax",
    "glm": "Z.AI",
    "custom": "Custom",
    "default": "Skip for now",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_setup_wizard(
    pre_selected_profile: Optional[str] = None,
    pre_set_key: Optional[str] = None,
) -> str:
    """Run the interactive first-time setup wizard.

    Args:
        pre_selected_profile (Optional[str]): If supplied (e.g. via
            ``--profile``), skip the provider selection step.
        pre_set_key (Optional[str]): If supplied (e.g. via ``--api-key``),
            skip the API-key prompt.

    Returns:
        str: Absolute path to the written config file.
    """
    _print_welcome()

    # ── step 1: choose profile ──────────────────────────────────────────────
    if pre_selected_profile:
        try:
            spec = get_profile(pre_selected_profile)
        except ValueError as exc:
            _log.error(str(exc), exit_code=1)
            return ""
    else:
        spec = _ask_profile()

    # ── step 2: API key ─────────────────────────────────────────────────────
    api_key: Optional[str] = None
    embedding_api_key: Optional[str] = None
    if spec.needs_api_key:
        api_key = _ask_api_key(spec, pre_set_key)
        if spec.embedding_env_var and spec.embedding_env_var != spec.env_var:
            embedding_api_key = _ask_embedding_api_key(spec)

    # ── step 2.5: api_base (openai + custom ask; others use spec default) ───
    api_base: Optional[str] = None
    if spec.name in ("openai", "custom"):
        api_base = _ask_api_base(spec)

    # ── step 3: model names (default profile skips this) ────────────────────
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    if spec.name != "default":
        llm_model, embedding_model = _ask_model_names(spec)

    # ── step 4: write config ─────────────────────────────────────────────────
    config_path = write_profile_config(
        spec.name,
        api_key=api_key,
        activate=True,
        llm_model=llm_model,
        embedding_model=embedding_model,
        api_base=api_base,
        embedding_api_key=embedding_api_key,
    )
    _log.success(f"✔ Config saved → {config_path}")
    return str(config_path)


def run_setup_noninteractive(
    profile_name: str = "openai",
    api_key: Optional[str] = None,
) -> str:
    """Create a config without prompting (``--yes`` / CI mode).

    Uses the literal *api_key* if provided; otherwise falls back to the
    environment variable defined in the profile spec.

    Args:
        profile_name (str): Profile to configure.
        api_key (Optional[str]): Explicit API key; *None* means use env var.

    Returns:
        str: Absolute path to the written config file.
    """
    spec = get_profile(profile_name)

    # If no explicit key, try to read from environment
    resolved_key = api_key or (spec.env_key() if spec.needs_api_key else None)

    config_path = write_profile_config(spec.name, api_key=resolved_key, activate=True)
    _log.success(f"✔ Config saved → {config_path}")
    return str(config_path)


def maybe_run_wizard(
    profile: Optional[str],
    config: Optional[str],
    yes: bool,
    api_key: Optional[str],
) -> str:
    """Decide whether to run the wizard and return a ready config path.

    This is the single call-site used by ``start webserver`` to obtain a
    config path, handling all first-run and re-configuration scenarios.

    Priority:
    1. ``--config`` path supplied → use it directly (skip wizard).
    2. Config already exists (via ``--profile`` or active default) → reuse.
    3. ``--yes`` → non-interactive setup.
    4. Interactive wizard.

    Args:
        profile (Optional[str]): ``--profile`` CLI flag value.
        config (Optional[str]): ``--config`` CLI flag value.
        yes (bool): ``--yes`` / ``-y`` flag.
        api_key (Optional[str]): ``--api-key`` flag value.

    Returns:
        str: Absolute path to a usable config file.
    """
    # 1. Explicit --config
    if config:
        return config

    # 2. Existing profile config
    existing = resolve_config_path(profile=profile, config=None)
    if existing:
        return existing

    # 3. Non-interactive
    if yes:
        return run_setup_noninteractive(
            profile_name=profile or "openai",
            api_key=api_key,
        )

    # 4. Interactive wizard
    return run_setup_wizard(
        pre_selected_profile=profile,
        pre_set_key=api_key,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _print_welcome() -> None:
    _log.print("")
    _log.print("[bold bright_blue]Welcome to InsightAgent! 🎉[/bold bright_blue]")
    _log.print("")
    _log.info(
        "Let's set up your configuration. This only takes a moment.\n"
        "You can re-run [bold]dbgpt setup[/bold] at any time to change settings."
    )
    _log.print("")


def _build_provider_option(spec: ProfileSpec) -> tuple[str, str]:
    """Return (display_name, description) for a provider."""
    display_name = _DISPLAY_NAMES.get(spec.name, spec.name.capitalize())
    desc = _PROVIDER_META.get(spec.name, spec.label)
    return (display_name, desc)


def _ask_profile() -> ProfileSpec:
    """Prompt the user to choose a provider with an arrow-key selector."""
    profiles = list_profiles()

    options = [_build_provider_option(spec) for spec in profiles]

    idx = _log.select("Which LLM provider would you like to use?", options)
    return profiles[idx]


def _ask_api_key(spec: ProfileSpec, pre_set_key: Optional[str]) -> Optional[str]:
    """Ask for an API key, honouring a pre-set value or env var.

    Returns *None* for providers that don't need a key (Ollama).
    Returns an empty string if the user explicitly skips.
    """
    if not spec.needs_api_key:
        return None

    # If an explicit key was passed in (e.g. via --api-key flag), use it.
    if pre_set_key:
        _log.success(f"✔ Using supplied API key for {spec.label}")
        return pre_set_key

    # Check environment
    env_val = spec.env_key()
    if env_val:
        _log.success(f"✔ Found [bold]{spec.env_var}[/bold] in environment — using it.")
        return env_val

    # Prompt the user
    _log.print(
        f"\nEnter your [bold]{spec.env_var}[/bold] "
        f"(or press Enter to use env-var at runtime):"
    )

    import getpass

    try:
        entered = getpass.getpass(prompt="  API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        _log.warning("\nSkipping API key — you can set it via the environment later.")
        return None

    if not entered:
        _log.warning(
            f"No key entered. The config will reference ${spec.env_var} at runtime."
        )
        return None

    return entered


def _ask_model_names(spec: ProfileSpec) -> tuple[str, str]:
    llm = _log.ask("LLM model name", default=spec.llm_model)
    emb = _log.ask("Embedding model name", default=spec.embedding_model)
    return (llm, emb)


def _ask_api_base(spec: ProfileSpec) -> str:
    return _log.ask("API base URL", default=spec.llm_api_base)


def _ask_embedding_api_key(spec: ProfileSpec) -> Optional[str]:
    emb_env_var = spec.embedding_env_var or spec.env_var

    env_val = os.environ.get(emb_env_var) if emb_env_var else None
    if env_val:
        _log.success(
            f"✔ Found [bold]{emb_env_var}[/bold] in environment"
            " — using it for embeddings."
        )
        return env_val

    _log.print(
        f"\nEnter your [bold]{emb_env_var}[/bold] for embeddings "
        f"(or press Enter to use env-var at runtime):"
    )

    import getpass

    try:
        entered = getpass.getpass(prompt="  Embedding API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        _log.warning(
            "\nSkipping embedding API key — you can set it via the environment later."
        )
        return None

    if not entered:
        _log.warning(
            f"No key entered. The config will reference ${emb_env_var} at runtime."
        )
        return None

    return entered
