"""Tests for _profiles.py — GLM/Custom/Default profiles and label fixes."""

import pytest

from dbgpt.cli._profiles import ProfileSpec, get_profile, list_profiles


class TestGlmProfile:
    """Tests for the glm profile."""

    def test_glm_profile_spec(self):
        """get_profile('glm') should return a ProfileSpec with correct fields."""
        p = get_profile("glm")
        assert isinstance(p, ProfileSpec)
        assert p.name == "glm"
        assert p.label == "z.ai (zhipu.ai API)"
        assert p.env_var == "ZHIPUAI_API_KEY"
        assert p.llm_model == "glm-4-plus"
        assert p.llm_provider == "proxy/zhipu"
        assert p.llm_api_base == "https://open.bigmodel.cn/api/paas/v4"
        assert p.embedding_model == "embedding-3"
        assert p.embedding_provider == "proxy/zhipu"
        assert p.needs_api_key is True

    def test_glm_case_insensitive(self):
        """get_profile('GLM') should work the same as get_profile('glm')."""
        p_lower = get_profile("glm")
        p_upper = get_profile("GLM")
        assert p_lower.name == p_upper.name
        assert p_lower.label == p_upper.label
        assert p_lower.env_var == p_upper.env_var


class TestCustomProfile:
    """Tests for the custom profile."""

    def test_custom_profile_spec(self):
        """get_profile('custom') should return a ProfileSpec with correct fields."""
        p = get_profile("custom")
        assert isinstance(p, ProfileSpec)
        assert p.name == "custom"
        assert p.label == "Custom Provider (Any OpenAI compatible endpoint)"
        assert p.env_var == "OPENAI_API_KEY"
        assert p.llm_model == "gpt-4o"
        assert p.llm_provider == "proxy/openai"
        assert p.llm_api_base == "https://api.openai.com/v1"
        assert p.needs_api_key is True


class TestDefaultProfile:
    """Tests for the default (formerly skip) profile."""

    def test_default_profile_spec(self):
        """get_profile('default') returns a ProfileSpec with needs_api_key=False."""
        p = get_profile("default")
        assert isinstance(p, ProfileSpec)
        assert p.name == "default"
        assert p.needs_api_key is False

    def test_default_profile_has_real_openai_values(self):
        """default profile should have real OpenAI values for config generation."""
        p = get_profile("default")
        assert p.env_var == "OPENAI_API_KEY"
        assert p.llm_model == "gpt-4o"
        assert p.llm_provider == "proxy/openai"
        assert p.llm_api_base == "https://api.openai.com/v1"
        assert p.embedding_model == "text-embedding-3-small"
        assert p.embedding_provider == "proxy/openai"

    def test_default_profile_label(self):
        """default profile label should mention 'Skip for now'."""
        p = get_profile("default")
        assert "Skip for now" in p.label

    def test_skip_profile_no_longer_exists(self):
        """'skip' is no longer a valid profile name."""
        with pytest.raises(ValueError):
            get_profile("skip")


class TestProfileOrder:
    """Tests for profile ordering."""

    def test_profile_order_ends_with_new_profiles(self):
        """list_profiles() should end with glm, custom, default."""
        profiles = list_profiles()
        names = [p.name for p in profiles]
        assert names[-3:] == ["glm", "custom", "default"]


class TestExistingLabels:
    """Tests for fixed labels on existing profiles."""

    def test_openai_label_fixed(self):
        """openai profile label should be updated."""
        p = get_profile("openai")
        assert p.label == "OpenAI (OpenAI or OpenAI API proxy)"

    def test_qwen_label_fixed(self):
        """qwen profile label should be updated."""
        p = get_profile("qwen")
        assert p.label == "Qwen (DashScope API)"


class TestErrorHandling:
    """Tests for error handling."""

    def test_unknown_profile_raises_value_error(self):
        """get_profile with unknown name should raise ValueError."""
        with pytest.raises(ValueError):
            get_profile("nonexistent")


class TestKimiEmbedding:
    """Tests for Kimi embedding configuration using OpenAI."""

    def test_kimi_embedding_uses_openai_provider(self):
        p = get_profile("kimi")
        assert p.embedding_provider == "proxy/openai"

    def test_kimi_embedding_model_is_text_embedding_3_small(self):
        p = get_profile("kimi")
        assert p.embedding_model == "text-embedding-3-small"

    def test_kimi_embedding_api_url_is_openai(self):
        p = get_profile("kimi")
        assert p.embedding_api_url == "https://api.openai.com/v1/embeddings"

    def test_kimi_has_separate_embedding_env_var(self):
        p = get_profile("kimi")
        assert p.embedding_env_var == "OPENAI_API_KEY"
        assert p.embedding_env_var != p.env_var

    def test_kimi_llm_still_uses_moonshot_env_var(self):
        p = get_profile("kimi")
        assert p.env_var == "MOONSHOT_API_KEY"


class TestMinimaxEmbedding:
    """Tests for MiniMax embedding configuration."""

    def test_minimax_embedding_model_is_embo_01(self):
        p = get_profile("minimax")
        assert p.embedding_model == "embo-01"

    def test_minimax_embedding_provider_is_openai(self):
        p = get_profile("minimax")
        assert p.embedding_provider == "proxy/openai"

    def test_minimax_embedding_api_url_is_minimax(self):
        p = get_profile("minimax")
        assert p.embedding_api_url == "https://api.minimax.chat/v1/embeddings"

    def test_minimax_no_separate_embedding_env_var(self):
        p = get_profile("minimax")
        assert p.embedding_env_var is None


class TestEmbeddingEnvVarDefault:
    """Tests for the embedding_env_var default behaviour."""

    def test_openai_has_no_separate_embedding_env_var(self):
        p = get_profile("openai")
        assert p.embedding_env_var is None

    def test_qwen_has_no_separate_embedding_env_var(self):
        p = get_profile("qwen")
        assert p.embedding_env_var is None

    def test_glm_has_no_separate_embedding_env_var(self):
        p = get_profile("glm")
        assert p.embedding_env_var is None
