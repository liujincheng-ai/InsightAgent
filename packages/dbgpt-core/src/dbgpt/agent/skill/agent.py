"""Skills-enabled agent for InsightAgent.

This module provides an agent implementation with SkillsMiddleware integration,
enabling progressive disclosure of skills from multiple sources.
"""

import dataclasses
from typing import Any, Dict, List, Optional

from dbgpt.agent.core.agent import AgentContext
from dbgpt.agent.core.base_agent import ConversableAgent
from dbgpt.agent.skill.middleware import (
    LoadedSkill,
    SkillsMiddleware,
)


@dataclasses.dataclass
class SkillsAgentConfig:
    """Configuration for SkillsAgent."""

    skill_sources: List[str]
    """List of skill source directories."""

    auto_load: bool = True
    """Automatically load skills on initialization."""

    auto_match: bool = True
    """Automatically match skills based on user input."""

    lazy_content_load: bool = True
    """Load skill content on demand (progressive disclosure)."""

    inject_to_system_prompt: bool = True
    """Inject skills metadata into system prompt."""


class SkillsAgent(ConversableAgent):
    """Agent with progressive disclosure skills support.

    This agent integrates SkillsMiddleware to provide:
    - Automatic skill loading from multiple sources
    - Progressive disclosure (metadata first, content on demand)
    - Automatic skill matching based on user input
    - Skill injection into system prompt

    Example:
        ```python
        from dbgpt.agent.core.profile.base import ProfileConfig
        from dbgpt.agent.skill.agent import SkillsAgent, SkillsAgentConfig

        profile = ProfileConfig(name="assistant", role="AI Assistant")
        config = SkillsAgentConfig(
            skill_sources=["/path/to/skills/user", "/path/to/skills/project"]
        )

        agent = SkillsAgent(profile=profile, skills_config=config)
        ```
    """

    def __init__(
        self,
        skills_config: SkillsAgentConfig,
        **kwargs,
    ):
        """Initialize a SkillsAgent.

        Args:
            skills_config: Configuration for skills middleware.
            **kwargs: Additional arguments for ConversableAgent.
        """
        super().__init__(**kwargs)

        self._skills_config = skills_config
        self._skills_middleware = SkillsMiddleware(sources=skills_config.skill_sources)
        self._active_skills: List[LoadedSkill] = []
        self._base_prompt = None

        if skills_config.auto_load:
            self._skills_middleware.load_skills()

    @property
    def skills_middleware(self) -> SkillsMiddleware:
        """Return the skills middleware."""
        return self._skills_middleware

    @property
    def active_skills(self) -> List[LoadedSkill]:
        """Return currently active skills."""
        return self._active_skills

    @property
    def skills_config(self) -> SkillsAgentConfig:
        """Return skills configuration."""
        return self._skills_config

    def load_skills(self) -> Dict[str, LoadedSkill]:
        """Load skills from all configured sources.

        Returns:
            Dictionary of loaded skills keyed by name.
        """
        return self._skills_middleware.load_skills()

    def get_skill(self, name: str) -> Optional[LoadedSkill]:
        """Get a skill by name.

        Args:
            name: Skill name.

        Returns:
            LoadedSkill or None.
        """
        return self._skills_middleware.get_skill(name)

    def list_skills(self) -> List[str]:
        """List all available skill names.

        Returns:
            List of skill names.
        """
        skills = self._skills_middleware.list_skills()
        return [skill.name for skill in skills]

    def match_skills(self, user_input: str) -> List[LoadedSkill]:
        """Find skills that match user input.

        Args:
            user_input: User input string.

        Returns:
            List of matching skills.
        """
        return self._skills_middleware.match_skills(user_input)

    def set_skill(self, skill_name: str):
        """Manually activate a specific skill.

        Args:
            skill_name: Name of skill to activate.

        Raises:
            ValueError: If skill not found.
        """
        skill = self._skills_middleware.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")

        if skill not in self._active_skills:
            self._active_skills.append(skill)
            self._update_prompt_with_skills()

    def clear_active_skills(self):
        """Clear all active skills and revert to base prompt."""
        self._active_skills = []
        if self._base_prompt:
            self.bind_prompt = self._base_prompt

    def _update_prompt_with_skills(self):
        """Update agent prompt with active skills."""
        if self._skills_config.inject_to_system_prompt:
            skills_section = self._skills_middleware.create_skills_prompt_section()

            if self.bind_prompt is None:
                self._base_prompt = self.bind_prompt

            if self.bind_prompt:
                combined = f"{skills_section}\n\n{self.bind_prompt.template}"
            else:
                combined = skills_section

            from dbgpt.core import PromptTemplate

            self.bind_prompt = PromptTemplate.from_template(combined)

    async def build_system_prompt(
        self,
        question: Optional[str] = None,
        most_recent_memories: Optional[str] = None,
        resource_vars: Optional[Dict] = None,
        context: Optional[Dict[str, Any]] = None,
        is_retry_chat: bool = False,
    ):
        """Build system prompt with skills integration.

        Args:
            question: Current question.
            most_recent_memories: Most recent memories.
            resource_vars: Resource variables.
            context: Additional context.
            is_retry_chat: Whether this is a retry chat.

        Returns:
            System prompt string.
        """
        if self._skills_config.inject_to_system_prompt:
            self._update_prompt_with_skills()

        return await super().build_system_prompt(
            question=question,
            most_recent_memories=most_recent_memories,
            resource_vars=resource_vars,
            context=context,
            is_retry_chat=is_retry_chat,
        )

    async def _a_init_reply_message(
        self,
        received_message,
        rely_messages: Optional[List] = None,
    ):
        """Initialize reply message with skill detection.

        Args:
            received_message: The received message.
            rely_messages: List of relied messages.

        Returns:
            AgentMessage or None.
        """
        if self._skills_config.auto_match and received_message.content:
            matched_skills = self.match_skills(received_message.content)

            if matched_skills:
                self._active_skills = matched_skills
                self._update_prompt_with_skills()

        return await super()._a_init_reply_message(
            received_message=received_message,
            rely_messages=rely_messages,
        )

    def get_skills_summary(self) -> str:
        """Get a summary of available and active skills.

        Returns:
            Formatted summary string.
        """
        all_skills = self._skills_middleware.list_skills()
        active_names = [s.metadata.name for s in self._active_skills]

        summary = f"Total Skills: {len(all_skills)}\n"
        summary += f"Active Skills: {len(active_names)}\n\n"

        if active_names:
            summary += "**Active Skills:**\n"
            for name in active_names:
                summary += f"  - {name}\n"
            summary += "\n"

        summary += "**Available Skills:**\n"
        for skill_metadata in all_skills:
            is_active = skill_metadata.name in active_names
            status = "[ACTIVE]" if is_active else ""
            summary += (
                f"  {status} {skill_metadata.name}: {skill_metadata.description}\n"
            )

        return summary


async def create_skills_agent(
    skill_sources: List[str],
    context: AgentContext,
    **kwargs,
) -> SkillsAgent:
    """Create a SkillsAgent with skills from specified sources.

    Args:
        skill_sources: List of skill source directories.
        context: Agent context.
        **kwargs: Additional arguments for SkillsAgent.

    Returns:
        Configured SkillsAgent instance.
    """
    skills_config = SkillsAgentConfig(
        skill_sources=skill_sources,
        auto_load=True,
        auto_match=True,
        lazy_content_load=True,
        inject_to_system_prompt=True,
    )

    agent = SkillsAgent(
        skills_config=skills_config,
        agent_context=context,
        **kwargs,
    )

    await agent.bind(context).build()

    return agent
