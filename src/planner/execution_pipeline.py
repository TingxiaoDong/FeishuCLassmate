"""Execution pipeline for robot tasks."""

from typing import Any

from .simple_planner import SimplePlanner


class ExecutionPipeline:
    """Simple execution pipeline: Planner → Skill → RobotAPI → Result"""

    def __init__(self, robot_api: Any):
        """Initialize pipeline with robot API.

        Args:
            robot_api: Robot API instance (must have execute_skill method)
        """
        self.planner = SimplePlanner()
        self.robot_api = robot_api

    async def execute(self, task: str) -> dict[str, Any]:
        """Execute a task through the pipeline.

        Args:
            task: Task description string

        Returns:
            Dictionary with task and results
        """
        # 1. Planner generates skill sequence
        skills = self.planner.plan(task)

        # 2. Execute each skill in sequence
        results = []
        for skill in skills:
            result = await self.execute_skill(skill)
            results.append(result)
            if result.get("status") == "failed":
                break

        return {"task": task, "results": results}

    async def execute_skill(self, skill: dict[str, Any]) -> dict[str, Any]:
        """Execute a single skill.

        Args:
            skill: Skill dictionary with 'skill' and 'params' keys

        Returns:
            Execution result from robot API
        """
        return await self.robot_api.execute_skill(
            skill["skill"], skill["params"]
        )
