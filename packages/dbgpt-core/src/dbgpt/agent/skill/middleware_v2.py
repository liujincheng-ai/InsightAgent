"""Skills middleware using the new middleware system.

This module implements SkillsMiddleware as an AgentMiddleware, following
deepagents' pattern with lifecycle hooks.
"""

import logging
from typing import Any, Dict, List, Optional

from ..middleware.base import AgentMiddleware
from .middleware import LoadedSkill
from .middleware import SkillsMiddleware as BaseSkillsMiddleware

logger = logging.getLogger(__name__)


class SkillsMiddlewareV2(AgentMiddleware):
    """Skills middleware using AgentMiddleware pattern.

    Integrates with the middleware system to inject skills into the agent
    lifecycle, similar to deepagents' SkillsMiddleware.

    Example:
        ```python
        from dbgpt.agent.middleware.base import MiddlewareManager
        from dbgpt.agent.skill.middleware_v2 import SkillsMiddlewareV2

        middleware = SkillsMiddlewareV2(
            sources=["/path/to/skills/user", "/path/to/skills/project"]
        )
        manager = MiddlewareManager()
        manager.register(middleware)
        ```
    """

    def __init__(
        self,
        sources: List[str],
        auto_load: bool = True,
        auto_match: bool = True,
        inject_to_system_prompt: bool = True,
    ):
        """Initialize the skills middleware.

        Args:
            sources: List of skill source paths.
            auto_load: Automatically load skills on initialization.
            auto_match: Automatically match skills based on user input.
            inject_to_system_prompt: Inject skills into system prompt.
        """
        super().__init__()
        self.sources = sources
        self.auto_load = auto_load
        self.auto_match = auto_match
        self.inject_to_system_prompt = inject_to_system_prompt

        self._base_middleware = BaseSkillsMiddleware(sources=sources)
        self._loaded = False

        if auto_load:
            self.load_skills()

    def load_skills(self) -> Dict[str, LoadedSkill]:
        """Load skills from all configured sources.

        Returns:
            Dictionary of loaded skills keyed by name.
        """
        self._loaded = True
        return self._base_middleware.load_skills()

    def get_skill(self, name: str) -> Optional[LoadedSkill]:
        """Get a skill by name.

        Args:
            name: Skill name.

        Returns:
            LoadedSkill or None.
        """
        if not self._loaded:
            self.load_skills()
        return self._base_middleware.get_skill(name)

    def list_skills(self) -> List:
        """List all loaded skills.

        Returns:
            List of skill metadata.
        """
        if not self._loaded:
            self.load_skills()
        return self._base_middleware.list_skills()

    def match_skills(self, user_input: str) -> List[LoadedSkill]:
        """Find skills that match user input.

        Args:
            user_input: User input string.

        Returns:
            List of matching skills.
        """
        if not self._loaded:
            self.load_skills()
        return self._base_middleware.match_skills(user_input)

    async def after_init(self, agent, **kwargs) -> Optional[Dict[str, Any]]:
        """Called after agent initialization.

        Loads skills and stores them in middleware state.

        Args:
            agent: The agent instance.
            **kwargs: Additional arguments.

        Returns:
            State with skills metadata.
        """
        logger.info(f"SkillsMiddlewareV2: after_init for {agent.__class__.__name__}")

        if self.auto_load:
            skills = self.load_skills()
            logger.info(f"Loaded {len(skills)} skills from {self.sources}")
            return {
                "skills_loaded": True,
                "skills_count": len(skills),
                "skills_sources": self.sources,
            }
        return {}

    async def before_generate_reply(
        self,
        agent,
        context,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called before generating a reply.

        Matches skills based on user input if auto_match is enabled.

        Args:
            agent: The agent instance.
            context: The generate context.
            **kwargs: Additional arguments.

        Returns:
            State with matched skills.
        """
        if not self.auto_match or not context.message:
            return {}

        user_input = context.message.content or ""
        if user_input:
            matched_skills = self.match_skills(user_input)
            if matched_skills:
                logger.info(
                    f"Matched {len(matched_skills)} skills for input:"
                    f" {user_input[:50]}..."
                )
                return {
                    "matched_skills": [s.metadata.name for s in matched_skills],
                    "matched_skills_count": len(matched_skills),
                }
        return {}

    async def modify_system_prompt(
        self,
        agent,
        original_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Modify the system prompt with skills information.

        Args:
            agent: The agent instance.
            original_prompt: The original system prompt.
            context: Additional context information.

        Returns:
            Modified system prompt with skills section.
        """
        if not self.inject_to_system_prompt:
            return original_prompt

        if not self._loaded:
            self.load_skills()

        skills_section = self._base_middleware.create_skills_prompt_section()

        if original_prompt:
            modified = f"{skills_section}\n\n{original_prompt}"
        else:
            modified = skills_section

        return modified

    def get_skills_summary(self) -> str:
        """Get a summary of available skills.

        Returns:
            Formatted summary string.
        """
        all_skills = self.list_skills()
        summary = f"Total Skills: {len(all_skills)}\n"
        summary += f"Sources: {', '.join(self.sources)}\n\n"
        summary += "**Available Skills:**\n"
        for skill_metadata in all_skills:
            summary += f"  - {skill_metadata.name}: {skill_metadata.description}\n"

        return summary


__all__ = [
    "SkillsMiddlewareV2",
]
