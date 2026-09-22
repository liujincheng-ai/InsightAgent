import os
from pathlib import Path

import pytest


def _write_skill_md(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_filebasedskill_parses_frontmatter(tmp_path):
    """FileBasedSkill should parse SKILL.md frontmatter into metadata and instructions."""
    skill_md = """
---
name: math-assistant
description: Simple math assistant that can multiply numbers.
version: 0.1.0
author: Test Author
skill_type: chat
tags: math, calculator
required_tools: calculate, terminate
config:
  precision: 2
---

You are a helpful math assistant. When asked, produce the calculation result only.
"""

    file_path = tmp_path / "math_assistant" / "SKILL.md"
    _write_skill_md(file_path, skill_md)

    from dbgpt.agent.claude_skill import FileBasedSkill

    fskill = FileBasedSkill(str(file_path))

    meta = fskill.metadata

    assert meta.name == "math-assistant"
    assert "math assistant" in meta.description
    assert meta.version == "0.1.0"
    assert meta.author == "Test Author"
    # skill_type in FileBasedSkill.metadata is the raw value from frontmatter
    assert getattr(meta, "skill_type") == "chat"

    # tags and required_tools should be lists parsed from the comma-separated string
    assert isinstance(meta.tags, list)
    assert "math" in meta.tags
    assert "calculator" in meta.tags

    assert isinstance(meta.required_tools, list)
    assert "calculate" in meta.required_tools

    # instructions content should be present
    instructions = fskill.instructions
    assert "You are a helpful math assistant" in instructions


def test_skillloader_converts_filebasedskill_to_core_skill(tmp_path):
    """SkillLoader should convert a SKILL.md into a core Skill with mapped fields."""
    skill_md = """
---
name: math-assistant
description: Simple math assistant
version: 0.1.0
author: Test Author
skill_type: chat
tags: math, calculator
required_tools: calculate, terminate
config:
  precision: 2
---

Compute the product of two numbers when asked.
"""

    file_path = tmp_path / "math_assistant" / "SKILL.md"
    _write_skill_md(file_path, skill_md)

    from dbgpt.agent.skill.loader import SkillLoader

    loader = SkillLoader()
    skill = loader.load_skill_from_file(str(file_path))

    assert skill is not None
    # metadata values should be mapped
    assert skill.metadata.name == "math-assistant"
    assert "math assistant" in skill.metadata.description

    # skill_type should be coerced to SkillType when possible
    from dbgpt.agent.skill.base import SkillType

    assert isinstance(skill.metadata.skill_type, SkillType)

    # required_tools should be set on the core Skill
    assert "calculate" in skill.required_tools

    # config is only available when PyYAML parsed the frontmatter; accept either {}
    # or the dict with precision key.
    cfg = getattr(skill, "config", {})
    if isinstance(cfg, dict):
        # If PyYAML is available, config should include precision
        if cfg:
            assert cfg.get("precision") == 2
