"""Workspace provisioning module for dbgpt-app pip package users.

Copies pilot template files to the user's workspace directory on first startup.
"""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def _ensure_pilot_workspace(dest_root: str) -> None:
    """Idempotently copy pilot workspace template files to dest_root.

    This function is safe to call multiple times — it will never overwrite
    existing files. On first run, it provisions the full pilot/ directory
    structure including alembic config and benchmark data.

    Args:
        dest_root (str): The destination root directory (parent of meta_data/).
            Example: ~/.dbgpt/workspace/pilot/
    """
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pilot_template",
    )
    for src_dir, dirs, files in os.walk(template_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "versions")]
        for filename in files:
            if filename in (".DS_Store",) or filename.endswith((".pyc",)):
                continue
            src_file = os.path.join(src_dir, filename)
            rel_path = os.path.relpath(src_file, template_dir)
            dest_file = os.path.join(dest_root, rel_path)
            if not os.path.exists(dest_file):
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy2(src_file, dest_file)
                logger.info("Provisioned: %s", dest_file)
            else:
                logger.debug("Skipped (exists): %s", dest_file)
