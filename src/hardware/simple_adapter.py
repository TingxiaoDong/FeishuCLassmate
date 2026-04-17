"""
Simple Hardware Adapter for Robot Control API.

This module contains the simple hardware adapter interface and mock implementation.
Per locked architecture: Layer 4 - Hardware Abstraction Layer

This provides the interface expected by the RobotAPI layer (execute, get_world_state).
"""
import time
from typing import Union, TypedDict

from src.shared.interfaces import RobotState, RobotStatus


# ============================================================
# TypedDicts for Simple Hardware Adapter
# ============================================================

class MoveJointsParams(TypedDict):
    joints: list[float]
    speed: float


class MovePoseParams(TypedDict):
    position: dict
    orientation: dict
    speed: float


class MoveLinearParams(TypedDict):
    target: dict
    speed: float


class SetGripperParams(TypedDict):
    position: float
    force: float


class StopParams(TypedDict):
    immediate: bool


class ExecuteSkillParams(TypedDict):
    skill_name: str
    parameters: dict


# Union type for all command params
CommandParams = Union[
    MoveJointsParams,
    MovePoseParams,
    MoveLinearParams,
    SetGripperParams,
    StopParams,
    ExecuteSkillParams,
]


# ============================================================
# IHardwareAdapter Interface (Simple Version)
# ============================================================

class IHardwareAdapter:
    """Interface for hardware adapters (simple version for RobotAPI)."""

    def execute(
        self,
        command_id: str,
        action: "RobotAction",
        params: CommandParams,
    ) -> RobotStatus:
        """Execute a robot command."""
        ...

    def get_world_state(self) -> "WorldState":
        """Get current world state."""
        ...


# ============================================================
# MockHardwareAdapter (Simple Version)
# ============================================================

class MockHardwareAdapter(IHardwareAdapter):
    """
    Mock hardware adapter for testing and simulation.

    This adapter simulates robot behavior without actual hardware.
    Used by RobotAPI layer for testing.
    """

    def execute(
        self,
        command_id: str,
        action: "RobotAction",
        params: CommandParams,
    ) -> RobotStatus:
        """Simulate command execution."""
        from src.shared.interfaces import RobotAction as RA

        if action == RA.MOVE_JOINTS:
            joints = params["joints"]
            return RobotStatus(
                command_id=command_id,
                state=RobotState.COMPLETED,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                joints=joints,
                gripper_state=0.0,
                sensor_data={},
                message=f"Moved to joints: {joints}",
            )

        elif action == RA.MOVE_POSE:
            position = params["position"]
            return RobotStatus(
                command_id=command_id,
                state=RobotState.COMPLETED,
                position=position,
                joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                gripper_state=0.0,
                sensor_data={},
                message=f"Moved to pose: {position}",
            )

        elif action == RA.MOVE_LINEAR:
            target = params["target"]
            return RobotStatus(
                command_id=command_id,
                state=RobotState.COMPLETED,
                position=target,
                joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                gripper_state=0.0,
                sensor_data={},
                message=f"Linear move to: {target}",
            )

        elif action == RA.SET_GRIPPER:
            position = params["position"]
            return RobotStatus(
                command_id=command_id,
                state=RobotState.COMPLETED,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                gripper_state=position,
                sensor_data={},
                message=f"Gripper set to: {position}",
            )

        elif action == RA.STOP:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.IDLE,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                gripper_state=0.0,
                sensor_data={},
                message="Stopped",
            )

        elif action == RA.EXECUTE_SKILL:
            skill_name = params["skill_name"]
            return RobotStatus(
                command_id=command_id,
                state=RobotState.COMPLETED,
                position={"x": 0.0, "y": 0.0, "z": 0.0},
                joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                gripper_state=0.0,
                sensor_data={},
                message=f"Skill '{skill_name}' executed",
            )

        return RobotStatus(
            command_id=command_id,
            state=RobotState.ERROR,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            gripper_state=0.0,
            sensor_data={},
            message=f"Unknown action: {action}",
        )

    def get_world_state(self) -> "WorldState":
        """Return mock world state."""
        from src.shared.world_state import WorldState, RobotState as WSRobotState, Pose, Environment, WorkspaceBounds

        return WorldState(
            timestamp=time.time(),
            robot=WSRobotState(
                joint_positions=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                end_effector_pose=Pose(x=0.0, y=0.0, z=0.0),
                gripper_width=0.0,
                gripper_force=0.0,
            ),
            objects=[],
            environment=Environment(workspace_bounds=WorkspaceBounds()),
        )


# Forward reference placeholder
class WorldState:
    """Placeholder - actual definition in world_state.py"""
    pass
