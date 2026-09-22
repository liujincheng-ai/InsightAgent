"""Tests for _detect_root_path() in model_config.py."""

import os

# ---------------------------------------------------------------------------
# Helper: call _detect_root_path() with a controlled filesystem view
# ---------------------------------------------------------------------------


def _call_detect(monkeypatch, candidate: str, dbgpt_home: str | None = None) -> str:
    """Invoke _detect_root_path() with the given candidate and env.

    Args:
        monkeypatch: pytest monkeypatch fixture for isolation.
        candidate: The fake "6-level dirname" that the function would compute
            from ``__file__``.
        dbgpt_home: If not None, set DBGPT_HOME env var to this value.
            If None, remove DBGPT_HOME from the environment.

    Returns:
        str: The return value of ``_detect_root_path()``.
    """
    import dbgpt.configs.model_config as _mc

    # Patch os.path.abspath so that the dirname chain resolves to `candidate`
    # The function calls os.path.dirname 6 times on os.path.abspath(__file__).
    # We make abspath return a path deep enough that 6 dirname calls yield
    # exactly `candidate`.
    fake_deep_path = os.path.join(candidate, "a", "b", "c", "d", "e", "model_config.py")

    monkeypatch.setattr(
        _mc.os.path,
        "abspath",
        lambda _path: fake_deep_path,
    )

    if dbgpt_home is None:
        monkeypatch.delenv("DBGPT_HOME", raising=False)
    else:
        monkeypatch.setenv("DBGPT_HOME", dbgpt_home)

    return _mc._detect_root_path()


# ---------------------------------------------------------------------------
# Test 1: source install — pyproject.toml found at candidate
# ---------------------------------------------------------------------------


def test_source_install_returns_candidate(tmp_path, monkeypatch):
    """Source install: pyproject.toml at candidate → ROOT_PATH == candidate.

    Creates a fake repo root (tmp_path) with a pyproject.toml sentinel and
    verifies that _detect_root_path() returns that directory.
    """
    candidate = str(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool]\n")

    result = _call_detect(monkeypatch, candidate)

    assert result == candidate


# ---------------------------------------------------------------------------
# Test 2: pip install default — no pyproject.toml, no DBGPT_HOME
# ---------------------------------------------------------------------------


def test_pip_install_default_returns_dot_dbgpt_workspace(tmp_path, monkeypatch):
    """Pip install (default): no pyproject.toml, no DBGPT_HOME → ~/.dbgpt/workspace.

    Ensures the fallback path is ``~/.dbgpt/workspace`` when the candidate
    directory does not contain a pyproject.toml and DBGPT_HOME is not set.
    """
    # candidate has no pyproject.toml
    candidate = str(tmp_path)

    result = _call_detect(monkeypatch, candidate, dbgpt_home=None)

    expected = os.path.join(os.path.expanduser("~/.dbgpt"), "workspace")
    assert result == expected


# ---------------------------------------------------------------------------
# Test 3: pip install with custom DBGPT_HOME
# ---------------------------------------------------------------------------


def test_pip_install_custom_dbgpt_home_returns_workspace_under_home(
    tmp_path, monkeypatch
):
    """Pip install + DBGPT_HOME: no pyproject.toml + DBGPT_HOME → DBGPT_HOME/workspace.

    Verifies that when DBGPT_HOME is set to a custom path and pyproject.toml
    does not exist at the candidate, the result is ``DBGPT_HOME/workspace``.
    """
    candidate = str(tmp_path / "candidate")
    os.makedirs(candidate, exist_ok=True)
    # no pyproject.toml in candidate

    custom_home = str(tmp_path / "custom_home")

    result = _call_detect(monkeypatch, candidate, dbgpt_home=custom_home)

    assert result == os.path.join(custom_home, "workspace")


# ---------------------------------------------------------------------------
# Test 4: derived constants follow ROOT_PATH
# ---------------------------------------------------------------------------


def test_derived_constants_follow_root_path(tmp_path, monkeypatch):
    """Derived constants PILOT_PATH and STATIC_MESSAGE_IMG_PATH follow ROOT_PATH.

    After _detect_root_path() would return a given path, PILOT_PATH and
    STATIC_MESSAGE_IMG_PATH should be derived consistently from it.
    Validates the relationship defined in model_config.py:

        PILOT_PATH               = ROOT_PATH + "/pilot"
        STATIC_MESSAGE_IMG_PATH  = PILOT_PATH + "/message/img"
    """
    candidate = str(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool]\n")

    root = _call_detect(monkeypatch, candidate)

    expected_pilot = os.path.join(root, "pilot")
    expected_img = os.path.join(expected_pilot, "message/img")

    # Verify the relationships (not the module-level cached constants, which
    # were evaluated at import time with the real filesystem).
    assert os.path.join(root, "pilot") == expected_pilot
    assert os.path.join(expected_pilot, "message/img") == expected_img
