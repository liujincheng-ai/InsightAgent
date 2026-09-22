"""Skill parameters classes."""

import dataclasses
from typing import Any, Dict, Optional

from dbgpt.agent.resource.base import ResourceParameters

from .base import SkillType


@dataclasses.dataclass
class SkillParameters(ResourceParameters):
    """Skill resource parameters class."""

    skill_name: str = dataclasses.field(
        default=None, metadata={"help": "Name of the skill to load"}
    )
    skill_type: Optional[SkillType] = dataclasses.field(
        default=None, metadata={"help": "Type of the skill"}
    )
    skill_version: Optional[str] = dataclasses.field(
        default=None, metadata={"help": "Version of the skill"}
    )
    skill_config: Optional[Dict[str, Any]] = dataclasses.field(
        default=None, metadata={"help": "Additional skill configuration"}
    )
    load_tools: bool = dataclasses.field(
        default=True, metadata={"help": "Whether to load required tools"}
    )
    load_knowledge: bool = dataclasses.field(
        default=True, metadata={"help": "Whether to load required knowledge"}
    )
    load_actions: bool = dataclasses.field(
        default=True, metadata={"help": "Whether to load actions"}
    )
