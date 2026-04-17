"""
Shared World State representation for robotics system.

This module provides the schema for the world state that is shared across
all layers: Planner, Skill, Robot API, and Hardware.
"""
from dataclasses import dataclass, field
from typing import Optional, TypedDict
from enum import Enum


class Size3D(TypedDict):
    """3D dimension container."""
    x: float
    y: float
    z: float


class ObjectState(Enum):
    """State of a world object."""
    VISIBLE = "visible"
    GRASPED = "grasped"
    PLACED = "placed"
    HIDDEN = "hidden"


@dataclass
class Pose:
    """3D pose representation."""
    x: float
    y: float
    z: float
    rx: float = 0.0  # rotation in radians
    ry: float = 0.0
    rz: float = 0.0


@dataclass
class RobotState:
    """State of the robot."""
    joint_positions: list[float] = field(default_factory=lambda: [0.0] * 6)
    end_effector_pose: Optional[Pose] = None
    gripper_width: float = 0.0
    gripper_force: float = 0.0


@dataclass
class WorldObject:
    """An object in the world."""
    id: str
    type: str  # e.g., "block", "sphere", "tool"
    pose: Pose
    color: Optional[str] = None
    state: ObjectState = ObjectState.VISIBLE
    metadata: dict = field(default_factory=dict)


@dataclass
class Obstacle:
    """An obstacle in the workspace."""
    id: str
    pose: Pose
    shape: str  # e.g., "box", "sphere"
    size: Size3D  # e.g., {"x": 0.1, "y": 0.1, "z": 0.1}


@dataclass
class WorkspaceBounds:
    """Bounds of the robot's workspace."""
    x_min: float = -0.5
    x_max: float = 0.5
    y_min: float = -0.5
    y_max: float = 0.5
    z_min: float = 0.0
    z_max: float = 0.5


@dataclass
class Environment:
    """Environment context."""
    obstacles: list[Obstacle] = field(default_factory=list)
    workspace_bounds: WorkspaceBounds = field(default_factory=WorkspaceBounds)


@dataclass
class WorldState:
    """
    Shared world state representation.

    This is the single source of truth for all layers.
    Updated by Hardware layer, read by all other layers.
    """
    timestamp: float
    robot: RobotState
    objects: list[WorldObject] = field(default_factory=list)
    environment: Environment = field(default_factory=Environment)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        def pose_to_dict(p: Pose) -> dict:
            return {
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "rx": p.rx,
                "ry": p.ry,
                "rz": p.rz,
            }
        return {
            "timestamp": self.timestamp,
            "robot": {
                "joint_positions": self.robot.joint_positions,
                "end_effector_pose": pose_to_dict(self.robot.end_effector_pose) if self.robot.end_effector_pose else None,
                "gripper_width": self.robot.gripper_width,
                "gripper_force": self.robot.gripper_force,
            },
            "objects": [
                {
                    "id": obj.id,
                    "type": obj.type,
                    "pose": pose_to_dict(obj.pose),
                    "color": obj.color,
                    "state": obj.state.value,
                    "metadata": obj.metadata,
                }
                for obj in self.objects
            ],
            "environment": {
                "obstacles": [
                    {
                        "id": obs.id,
                        "pose": pose_to_dict(obs.pose),
                        "shape": obs.shape,
                        "size": obs.size,
                    }
                    for obs in self.environment.obstacles
                ],
                "workspace_bounds": {
                    "x_min": self.environment.workspace_bounds.x_min,
                    "x_max": self.environment.workspace_bounds.x_max,
                    "y_min": self.environment.workspace_bounds.y_min,
                    "y_max": self.environment.workspace_bounds.y_max,
                    "z_min": self.environment.workspace_bounds.z_min,
                    "z_max": self.environment.workspace_bounds.z_max,
                },
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldState":
        """Create from dictionary representation."""
        robot_data = data.get("robot", {})
        ee_pose = robot_data.get("end_effector_pose")
        ee_pose_obj = Pose(**ee_pose) if ee_pose else None

        robot = RobotState(
            joint_positions=robot_data.get("joint_positions", [0.0] * 6),
            end_effector_pose=ee_pose_obj,
            gripper_width=robot_data.get("gripper_width", 0.0),
            gripper_force=robot_data.get("gripper_force", 0.0),
        )

        objects = [
            WorldObject(
                id=obj.get("id", ""),
                type=obj.get("type", ""),
                pose=Pose(**obj.get("pose", {"x": 0, "y": 0, "z": 0})),
                color=obj.get("color"),
                state=ObjectState(obj.get("state", "visible")),
                metadata=obj.get("metadata", {}),
            )
            for obj in data.get("objects", [])
        ]

        env_data = data.get("environment", {})
        bounds_data = env_data.get("workspace_bounds", {})
        bounds = WorkspaceBounds(**bounds_data)

        obstacles = [
            Obstacle(
                id=obs.get("id", ""),
                pose=Pose(**obs.get("pose", {"x": 0, "y": 0, "z": 0})),
                shape=obs.get("shape", ""),
                size=obs.get("size", {}),
            )
            for obs in env_data.get("obstacles", [])
        ]

        environment = Environment(obstacles=obstacles, workspace_bounds=bounds)

        return cls(
            timestamp=data.get("timestamp", 0.0),
            robot=robot,
            objects=objects,
            environment=environment,
        )