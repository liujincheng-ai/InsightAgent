#!/usr/bin/env bash
# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  InsightAgent Quick Installer                                                  ║
# ║                                                                          ║
# ║  One-line usage:                                                         ║
# ║    curl -fsSL https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/\    ║
# ║      main/scripts/install/install.sh | bash                             ║
# ║                                                                          ║
# ║  What this script does:                                                  ║
# ║    1. Detect OS (macOS / Linux)                                          ║
# ║    2. Ensure git and curl are available                                  ║
# ║    3. Install uv (if not already present)                                ║
# ║    4. Clone (or update) the InsightAgent repository                           ║
# ║    5. Run `uv sync` with the extras for the chosen profile              ║
# ║    6. Generate config via dbgpt setup wizard                             ║
# ║    7. Print next-steps (start command, URL)                              ║
# ║                                                                          ║
# ║  What this script does NOT do:                                           ║
# ║    - Install GPU drivers or CUDA                                         ║
# ║    - Download large local models                                         ║
# ║    - Modify shell rc files (except via uv installer)                     ║
# ║    - Collect telemetry                                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Resolve script location (works for both local and curl|bash) ─────────────
# When piped from curl, BASH_SOURCE is empty.  In that case we download the
# helper libs from GitHub on the fly.
SCRIPT_DIR=""
REMOTE_BASE="https://raw.githubusercontent.com/liujincheng-ai/InsightAgent/main/scripts/install"

_resolve_script_dir() {
  if [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "bash" ]]; then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  fi
}
_resolve_script_dir

# ── Source helper libs ────────────────────────────────────────────────────────
_source_lib() {
  local name="$1"
  if [[ -n "${SCRIPT_DIR}" && -f "${SCRIPT_DIR}/lib/${name}" ]]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/lib/${name}"
  else
    # Running via curl | bash — fetch from GitHub
    local tmp
    tmp="$(mktemp)"
    curl -fsSL "${REMOTE_BASE}/lib/${name}" -o "${tmp}"
    # shellcheck source=/dev/null
    source "${tmp}"
    rm -f "${tmp}"
  fi
}

_source_lib "common.sh"
_source_lib "profiles.sh"

# ── Default values ────────────────────────────────────────────────────────────
PROFILE=""
INSTALL_DIR="${DBGPT_INSTALL_DIR:-${HOME}/.dbgpt}"
VERSION="${DBGPT_VERSION:-main}"
REPO_DIR="${DBGPT_REPO_DIR:-}"
USE_EXISTING_REPO="false"
MIRROR=""
YES="false"
START_AFTER_INSTALL="false"
USER_CONFIG=""

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
  cat <<'EOF'
InsightAgent Quick Installer

Usage:
  install.sh [options]

Options:
  --profile <name>       Deployment profile (openai, kimi, qwen, minimax, glm, custom, default)
  --config <path>        Use existing TOML config (skip config generation)
  --install-dir <path>   Where to install (default: ~/.dbgpt)
  --version <git-ref>    Git tag or branch to check out (default: main)
  --repo-dir <path>      Use an existing local InsightAgent checkout
  --mirror china         Use China PyPI mirror (Tsinghua)
  --yes                  Non-interactive — accept all defaults
  --start                Start InsightAgent server after install
  -h, --help             Show this help

Environment variables:
  OPENAI_API_KEY         Automatically injected into OpenAI / custom / default / kimi(embedding) config
  MOONSHOT_API_KEY       Automatically injected into Kimi config
  DASHSCOPE_API_KEY      Automatically injected into Qwen config
  MINIMAX_API_KEY        Automatically injected into MiniMax config
  ZHIPUAI_API_KEY        Automatically injected into GLM config
  DBGPT_INSTALL_DIR      Override default install directory
  DBGPT_REPO_DIR         Reuse an existing local InsightAgent repo
  DBGPT_VERSION          Override default git ref

Examples:
  # Interactive (will ask which profile)
  bash install.sh

  # Fully non-interactive
  bash install.sh --profile openai --yes

  # With OpenAI API key
  OPENAI_API_KEY=sk-xxx bash install.sh --profile openai --yes

  # With Kimi / Moonshot API key
  MOONSHOT_API_KEY=sk-xxx bash install.sh --profile kimi --yes

  # With Qwen / DashScope API key
  DASHSCOPE_API_KEY=sk-xxx bash install.sh --profile qwen --yes

  # With MiniMax API key
  MINIMAX_API_KEY=sk-xxx bash install.sh --profile minimax --yes

  # With GLM / ZhipuAI API key
  ZHIPUAI_API_KEY=sk-xxx bash install.sh --profile glm --yes

  # Reuse your current local repo (skip clone/update)
  OPENAI_API_KEY=sk-xxx bash install.sh --profile openai --repo-dir . --yes

  # Power-user: provide your own config file (skip config generation)
  bash install.sh --config /path/to/my.toml --profile openai --yes

  # China mirror
  bash install.sh --profile openai --mirror china
EOF
}

# ── Argument parsing ──────────────────────────────────────────────────────────
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        PROFILE="${2:-}"
        [[ -z "${PROFILE}" ]] && die "--profile requires a value"
        shift 2
        ;;
      --install-dir)
        INSTALL_DIR="${2:-}"
        [[ -z "${INSTALL_DIR}" ]] && die "--install-dir requires a value"
        shift 2
        ;;
      --version)
        VERSION="${2:-}"
        [[ -z "${VERSION}" ]] && die "--version requires a value"
        shift 2
        ;;
      --repo-dir)
        REPO_DIR="${2:-}"
        [[ -z "${REPO_DIR}" ]] && die "--repo-dir requires a value"
        shift 2
        ;;
      --mirror)
        MIRROR="${2:-}"
        [[ -z "${MIRROR}" ]] && die "--mirror requires a value"
        shift 2
        ;;
      --yes)
        YES="true"
        shift
        ;;
      --start)
        START_AFTER_INSTALL="true"
        shift
        ;;
      --config)
        USER_CONFIG="${2:-}"
        [[ -z "${USER_CONFIG}" ]] && die "--config requires a value"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1. Run with --help for usage."
        ;;
    esac
  done
}

# ── Steps ─────────────────────────────────────────────────────────────────────

step_check_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "${os}" in
    Darwin|Linux) ;;
    *)
      die "Unsupported OS: ${os}. This installer supports macOS and Linux."
      ;;
  esac

  info "Platform: ${os} ${arch}"
}

step_ensure_base_commands() {
  require_cmd curl
  require_cmd git
}

step_choose_profile() {
  if [[ -n "${PROFILE}" ]]; then
    return
  fi

  if [[ "${YES}" == "true" ]]; then
    PROFILE="openai"
    info "Non-interactive mode: defaulting to profile 'openai'"
    return
  fi

  printf '\n'
  printf '%b' "${COLOR_CYAN}Select a deployment profile:${COLOR_RESET}\n"
  printf '  1) openai     — OpenAI API proxy (recommended)\n'
  printf '  2) kimi       — Kimi 2.5 via Moonshot API\n'
  printf '  3) qwen       — Qwen via DashScope API\n'
  printf '  4) minimax    — MiniMax OpenAI-compatible API\n'
  printf '  5) glm        — GLM-5 via ZhipuAI API\n'
  printf '  6) custom     — Custom OpenAI-compatible provider\n'
  printf '  7) default    — Default (OpenAI-compatible)\n'
  printf '  q) quit\n'
  printf '\n'
  printf '%b' "${COLOR_CYAN}Please select a profile by entering the corresponding number:${COLOR_RESET}\n"
  printf '\n'

  local choice
  prompt_input "Enter choice [1]: " choice
  choice="${choice:-1}"

  case "${choice}" in
    1|openai)   PROFILE="openai" ;;
    2|kimi)     PROFILE="kimi" ;;
    3|qwen)     PROFILE="qwen" ;;
    4|minimax)  PROFILE="minimax" ;;
    5|glm)      PROFILE="glm" ;;
    6|custom)   PROFILE="custom" ;;
    7|default)  PROFILE="default" ;;
    q|Q)        info "Installation cancelled."; exit 0 ;;
    *)          die "Invalid choice: ${choice}" ;;
  esac
}

step_ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    success "uv found: $(uv --version 2>/dev/null || echo 'unknown')"
    return
  fi

  info "uv not found. Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # uv installer puts the binary in ~/.local/bin or ~/.cargo/bin.
  # Try to pick it up without requiring the user to reload their shell.
  for candidate in \
    "${HOME}/.local/bin" \
    "${HOME}/.cargo/bin"
  do
    if [[ -x "${candidate}/uv" ]]; then
      export PATH="${candidate}:${PATH}"
      break
    fi
  done

  if ! command -v uv >/dev/null 2>&1; then
    die "uv was installed but cannot be found on PATH. Please open a new terminal and re-run."
  fi

  success "uv installed: $(uv --version 2>/dev/null || echo 'unknown')"
}

step_apply_mirror() {
  if [[ "${MIRROR}" == "china" ]]; then
    export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
    info "China mirror enabled: UV_INDEX_URL=${UV_INDEX_URL}"
  fi
}

step_prepare_dirs() {
  mkdir -p "${INSTALL_DIR}"
}

resolve_repo_dir() {
  if [[ -z "${REPO_DIR}" ]]; then
    REPO_DIR="${INSTALL_DIR}/InsightAgent"
    return
  fi

  USE_EXISTING_REPO="true"

  [[ -d "${REPO_DIR}" ]] || die "--repo-dir does not exist: ${REPO_DIR}"

  local resolved_repo_dir
  resolved_repo_dir="$(git -C "${REPO_DIR}" rev-parse --show-toplevel 2>/dev/null)" \
    || die "--repo-dir must point to a InsightAgent git checkout: ${REPO_DIR}"

  REPO_DIR="${resolved_repo_dir}"

  if [[ "${VERSION}" != "main" ]]; then
    warn "--version is ignored when --repo-dir is set. Using existing checkout at ${REPO_DIR}."
  fi
}

step_clone_or_update_repo() {
  local repo_dir="${REPO_DIR}"

  if [[ "${USE_EXISTING_REPO}" == "true" ]]; then
    info "Using existing local repo: ${repo_dir}"
    return
  fi

  if [[ ! -e "${repo_dir}" ]]; then
    run "Cloning InsightAgent repository..." \
      git clone --depth 1 --branch "${VERSION}" \
      https://github.com/liujincheng-ai/InsightAgent.git "${repo_dir}"
    return
  fi

  if [[ ! -d "${repo_dir}/.git" ]]; then
    die "Directory exists but is not a git repo: ${repo_dir}. Remove it and re-run."
  fi

  info "Existing InsightAgent repo found: ${repo_dir}"
  if confirm "Update to version '${VERSION}'?"; then
    run "Fetching latest..." git -C "${repo_dir}" fetch --tags --prune
    run "Checking out ${VERSION}..." git -C "${repo_dir}" checkout "${VERSION}"
  else
    info "Skipping repo update."
  fi
}

step_install_deps() {
  local repo_dir="${REPO_DIR}"
  local extras
  extras="$(profile_extras "${PROFILE}")"

  info "Installing dependencies for profile: ${PROFILE}"

  local extra_args=()
  while IFS= read -r extra; do
    [[ -z "${extra}" ]] && continue
    extra_args+=(--extra "${extra}")
  done <<< "${extras}"

  (
    cd "${repo_dir}"
    run "Running uv sync (this may take a few minutes)..." \
      uv sync --all-packages "${extra_args[@]}"
  )

  success "Dependencies installed."
}

step_check_api_key() {
  local env_name
  env_name="$(profile_api_key_env "${PROFILE}")"

  # Primary API key check
  if [[ -n "${env_name}" ]] && [[ -z "${!env_name:-}" ]]; then
    warn "Environment variable ${env_name} is not set."
    warn "The wizard will generate config with a placeholder."
    warn "Set it before starting: export ${env_name}=sk-xxx"
  fi

  # Kimi special handling: also needs OPENAI_API_KEY for embeddings
  if [[ "${PROFILE}" == "kimi" ]] && [[ -z "${OPENAI_API_KEY:-}" ]]; then
    warn "Kimi profile also needs OPENAI_API_KEY for embeddings."
    warn "Set it before starting: export OPENAI_API_KEY=sk-xxx"
  fi
}

step_generate_config() {
  info "Generating configuration via dbgpt setup..."

  local setup_args=(dbgpt setup --profile "${PROFILE}" --yes)

  # If user explicitly provided an API key via environment, pass it through
  local api_key_env
  api_key_env="$(profile_api_key_env "${PROFILE}")"
  if [[ -n "${api_key_env}" && -n "${!api_key_env:-}" ]]; then
    setup_args+=(--api-key "${!api_key_env}")
  fi

  (
    cd "${REPO_DIR}"
    run "Running dbgpt setup..." uv run "${setup_args[@]}"
  )

  local config_path="${HOME}/.dbgpt/configs/${PROFILE}.toml"
  if [[ -f "${config_path}" ]]; then
    success "Config written to ${config_path}"
  else
    die "Config generation failed — ${config_path} not found"
  fi
}

step_validate() {
  local repo_dir="${REPO_DIR}"

  (
    cd "${repo_dir}"
    if uv run dbgpt --version >/dev/null 2>&1; then
      success "dbgpt CLI verified: $(uv run dbgpt --version 2>/dev/null || echo 'ok')"
    else
      warn "Could not verify dbgpt CLI. This may be fine — try starting the server."
    fi
  )
}

step_print_summary() {
  local repo_dir="${REPO_DIR}"
  local config_path="${HOME}/.dbgpt/configs/${PROFILE}.toml"

  printf '%b' "
${COLOR_GREEN}════════════════════════════════════════════════════════════${COLOR_RESET}
${COLOR_GREEN}  InsightAgent installed successfully!${COLOR_RESET}
${COLOR_GREEN}════════════════════════════════════════════════════════════${COLOR_RESET}

  Profile:    ${PROFILE}
  Repository: ${repo_dir}
  Config:     ${config_path}

  ${COLOR_CYAN}Next steps:${COLOR_RESET}

  1. Review / Edit your config (set Custom API key Or BaseURL if not done):
     ${COLOR_YELLOW}${config_path}${COLOR_RESET}

  2. Start InsightAgent:
     ${COLOR_YELLOW}cd \"${repo_dir}\" && uv run dbgpt start webserver --profile ${PROFILE}${COLOR_RESET}

  3. Open your browser:
     ${COLOR_YELLOW}http://localhost:5670${COLOR_RESET}

"
}

step_start_if_requested() {
  if [[ "${START_AFTER_INSTALL}" != "true" ]]; then
    return
  fi

  local repo_dir="${REPO_DIR}"
  info "Starting InsightAgent server..."
  (
    cd "${repo_dir}"
    if [[ -n "${USER_CONFIG:-}" ]]; then
      exec uv run dbgpt start webserver --config "${USER_CONFIG}"
    else
      exec uv run dbgpt start webserver --profile "${PROFILE}"
    fi
  )
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  printf '%b' "${COLOR_GREEN}"
  cat <<'BANNER'

  ____  ____        ____ ____ _____
 |  _ \| __ )      / ___|  _ \_   _|
 | | | |  _ \ ____| |  _| |_) || |
 | |_| | |_) |____| |_| |  __/ | |
 |____/|____/      \____|_|    |_|

  Quick Installer

BANNER
  printf '%b' "${COLOR_RESET}"

  parse_args "$@"
  step_check_platform
  step_ensure_base_commands

  if [[ -n "${USER_CONFIG:-}" ]]; then
    [[ -f "${USER_CONFIG}" ]] || die "Config file not found: ${USER_CONFIG}"
    info "Using user-provided config: ${USER_CONFIG}"
    if [[ -z "${PROFILE}" ]]; then
      PROFILE="openai"
      info "No --profile specified with --config; defaulting to 'openai' for dependency extras."
    fi
    validate_profile "${PROFILE}"
    step_apply_mirror
    step_prepare_dirs
    resolve_repo_dir
    step_ensure_uv
    step_clone_or_update_repo
    step_install_deps
    step_validate
    step_print_summary
    step_start_if_requested
  else
    step_choose_profile
    validate_profile "${PROFILE}"
    step_apply_mirror
    step_prepare_dirs
    resolve_repo_dir
    step_ensure_uv
    step_clone_or_update_repo
    step_install_deps
    step_check_api_key
    step_generate_config
    step_validate
    step_print_summary
    step_start_if_requested
  fi
}

main "$@"
