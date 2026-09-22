"""Tests for workspace_provisioning module."""

import os

from dbgpt_app.initialization.workspace_provisioning import _ensure_pilot_workspace


def test_ensure_pilot_workspace_copies_alembic_ini(tmp_path):
    """Test that alembic.ini is copied to dest_root/meta_data/alembic.ini"""
    _ensure_pilot_workspace(str(tmp_path))
    assert os.path.exists(tmp_path / "meta_data" / "alembic.ini")


def test_ensure_pilot_workspace_copies_alembic_env_py(tmp_path):
    """Test that alembic/env.py is copied"""
    _ensure_pilot_workspace(str(tmp_path))
    assert os.path.exists(tmp_path / "meta_data" / "alembic" / "env.py")


def test_ensure_pilot_workspace_copies_alembic_script_mako(tmp_path):
    """Test that alembic/script.py.mako is copied"""
    _ensure_pilot_workspace(str(tmp_path))
    assert os.path.exists(tmp_path / "meta_data" / "alembic" / "script.py.mako")


def test_ensure_pilot_workspace_copies_benchmark_xlsx(tmp_path):
    """Test that benchmark xlsx is copied"""
    _ensure_pilot_workspace(str(tmp_path))
    xlsx_files = list((tmp_path / "benchmark_meta_data").glob("*.xlsx"))
    assert len(xlsx_files) == 1


def test_ensure_pilot_workspace_idempotent_no_overwrite(tmp_path):
    """Test that calling twice does not overwrite existing files"""
    _ensure_pilot_workspace(str(tmp_path))
    ini_path = tmp_path / "meta_data" / "alembic.ini"
    # write custom content to simulate user modification
    ini_path.write_text("custom content")
    _ensure_pilot_workspace(str(tmp_path))  # call again
    assert ini_path.read_text() == "custom content"  # must not be overwritten


def test_ensure_pilot_workspace_creates_missing_directories(tmp_path):
    """Test that missing destination directories are created automatically"""
    dest = tmp_path / "deep" / "nested" / "pilot"
    _ensure_pilot_workspace(str(dest))
    assert os.path.exists(dest / "meta_data" / "alembic.ini")
