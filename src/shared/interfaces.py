"""
Core interfaces for robotics system.
Locked Architecture - Layer 3: Robot Control API Layer
"""
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


# ============================================================
# Enums
# ============================================================

class SkillStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class RobotState(Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class RobotAction(Enum):
    MOVE_JOINTS = "move_joints"
    MOVE_POSE = "move_pose"
    MOVE_LINEAR = "move_linear"
    SET_GRIPPER = "set_gripper"
    STOP = "stop"
    EXECUTE_SKILL = "execute_skill"


# ============================================================
# Shared TypedDicts
# ============================================================

class Position3D(TypedDict):
    """3D position representation."""
    x: float
    y: float
    z: float


class Orientation3D(TypedDict):
    """3D orientation representation (roll, pitch, yaw)."""
    roll: float
    pitch: float
    yaw: float


# ============================================================
# Skill → Robot API TypedDicts
# ============================================================

class MoveJointsParams(TypedDict):
    joints: list[float]
    speed: float


class MovePoseParams(TypedDict):
    position: Position3D
    orientation: Orientation3D
    speed: float


class MoveLinearParams(TypedDict):
    target: Position3D
    speed: float


class SetGripperParams(TypedDict):
    position: float  # 0.0 (closed) to 1.0 (open)
    force: float


class StopParams(TypedDict):
    immediate: bool


class ExecuteSkillParams(TypedDict):
    skill_name: str
    parameters: dict


@dataclass
class RobotCommand:
    """Command sent from Skill to Robot API."""
    command_id: str
    command: RobotAction
    params: MoveJointsParams | MovePoseParams | MoveLinearParams | SetGripperParams | StopParams | ExecuteSkillParams


@dataclass
class RobotStatus:
    """Status response from Robot."""
    command_id: str
    state: RobotState
    position: dict
    joints: list[float]
    gripper_state: float
    sensor_data: dict
    message: str


class IRobotAPI:
    """Robot Control API Layer - hardware-agnostic interface."""

    def move_joints(self, joints: list[float], speed: float) -> RobotStatus:
        """Move robot to joint positions."""
        ...

    def move_pose(self, position: dict, orientation: dict, speed: float) -> RobotStatus:
        """Move robot end-effector to pose."""
        ...

    def move_linear(self, target: dict, speed: float) -> RobotStatus:
        """Move robot in a straight line."""
        ...

    def set_gripper(self, position: float, force: float) -> RobotStatus:
        """Control gripper position and force."""
        ...

    def get_world_state(self) -> "WorldState":
        """Get current world state."""
        ...

    def execute_skill(self, skill_name: str, parameters: dict) -> RobotStatus:
        """Execute a named skill with parameters."""
        ...

    def stop(self, immediate: bool = False) -> RobotStatus:
        """Stop robot motion."""
        ...


# Forward reference for WorldState
class WorldState:
    """Placeholder - actual definition in world_state.py"""
    pass
