#!/usr/bin/env bash
# profiles.sh - Profile definitions for InsightAgent installer
#
# Each profile maps to:
#   1. A set of uv extras (fed to `uv sync --extra ...`)
#   2. The API key environment variable name

# ── Validation ────────────────────────────────────────────────────────────────

# Currently supported profiles.  Extend this list when adding new profiles.
readonly SUPPORTED_PROFILES="openai kimi qwen minimax glm custom default"

validate_profile() {
  local profile="$1"
  case "${profile}" in
    openai|kimi|qwen|minimax|glm|custom|default) ;;
    *)
      die "Unsupported profile: ${profile}. Supported profiles: ${SUPPORTED_PROFILES}"
      ;;
  esac
}

# ── Extras mapping ────────────────────────────────────────────────────────────
# Returns newline-separated extras for the given profile.
# These are taken directly from install_help.py / get_deployment_presets().

profile_extras() {
  local profile="$1"
  case "${profile}" in
    openai)
      cat <<'EOF'
base
proxy_openai
rag
storage_chromadb
dbgpts
EOF
      ;;
    kimi)
      cat <<'EOF'
base
proxy_openai
rag
storage_chromadb
dbgpts
EOF
      ;;
    qwen)
      cat <<'EOF'
base
proxy_openai
proxy_tongyi
rag
storage_chromadb
dbgpts
EOF
      ;;
    minimax)
      cat <<'EOF'
base
proxy_openai
rag
storage_chromadb
dbgpts
EOF
      ;;
    glm)
      cat <<'EOF'
base
proxy_openai
proxy_zhipuai
rag
storage_chromadb
dbgpts
EOF
      ;;
    custom)
      cat <<'EOF'
base
proxy_openai
rag
storage_chromadb
dbgpts
EOF
      ;;
    default)
      cat <<'EOF'
base
proxy_openai
rag
storage_chromadb
dbgpts
EOF
      ;;
    *)
      die "No extras defined for profile: ${profile}"
      ;;
  esac
}

# ── Environment variable name for API key ─────────────────────────────────────

profile_api_key_env() {
  local profile="$1"
  case "${profile}" in
    openai)   echo "OPENAI_API_KEY" ;;
    kimi)     echo "MOONSHOT_API_KEY" ;;
    qwen)     echo "DASHSCOPE_API_KEY" ;;
    minimax)  echo "MINIMAX_API_KEY" ;;
    glm)      echo "ZHIPUAI_API_KEY" ;;
    custom)   echo "OPENAI_API_KEY" ;;
    default)  echo "OPENAI_API_KEY" ;;
    *)        echo "" ;;
  esac
}
