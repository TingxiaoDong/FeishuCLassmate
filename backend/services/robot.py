"""
Robot service - wraps RobotAPI for backend consumption.
Performance optimized with fire-and-forget logging.
"""
import sys
import os
import uuid
import json
import asyncio
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.robot_api.robot_api import RobotAPI
from src.hardware.adapters.temi_adapter import TemiAdapter
from src.shared.interfaces import RobotStatus as RobotStatusEnum, RobotState
from backend.db.database import get_db
from backend.models.schemas import (
    MoveJointsRequest,
    MovePoseRequest,
    MoveLinearRequest,
    SetGripperRequest,
    StopRequest,
    ExecuteSkillRequest,
    RobotStatusResponse,
    WorldStateResponse,
    RobotState,
)


class RobotService:
    """Service layer for robot control."""

    def __init__(self):
        """Initialize robot service with RobotAPI."""
        # Use TemiAdapter with the robot's IP address
        temi_adapter = TemiAdapter(ip="192.168.31.121", port=8175)
        self._robot_api = RobotAPI(hardware_adapter=temi_adapter)
        # Pre-cached UUID generator for reduced allocations
        self._uuid_cache = [str(uuid.uuid4()) for _ in range(10)]
        self._uuid_index = 0

    async def move_joints(self, request: MoveJointsRequest) -> RobotStatusResponse:
        """Execute move_joints command."""
        result = self._robot_api.move_joints(request.joints, request.speed)
        await self._log_skill_execution("move_joints", {"joints": request.joints, "speed": request.speed}, result)
        return self._to_response(result)

    async def move_pose(self, request: MovePoseRequest) -> RobotStatusResponse:
        """Execute move_pose command."""
        result = self._robot_api.move_pose(
            {"x": request.position.x, "y": request.position.y, "z": request.position.z},
            {"roll": request.orientation.roll, "pitch": request.orientation.pitch, "yaw": request.orientation.yaw},
            request.speed
        )
        await self._log_skill_execution("move_pose", request.model_dump(), result)
        return self._to_response(result)

    async def move_linear(self, request: MoveLinearRequest) -> RobotStatusResponse:
        """Execute move_linear command."""
        result = self._robot_api.move_linear(
            {"x": request.target.x, "y": request.target.y, "z": request.target.z},
            request.speed
        )
        await self._log_skill_execution("move_linear", request.model_dump(), result)
        return self._to_response(result)

    async def set_gripper(self, request: SetGripperRequest) -> RobotStatusResponse:
        """Execute set_gripper command."""
        result = self._robot_api.set_gripper(request.position, request.force)
        await self._log_skill_execution("set_gripper", request.model_dump(), result)
        return self._to_response(result)

    async def stop(self, request: StopRequest) -> RobotStatusResponse:
        """Execute stop command."""
        result = self._robot_api.stop(request.immediate)
        await self._log_skill_execution("stop", {"immediate": request.immediate}, result)
        return self._to_response(result)

    async def execute_skill(self, request: ExecuteSkillRequest) -> RobotStatusResponse:
        """Execute a named skill."""
        result = self._robot_api.execute_skill(request.skill_name, request.parameters)
        await self._log_skill_execution(request.skill_name, request.parameters, result)
        return self._to_response(result)

    async def get_status(self) -> RobotStatusResponse:
        """Get current robot status."""
        world_state = self._robot_api.get_world_state()
        return RobotStatusResponse(
            command_id=str(uuid.uuid4()),
            state=RobotState.IDLE,
            position={"x": world_state.robot.end_effector_pose.x if world_state.robot.end_effector_pose else 0.0,
                     "y": world_state.robot.end_effector_pose.y if world_state.robot.end_effector_pose else 0.0,
                     "z": world_state.robot.end_effector_pose.z if world_state.robot.end_effector_pose else 0.0},
            joints=world_state.robot.joint_positions,
            gripper_state=world_state.robot.gripper_width,
            sensor_data={},
            message="Current status"
        )

    async def get_world_state(self) -> WorldStateResponse:
        """Get current world state."""
        world_state = self._robot_api.get_world_state()
        await self._save_world_state(world_state)
        return WorldStateResponse(
            timestamp=world_state.timestamp,
            robot=world_state.to_dict()["robot"],
            objects=world_state.to_dict()["objects"],
            environment=world_state.to_dict()["environment"]
        )

    def _to_response(self, status: RobotStatusEnum) -> RobotStatusResponse:
        """Convert RobotStatus to RobotStatusResponse."""
        return RobotStatusResponse(
            command_id=status.command_id,
            state=RobotState(status.state.value),
            position=status.position,
            joints=status.joints,
            gripper_state=status.gripper_state,
            sensor_data=status.sensor_data,
            message=status.message
        )

    async def _log_skill_execution(self, skill_name: str, parameters: dict, result: RobotStatusEnum):
        """Log skill execution to database (fire-and-forget for latency)."""
        # Reuse cached UUID to reduce allocations
        self._uuid_index = (self._uuid_index + 1) % len(self._uuid_cache)
        execution_id = self._uuid_cache[self._uuid_index]

        # Fire-and-forget: don't await database write
        asyncio.create_task(self._persist_skill_execution(
            execution_id, skill_name, parameters, result.state.value, result.message
        ))

    async def _persist_skill_execution(self, execution_id: str, skill_name: str,
                                       parameters: dict, state_value: str, message: str):
        """Persist skill execution to database (called as background task)."""
        try:
            async with get_db() as db:
                await db.execute(
                    """
                    INSERT INTO skill_executions (id, skill_name, parameters, status, result, completed_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (execution_id, skill_name, json.dumps(parameters),
                     state_value, json.dumps({"message": message}))
                )
                await db.commit()
        except Exception:
            # Silently ignore logging failures to not affect main path
            pass

    async def _save_world_state(self, world_state):
        """Save world state snapshot to database (fire-and-forget)."""
        state_dict = world_state.to_dict()
        timestamp = world_state.timestamp
        # Fire-and-forget: don't await database write
        asyncio.create_task(self._persist_world_state(timestamp, state_dict))

    async def _persist_world_state(self, timestamp: float, state_dict: dict):
        """Persist world state to database (called as background task)."""
        try:
            async with get_db() as db:
                await db.execute(
                    "INSERT INTO world_state_history (timestamp, state_json) VALUES (?, ?)",
                    (timestamp, json.dumps(state_dict))
                )
                await db.commit()
        except Exception:
            # Silently ignore logging failures
            pass


# Singleton instance
_robot_service: Optional[RobotService] = None


def get_robot_service() -> RobotService:
    """Get robot service singleton."""
    global _robot_service
    if _robot_service is None:
        _robot_service = RobotService()
    return _robot_service
