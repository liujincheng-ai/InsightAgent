"""Tests for GitHub/skills.sh URL parsing.

These tests define the TARGET behavior for _parse_github_url.
Some tests will FAIL against the current partial implementation (TDD RED phase):
  - skills.sh URLs (not yet supported)
  - /blob/ URLs (not yet supported)
  - bare URL returning branch="main" instead of None (current returns None)
"""

import pytest

from dbgpt_app.openapi.api_v1.agentic_data_api import _parse_github_url


class TestParseGithubUrl:
    """Test cases for _parse_github_url function."""

    def test_parse_github_bare_url(self):
        """Bare github.com/owner/repo should return branch="main", subpath=None."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://github.com/owner/repo"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "main"
        assert subpath is None

    def test_parse_github_tree_url(self):
        """github.com/owner/repo/tree/main should return branch="main", subpath=None."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://github.com/owner/repo/tree/main"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "main"
        assert subpath is None

    def test_parse_github_tree_subpath(self):
        """github.com tree URL with subpath should capture branch and subdir."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://github.com/owner/repo/tree/develop/skills/my-skill"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "develop"
        assert subpath == "skills/my-skill"

    def test_parse_github_blob_url(self):
        """github.com /blob/ URL should strip the filename, keeping dir as subpath."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://github.com/owner/repo/blob/main/skills/my-skill/SKILL.md"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "main"
        # SKILL.md filename should be stripped — only directory portion retained
        assert subpath == "skills/my-skill"

    def test_parse_skillssh_url(self):
        """skills.sh/owner/repo/my-skill should be supported."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://skills.sh/owner/repo/my-skill"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "main"
        assert subpath == "my-skill"

    def test_parse_skillssh_bare(self):
        """Bare skills.sh/owner/repo should return branch="main", subpath=None."""
        owner, repo, branch, subpath = _parse_github_url("https://skills.sh/owner/repo")
        assert owner == "owner"
        assert repo == "repo"
        assert branch == "main"
        assert subpath is None

    def test_parse_invalid_url_raises(self):
        """Non-github.com/skills.sh URL should raise ValueError."""
        with pytest.raises(ValueError):
            _parse_github_url("https://gitlab.com/owner/repo")

    def test_parse_invalid_format_raises(self):
        """URL with only owner (no repo) should raise ValueError."""
        with pytest.raises(ValueError):
            _parse_github_url("https://github.com/only-owner")

    def test_parse_github_git_suffix(self):
        """github.com URL with .git suffix should strip it from repo name."""
        owner, repo, branch, subpath = _parse_github_url(
            "https://github.com/owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"
        assert ".git" not in repo
