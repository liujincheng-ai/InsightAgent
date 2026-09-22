"""Skills middleware for InsightAgent agents.

This module implements progressive disclosure for skills, similar to
deepagents' SkillsMiddleware. Skills are loaded from configured sources
and their metadata is injected into system prompt, with full content
loaded on demand.
"""

import dataclasses
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dbgpt.core import PromptTemplate

logger = logging.getLogger(__name__)

MAX_SKILL_FILE_SIZE = 10 * 1024 * 1024
MAX_SKILL_NAME_LENGTH = 64
MAX_SKILL_DESCRIPTION_LENGTH = 1024


@dataclasses.dataclass
class SkillMetadata:
    """Metadata for a skill."""

    name: str
    description: str
    path: str
    version: str = "1.0.0"
    author: Optional[str] = None
    skill_type: str = "custom"
    tags: List[str] = dataclasses.field(default_factory=list)
    license: Optional[str] = None
    allowed_tools: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "version": self.version,
            "author": self.author,
            "skill_type": self.skill_type,
            "tags": self.tags,
            "license": self.license,
            "allowed_tools": self.allowed_tools,
        }


class LoadedSkill:
    """A loaded skill with metadata and optional content."""

    def __init__(
        self,
        metadata: SkillMetadata,
        content: Optional[str] = None,
    ):
        """Initialize loaded skill.

        Args:
            metadata: Skill metadata.
            content: Full skill content (markdown instructions).
        """
        self._metadata = metadata
        self._content = content

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return self._metadata

    @property
    def content(self) -> Optional[str]:
        """Return skill content."""
        if self._content is None and self._metadata.path:
            try:
                with open(self._metadata.path, "r", encoding="utf-8") as f:
                    self._content = f.read()
            except Exception as e:
                logger.error(
                    f"Failed to load skill content from {self._metadata.path}: {e}"
                )
        return self._content

    def get_prompt_template(self) -> PromptTemplate:
        """Get prompt template with skill instructions.

        Returns:
            PromptTemplate with the skill's full instructions.
        """
        content = (
            self.content or f"# {self.metadata.name}\n\n{self.metadata.description}"
        )
        return PromptTemplate.from_template(content)


def _validate_skill_name(name: str) -> tuple[bool, str]:
    """Validate skill name.

    Requirements:
    - Max 64 characters
    - Lowercase alphanumeric and hyphens only (a-z, 0-9, -)
    - Cannot start or end with hyphen
    - No consecutive hyphens

    Args:
        name: Skill name to validate.

    Returns:
        (is_valid, error_message) tuple.
    """
    if not name:
        return False, "name is required"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, "name exceeds 64 characters"
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        return False, "name must be lowercase alphanumeric with single hyphens only"
    return True, ""


def _parse_skill_metadata(
    content: str, skill_path: str, directory_name: str
) -> Optional[SkillMetadata]:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Content of the SKILL.md file.
        skill_path: Path to the SKILL.md file.
        directory_name: Name of the parent directory.

    Returns:
        SkillMetadata if parsing succeeds, None otherwise.
    """
    if len(content) > MAX_SKILL_FILE_SIZE:
        logger.warning(
            "Skipping %s: content too large (%d bytes)", skill_path, len(content)
        )
        return None

    frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        logger.warning("Skipping %s: no valid YAML frontmatter found", skill_path)
        return None

    frontmatter_str = match.group(1)

    try:
        import yaml

        frontmatter_data = yaml.safe_load(frontmatter_str)
    except ImportError:
        logger.error("PyYAML not installed, cannot parse SKILL.md files")
        return None
    except Exception as e:
        logger.warning("Failed to parse YAML in %s: %s", skill_path, e)
        return None

    if not isinstance(frontmatter_data, dict):
        logger.warning("Skipping %s: frontmatter is not a mapping", skill_path)
        return None

    name = frontmatter_data.get("name")
    description = frontmatter_data.get("description")

    if not name or not description:
        logger.warning(
            "Skipping %s: missing required 'name' or 'description'", skill_path
        )
        return None

    is_valid, error = _validate_skill_name(str(name))
    if not is_valid:
        logger.warning(
            "Skill '%s' in %s does not follow naming convention: %s",
            name,
            skill_path,
            error,
        )

    description_str = str(description).strip()
    if len(description_str) > MAX_SKILL_DESCRIPTION_LENGTH:
        logger.warning(
            "Description exceeds %d characters in %s, truncating",
            MAX_SKILL_DESCRIPTION_LENGTH,
            skill_path,
        )
        description_str = description_str[:MAX_SKILL_DESCRIPTION_LENGTH]

    allowed_tools = []
    allowed_tools_value = frontmatter_data.get("allowed-tools")
    if allowed_tools_value and isinstance(allowed_tools_value, str):
        allowed_tools = allowed_tools_value.split(" ")

    return SkillMetadata(
        name=str(name),
        description=description_str,
        path=skill_path,
        version=frontmatter_data.get("version", "1.0.0"),
        author=frontmatter_data.get("author", "").strip() or None,
        license=frontmatter_data.get("license", "").strip() or None,
        allowed_tools=allowed_tools,
        skill_type=frontmatter_data.get("skill_type", "custom"),
        tags=frontmatter_data.get("tags", []),
    )


def _list_skills_from_directory(source_path: str) -> List[SkillMetadata]:
    """List all skills from a directory.

    Args:
        source_path: Path to the skills directory.

    Returns:
        List of skill metadata from successfully parsed SKILL.md files.
    """
    skills: List[SkillMetadata] = []
    base_path = Path(source_path)

    if not base_path.exists() or not base_path.is_dir():
        logger.warning("Directory not found: %s", source_path)
        return skills

    for skill_dir in base_path.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            continue

        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            directory_name = skill_dir.name
            skill_metadata = _parse_skill_metadata(
                content=content,
                skill_path=str(skill_md_path),
                directory_name=directory_name,
            )

            if skill_metadata:
                skills.append(skill_metadata)

        except Exception as e:
            logger.warning("Failed to load skill from %s: %s", skill_md_path, e)

    return skills


SKILLS_SYSTEM_PROMPT = """

## Skills System

You have access to a skills library that provides specialized
capabilities and domain knowledge.

{skills_locations}

**Available Skills:**

{skills_list}

**How to Use Skills (Progressive Disclosure):**

Skills follow a **progressive disclosure** pattern - you see their name and
description above, but only read full instructions when needed:

1. **Recognize when a skill applies**: Check if the user's task matches
a skill's description
2. **Read the skill's full instructions**: Use the path shown in the skill list above
3. **Follow the skill's instructions**: SKILL.md contains step-by-step workflows,
best practices, and examples
4. **Access supporting files**: Skills may include helper scripts, configs, or
reference docs - use absolute paths

**When to Use Skills:**
- User's request matches a skill's domain (e.g., "research X" -> web-research skill)
- You need specialized knowledge or structured workflows
- A skill provides proven patterns for complex tasks

**Example Workflow:**

User: "Can you research the latest developments in quantum computing?"

1. Check available skills -> See "web-research" skill with its path
2. Read the skill using the path shown
3. Follow the skill's research workflow (search -> organize -> synthesize)
4. Use any helper scripts with absolute paths

Remember: Skills make you more capable and consistent. When in doubt, check if
a skill exists for the task!
"""


class SkillsMiddleware:
    """Middleware for loading and exposing agent skills to the system prompt.

    Loads skills from sources and injects them into the system prompt
    using progressive disclosure (metadata first, full content on demand).

    Example:
        ```python
        middleware = SkillsMiddleware(
            sources=[
                "/path/to/skills/user/",
                "/path/to/skills/project/",
            ],
        )
        ```
    """

    def __init__(self, sources: List[str]):
        """Initialize the skills middleware.

        Args:
            sources: List of skill source paths.
        """
        self.sources = sources
        self._skills: Dict[str, LoadedSkill] = {}
        self._loaded = False

    def load_skills(self) -> Dict[str, LoadedSkill]:
        """Load skills from all configured sources.

        Skills are loaded in source order with later sources overriding
        earlier ones if they contain skills with the same name.

        Returns:
            Dictionary of loaded skills keyed by name.
        """
        if self._loaded:
            return self._skills

        all_skills: Dict[str, LoadedSkill] = {}

        for source_path in self.sources:
            source_skills = _list_skills_from_directory(source_path)
            for skill_metadata in source_skills:
                loaded_skill = LoadedSkill(metadata=skill_metadata)
                all_skills[skill_metadata.name] = loaded_skill

        self._skills = all_skills
        self._loaded = True
        return self._skills

    def get_skill(self, name: str) -> Optional[LoadedSkill]:
        """Get a skill by name.

        Args:
            name: Skill name.

        Returns:
            LoadedSkill or None.
        """
        if not self._loaded:
            self.load_skills()

        return self._skills.get(name)

    def list_skills(self) -> List[SkillMetadata]:
        """List all loaded skills.

        Returns:
            List of skill metadata.
        """
        if not self._loaded:
            self.load_skills()

        return [skill.metadata for skill in self._skills.values()]

    def format_skills_locations(self) -> str:
        """Format skills locations for display in system prompt.

        Returns:
            Formatted string of skills locations.
        """
        locations = []
        for i, source_path in enumerate(self.sources):
            name = Path(source_path.rstrip("/")).name.capitalize()
            suffix = " (higher priority)" if i == len(self.sources) - 1 else ""
            locations.append(f"**{name} Skills**: `{source_path}`{suffix}")
        return "\n".join(locations)

    def format_skills_list(self) -> str:
        """Format skills metadata for display in system prompt.

        Returns:
            Formatted string of skills list.
        """
        if not self._loaded:
            self.load_skills()

        if not self._skills:
            paths = [f"`{source_path}`" for source_path in self.sources]
            return (
                f"(No skills available yet. You can create skills in"
                f" {' or '.join(paths)})"
            )

        lines = []
        for skill in self._skills.values():
            lines.append(f"- **{skill.metadata.name}**: {skill.metadata.description}")
            lines.append(f"  -> Read `{skill.metadata.path}` for full instructions")

        return "\n".join(lines)

    def create_skills_prompt_section(self) -> str:
        """Create the skills section for the system prompt.

        Returns:
            Formatted skills system prompt section.
        """
        skills_locations = self.format_skills_locations()
        skills_list = self.format_skills_list()

        return SKILLS_SYSTEM_PROMPT.format(
            skills_locations=skills_locations,
            skills_list=skills_list,
        )

    def get_skills_by_type(self, skill_type: str) -> List[LoadedSkill]:
        """Get skills by type.

        Args:
            skill_type: Skill type to filter by.

        Returns:
            List of matching skills.
        """
        if not self._loaded:
            self.load_skills()

        return [
            skill
            for skill in self._skills.values()
            if skill.metadata.skill_type == skill_type
        ]

    def match_skills(self, user_input: str) -> List[LoadedSkill]:
        """Find skills that match user input based on description.

        Args:
            user_input: User input string.

        Returns:
            List of matching skills.
        """
        if not self._loaded:
            self.load_skills()

        user_input_lower = user_input.lower()
        matches = []

        for skill in self._skills.values():
            description_lower = skill.metadata.description.lower()

            keywords = self._extract_keywords(description_lower)
            for keyword in keywords:
                if keyword in user_input_lower:
                    matches.append(skill)
                    break

        return matches

    def _extract_keywords(self, description: str) -> List[str]:
        """Extract potential trigger keywords from description.

        Args:
            description: Skill description.

        Returns:
            List of keywords.
        """
        keywords = []

        pattern = (
            r"(?:when|use|for|to)\s+(?:the\s+)?(?:user\s+)?"
            r"(?:asks|requests|wants|needs)?\s*(?:to\s+)?([a-z\s]+?)"
            r"(?:\s*(?:\.|,|;|or|\(|\)|use when|$))"
        )
        matches = re.findall(pattern, description, re.IGNORECASE)

        for match in matches:
            words = [w.strip() for w in match.split() if len(w.strip()) > 2]
            keywords.extend(words)

        return list(set(keywords))
