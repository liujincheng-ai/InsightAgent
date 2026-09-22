"""Example: Using SkillsMiddleware with MiddlewareAgent.

This example demonstrates how to use the new middleware system
to load and use skills in InsightAgent agents.
"""

import asyncio

from dbgpt.agent.core.agent import AgentContext
from dbgpt.agent.core.profile.base import ProfileConfig
from dbgpt.agent.middleware.agent import AgentConfig, MiddlewareAgent
from dbgpt.agent.skill.middleware_v2 import SkillsMiddlewareV2


async def example_with_skills():
    """Example of using skills with MiddlewareAgent."""

    profile = ProfileConfig(
        name="assistant",
        role="AI Assistant",
        goal="Help users with their tasks using available skills.",
    )

    config = AgentConfig(
        enable_middleware=True,
        enable_skills=True,
        skill_sources=[
            "/path/to/skills/user",
            "/path/to/skills/project",
        ],
        skill_auto_load=True,
        skill_auto_match=True,
        skill_inject_to_prompt=True,
    )

    agent = MiddlewareAgent(
        profile=profile,
        agent_config=config,
    )

    agent_context = AgentContext(
        conv_id="test_conv_001",
        language="zh-CN",
    )

    await agent.bind(agent_context).build()

    return agent


async def example_custom_middleware():
    """Example of using custom middleware."""

    from dbgpt.agent.middleware.base import AgentMiddleware

    class LoggingMiddleware(AgentMiddleware):
        """Custom middleware for logging."""

        async def before_generate_reply(self, agent, context, **kwargs):
            """Called before generating a reply."""
            print(f"Before generate reply: {context.message.content}")

        async def after_generate_reply(self, agent, context, reply_message, **kwargs):
            """Called after generating a reply."""
            print(f"After generate reply: {reply_message.content}")

    profile = ProfileConfig(
        name="assistant",
        role="AI Assistant",
    )

    agent = MiddlewareAgent(
        profile=profile,
        agent_config=AgentConfig(enable_middleware=True),
    )

    logging_middleware = LoggingMiddleware()
    agent.register_middleware(logging_middleware)

    return agent


async def example_skills_middleware_direct():
    """Example of using SkillsMiddlewareV2 directly."""

    skills_middleware = SkillsMiddlewareV2(
        sources=["/path/to/skills/user"],
        auto_load=True,
        auto_match=True,
        inject_to_system_prompt=True,
    )

    skills = skills_middleware.load_skills()
    print(f"Loaded {len(skills)} skills:")
    for name, skill in skills.items():
        print(f"  - {name}: {skill.metadata.description}")

    matched_skills = skills_middleware.match_skills("research quantum computing")
    print(f"\nMatched {len(matched_skills)} skills")


if __name__ == "__main__":
    asyncio.run(example_with_skills())
    asyncio.run(example_custom_middleware())
    asyncio.run(example_skills_middleware_direct())
