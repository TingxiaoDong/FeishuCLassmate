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


class RobotSimulator(IRobotAPI):
    """
    Simulated robot implementing IRobotAPI interface.

    Tracks internal state and simulates motion without real hardware.
    """

    def __init__(self):
        # Internal robot state
        self._joint_positions: list[float] = [0.0] * 6
        self._end_effector_pose: Pose = Pose(x=0.0, y=0.0, z=0.0)
        self._gripper_width: float = 0.0
        self._gripper_force: float = 0.0
        self._state: RobotState = RobotState.IDLE
        self._sensor_data: dict = {}
        self._command_count: int = 0

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

        self._state = RobotState.EXECUTING

        # Simulate joint movement
        self._joint_positions = joints.copy()

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
            objects=[],
            environment=None
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
        self._joint_positions = [0.0] * 6
        self._end_effector_pose = Pose(x=0.0, y=0.0, z=0.0)
        self._gripper_width = 0.0
        self._gripper_force = 0.0
        self._state = RobotState.IDLE

        return RobotStatus(
            command_id="reset",
            state=RobotState.IDLE,
            position=self._pose_to_dict(),
            joints=self._joint_positions,
            gripper_state=self._gripper_width,
            sensor_data=self._sensor_data,
            message="Robot reset to default state"
        )

    # ============================================================
    # Internal helper methods
    # ============================================================

    def _pose_to_dict(self) -> dict:
        """Convert pose to dictionary."""
        return {
            "x": self._end_effector_pose.x,
            "y": self._end_effector_pose.y,
            "z": self._end_effector_pose.z,
            "rx": self._end_effector_pose.rx,
            "ry": self._end_effector_pose.ry,
            "rz": self._end_effector_pose.rz
        }

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
