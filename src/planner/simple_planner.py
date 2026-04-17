"""Simple planner that returns fixed skill sequences."""

from typing import Any


class SimplePlanner:
    """Returns fixed skill sequences based on task keywords."""

    SKILL_SEQUENCES = {
        "pick": ["approach", "grasp"],
        "place": ["move_to", "release"],
        "move": ["move_to"],
        "grasp": ["approach", "grasp"],
        "release": ["move_to", "release"],
    }

    def plan(self, task: str) -> list[dict[str, Any]]:
        """Convert task string to skill sequence.

        Simple rules:
        - "pick" → [approach, grasp]
        - "place" → [move_to, release]
        - "move" → [move_to]
        - "grasp" → [approach, grasp]
        - "release" → [move_to, release]

        Args:
            task: Task description string

        Returns:
            List of skill dictionaries with name and parameters
        """
        task_lower = task.lower()

        # Find matching keyword
        for keyword, skills in self.SKILL_SEQUENCES.items():
            if keyword in task_lower:
                return [{"skill": s, "params": {}} for s in skills]

        # Default: just move_to
        return [{"skill": "move_to", "params": {"target": "default"}}]
