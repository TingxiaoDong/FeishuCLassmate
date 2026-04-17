"""Robot API module."""
from src.robot_api.robot_api import RobotAPI, IRobotAPI
from src.hardware.simple_adapter import IHardwareAdapter, MockHardwareAdapter
from src.robot_api.collision import (
    CollisionDetector,
    SafetyChecker,
    Vector3,
    BoundingBox,
    Sphere,
    Capsule,
    CollisionObject,
    RobotLink,
)
from src.robot_api.trajectory import (
    Trajectory,
    TrajectoryPoint,
    TrajectoryGenerator,
    TrajectoryValidator,
)
from src.robot_api.debug import (
    RobotDebugger,
    CommandLogEntry,
    TrajectoryVisualizationData,
    SensorDebugSnapshot,
    get_robot_debugger,
)

__all__ = [
    # Core API
    "RobotAPI",
    "IRobotAPI",
    "IHardwareAdapter",
    "MockHardwareAdapter",
    # Collision detection
    "CollisionDetector",
    "SafetyChecker",
    "Vector3",
    "BoundingBox",
    "Sphere",
    "Capsule",
    "CollisionObject",
    "RobotLink",
    # Trajectory
    "Trajectory",
    "TrajectoryPoint",
    "TrajectoryGenerator",
    "TrajectoryValidator",
    # Debugging
    "RobotDebugger",
    "CommandLogEntry",
    "TrajectoryVisualizationData",
    "SensorDebugSnapshot",
    "get_robot_debugger",
]
