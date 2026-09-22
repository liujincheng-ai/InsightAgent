"""Tests for GitHub skill ZIP extraction.

These tests define the TARGET behavior for _extract_skill_from_zip.
Tests in TestExtractSkillFromZip are marked skipif when the function is not yet
implemented (TDD RED phase — they will be skipped until Task 7 implements the function).

Tests for the already-existing _install_skill_from_dir function will pass immediately.
"""

import io
import zipfile

import pytest

from dbgpt_app.openapi.api_v1.agentic_data_api import _install_skill_from_dir

try:
    from dbgpt_app.openapi.api_v1.agentic_data_api import (
        _extract_skill_from_zip,
        _is_macos_junk,
    )
except ImportError:
    _extract_skill_from_zip = None  # type: ignore[assignment]
    _is_macos_junk = None  # type: ignore[assignment]


def _make_zip(files: dict) -> bytes:
    """Create a zip file in memory from a dict of {path: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


_needs_extract = pytest.mark.skipif(
    _extract_skill_from_zip is None,
    reason="_extract_skill_from_zip not yet implemented (TDD RED)",
)


class TestExtractSkillFromZip:
    """Test cases for _extract_skill_from_zip function."""

    @_needs_extract
    def test_extract_valid_skill_zip(self, tmp_path):
        """Extract a zip with repo-main/SKILL.md at root level."""
        zip_bytes = _make_zip({"repo-main/SKILL.md": "name: test-skill\n"})
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        assert (dest / "SKILL.md").exists()
        assert "test-skill" in (dest / "SKILL.md").read_text()

    @_needs_extract
    def test_extract_subpath_skill(self, tmp_path):
        """Extract a zip using a subpath to a specific skill directory."""
        zip_bytes = _make_zip(
            {
                "repo-main/skills/my-skill/SKILL.md": "name: my-skill\n",
                "repo-main/skills/other-skill/SKILL.md": "name: other-skill\n",
            }
        )
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        _extract_skill_from_zip(zip_path, subpath="skills/my-skill", dest_dir=dest)

        assert (dest / "SKILL.md").exists()
        assert "my-skill" in (dest / "SKILL.md").read_text()
        # Other skill should NOT be extracted
        assert not (dest / "other-skill").exists()

    @_needs_extract
    def test_extract_no_skillmd_error(self, tmp_path):
        """Extraction fails if no SKILL.md is found."""
        zip_bytes = _make_zip({"repo-main/readme.txt": "just a readme\n"})
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        with pytest.raises(Exception):
            _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

    @_needs_extract
    def test_extract_multi_skill_lists_subdirs(self, tmp_path):
        """Multiple skills with no subpath: error lists available ones."""
        zip_bytes = _make_zip(
            {
                "repo-main/a/SKILL.md": "name: skill-a\n",
                "repo-main/b/SKILL.md": "name: skill-b\n",
            }
        )
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        with pytest.raises(Exception) as exc_info:
            _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        error_msg = str(exc_info.value)
        assert "a" in error_msg
        assert "b" in error_msg

    @_needs_extract
    def test_extract_path_traversal_blocked(self, tmp_path):
        """Zip entries with path traversal sequences must be blocked."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            # Manually add a dangerous path traversal entry
            zf.writestr("../../etc/passwd", "root:x:0:0:root:/root:/bin/bash\n")
        zip_path = tmp_path / "evil.zip"
        zip_path.write_bytes(buf.getvalue())
        dest = tmp_path / "target"

        with pytest.raises(Exception):
            _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

    @_needs_extract
    def test_extract_overwrite_existing(self, tmp_path):
        """Extracting into an existing directory replaces old SKILL.md."""
        dest = tmp_path / "target"
        dest.mkdir()
        (dest / "SKILL.md").write_text("name: old-skill\n")

        zip_bytes = _make_zip({"repo-main/SKILL.md": "name: new-skill\n"})
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)

        _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        content = (dest / "SKILL.md").read_text()
        assert "new-skill" in content
        assert "old-skill" not in content

    @_needs_extract
    def test_extract_creates_user_dir(self, tmp_path):
        """dest_dir does not need to exist — it should be created."""
        zip_bytes = _make_zip({"repo-main/SKILL.md": "name: test-skill\n"})
        zip_path = tmp_path / "repo.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "nonexistent" / "nested" / "target"

        _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        assert dest.exists()
        assert (dest / "SKILL.md").exists()


class TestInstallSkillFromDir:
    """Test cases for the already-existing _install_skill_from_dir function."""

    def test_install_skill_from_dir_basic(self, tmp_path):
        """Copy src_dir with a SKILL.md into user_dir/skill_name."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("name: test-skill\n")

        user_dir = tmp_path / "user"
        user_dir.mkdir()

        result = _install_skill_from_dir(src_dir, "test-skill", user_dir)

        installed_skill_md = user_dir / "test-skill" / "SKILL.md"
        assert installed_skill_md.exists()
        assert "test-skill" in installed_skill_md.read_text()
        # Return value should be relative path "user/test-skill"
        assert "test-skill" in result

    def test_install_skill_from_dir_overwrite(self, tmp_path):
        """Installing a skill with an existing name should overwrite the old content."""
        src_dir_v1 = tmp_path / "src_v1"
        src_dir_v1.mkdir()
        (src_dir_v1 / "SKILL.md").write_text("name: my-skill\nversion: 1\n")

        user_dir = tmp_path / "user"
        user_dir.mkdir()

        _install_skill_from_dir(src_dir_v1, "my-skill", user_dir)
        old_content = (user_dir / "my-skill" / "SKILL.md").read_text()
        assert "version: 1" in old_content

        src_dir_v2 = tmp_path / "src_v2"
        src_dir_v2.mkdir()
        (src_dir_v2 / "SKILL.md").write_text("name: my-skill\nversion: 2\n")

        _install_skill_from_dir(src_dir_v2, "my-skill", user_dir)
        new_content = (user_dir / "my-skill" / "SKILL.md").read_text()
        assert "version: 2" in new_content
        assert "version: 1" not in new_content


class TestIsMacosJunk:
    """Tests for _is_macos_junk helper."""

    _needs = pytest.mark.skipif(
        _is_macos_junk is None,
        reason="_is_macos_junk not available",
    )

    @_needs
    def test_macosx_dir(self):
        assert _is_macos_junk("__MACOSX/foo/bar") is True

    @_needs
    def test_dot_underscore_file(self):
        assert _is_macos_junk("my-skill/._SKILL.md") is True

    @_needs
    def test_normal_file(self):
        assert _is_macos_junk("my-skill/SKILL.md") is False

    @_needs
    def test_nested_macosx(self):
        assert _is_macos_junk("repo-main/__MACOSX/my-skill/SKILL.md") is True


class TestExtractSkillFromZipEnhancements:
    """Tests for the enhanced _extract_skill_from_zip (strict, __MACOSX filter)."""

    _needs = pytest.mark.skipif(
        _extract_skill_from_zip is None,
        reason="_extract_skill_from_zip not available",
    )

    @_needs
    def test_macosx_filtered_single_top_dir(self, tmp_path):
        """ZIP with __MACOSX alongside skill dir should not create nested dirs."""
        zip_bytes = _make_zip(
            {
                "my-skill/SKILL.md": "name: my-skill\n",
                "my-skill/scripts/run.sh": "echo hello\n",
                "__MACOSX/my-skill/._SKILL.md": "binary junk",
            }
        )
        zip_path = tmp_path / "pkg.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        skill_name = _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        assert skill_name == "my-skill"
        assert (dest / "SKILL.md").exists()
        assert (dest / "scripts" / "run.sh").exists()
        # __MACOSX content must NOT be extracted
        assert not (dest / "__MACOSX").exists()
        assert not (dest / "._SKILL.md").exists()

    @_needs
    def test_strict_false_no_skill_md(self, tmp_path):
        """With strict=False, missing SKILL.md should NOT raise."""
        zip_bytes = _make_zip(
            {
                "my-tool/config.json": '{"key": "value"}\n',
                "my-tool/README.md": "# readme\n",
            }
        )
        zip_path = tmp_path / "pkg.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        skill_name = _extract_skill_from_zip(
            zip_path, subpath=None, dest_dir=dest, strict=False
        )

        assert skill_name == "my-tool"
        assert (dest / "config.json").exists()
        assert (dest / "README.md").exists()

    @_needs
    def test_strict_true_no_skill_md_raises(self, tmp_path):
        """With strict=True (default), missing SKILL.md MUST raise."""
        zip_bytes = _make_zip({"my-tool/config.json": '{"key": "value"}\n'})
        zip_path = tmp_path / "pkg.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        with pytest.raises(ValueError, match="No SKILL.md found"):
            _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

    @_needs
    def test_single_subdir_with_skill_md_auto_selected(self, tmp_path):
        """When exactly one sub-directory has SKILL.md, select it automatically."""
        zip_bytes = _make_zip(
            {
                "repo-main/my-skill/SKILL.md": "name: my-skill\n",
                "repo-main/my-skill/scripts/run.sh": "echo hi\n",
            }
        )
        zip_path = tmp_path / "pkg.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        skill_name = _extract_skill_from_zip(zip_path, subpath=None, dest_dir=dest)

        assert skill_name == "my-skill"
        assert (dest / "SKILL.md").exists()
        assert (dest / "scripts" / "run.sh").exists()

    @_needs
    def test_flat_zip_no_top_dir(self, tmp_path):
        """ZIP with files at root (no wrapping dir), strict=False."""
        zip_bytes = _make_zip(
            {
                "config.json": '{"key": "value"}\n',
                "README.md": "# Hi\n",
            }
        )
        zip_path = tmp_path / "my-pkg.zip"
        zip_path.write_bytes(zip_bytes)
        dest = tmp_path / "target"

        skill_name = _extract_skill_from_zip(
            zip_path, subpath=None, dest_dir=dest, strict=False
        )

        # skill_name falls back to dest_dir.name when no archive_root
        assert skill_name == "target"
        assert (dest / "config.json").exists()
        assert (dest / "README.md").exists()
