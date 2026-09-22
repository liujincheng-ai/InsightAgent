"""Skill base classes."""

import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from dbgpt.core import PromptTemplate


class SkillType(str, Enum):
    """Skill type enumeration."""

    Coding = "coding"
    DataAnalysis = "data_analysis"
    WebSearch = "web_search"
    KnowledgeQA = "knowledge_qa"
    Chat = "chat"
    Custom = "custom"


@dataclasses.dataclass
class SkillMetadata:
    """Metadata for a skill."""

    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    skill_type: SkillType = SkillType.Custom
    tags: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "skill_type": self.skill_type.value
            if isinstance(self.skill_type, SkillType)
            else self.skill_type,
            "tags": self.tags,
        }


class SkillBase(ABC):
    """Base class for a skill."""

    @classmethod
    @abstractmethod
    def type(cls) -> SkillType:
        """Return the skill type."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return the skill metadata."""
        pass

    @property
    @abstractmethod
    def prompt_template(self) -> Optional[PromptTemplate]:
        """Return the prompt template."""
        pass

    @property
    @abstractmethod
    def required_tools(self) -> List[str]:
        """Return the list of required tool names."""
        pass

    @property
    @abstractmethod
    def required_knowledge(self) -> List[str]:
        """Return the list of required knowledge names."""
        pass

    @property
    @abstractmethod
    def actions(self) -> List[Any]:
        """Return the list of actions."""
        pass


class Skill(SkillBase):
    """Concrete implementation of a skill."""

    def __init__(
        self,
        metadata: SkillMetadata,
        prompt_template: Optional[PromptTemplate] = None,
        required_tools: Optional[List[str]] = None,
        required_knowledge: Optional[List[str]] = None,
        actions: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a skill.

        Args:
            metadata: The skill metadata.
            prompt_template: The prompt template for the skill.
            required_tools: List of required tool names.
            required_knowledge: List of required knowledge names.
            actions: List of actions.
            config: Additional configuration.
        """
        self._metadata = metadata
        self._prompt_template = prompt_template
        self._required_tools = required_tools or []
        self._required_knowledge = required_knowledge or []
        self._actions = actions or []
        self._config = config or {}

    @classmethod
    def type(cls) -> SkillType:
        """Return the skill type."""
        return SkillType.Custom

    @property
    def metadata(self) -> SkillMetadata:
        """Return the skill metadata."""
        return self._metadata

    @property
    def prompt_template(self) -> Optional[PromptTemplate]:
        """Return the prompt template."""
        return self._prompt_template

    @property
    def required_tools(self) -> List[str]:
        """Return the list of required tool names."""
        return self._required_tools

    @property
    def required_knowledge(self) -> List[str]:
        """Return the list of required knowledge names."""
        return self._required_knowledge

    @property
    def actions(self) -> List[Any]:
        """Return the list of actions."""
        return self._actions

    @property
    def config(self) -> Dict[str, Any]:
        """Return the skill configuration."""
        return self._config
