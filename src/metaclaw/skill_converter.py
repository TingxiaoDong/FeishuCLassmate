"""
Skill Schema Converter - Bridges robot skill schemas with MetaClaw SkillManager.

Converts SkillSchema objects (from src/skill/skill_schemas.py) to
MetaClaw's SKILL.md format for integration with MetaClaw's skill evolution.
"""

import logging
from typing import Optional

from src.skill.skill_schemas import SKILL_REGISTRY, SkillSchema, SkillType

logger = logging.getLogger(__name__)


class RobotSkillConverter:
    """
    Converts robot SkillSchema objects to MetaClaw SKILL.md format.

    MetaClaw SkillManager expects:
    - YAML frontmatter: name, description, category
    - Markdown body with skill content
    """

    # Map SkillType to MetaClaw categories (robotics/ prefix per skill-designer)
    # Falls back to skill_type.value if not found
    CATEGORY_MAP = {
        SkillType.MOTION: "robotics/motion",
        SkillType.MANIPULATION: "robotics/manipulation",
        SkillType.SENSING: "robotics/sensing",
        SkillType.COMPOSITE: "robotics/composite",
    }

    # Default category for unknown types
    DEFAULT_CATEGORY = "robotics/task"

    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize converter.

        Args:
            skills_dir: Optional directory to write SKILL.md files
        """
        self._skills_dir = skills_dir

    def schema_to_skill_dict(self, schema: SkillSchema) -> dict:
        """
        Convert a SkillSchema to MetaClaw skill dict format.

        Args:
            schema: Robot SkillSchema object

        Returns:
            Dict with keys: name, description, content, category
        """
        category = self.CATEGORY_MAP.get(schema.skill_type, self.DEFAULT_CATEGORY)

        # Build structured content from schema
        content = self._build_content(schema)

        return {
            "name": schema.name,
            "description": schema.description,
            "category": category,
            "content": content,
            # Preserve original schema info for reference
            "_skill_type": schema.skill_type.value,
            "_preconditions": schema.preconditions,
            "_effects": schema.effects,
            "_safety_constraints": schema.safety_constraints,
        }

    def _build_content(self, schema: SkillSchema) -> str:
        """
        Build markdown content from schema.

        Creates structured documentation including:
        - Overview
        - Preconditions
        - Expected Effects
        - Safety Constraints
        - Example usage
        """
        lines = [
            f"# {schema.name.replace('_', ' ').title()}",
            "",
            f"**Type:** {schema.skill_type.value}",
            "",
            f"## Description",
            "",
            schema.description,
            "",
        ]

        # Preconditions
        if schema.preconditions:
            lines.extend([
                "## Preconditions",
                "",
                "The following conditions must be true before execution:",
                "",
            ])
            for precond in schema.preconditions:
                lines.append(f"- {precond}")
            lines.append("")

        # Effects
        if schema.effects:
            lines.extend([
                "## Expected Effects",
                "",
                "After successful execution:",
                "",
            ])
            for effect in schema.effects:
                lines.append(f"- {effect}")
            lines.append("")

        # Safety Constraints
        if schema.safety_constraints:
            lines.extend([
                "## Safety Constraints",
                "",
                "**WARNING:** Violation of these constraints may result in damage or injury:",
                "",
            ])
            for constraint in schema.safety_constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        # Parameters section (from TypedDict)
        if hasattr(schema.inputs, "__annotations__"):
            lines.extend([
                "## Parameters",
                "",
            ])
            for param_name, param_type in schema.inputs.__annotations__.items():
                lines.append(f"- `{param_name}`: {param_type}")
            lines.append("")

        # Anti-pattern section
        lines.extend([
            "## Anti-pattern",
            "",
            f"Do NOT use this skill when preconditions are not met.",
            f"Always verify safety constraints before execution.",
            "",
        ])

        return "\n".join(lines)

    def schema_to_skill_md(self, schema: SkillSchema) -> str:
        """
        Convert SkillSchema to complete SKILL.md format string.

        Args:
            schema: Robot SkillSchema object

        Returns:
            Complete SKILL.md file content with YAML frontmatter
        """
        skill_dict = self.schema_to_skill_dict(schema)

        # Build YAML frontmatter
        fm_lines = [
            "---",
            f"name: {skill_dict['name']}",
            f"description: {skill_dict['description']}",
            f"category: {skill_dict['category']}",
            "---",
            "",
        ]

        # Combine frontmatter with content
        return "".join(fm_lines) + skill_dict["content"]

    def export_all_skills(self, output_dir: Optional[str] = None) -> dict[str, str]:
        """
        Export all skills from SKILL_REGISTRY to SKILL.md format.

        Args:
            output_dir: Optional directory to write files

        Returns:
            Dict mapping skill name to SKILL.md content
        """
        output_dir = output_dir or self._skills_dir
        results = {}

        for skill_name, schema in SKILL_REGISTRY.items():
            content = self.schema_to_skill_md(schema)
            results[skill_name] = content

            if output_dir:
                self._write_skill_file(skill_name, content, output_dir)

        logger.info(f"[RobotSkillConverter] Exported {len(results)} skills")
        return results

    def _write_skill_file(self, skill_name: str, content: str, output_dir: str) -> None:
        """Write a skill file to the output directory."""
        import os

        skill_dir = os.path.join(output_dir, skill_name)
        os.makedirs(skill_dir, exist_ok=True)

        file_path = os.path.join(skill_dir, "SKILL.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[RobotSkillConverter] Wrote {file_path}")

    def get_skill_for_task(
        self,
        task_description: str,
        skill_manager=None,
    ) -> list[dict]:
        """
        Get relevant skills for a task description.

        If skill_manager provided, uses its retrieval.
        Otherwise uses simple keyword matching.

        Args:
            task_description: Description of the task
            skill_manager: Optional MetaClaw SkillManager

        Returns:
            List of skill dicts relevant to the task
        """
        if skill_manager:
            # Use MetaClaw's retrieval
            return skill_manager.retrieve(task_description, top_k=6)

        # Simple fallback: keyword matching
        task_lower = task_description.lower()
        relevant = []

        for skill_name, schema in SKILL_REGISTRY.items():
            # Check if skill name or type keywords appear in task
            if skill_name in task_lower:
                relevant.append(self.schema_to_skill_dict(schema))
            elif schema.skill_type.value in task_lower:
                relevant.append(self.schema_to_skill_dict(schema))

        # If no matches, return all
        if not relevant:
            for schema in SKILL_REGISTRY.values():
                relevant.append(self.schema_to_skill_dict(schema))

        return relevant


class SkillSchemaUpdater:
    """
    Updates SkillSchema based on MetaClaw evolution feedback.

    When MetaClaw's SkillEvolver generates improved skills,
    this class reconciles them with the robot skill schemas.
    """

    def __init__(self):
        self._evolution_history: list[dict] = []

    def apply_evolved_skill(
        self,
        evolved_skill: dict,
        original_skill_name: str,
    ) -> bool:
        """
        Apply an evolved skill back to the robot schema.

        Args:
            evolved_skill: Skill dict from MetaClaw SkillEvolver
            original_skill_name: Name of the original skill

        Returns:
            True if successfully applied
        """
        # Record the evolution
        self._evolution_history.append({
            "original": original_skill_name,
            "evolved": evolved_skill,
        })

        # In a full implementation, this would update the SKILL_REGISTRY
        # or create a new version of the skill. For now, we log it.
        logger.info(
            f"[SkillSchemaUpdater] Evolution recorded: {original_skill_name} -> {evolved_skill.get('name')}"
        )

        return True

    def get_evolution_history(self) -> list[dict]:
        """Get history of skill evolutions."""
        return self._evolution_history.copy()
