"""Profile definitions and API key resolution for InsightAgent CLI.

Each profile corresponds to a supported LLM provider and contains the
information needed to generate a TOML configuration file and resolve
API credentials from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProfileSpec:
    """Specification for a single LLM provider profile."""

    name: str
    """Internal identifier, e.g. 'openai'."""

    label: str
    """Human-readable display name, e.g. 'OpenAI (GPT-4o)'."""

    env_var: str
    """Primary environment variable that holds the API key."""

    llm_model: str
    """Default LLM model name."""

    llm_provider: str
    """InsightAgent provider string, e.g. 'proxy/openai'."""

    llm_api_base: str
    """Base URL for the LLM API."""

    embedding_model: str
    """Default embedding model name."""

    embedding_provider: str
    """InsightAgent provider string for embeddings."""

    embedding_api_url: str
    """URL for the embedding API endpoint."""

    needs_api_key: bool = True
    """Whether this profile requires an API key."""

    use_env_interpolation: bool = False
    """When True, model fields use ``${env:VAR:-default}`` syntax in generated TOML.

    Set to True only for the *default* profile so that ``default.toml`` mirrors
    ``configs/dbgpt-proxy-openai.toml`` exactly — allowing runtime override via
    environment variables without re-running the setup wizard.
    """

    extra_toml_lines: List[str] = field(default_factory=list)
    """Extra TOML lines appended verbatim to the generated config."""

    embedding_env_var: Optional[str] = None
    """Environment variable for the embedding API key.

    When *None* (the default), the same ``env_var`` used for the LLM key is
    reused for embeddings.  Set this to a different name when the embedding
    endpoint requires a separate API key (e.g. Kimi uses MOONSHOT_API_KEY for
    LLM but DASHSCOPE_API_KEY for embeddings via DashScope/Tongyi).
    """

    def env_key(self) -> Optional[str]:
        """Return the API key from the environment, or None."""
        return os.environ.get(self.env_var)

    def embedding_env_key(self) -> Optional[str]:
        """Return the embedding API key from the environment, or None.

        Falls back to the primary ``env_var`` when ``embedding_env_var`` is
        not set.
        """
        var = self.embedding_env_var or self.env_var
        return os.environ.get(var) if var else None


# ---------------------------------------------------------------------------
# Supported profiles
# ---------------------------------------------------------------------------

PROFILES: Dict[str, ProfileSpec] = {
    "openai": ProfileSpec(
        name="openai",
        label="OpenAI (OpenAI or OpenAI API proxy)",
        env_var="OPENAI_API_KEY",
        llm_model="gpt-4o",
        llm_provider="proxy/openai",
        llm_api_base="https://api.openai.com/v1",
        embedding_model="text-embedding-3-small",
        embedding_provider="proxy/openai",
        embedding_api_url="https://api.openai.com/v1/embeddings",
    ),
    "kimi": ProfileSpec(
        name="kimi",
        label="Kimi (Moonshot AI / kimi-k2)",
        env_var="MOONSHOT_API_KEY",
        llm_model="kimi-k2",
        llm_provider="proxy/moonshot",
        llm_api_base="https://api.moonshot.cn/v1",
        embedding_model="text-embedding-3-small",
        embedding_provider="proxy/openai",
        embedding_api_url="https://api.openai.com/v1/embeddings",
        embedding_env_var="OPENAI_API_KEY",
    ),
    "qwen": ProfileSpec(
        name="qwen",
        label="Qwen (DashScope API)",
        env_var="DASHSCOPE_API_KEY",
        llm_model="qwen-plus",
        llm_provider="proxy/tongyi",
        llm_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        embedding_model="text-embedding-v3",
        embedding_provider="proxy/tongyi",
        embedding_api_url="https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
    ),
    "minimax": ProfileSpec(
        name="minimax",
        label="MiniMax (abab series)",
        env_var="MINIMAX_API_KEY",
        llm_model="abab6.5s-chat",
        llm_provider="proxy/openai",
        llm_api_base="https://api.minimax.chat/v1",
        embedding_model="embo-01",
        embedding_provider="proxy/openai",
        embedding_api_url="https://api.minimax.chat/v1/embeddings",
    ),
    "glm": ProfileSpec(
        name="glm",
        label="z.ai (zhipu.ai API)",
        env_var="ZHIPUAI_API_KEY",
        llm_model="glm-4-plus",
        llm_provider="proxy/zhipu",
        llm_api_base="https://open.bigmodel.cn/api/paas/v4",
        embedding_model="embedding-3",
        embedding_provider="proxy/zhipu",
        embedding_api_url="https://open.bigmodel.cn/api/paas/v4/embeddings",
    ),
    "custom": ProfileSpec(
        name="custom",
        label="Custom Provider (Any OpenAI compatible endpoint)",
        env_var="OPENAI_API_KEY",
        llm_model="gpt-4o",
        llm_provider="proxy/openai",
        llm_api_base="https://api.openai.com/v1",
        embedding_model="text-embedding-3-small",
        embedding_provider="proxy/openai",
        embedding_api_url="https://api.openai.com/v1/embeddings",
    ),
    "default": ProfileSpec(
        name="default",
        label="Skip for now (use OpenAI defaults)",
        env_var="OPENAI_API_KEY",
        llm_model="gpt-4o",
        llm_provider="proxy/openai",
        llm_api_base="https://api.openai.com/v1",
        embedding_model="text-embedding-3-small",
        embedding_provider="proxy/openai",
        embedding_api_url="https://api.openai.com/v1/embeddings",
        needs_api_key=False,
        use_env_interpolation=True,
    ),
}

# Ordered list for display in the wizard
PROFILE_ORDER: List[str] = [
    "openai",
    "kimi",
    "qwen",
    "minimax",
    "glm",
    "custom",
    "default",
]


def get_profile(name: str) -> ProfileSpec:
    """Return a ProfileSpec by name.

    Args:
        name (str): Profile identifier (case-insensitive).

    Returns:
        ProfileSpec: The matching profile spec.

    Raises:
        ValueError: If the profile name is not recognised.
    """
    key = name.lower()
    if key not in PROFILES:
        valid = ", ".join(PROFILE_ORDER)
        raise ValueError(f"Unknown profile '{name}'. Valid profiles: {valid}")
    return PROFILES[key]


def list_profiles() -> List[ProfileSpec]:
    """Return profiles in canonical display order."""
    return [PROFILES[k] for k in PROFILE_ORDER]
