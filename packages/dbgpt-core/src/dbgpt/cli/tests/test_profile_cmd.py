"""Tests for dbgpt profile subcommands."""

from click.testing import CliRunner

from dbgpt.cli.cli_scripts import cli


class TestProfileList:
    def test_profile_list_with_no_configs_shows_empty_message(
        self, isolated_dbgpt_home
    ):
        """profile list with no configs dir → 'No profiles configured'."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0, result.output
        assert (
            "no profile" in result.output.lower()
            or "no config" in result.output.lower()
        )

    def test_profile_list_shows_all_profiles(self, isolated_dbgpt_home):
        """profile list with 2 TOML files → both shown."""
        # Create fake TOML files
        import dbgpt.cli._config as _cfg

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\n")
        (_cfg._CONFIGS_DIR / "kimi.toml").write_text("[models]\n")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0, result.output
        assert "openai" in result.output
        assert "kimi" in result.output

    def test_profile_list_marks_active_with_asterisk(self, isolated_dbgpt_home):
        """profile list marks active profile with *."""
        import dbgpt.cli._config as _cfg

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\n")
        (_cfg._CONFIGS_DIR / "kimi.toml").write_text("[models]\n")
        _cfg._ACTIVE_CONFIG.write_text('[default]\nprofile = "openai"\n')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0, result.output
        # openai should have * marker
        lines = result.output.splitlines()
        openai_line = next((line for line in lines if "openai" in line), "")
        assert "*" in openai_line, f"Expected * in openai line, got: {openai_line!r}"


class TestProfileShow:
    def test_profile_show_prints_toml_content(self, isolated_dbgpt_home):
        """profile show openai → prints TOML file content."""
        import dbgpt.cli._config as _cfg

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        (_cfg._CONFIGS_DIR / "openai.toml").write_text("[models]\nllms = []\n")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "show", "openai"])
        assert result.exit_code == 0, result.output
        assert "[models]" in result.output

    def test_profile_show_nonexistent_exits_nonzero(self, isolated_dbgpt_home):
        """profile show nonexistent → exit_code != 0."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "show", "nonexistent"])
        assert result.exit_code != 0


class TestProfileSwitch:
    def test_profile_switch_updates_active(self, isolated_dbgpt_home):
        """profile switch kimi → kimi becomes active."""
        import dbgpt.cli._config as _cfg
        from dbgpt.cli._config import read_active_profile

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        (_cfg._CONFIGS_DIR / "kimi.toml").write_text("[models]\n")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "switch", "kimi"])
        assert result.exit_code == 0, result.output
        assert read_active_profile() == "kimi"

    def test_profile_switch_nonexistent_exits_nonzero(self, isolated_dbgpt_home):
        """profile switch nonexistent → exit_code != 0, suggests create."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "switch", "nonexistent"])
        assert result.exit_code != 0
        assert (
            "create" in result.output.lower() or "nonexistent" in result.output.lower()
        )


class TestProfileDelete:
    def test_profile_delete_with_yes_removes_file(self, isolated_dbgpt_home):
        """profile delete openai --yes → openai.toml removed."""
        import dbgpt.cli._config as _cfg

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        toml_path = _cfg._CONFIGS_DIR / "openai.toml"
        toml_path.write_text("[models]\n")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "delete", "openai", "--yes"])
        assert result.exit_code == 0, result.output
        assert not toml_path.exists()

    def test_profile_delete_active_clears_active_pointer(self, isolated_dbgpt_home):
        """profile delete active profile → clears active pointer."""
        import dbgpt.cli._config as _cfg
        from dbgpt.cli._config import read_active_profile

        _cfg._CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        toml_path = _cfg._CONFIGS_DIR / "openai.toml"
        toml_path.write_text("[models]\n")
        _cfg._ACTIVE_CONFIG.write_text('[default]\nprofile = "openai"\n')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "delete", "openai", "--yes"])
        assert result.exit_code == 0, result.output
        assert not toml_path.exists()
        assert read_active_profile() is None

    def test_profile_delete_nonexistent_exits_nonzero(self, isolated_dbgpt_home):
        """profile delete nonexistent --yes → exit_code != 0."""
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["profile", "delete", "nonexistent", "--yes"])
        assert result.exit_code != 0
