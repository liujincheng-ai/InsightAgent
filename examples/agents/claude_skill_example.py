"""
Example: Using Claude-style SKILL files with InsightAgent agents.

This demonstrates how to use the Claude SKILL mechanism
where skills are defined in Markdown files.
"""

import asyncio
import os

from dbgpt.agent import AgentContext, AgentMemory, LLMConfig
from dbgpt.agent.claude_skill import (
    ClaudeSkillAgent,
    get_registry,
    load_skills_from_dir,
)
from dbgpt.model.proxy.llms.siliconflow import SiliconFlowLLMClient


async def main():
    """Main function demonstrating Claude SKILL usage."""

    # Load skills from directory
    skill_dir = os.path.join(os.path.dirname(__file__), "../skills/claude")

    load_skills_from_dir(skill_dir, recursive=True)

    # List available skills
    registry = get_registry()
    print("Loaded skills:")
    for skill_metadata in registry.list_skills():
        print(f"  - {skill_metadata.name}: {skill_metadata.description}")

    # Create LLM client
    llm_client = SiliconFlowLLMClient(
        model_alias=os.getenv(
            "SILICONFLOW_MODEL_VERSION", "Qwen/Qwen2.5-Coder-32B-Instruct"
        ),
    )

    # Create agent context
    agent_memory = AgentMemory()
    agent_memory.gpts_memory.init(conv_id="claude_skill_test")

    context: AgentContext = AgentContext(
        conv_id="claude_skill_test",
        gpts_app_name="Claude Skill Agent",
    )

    # Create Claude Skill Agent
    agent = ClaudeSkillAgent()

    # Bind necessary components
    await (
        agent.bind(context)
        .bind(LLMConfig(llm_client=llm_client))
        .bind(agent_memory)
        .build()
    )

    print("\n" + "=" * 60)
    print("Claude Skill Agent Ready!")
    print("=" * 60)

    # Example interactions
    test_inputs = [
        "Can you explain how this code works?",
        "My code isn't working, can you help debug it?",
        "Write a function to sort a list",
        "Simplify this complex code for me",
    ]

    print("\nTest inputs and skill detection:")
    print("-" * 60)

    for user_input in test_inputs:
        agent.detect_and_apply_skill(user_input)

        if agent.current_skill:
            print(f"Input: {user_input}")
            print(f"Matched Skill: {agent.current_skill.metadata.name}")
            print(f"Description: {agent.current_skill.metadata.description}")
            print(f"Instructions preview: {agent.current_skill.instructions[:100]}...")
            print()

    # Show available skills
    print("\nAvailable skills:")
    for skill_name in agent.get_available_skills():
        print(f"  - {skill_name}")

    # Manual skill selection example
    print("\n" + "-" * 60)
    print("Manual skill selection:")
    agent.set_skill("explain-code")
    print(f"Current skill: {agent.current_skill.metadata.name}")

    agent.clear_skill()
    print(f"After clearing: {agent.current_skill}")


if __name__ == "__main__":
    asyncio.run(main())
