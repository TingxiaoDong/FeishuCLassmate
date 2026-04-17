"""Mock Robot API for testing."""

from typing import Any


class MockRobotAPI:
    """Simple Mock Robot API for testing without real hardware."""

    async def execute_skill(self, skill_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a skill (mock implementation).

        Args:
            skill_name: Name of the skill to execute
            params: Skill parameters

        Returns:
            Mock execution result
        """
        # Simulate execution delay
        import asyncio
        await asyncio.sleep(0.01)

        return {
            "status": "completed",
            "skill": skill_name,
            "params": params,
            "message": f"Mock execution of {skill_name}"
        }

    async def move_to(self, target: str, **kwargs) -> dict[str, Any]:
        """Mock move_to skill."""
        return await self.execute_skill("move_to", {"target": target, **kwargs})

    async def approach(self, **kwargs) -> dict[str, Any]:
        """Mock approach skill."""
        return await self.execute_skill("approach", kwargs)

    async def grasp(self, **kwargs) -> dict[str, Any]:
        """Mock grasp skill."""
        return await self.execute_skill("grasp", kwargs)

    async def release(self, **kwargs) -> dict[str, Any]:
        """Mock release skill."""
        return await self.execute_skill("release", kwargs)
