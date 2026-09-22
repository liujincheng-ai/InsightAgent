"""Test script for SkillsMiddlewareV2.

This script demonstrates how to use the new middleware system
to load and use skills in InsightAgent agents.
"""

import asyncio
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../packages/dbgpt-core/src")
)

from dbgpt.agent.core.agent import AgentContext
from dbgpt.agent.core.profile.base import ProfileConfig
from dbgpt.agent.middleware.agent import AgentConfig, MiddlewareAgent
from dbgpt.agent.skill.middleware_v2 import SkillsMiddlewareV2


async def test_skills_middleware():
    """Test SkillsMiddlewareV2 functionality."""

    skills_path = os.path.join(os.path.dirname(__file__), "skills/user")

    if not os.path.exists(skills_path):
        print(f"Skills directory not found: {skills_path}")
        print("Creating test skills...")
        return

    config = AgentConfig(
        enable_middleware=True,
        enable_skills=True,
        skill_sources=[skills_path],
        skill_auto_load=True,
        skill_auto_match=True,
        skill_inject_to_prompt=True,
    )

    profile = ProfileConfig(
        name="assistant",
        role="AI Assistant",
        goal="Help users with their tasks using available skills.",
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

    print("\n=== Skills Summary ===")
    skills = agent.middleware_manager._middlewares[0]  # Get SkillsMiddlewareV2
    print(skills.get_skills_summary())

    print("\n=== Testing Skill Matching ===")
    test_inputs = [
        "research quantum computing",
        "review my python code",
        "analyze this data",
    ]

    for test_input in test_inputs:
        print(f"\nInput: {test_input}")
        matched = skills.match_skills(test_input)
        if matched:
            print(f"Matched skills: {[s.metadata.name for s in matched]}")
        else:
            print("No skills matched")

    print("\n=== Test Complete ===")


async def test_custom_middleware():
    """Test custom middleware."""

    from dbgpt.agent.middleware.base import AgentMiddleware

    class LoggingMiddleware(AgentMiddleware):
        """Custom middleware for logging."""

        async def before_generate_reply(self, agent, context, **kwargs):
            print(f"[LoggingMiddleware] Before generate reply")
            if context and hasattr(context, "message"):
                print(f"  Message: {context.message.content[:50]}...")

        async def after_generate_reply(self, agent, context, reply_message, **kwargs):
            print(f"[LoggingMiddleware] After generate reply")
            if reply_message:
                print(f"  Reply: {reply_message.content[:50]}...")

        async def modify_system_prompt(self, agent, original_prompt, context=None):
            modified = (
                f"\n[LoggingMiddleware] Custom prompt section\n\n{original_prompt}"
            )
            return modified

    profile = ProfileConfig(
        name="assistant",
        role="AI Assistant",
    )

    config = AgentConfig(
        enable_middleware=True,
        enable_skills=False,  # Disable skills for this test
    )

    agent = MiddlewareAgent(
        profile=profile,
        agent_config=config,
    )

    logging_middleware = LoggingMiddleware()
    agent.register_middleware(logging_middleware)

    agent_context = AgentContext(
        conv_id="test_logging_conv",
        language="en",
    )

    await agent.bind(agent_context).build()

    print("\n=== Custom Middleware Test ===")
    print("LoggingMiddleware has been registered")
    print(f"Total middleware: {len(agent.middleware_manager._middlewares)}")

    print("\n=== Test Complete ===")


async def main():
    """Run all tests."""

    print("=" * 80)
    print("InsightAgent Skills Middleware Test")
    print("=" * 80)

    print("\n\n### Test 1: SkillsMiddlewareV2 ###")
    await test_skills_middleware()

    print("\n\n### Test 2: Custom Middleware ###")
    await test_custom_middleware()

    print("\n\n### All Tests Complete ###")


if __name__ == "__main__":
    asyncio.run(main())
