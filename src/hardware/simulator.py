"""
Hardware/Simulator Layer.

Implements the IRobotAPI interface for simulation purposes.
This is a mock implementation for testing without real hardware.

Per locked architecture: Robot API → Hardware/Simulator
"""
import time
import math
from typing import Optional
from src.shared.interfaces import (
    IRobotAPI,
    RobotCommand,
    RobotStatus,
    RobotAction,
    MoveJointsParams,
    MovePoseParams,
    MoveLinearParams,
    SetGripperParams,
    StopParams,
    ExecuteSkillParams,
    RobotState,
)
from src.shared.world_state import WorldState, RobotState as WS_RobotState, Pose
from src.robot_api.collision import CollisionDetector, SafetyChecker, Vector3, RobotLink


class RobotSimulator(IRobotAPI):
    """
    Simulated robot implementing IRobotAPI interface.

    Tracks internal state and simulates motion without real hardware.
    Performance optimized with cached pose dict and in-place updates.
    """

    __slots__ = ('_joint_positions', '_end_effector_pose', '_gripper_width',
                 '_gripper_force', '_state', '_sensor_data', '_command_count',
                 '_cached_pose_dict', '_collision_detector', '_safety_checker',
                 '_safety_enabled')

    # Pre-allocated constants for hot paths
    _ZERO_JOINTS: list[float] = [0.0] * 6
    _EMPTY_OBJECTS: list = []
    _EMPTY_ENV: None = None

    def __init__(self, safety_enabled: bool = True):
        # Internal robot state
        self._joint_positions: list[float] = [0.0] * 6
        self._end_effector_pose: Pose = Pose(x=0.0, y=0.0, z=0.0)
        self._gripper_width: float = 0.0
        self._gripper_force: float = 0.0
        self._state: RobotState = RobotState.IDLE
        self._sensor_data: dict = {}
        self._command_count: int = 0
        # Cached pose dict for avoid repeated allocations
        self._cached_pose_dict: dict = {
            "x": 0.0, "y": 0.0, "z": 0.0,
            "rx": 0.0, "ry": 0.0, "rz": 0.0
        }
        # Safety monitoring components
        self._collision_detector: CollisionDetector = CollisionDetector()
        self._safety_checker: SafetyChecker = SafetyChecker(self._collision_detector)
        self._safety_enabled: bool = safety_enabled

    def move_joints(self, joints: list[float], speed: float) -> RobotStatus:
        """Move robot to specified joint positions."""
        self._command_count += 1
        command_id = f"move_joints_{self._command_count}"

        if self._state == RobotState.ERROR:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message="Robot is in error state"
            )

        # Safety check before execution
        is_safe, safety_msg = self._check_safety(joints)
        if not is_safe:
            self._state = RobotState.ERROR
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message=f"Safety check failed: {safety_msg}"
            )

        self._state = RobotState.EXECUTING

        # Simulate joint movement - in-place update for speed
        for i, v in enumerate(joints):
            self._joint_positions[i] = v

        # Calculate end-effector pose from joints (simplified kinematics)
        self._update_end_effector_from_joints()

        self._state = RobotState.COMPLETED

        return RobotStatus(
            command_id=command_id,
            state=RobotState.COMPLETED,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message=f"Moved joints to {joints}"
        )

    def move_pose(self, position: dict, orientation: dict, speed: float) -> RobotStatus:
        """Move robot end-effector to pose."""
        self._command_count += 1
        command_id = f"move_pose_{self._command_count}"

        if self._state == RobotState.ERROR:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message="Robot is in error state"
            )

        self._state = RobotState.EXECUTING

        # Update end-effector pose
        self._end_effector_pose = Pose(
            x=position.get("x", 0.0),
            y=position.get("y", 0.0),
            z=position.get("z", 0.0),
            rx=orientation.get("roll", 0.0),
            ry=orientation.get("pitch", 0.0),
            rz=orientation.get("yaw", 0.0)
        )

        # Update joints based on pose (simplified inverse kinematics)
        self._update_joints_from_pose()

        self._state = RobotState.COMPLETED

        return RobotStatus(
            command_id=command_id,
            state=RobotState.COMPLETED,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message=f"Moved to pose {position}"
        )

    def move_linear(self, target: dict, speed: float) -> RobotStatus:
        """Move robot end-effector in a straight line."""
        self._command_count += 1
        command_id = f"move_linear_{self._command_count}"

        if self._state == RobotState.ERROR:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message="Robot is in error state"
            )

        # Safety check for target position
        x = target.get("x", self._end_effector_pose.x)
        y = target.get("y", self._end_effector_pose.y)
        z = target.get("z", self._end_effector_pose.z)
        is_safe, safety_msg = self._check_workspace_safety(x, y, z)
        if not is_safe:
            self._state = RobotState.ERROR
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message=f"Safety check failed: {safety_msg}"
            )

        self._state = RobotState.EXECUTING

        # Update end-effector position in a straight line
        self._end_effector_pose.x = target.get("x", self._end_effector_pose.x)
        self._end_effector_pose.y = target.get("y", self._end_effector_pose.y)
        self._end_effector_pose.z = target.get("z", self._end_effector_pose.z)

        # Update joints
        self._update_joints_from_pose()

        self._state = RobotState.COMPLETED

        return RobotStatus(
            command_id=command_id,
            state=RobotState.COMPLETED,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message=f"Linear move to {target}"
        )

    def set_gripper(self, position: float, force: float) -> RobotStatus:
        """Control gripper position and force."""
        self._command_count += 1
        command_id = f"set_gripper_{self._command_count}"

        if self._state == RobotState.ERROR:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message="Robot is in error state"
            )

        self._state = RobotState.EXECUTING

        # Clamp gripper position
        self._gripper_width = max(0.0, min(1.0, position))
        self._gripper_force = max(0.0, min(1.0, force))

        self._state = RobotState.COMPLETED

        return RobotStatus(
            command_id=command_id,
            state=RobotState.COMPLETED,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message=f"Gripper set: position={self._gripper_width}, force={self._gripper_force}"
        )

    def get_world_state(self) -> WorldState:
        """Get current world state."""
        ws_robot = WS_RobotState(
            joint_positions=self._joint_positions,
            end_effector_pose=self._end_effector_pose,
            gripper_width=self._gripper_width,
            gripper_force=self._gripper_force
        )

        return WorldState(
            timestamp=time.time(),
            robot=ws_robot,
            objects=self._EMPTY_OBJECTS,
            environment=self._EMPTY_ENV
        )

    def execute_skill(self, skill_name: str, parameters: dict) -> RobotStatus:
        """Execute a named skill with parameters."""
        self._command_count += 1
        command_id = f"execute_skill_{skill_name}_{self._command_count}"

        if self._state == RobotState.ERROR:
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message="Robot is in error state"
            )

        self._state = RobotState.EXECUTING

        # Route skill execution to appropriate method
        if skill_name == "move_to":
            x = parameters.get("x", 0.0)
            y = parameters.get("y", 0.0)
            z = parameters.get("z", 0.0)
            return self.move_linear({"x": x, "y": y, "z": z}, parameters.get("speed", 1.0))

        elif skill_name == "grasp":
            return self.set_gripper(0.0, parameters.get("force", 0.5))

        elif skill_name == "release":
            return self.set_gripper(1.0, 0.0)

        elif skill_name == "lift":
            height = parameters.get("height", self._end_effector_pose.z)
            return self.move_linear(
                {"x": self._end_effector_pose.x, "y": self._end_effector_pose.y, "z": height},
                parameters.get("speed", 1.0)
            )

        elif skill_name == "place":
            x = parameters.get("x", self._end_effector_pose.x)
            y = parameters.get("y", self._end_effector_pose.y)
            z = parameters.get("z", self._end_effector_pose.z)
            return self.move_linear({"x": x, "y": y, "z": z}, parameters.get("speed", 1.0))

        else:
            self._state = RobotState.ERROR
            return RobotStatus(
                command_id=command_id,
                state=RobotState.ERROR,
                position=self._pose_to_dict(),
                joints=self._joint_positions,
                gripper_state=self._gripper_width,
                sensor_data=self._sensor_data,
                message=f"Unknown skill: {skill_name}"
            )

    def stop(self, immediate: bool = False) -> RobotStatus:
        """Stop robot motion."""
        self._command_count += 1
        command_id = f"stop_{self._command_count}"

        self._state = RobotState.IDLE

        return RobotStatus(
            command_id=command_id,
            state=RobotState.IDLE,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message="Robot stopped"
        )

    def emergency_stop(self) -> RobotStatus:
        """Trigger emergency stop."""
        self._state = RobotState.ERROR
        self._safety_checker.trigger_emergency_stop()
        return RobotStatus(
            command_id="emergency_stop",
            state=RobotState.ERROR,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message="EMERGENCY STOP ACTIVATED"
        )

    def reset(self) -> RobotStatus:
        """Reset robot to default state."""
        # Use pre-allocated constant and clear cached dict
        self._joint_positions = self._ZERO_JOINTS.copy()
        self._end_effector_pose.x = 0.0
        self._end_effector_pose.y = 0.0
        self._end_effector_pose.z = 0.0
        self._gripper_width = 0.0
        self._gripper_force = 0.0
        self._state = RobotState.IDLE
        # Reset emergency stop
        self._safety_checker.reset_emergency_stop()
        # Reset cached pose dict
        self._cached_pose_dict["x"] = 0.0
        self._cached_pose_dict["y"] = 0.0
        self._cached_pose_dict["z"] = 0.0
        self._cached_pose_dict["rx"] = 0.0
        self._cached_pose_dict["ry"] = 0.0
        self._cached_pose_dict["rz"] = 0.0

        return RobotStatus(
            command_id="reset",
            state=RobotState.IDLE,
            position=self._cached_pose_dict,
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message="Robot reset to default state"
        )

    # ============================================================
    # Internal helper methods
    # ============================================================

    def _get_robot_links(self) -> list[RobotLink]:
        """Create robot links from current joint positions for collision checking."""
        links = []
        # Simplified robot link representation based on joint angles
        # In reality this would use proper robot geometry
        for i in range(len(self._joint_positions) - 1):
            start_x = sum(self._joint_positions[:i+1]) * 0.1 if i > 0 else 0.0
            end_x = sum(self._joint_positions[:i+2]) * 0.1
            links.append(RobotLink(
                name=f"link_{i}",
                start_position=Vector3(start_x, 0.0, 0.0),
                end_position=Vector3(end_x, 0.0, 0.0),
                radius=0.05
            ))
        return links

    def _check_safety(self, target_positions: list[float] | None = None) -> tuple[bool, str]:
        """Run safety check before command execution."""
        if not self._safety_enabled:
            return True, ""

        if self._safety_checker.emergency_stop_active:
            return False, "Emergency stop is active"

        # Create temporary joint positions for safety check
        check_positions = target_positions if target_positions else self._joint_positions
        temp_joints = self._joint_positions.copy()
        for i, v in enumerate(check_positions):
            if i < len(self._joint_positions):
                self._joint_positions[i] = v

        self._collision_detector.set_robot_links(self._get_robot_links())
        has_collision, collisions = self._collision_detector.check_collision()

        # Restore joint positions
        self._joint_positions = temp_joints

        if has_collision:
            return False, "; ".join(collisions)

        return True, ""

    def _check_workspace_safety(self, x: float, y: float, z: float) -> tuple[bool, str]:
        """Check if target position is within workspace bounds."""
        if not self._safety_enabled:
            return True, ""
        return self._safety_checker.validate_workspace_target(x, y, z)

    def _pose_to_dict(self) -> dict:
        """Convert pose to dictionary (cached, in-place update)."""
        self._cached_pose_dict["x"] = self._end_effector_pose.x
        self._cached_pose_dict["y"] = self._end_effector_pose.y
        self._cached_pose_dict["z"] = self._end_effector_pose.z
        self._cached_pose_dict["rx"] = self._end_effector_pose.rx
        self._cached_pose_dict["ry"] = self._end_effector_pose.ry
        self._cached_pose_dict["rz"] = self._end_effector_pose.rz
        return self._cached_pose_dict

    def _update_end_effector_from_joints(self) -> None:
        """Simplified forward kinematics: update end-effector pose from joint positions."""
        # Very simplified FK - in reality this would be proper robot kinematics
        self._end_effector_pose.x = sum(self._joint_positions[:3]) * 0.1
        self._end_effector_pose.y = self._joint_positions[3] * 0.1 if len(self._joint_positions) > 3 else 0.0
        self._end_effector_pose.z = self._joint_positions[4] * 0.1 if len(self._joint_positions) > 4 else 0.1

    def _update_joints_from_pose(self) -> None:
        """Simplified inverse kinematics: update joints from end-effector pose."""
        # Very simplified IK - in reality this would be proper inverse kinematics
        self._joint_positions[0] = self._end_effector_pose.x / 0.1 if self._end_effector_pose.x != 0 else 0.0
        self._joint_positions[1] = self._end_effector_pose.y / 0.1 if self._end_effector_pose.y != 0 else 0.0
        self._joint_positions[2] = self._end_effector_pose.z / 0.1 if self._end_effector_pose.z != 0 else 0.0


# Singleton instance for easy access
_default_robot: Optional[RobotSimulator] = None


def get_robot_simulator() -> RobotSimulator:
    """Get the default robot simulator instance."""
    global _default_robot
    if _default_robot is None:
        _default_robot = RobotSimulator()
    return _default_robot
