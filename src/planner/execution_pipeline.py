"""Execution pipeline for robot tasks."""

import time
import uuid
from typing import Any, Optional

from .openclaw_planner import OpenClawPlanner


class ExecutionPipeline:
    """Simple execution pipeline: Planner → Skill → RobotAPI → Result"""

    def __init__(self, robot_api: Any, planner: Optional[Any] = None):
        """Initialize pipeline with robot API and optional planner.

        Args:
            robot_api: Robot API instance (must have execute_skill method)
            planner: Planner instance (defaults to OpenClawPlanner)
        """
        self.planner = planner or OpenClawPlanner()
        self.robot_api = robot_api
        self._trajectory_logger = None  # Optional async callback for logging

    def set_trajectory_logger(self, logger_fn):
        """Set callback for trajectory logging.

        Args:
            logger_fn: Async function(trajectory_id, task, skill_sequence, state_changes, final_result, duration_ms)
        """
        self._trajectory_logger = logger_fn

    async def execute(self, task: str, context: Optional[dict] = None) -> dict[str, Any]:
        """Execute a task through the pipeline.

        Args:
            task: Task description string
            context: Optional context dict for planning

        Returns:
            Dictionary with task and results
        """
        context = context or {}
        start_time = time.time()
        trajectory_id = str(uuid.uuid4())

        # 1. Planner generates skill sequence
        skills = await self.planner.plan(task, context)

        # 2. Execute each skill in sequence, tracking state changes
        results = []
        state_changes = []
        for skill in skills:
            before_state = self._get_robot_state()
            result = await self.execute_skill(skill)
            after_state = self._get_robot_state()

            normalized = self._normalize_result(result)
            results.append(normalized)

            # Track state change for this skill
            state_changes.append({
                "skill": skill["skill"],
                "before_state": before_state,
                "after_state": after_state,
                "result": normalized
            })

            if self._is_failure(result):
                break

        duration_ms = (time.time() - start_time) * 1000

        # Build final result
        all_success = all(r.get("status") == "completed" for r in results)
        final_result = {
            "success": all_success,
            "message": "All skills completed successfully" if all_success else "Pipeline failed",
            "outcome": {
                "skills_executed": len(results),
                "skills_completed": sum(1 for r in results if r.get("status") == "completed")
            }
        }

        # Log trajectory if logger is set
        if self._trajectory_logger:
            await self._trajectory_logger(
                trajectory_id=trajectory_id,
                task=task,
                skill_sequence=skills,
                state_changes=state_changes,
                final_result=final_result,
                duration_ms=duration_ms
            )

        return {
            "task": task,
            "trajectory_id": trajectory_id,
            "skill_sequence": skills,
            "state_changes": state_changes,
            "results": results,
            "final_result": final_result,
            "duration_ms": duration_ms
        }

    def _get_robot_state(self) -> dict:
        """Get current robot state for state change tracking."""
        if hasattr(self.robot_api, 'get_world_state'):
            try:
                ws = self.robot_api.get_world_state()
                return {
                    "timestamp": ws.timestamp if hasattr(ws, 'timestamp') else time.time(),
                    "gripper_width": ws.robot.gripper_width if hasattr(ws, 'robot') else 0,
                    "gripper_force": ws.robot.gripper_force if hasattr(ws, 'robot') else 0,
                }
            except:
                pass
        return {"timestamp": time.time()}

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        """Normalize result to dict format."""
        if isinstance(result, dict):
            return result
        if hasattr(result, 'success'):
            # RobotResult dataclass
            return {
                "status": "completed" if result.success else "failed",
                "message": result.message,
                "skill": getattr(result, 'skill', 'unknown'),
            }
        return {"status": "unknown", "message": str(result)}

    def _is_failure(self, result: Any) -> bool:
        """Check if result indicates failure."""
        if isinstance(result, dict):
            return result.get("status") == "failed"
        if hasattr(result, 'success'):
            return not result.success
        return False

    async def execute_skill(self, skill: dict[str, Any]) -> Any:
        """Execute a single skill.

        Args:
            skill: Skill dictionary with 'skill' and 'params' keys

        Returns:
            Execution result from robot API
        """
        # Transform params from planner format to robot API format
        params = self._transform_params(skill["skill"], skill["params"])
        return await self.robot_api.execute_skill(
            skill["skill"], params
        )

    def _transform_params(self, skill_name: str, params: dict) -> dict:
        """Transform planner params to robot API params format."""
        if skill_name == "move_to":
            # Convert target_x/y/z to target {x, y, z}
            if "target_x" in params or "target_y" in params or "target_z" in params:
                target = {
                    "x": params.pop("target_x", 0.0),
                    "y": params.pop("target_y", 0.0),
                    "z": params.pop("target_z", 0.0),
                }
                params["target"] = target
            # Convert target_rx/ry/rz to rotation {rx, ry, rz} if present
            if "target_rx" in params:
                params["rotation"] = {
                    "rx": params.pop("target_rx", 0.0),
                    "ry": params.pop("target_ry", 0.0),
                    "rz": params.pop("target_rz", 0.0),
                }
        return params
