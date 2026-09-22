"""Agent Resource wrapper for Skills.

This file introduces a Resource subclass so skills can be treated as a
first-class Resource (ResourceType.Skill). It uses SkillManager to build
skill instances from parameters and exposes prompt/get_prompt to integrate
with existing resource plumbing.
"""

from typing import Any, Dict, Optional, Tuple

from dbgpt.agent.resource.base import Resource, ResourceType
from dbgpt.agent.skill.parameters import SkillParameters


class SkillResource(Resource[SkillParameters]):
    @classmethod
    def type(cls) -> ResourceType:
        return ResourceType.Skill

    def __init__(
        self,
        name: str,
        skill=None,
        skill_name: Optional[str] = None,
        system_app: Any = None,
        **kwargs,
    ):
        self._name = name
        if skill:
            self._skill = skill
        elif skill_name:
            # Load skill from SkillManager
            from dbgpt.agent.skill.manage import get_skill_manager

            skill_manager = get_skill_manager(system_app)
            self._skill = skill_manager.get_skill(name=skill_name)
            if not self._skill:
                # Try to load by type if name not found
                # Or just keep it None and fail later or log warning
                pass
        else:
            self._skill = None

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def resource_parameters_class(cls, **kwargs):
        return SkillParameters

    async def get_prompt(
        self,
        *,
        lang: str = "en",
        prompt_type: str = "default",
        question: Optional[str] = None,
        resource_name: Optional[str] = None,
        **kwargs,
    ) -> Tuple[str, Optional[Dict]]:
        """Return the skill's prompt template as resource prompt."""
        if not self._skill or not self._skill.prompt_template:
            return "", None
        # skill.prompt_template is a PromptTemplate
        prompt = self._skill.prompt_template.format(question=question or "")
        return prompt, None

    async def get_resources(self, *args, **kwargs) -> Tuple[None, str, None]:
        prompt, _ = await self.get_prompt(*args, **kwargs)
        return None, prompt, None

    async def async_execute(self, *args, resource_name: Optional[str] = None, **kwargs):
        # Skills themselves don't execute here; actions/tools implement behavior.
        raise NotImplementedError("SkillResource is readonly wrapper")
