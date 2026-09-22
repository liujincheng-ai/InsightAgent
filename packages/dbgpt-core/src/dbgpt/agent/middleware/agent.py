"""Middleware-enabled ConversableAgent.

This module extends ConversableAgent to support middleware integration,
following deepagents' middleware pattern.
"""

import dataclasses
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.base_agent import ConversableAgent
from ..middleware.base import MiddlewareManager
from ..skill.middleware_v2 import SkillsMiddlewareV2

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class AgentConfig:
    """Configuration for MiddlewareAgent."""

    enable_middleware: bool = True
    """Enable middleware system."""

    enable_skills: bool = True
    """Enable skills middleware."""

    skill_sources: Optional[List[str]] = None
    """Skill source directories."""

    skill_auto_load: bool = True
    """Auto-load skills."""

    skill_auto_match: bool = True
    """Auto-match skills."""

    skill_inject_to_prompt: bool = True
    """Inject skills to system prompt."""


class MiddlewareAgent(ConversableAgent):
    """ConversableAgent with middleware support.

    This agent extends ConversableAgent to support middleware plugins,
    similar to deepagents' middleware pattern. The middleware system
    allows plugins to hook into agent lifecycle events.

    Example:
        ```python
        from dbgpt.agent.core.profile.base import ProfileConfig
        from dbgpt.agent.middleware.agent import MiddlewareAgent, AgentConfig
        from dbgpt.agent.skill.middleware_v2 import SkillsMiddlewareV2

        profile = ProfileConfig(name="assistant", role="AI Assistant")
        config = AgentConfig(skill_sources=["/path/to/skills/user"])

        agent = MiddlewareAgent(profile=profile, agent_config=config)
        ```
    """

    def __init__(self, agent_config: Optional[AgentConfig] = None, **kwargs):
        """Initialize MiddlewareAgent.

        Args:
            agent_config: Agent configuration.
            **kwargs: Additional arguments for ConversableAgent.
        """
        super().__init__(**kwargs)

        self.agent_config = agent_config or AgentConfig()
        self._middleware_manager = MiddlewareManager()

        if self.agent_config.enable_middleware and self.agent_config.enable_skills:
            skill_sources = self.agent_config.skill_sources or []
            if skill_sources:
                skills_middleware = SkillsMiddlewareV2(
                    sources=skill_sources,
                    auto_load=self.agent_config.skill_auto_load,
                    auto_match=self.agent_config.skill_auto_match,
                    inject_to_system_prompt=self.agent_config.skill_inject_to_prompt,
                )
                self._middleware_manager.register(skills_middleware)

    @property
    def middleware_manager(self) -> MiddlewareManager:
        """Return the middleware manager."""
        return self._middleware_manager

    def register_middleware(self, middleware):
        """Register a middleware.

        Args:
            middleware: The middleware to register.
        """
        self._middleware_manager.register(middleware)

    def unregister_middleware(self, middleware):
        """Unregister a middleware.

        Args:
            middleware: The middleware to unregister.
        """
        self._middleware_manager.unregister(middleware)

    async def build(self, is_retry_chat: bool = False) -> "MiddlewareAgent":
        """Build the agent with middleware integration.

        Args:
            is_retry_chat: Whether this is a retry chat.

        Returns:
            Built agent instance.
        """
        logger.info("Building MiddlewareAgent...")

        if self.agent_config.enable_middleware:
            await self._middleware_manager.execute_before_init(
                self, is_retry_chat=is_retry_chat
            )

        await super().build(is_retry_chat=is_retry_chat)

        if self.agent_config.enable_middleware:
            await self._middleware_manager.execute_after_init(
                self, is_retry_chat=is_retry_chat
            )

        return self

    async def _a_init_reply_message(
        self,
        received_message,
        rely_messages: Optional[List] = None,
    ):
        """Initialize reply message with middleware hooks.

        Args:
            received_message: The received message.
            rely_messages: List of relied messages.

        Returns:
            AgentMessage or None.
        """
        if self.agent_config.enable_middleware and received_message:
            from ..core.agent import AgentGenerateContext

            context = AgentGenerateContext(
                message=received_message,
                sender=self,
            )
            await self._middleware_manager.execute_before_generate_reply(
                self, context, rely_messages=rely_messages
            )

        return await super()._a_init_reply_message(
            received_message=received_message,
            rely_messages=rely_messages,
        )

    async def thinking(
        self,
        messages,
        sender=None,
        prompt=None,
        stream_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Think with middleware hooks.

        Args:
            messages: The messages to be reasoned.
            sender: Sender agent.
            prompt: The prompt to be reasoned.

        Returns:
            Tuple of (reply, model_name).
        """
        if self.agent_config.enable_middleware:
            from ..core.agent import AgentGenerateContext

            if messages:
                last_message = messages[-1] if messages else None
                context = AgentGenerateContext(
                    message=last_message,
                    sender=sender or self,
                )
                await self._middleware_manager.execute_before_thinking(self, context)

        llm_reply, model_name = await super().thinking(
            messages, sender, prompt, stream_callback=stream_callback
        )

        if self.agent_config.enable_middleware:
            from ..core.agent import AgentGenerateContext

            if messages:
                last_message = messages[-1] if messages else None
                context = AgentGenerateContext(
                    message=last_message,
                    sender=sender or self,
                )
                await self._middleware_manager.execute_after_thinking(
                    self,
                    context,
                    (llm_reply or ""),
                    (model_name or ""),
                )

        return llm_reply, model_name

    async def act(
        self,
        message,
        sender,
        reviewer=None,
        is_retry_chat=False,
        last_speaker_name=None,
        **kwargs,
    ):
        """Act with middleware hooks.

        Args:
            message: The message to be executed.
            sender: Sender agent.
            reviewer: Reviewer agent.
            is_retry_chat: Whether this is a retry chat.
            last_speaker_name: Last speaker name.
            **kwargs: Additional arguments.

        Returns:
            ActionOutput.
        """
        if self.agent_config.enable_middleware:
            from ..core.agent import AgentGenerateContext

            context = AgentGenerateContext(
                message=message,
                sender=sender,
                reviewer=reviewer,
            )
            await self._middleware_manager.execute_before_act(
                self, context, message, reviewer=reviewer
            )

        action_output = await super().act(
            message,
            sender,
            reviewer=reviewer,
            is_retry_chat=is_retry_chat,
            last_speaker_name=last_speaker_name,
            **kwargs,
        )

        if self.agent_config.enable_middleware:
            from ..core.agent import AgentGenerateContext

            context = AgentGenerateContext(
                message=message,
                sender=sender,
                reviewer=reviewer,
            )
            await self._middleware_manager.execute_after_act(
                self, context, action_output, reviewer=reviewer
            )

        return action_output

    async def build_system_prompt(
        self,
        question=None,
        most_recent_memories=None,
        resource_vars=None,
        context=None,
        is_retry_chat=False,
    ):
        """Build system prompt with middleware hooks.

        Args:
            question: Current question.
            most_recent_memories: Most recent memories.
            resource_vars: Resource variables.
            context: Additional context.
            is_retry_chat: Whether this is a retry chat.

        Returns:
            System prompt string.
        """
        original_prompt = await super().build_system_prompt(
            question=question,
            most_recent_memories=most_recent_memories,
            resource_vars=resource_vars,
            context=context,
            is_retry_chat=is_retry_chat,
        )

        if self.agent_config.enable_middleware:
            return await self._middleware_manager.execute_modify_system_prompt(
                self, original_prompt, context
            )

        return original_prompt


def create_middleware_agent(
    profile,
    agent_config: Optional[AgentConfig] = None,
    agent_context=None,
    **kwargs,
) -> MiddlewareAgent:
    """Create a MiddlewareAgent.

    Args:
        profile: Profile configuration.
        agent_config: Agent configuration.
        agent_context: Agent context.
        **kwargs: Additional arguments.

    Returns:
        Configured MiddlewareAgent instance.
    """
    agent = MiddlewareAgent(
        profile=profile,
        agent_config=agent_config,
        agent_context=agent_context,
        **kwargs,
    )

    return agent


__all__ = [
    "AgentConfig",
    "MiddlewareAgent",
    "create_middleware_agent",
]
