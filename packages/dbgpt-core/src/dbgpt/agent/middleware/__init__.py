"""Middleware system for InsightAgent agents."""

from .agent import AgentConfig, MiddlewareAgent, create_middleware_agent
from .base import AgentMiddleware, MiddlewareManager

__all__ = [
    "AgentMiddleware",
    "MiddlewareManager",
    "AgentConfig",
    "MiddlewareAgent",
    "create_middleware_agent",
]
