"""Tests for _config.py — TOML generation, path handling, etc."""

from dbgpt.cli._config import _render_profile_toml
from dbgpt.cli._profiles import get_profile


def test_escape_api_key_with_double_quote_generates_valid_toml(isolated_dbgpt_home):
    """API key containing double quote should produce valid parseable TOML."""
    import tomlkit

    spec = get_profile("openai")
    content = _render_profile_toml(spec, api_key='sk-abc"def')
    data = tomlkit.loads(content)  # should NOT raise
    llms = data["models"]["llms"]
    assert llms[0]["api_key"] == 'sk-abc"def'


def test_escape_api_key_with_backslash_generates_valid_toml(isolated_dbgpt_home):
    """API key containing backslash should produce valid parseable TOML."""
    import tomlkit

    spec = get_profile("openai")
    content = _render_profile_toml(spec, api_key="sk-abc\\def")
    data = tomlkit.loads(content)  # should NOT raise
    llms = data["models"]["llms"]
    assert llms[0]["api_key"] == "sk-abc\\def"


def test_escape_env_var_placeholder_not_escaped(isolated_dbgpt_home):
    """Env-var placeholder ${env:VAR:-default} should NOT be double-escaped."""
    spec = get_profile("openai")
    content = _render_profile_toml(spec, api_key=None)
    assert "${env:OPENAI_API_KEY:-sk-xxx}" in content
    assert "\\\\" not in content  # no double backslash introduced


def test_escape_normal_api_key_unchanged(isolated_dbgpt_home):
    """Normal API key (no special chars) should work exactly as before."""
    import tomlkit

    spec = get_profile("openai")
    content = _render_profile_toml(spec, api_key="sk-normal-key-123")
    data = tomlkit.loads(content)
    llms = data["models"]["llms"]
    assert llms[0]["api_key"] == "sk-normal-key-123"


class TestDbgptHomeEnvVar:
    def test_dbgpt_home_returns_custom_path(self, isolated_dbgpt_home):
        from dbgpt.cli._config import dbgpt_home

        result = dbgpt_home()
        assert result == isolated_dbgpt_home

    def test_configs_dir_under_custom_home(self, isolated_dbgpt_home):
        from dbgpt.cli._config import configs_dir

        result = configs_dir()
        assert result == isolated_dbgpt_home / "configs"

    def test_profile_config_path_under_custom_home(self, isolated_dbgpt_home):
        from dbgpt.cli._config import profile_config_path

        result = profile_config_path("openai")
        assert result == isolated_dbgpt_home / "configs" / "openai.toml"

    def test_active_config_path_under_custom_home(self, isolated_dbgpt_home):
        from dbgpt.cli._config import active_config_path

        result = active_config_path()
        assert result == isolated_dbgpt_home / "config.toml"

    def test_default_home_is_dotdbgpt(self, monkeypatch):
        monkeypatch.delenv("DBGPT_HOME", raising=False)
        from pathlib import Path

        import dbgpt.cli._config as _cfg

        expected = Path.home() / ".dbgpt"
        monkeypatch.setattr(_cfg, "_DBGPT_HOME", expected)
        monkeypatch.setattr(_cfg, "_CONFIGS_DIR", expected / "configs")
        monkeypatch.setattr(_cfg, "_ACTIVE_CONFIG", expected / "config.toml")
        from dbgpt.cli._config import dbgpt_home

        assert dbgpt_home() == expected


class TestWorkspacePaths:
    def test_render_toml_data_path_is_relative(self, isolated_dbgpt_home):
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("openai")
        content = _render_profile_toml(spec, api_key="test-key")
        # Database and vector paths should be relative
        assert 'path = "pilot/meta_data/dbgpt.db"' in content
        assert 'persist_path = "pilot/data"' in content

    def test_render_toml_data_path_not_absolute(self, isolated_dbgpt_home):
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("openai")
        content = _render_profile_toml(spec, api_key="test-key")
        # Paths should NOT contain workspace prefix (old absolute pattern)
        assert "workspace/pilot/meta_data" not in content
        assert "workspace/pilot/data" not in content


class TestExtendedSignature:
    def test_render_toml_with_llm_model_override_uses_override(
        self, isolated_dbgpt_home
    ):
        """llm_model override replaces spec default in generated TOML."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config(
            "openai", api_key="test-key", llm_model="gpt-4-turbo"
        )
        data = tomlkit.loads(path.read_text())
        assert data["models"]["llms"][0]["name"] == "gpt-4-turbo"

    def test_render_toml_with_embedding_model_override_uses_override(
        self, isolated_dbgpt_home
    ):
        """embedding_model override replaces spec default in generated TOML."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config(
            "openai", api_key="test-key", embedding_model="ada-002"
        )
        data = tomlkit.loads(path.read_text())
        assert data["models"]["embeddings"][0]["name"] == "ada-002"

    def test_render_toml_without_overrides_uses_spec_defaults(
        self, isolated_dbgpt_home
    ):
        """No overrides → TOML uses spec defaults (regression guard)."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config("openai", api_key="test-key")
        data = tomlkit.loads(path.read_text())
        assert data["models"]["llms"][0]["name"] == "gpt-4o"
        assert data["models"]["embeddings"][0]["name"] == "text-embedding-3-small"

    def test_render_toml_with_api_base_override_uses_override(
        self, isolated_dbgpt_home
    ):
        """api_base override replaces spec default in generated TOML."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config(
            "custom", api_key="test-key", api_base="https://my.api/v1"
        )
        data = tomlkit.loads(path.read_text())
        assert data["models"]["llms"][0]["api_base"] == "https://my.api/v1"

    def test_render_toml_custom_api_base_derives_embedding_url(
        self, isolated_dbgpt_home
    ):
        """When api_base is overridden, embedding api_url is derived from it."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config(
            "custom", api_key="test-key", api_base="https://my-proxy.com/v1"
        )
        data = tomlkit.loads(path.read_text())
        assert (
            data["models"]["embeddings"][0]["api_url"]
            == "https://my-proxy.com/v1/embeddings"
        )

    def test_render_toml_custom_api_base_trailing_slash_stripped(
        self, isolated_dbgpt_home
    ):
        """Trailing slash in api_base should not produce double-slash."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config(
            "custom", api_key="test-key", api_base="https://my-proxy.com/v1/"
        )
        data = tomlkit.loads(path.read_text())
        assert (
            data["models"]["embeddings"][0]["api_url"]
            == "https://my-proxy.com/v1/embeddings"
        )

    def test_render_toml_without_api_base_uses_spec_embedding_url(
        self, isolated_dbgpt_home
    ):
        """Without api_base override, embedding api_url uses spec default."""
        import tomlkit

        from dbgpt.cli._config import write_profile_config

        path = write_profile_config("openai", api_key="test-key")
        data = tomlkit.loads(path.read_text())
        assert (
            data["models"]["embeddings"][0]["api_url"]
            == "https://api.openai.com/v1/embeddings"
        )


class TestKimiEmbeddingEnvVar:
    def test_kimi_embedding_uses_openai_env_var(self, isolated_dbgpt_home):
        """Kimi profile should reference OPENAI_API_KEY for embeddings."""
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("kimi")
        content = _render_profile_toml(spec, api_key=None)
        assert "${env:OPENAI_API_KEY:-sk-xxx}" in content

    def test_kimi_llm_uses_moonshot_env_var(self, isolated_dbgpt_home):
        """Kimi profile LLM section should still reference MOONSHOT_API_KEY."""
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("kimi")
        content = _render_profile_toml(spec, api_key=None)
        assert "${env:MOONSHOT_API_KEY:-sk-xxx}" in content

    def test_kimi_literal_embedding_key_overrides_env_var(self, isolated_dbgpt_home):
        """When embedding_api_key is supplied, use it literally."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("kimi")
        content = _render_profile_toml(spec, api_key=None, embedding_api_key="ds-key")
        data = tomlkit.loads(content)
        assert data["models"]["embeddings"][0]["api_key"] == "ds-key"

    def test_kimi_embedding_api_url_is_openai(self, isolated_dbgpt_home):
        """Kimi embedding api_url should point to OpenAI."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("kimi")
        content = _render_profile_toml(spec, api_key=None)
        data = tomlkit.loads(content)
        assert data["models"]["embeddings"][0]["api_url"] == (
            "https://api.openai.com/v1/embeddings"
        )

    def test_openai_same_key_used_for_embeddings(self, isolated_dbgpt_home):
        """OpenAI profile uses the same literal key for both LLM and embeddings."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("openai")
        content = _render_profile_toml(spec, api_key="sk-test")
        data = tomlkit.loads(content)
        assert data["models"]["llms"][0]["api_key"] == "sk-test"
        assert data["models"]["embeddings"][0]["api_key"] == "sk-test"


class TestDefaultProfileConfig:
    """Tests for config generation with the 'default' (formerly skip) profile."""

    def test_default_profile_generates_env_var_placeholder(self, isolated_dbgpt_home):
        """default profile should use env-var placeholder with default."""
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("default")
        content = _render_profile_toml(spec, api_key=None)
        assert "${env:OPENAI_API_KEY:-sk-xxx}" in content
        # Also verify env-var interpolation for model fields
        assert "${env:LLM_MODEL_NAME:-gpt-4o}" in content
        assert "${env:LLM_MODEL_PROVIDER:-proxy/openai}" in content
        assert "${env:OPENAI_API_BASE:-https://api.openai.com/v1}" in content
        assert "${env:EMBEDDING_MODEL_NAME:-text-embedding-3-small}" in content
        assert "${env:EMBEDDING_MODEL_PROVIDER:-proxy/openai}" in content
        assert (
            "${env:EMBEDDING_MODEL_API_URL:-https://api.openai.com/v1/embeddings}"
            in content
        )

    def test_default_profile_generates_valid_toml(self, isolated_dbgpt_home):
        """default profile should produce parseable TOML with env-var interpolation."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("default")
        content = _render_profile_toml(spec, api_key=None)
        data = tomlkit.loads(content)
        # Model fields use env-var interpolation syntax as raw strings
        assert data["models"]["llms"][0]["name"] == "${env:LLM_MODEL_NAME:-gpt-4o}"
        assert (
            data["models"]["llms"][0]["provider"]
            == "${env:LLM_MODEL_PROVIDER:-proxy/openai}"
        )
        assert (
            data["models"]["embeddings"][0]["name"]
            == "${env:EMBEDDING_MODEL_NAME:-text-embedding-3-small}"
        )

    def test_default_profile_config_file_named_default(self, isolated_dbgpt_home):
        """write_profile_config('default') should create default.toml."""
        from dbgpt.cli._config import profile_config_path, write_profile_config

        path = write_profile_config("default", api_key=None)
        assert path == profile_config_path("default")
        assert path.name == "default.toml"
        assert path.exists()

    def test_default_profile_with_literal_api_key_uses_literal_not_env(
        self, isolated_dbgpt_home
    ):
        """When api_key is provided for default profile, use literal values."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("default")
        content = _render_profile_toml(spec, api_key="sk-literal")
        data = tomlkit.loads(content)
        # With a literal api_key, use_env_interpolation should NOT activate
        assert data["models"]["llms"][0]["name"] == "gpt-4o"
        assert data["models"]["llms"][0]["provider"] == "proxy/openai"
        assert data["models"]["llms"][0]["api_key"] == "sk-literal"
        # No env-var syntax for model name/provider
        assert "${env:LLM_MODEL_NAME" not in content

    def test_openai_profile_no_regression_with_api_key(self, isolated_dbgpt_home):
        """openai profile with literal api_key must still use literal model values."""
        import tomlkit

        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("openai")
        content = _render_profile_toml(spec, api_key="sk-xxx")
        data = tomlkit.loads(content)
        assert data["models"]["llms"][0]["name"] == "gpt-4o"
        assert data["models"]["llms"][0]["provider"] == "proxy/openai"
        assert data["models"]["llms"][0]["api_base"] == "https://api.openai.com/v1"
        assert data["models"]["llms"][0]["api_key"] == "sk-xxx"
        # No env-var interpolation for openai profile
        assert "${env:LLM_MODEL_NAME" not in content

    def test_openai_profile_no_regression_without_api_key(self, isolated_dbgpt_home):
        """openai profile with api_key=None uses env-var for key, literal for model."""
        from dbgpt.cli._config import _render_profile_toml
        from dbgpt.cli._profiles import get_profile

        spec = get_profile("openai")
        content = _render_profile_toml(spec, api_key=None)
        # api_key uses env-var syntax with default
        assert "${env:OPENAI_API_KEY:-sk-xxx}" in content
        # model name/provider/api_base remain literal
        assert 'name = "gpt-4o"' in content
        assert 'provider = "proxy/openai"' in content
        assert 'api_base = "https://api.openai.com/v1"' in content
        # No LLM_MODEL_NAME env-var for openai profile
        assert "${env:LLM_MODEL_NAME" not in content
