"""Example: Agent with Skill loading mechanism.

This example demonstrates how to use the SKILL loading mechanism
with InsightAgent agents.
"""

import asyncio
import logging
import os

from dbgpt.agent import (
    AgentContext,
    AgentMemory,
    ConversableAgent,
    LLMConfig,
    UserProxyAgent,
)
from dbgpt.agent.core.action.base import ActionOutput
from dbgpt.agent.core.profile.base import ProfileConfig
from dbgpt.agent.expand.actions.react_action import Terminate
from dbgpt.agent.expand.actions.tool_action import ToolAction
from dbgpt.agent.resource import ToolPack, tool
from dbgpt.agent.skill import (
    Skill,
    SkillBuilder,
    SkillLoader,
    SkillManager,
    SkillType,
    get_skill_manager,
    initialize_skill,
)
from dbgpt.component import SystemApp
from dbgpt.model import AutoLLMClient


@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression.

    Args:
        expression: The mathematical expression to calculate (e.g., "1 + 2 * 3").

    Returns:
        The result of the calculation.
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


# Use ToolAction as the agent's action module to enable tool usage.


class MathSkillAgent(ConversableAgent):
    """Agent with math skill.

    Supports binding a Skill instance using `.bind(skill_instance)` so that
    skills can be provided either in the constructor or later via `bind`.
    """

    def __init__(self, skill: Skill | None = None, **kwargs):
        """Initialize the agent with an optional skill."""
        super().__init__(**kwargs)
        self._skill = skill

    @property
    def skill(self) -> Skill:
        """Return the skill if bound, otherwise raise a helpful error."""
        if not getattr(self, "_skill", None):
            raise ValueError(
                "Skill not bound to agent. Call .bind(skill) before build()."
            )
        return self._skill


async def main():
    """Main function."""
    system_app = SystemApp()

    # Initialize skill manager
    initialize_skill(system_app)
    skill_manager = get_skill_manager(system_app)

    # First try to load a SKILL.md from skills/claude
    loader = SkillLoader()
    loaded_from_file = None
    try:
        loaded_from_file = loader.load_skill_from_file(
            "/Users/chenketing.ckt/Desktop/project/InsightAgent/skills/claude/math_assistant/SKILL.md"
        )
        if loaded_from_file:
            # register loaded skill (demonstrate file-based loading path)
            skill_manager.register_skill(
                skill_instance=loaded_from_file, name=loaded_from_file.metadata.name
            )
            print(f"Loaded SKILL.md skill: {loaded_from_file.metadata.name}")
    except Exception:
        loaded_from_file = None

    # If SKILL.md not available, fall back to building programmatically
    if not loaded_from_file:
        math_skill = (
            SkillBuilder(
                name="math_assistant", description="Mathematical calculation assistant"
            )
            .with_version("1.0.0")
            .with_author("InsightAgent Team")
            .with_skill_type(SkillType.Chat)
            .with_tags(["math", "calculation"])
            .with_prompt_template(
                "You are a mathematical assistant. Help users with calculations and "
                "explain mathematical concepts clearly. Use the calculate tool for "
                "computations."
            )
            .with_required_tool("calculate")
            .build()
        )

        # Register the skill
        skill_manager.register_skill(
            skill_instance=math_skill,
            name="math_assistant",
        )
        loaded_skill = skill_manager.get_skill(name="math_assistant")
        if loaded_skill:
            print(f"Loaded programmatic skill: {loaded_skill.metadata.name}")
    else:
        loaded_skill = loaded_from_file

    # Create an LLM client similar to react_agent_example so the example can
    # interact with a real model provider. Configure via environment variables.
    logging.basicConfig(level=logging.INFO)
    llm_client = AutoLLMClient(
        provider=os.getenv("LLM_PROVIDER", "proxy/siliconflow"),
        name=os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    )

    agent_memory = AgentMemory()
    agent_memory.gpts_memory.init(conv_id="skill_test_001")

    context: AgentContext = AgentContext(
        conv_id="skill_test_001", gpts_app_name="Math Skill Agent"
    )

    # Create agent with skill (provide ProfileConfig required by agent role)
    profile = ProfileConfig(name="MathAssistant", role="math_assistant")
    # Instantiate agent with profile and skill
    # If ResourceManager/SkillResource is not initialized when running example
    # standalone, the agent will still work as we bind tools directly. However
    # for completeness, register SkillResource with the global ResourceManager
    # so other components (ToolAction) can resolve skills if needed.
    try:
        from dbgpt.agent.resource.manage import (
            get_resource_manager,
            initialize_resource,
        )
        from dbgpt.agent.resource.skill_resource import SkillResource

        initialize_resource(system_app)
        rm = get_resource_manager(system_app)
        rm.register_resource(SkillResource, resource_type=None)
    except Exception as e:
        print(e)
        # ignore registration failures in example runs
        pass

    # Create a ToolPack from the calculate tool and bind it as the agent's resource
    tool_packs = ToolPack.from_resource([calculate, Terminate()])
    tool_pack = tool_packs[0]

    # Create agent and bind the loaded skill via .bind(skill) so skills can be
    # injected at runtime rather than only via constructor.
    math_agent = (
        await MathSkillAgent(profile=profile)
        .bind(loaded_skill)
        .bind(context)
        .bind(LLMConfig(llm_client=llm_client))
        .bind(agent_memory)
        .bind(tool_pack)
        .bind(ToolAction)
        .build()
    )

    print("Math Skill Agent created successfully!")
    print(f"Skill: {math_agent.skill.metadata.name}")
    print(f"Skill type: {math_agent.skill.metadata.skill_type}")
    print(f"Required tools: {math_agent.skill.required_tools}")

    # Create a user proxy to interact with the agent (same pattern as react example)
    user_proxy = await UserProxyAgent().bind(agent_memory).bind(context).build()

    # Example interactions
    await user_proxy.initiate_chat(
        recipient=math_agent,
        reviewer=user_proxy,
        message="Compute 10 * 99 using the calculate tool and return the numeric result.",
    )

    # Show dbgpt-vis link messages
    try:
        print(await agent_memory.gpts_memory.app_link_chat_message("skill_test_001"))
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
