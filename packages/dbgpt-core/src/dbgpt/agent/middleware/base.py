"""Agent Middleware System for InsightAgent.

This module implements a middleware system similar to deepagents' AgentMiddleware,
allowing plugins to hook into agent lifecycle events.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, Dict, List, Optional

from dbgpt.agent.core.agent import AgentGenerateContext, AgentMessage

logger = logging.getLogger(__name__)


class AgentMiddleware(ABC):
    """Base class for agent middleware.

    Middleware can hook into various lifecycle events of an agent:
    - before_init: Before agent initialization
    - after_init: After agent initialization
    - before_generate_reply: Before generating a reply
    - after_generate_reply: After generating a reply
    - before_thinking: Before the thinking step
    - after_thinking: After the thinking step
    - before_act: Before the act step
    - after_act: After the act step
    - modify_system_prompt: Modify the system prompt
    """

    def __init__(self):
        """Initialize the middleware."""
        self._enabled: bool = True

    @property
    def enabled(self) -> bool:
        """Check if middleware is enabled."""
        return self._enabled

    def enable(self):
        """Enable the middleware."""
        self._enabled = True

    def disable(self):
        """Disable the middleware."""
        self._enabled = False

    async def before_init(self, agent, **kwargs) -> Optional[Dict[str, Any]]:
        """Called before agent initialization.

        Args:
            agent: The agent instance.
            **kwargs: Additional initialization arguments.

        Returns:
            Optional state to be passed to other middleware or the agent.
        """
        return None

    async def after_init(self, agent, **kwargs) -> Optional[Dict[str, Any]]:
        """Called after agent initialization.

        Args:
            agent: The agent instance.
            **kwargs: Additional initialization arguments.

        Returns:
            Optional state to be merged with agent state.
        """
        return None

    async def before_generate_reply(
        self,
        agent,
        context: AgentGenerateContext,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called before generating a reply.

        Args:
            agent: The agent instance.
            context: The generate context.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def after_generate_reply(
        self,
        agent,
        context: AgentGenerateContext,
        reply_message: AgentMessage,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called after generating a reply.

        Args:
            agent: The agent instance.
            context: The generate context.
            reply_message: The generated reply message.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def before_thinking(
        self,
        agent,
        context: AgentGenerateContext,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called before the thinking step.

        Args:
            agent: The agent instance.
            context: The generate context.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def after_thinking(
        self,
        agent,
        context: AgentGenerateContext,
        llm_reply: str,
        model_name: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called after the thinking step.

        Args:
            agent: The agent instance.
            context: The generate context.
            llm_reply: The LLM reply.
            model_name: The model name used.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def before_act(
        self,
        agent,
        context: AgentGenerateContext,
        message: AgentMessage,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called before the act step.

        Args:
            agent: The agent instance.
            context: The generate context.
            message: The message to act on.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def after_act(
        self,
        agent,
        context: AgentGenerateContext,
        action_output,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Called after the act step.

        Args:
            agent: The agent instance.
            context: The generate context.
            action_output: The action output.
            **kwargs: Additional arguments.

        Returns:
            Optional state update.
        """
        return None

    async def modify_system_prompt(
        self,
        agent,
        original_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Modify the system prompt before it's sent to LLM.

        Args:
            agent: The agent instance.
            original_prompt: The original system prompt.
            context: Additional context information.

        Returns:
            Modified system prompt.
        """
        return original_prompt


class MiddlewareManager:
    """Manager for agent middleware.

    Handles registration, ordering, and execution of middleware.
    """

    def __init__(self):
        """Initialize the middleware manager."""
        self._middlewares: List[AgentMiddleware] = []
        self._state: Dict[str, Any] = {}

    def register(self, middleware: AgentMiddleware) -> "MiddlewareManager":
        """Register a middleware.

        Args:
            middleware: The middleware to register.

        Returns:
            Self for chaining.
        """
        if middleware not in self._middlewares:
            self._middlewares.append(middleware)
            logger.info(f"Registered middleware: {middleware.__class__.__name__}")
        return self

    def unregister(self, middleware: AgentMiddleware) -> "MiddlewareManager":
        """Unregister a middleware.

        Args:
            middleware: The middleware to unregister.

        Returns:
            Self for chaining.
        """
        if middleware in self._middlewares:
            self._middlewares.remove(middleware)
            logger.info(f"Unregistered middleware: {middleware.__class__.__name__}")
        return self

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value.

        Args:
            key: The state key.
            default: Default value if key doesn't exist.

        Returns:
            The state value.
        """
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value.

        Args:
            key: The state key.
            value: The state value.
        """
        self._state[key] = value

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with a dictionary.

        Args:
            updates: Dictionary of state updates.
        """
        self._state.update(updates)

    async def execute_before_init(self, agent, **kwargs) -> Dict[str, Any]:
        """Execute all before_init hooks.

        Args:
            agent: The agent instance.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.before_init(agent, **kwargs)
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_after_init(self, agent, **kwargs) -> Dict[str, Any]:
        """Execute all after_init hooks.

        Args:
            agent: The agent instance.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.after_init(agent, **kwargs)
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_before_generate_reply(
        self, agent, context: AgentGenerateContext, **kwargs
    ) -> Dict[str, Any]:
        """Execute all before_generate_reply hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.before_generate_reply(agent, context, **kwargs)
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_after_generate_reply(
        self,
        agent,
        context: AgentGenerateContext,
        reply_message: AgentMessage,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute all after_generate_reply hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            reply_message: The generated reply message.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.after_generate_reply(
                    agent, context, reply_message, **kwargs
                )
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_before_thinking(
        self, agent, context: AgentGenerateContext, **kwargs
    ) -> Dict[str, Any]:
        """Execute all before_thinking hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.before_thinking(agent, context, **kwargs)
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_after_thinking(
        self,
        agent,
        context: AgentGenerateContext,
        llm_reply: str,
        model_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute all after_thinking hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            llm_reply: The LLM reply.
            model_name: The model name used.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.after_thinking(
                    agent, context, llm_reply, model_name, **kwargs
                )
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_before_act(
        self, agent, context: AgentGenerateContext, message: AgentMessage, **kwargs
    ) -> Dict[str, Any]:
        """Execute all before_act hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            message: The message to act on.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.before_act(agent, context, message, **kwargs)
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_after_act(
        self, agent, context: AgentGenerateContext, action_output, **kwargs
    ) -> Dict[str, Any]:
        """Execute all after_act hooks.

        Args:
            agent: The agent instance.
            context: The generate context.
            action_output: The action output.
            **kwargs: Additional arguments.

        Returns:
            Combined state from all middleware.
        """
        combined_state = {}
        for middleware in self._middlewares:
            if middleware.enabled:
                state = await middleware.after_act(
                    agent, context, action_output, **kwargs
                )
                if state:
                    combined_state.update(state)
        return combined_state

    async def execute_modify_system_prompt(
        self,
        agent,
        original_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute all modify_system_prompt hooks.

        Args:
            agent: The agent instance.
            original_prompt: The original system prompt.
            context: Additional context information.

        Returns:
            Modified system prompt.
        """
        prompt = original_prompt
        for middleware in self._middlewares:
            if middleware.enabled:
                prompt = await middleware.modify_system_prompt(agent, prompt, context)
        return prompt


__all__ = [
    "AgentMiddleware",
    "MiddlewareManager",
]
