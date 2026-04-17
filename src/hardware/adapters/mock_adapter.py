"""
Mock hardware adapter for testing and simulation.

This adapter simulates robot behavior without actual hardware.
Used for development, testing, and simulation.
"""
import uuid
import time
from typing import Optional

from .base import (
    IHardwareAdapter,
    HardwareCommandResult,
    JointFeedback,
    SensorFeedback,
    HardwareStatus,
    JointPositions,
    PoseTarget,
    GripperCommand,
    StopCommand,
    ExecuteSkillCommand,
)
from src.shared.interfaces import RobotAction


class MockHardwareAdapter(IHardwareAdapter):
    """
    Mock hardware adapter for testing and simulation.

    Simulates robot behavior without actual hardware connections.
    """

    def __init__(self):
        self._name = "mock_hardware"
        self._connected = True  # Mock is always "connected"
        self._joint_positions = [0.0] * 6
        self._joint_velocities = [0.0] * 6
        self._joint_torques = [0.0] * 6
        self._gripper_position = 0.0
        self._gripper_force = 0.0
        self._end_effector_pose = {"x": 0.0, "y": 0.0, "z": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}
        self._is_moving = False
        self._error_code = 0
        self._error_message = ""

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Simulate connection."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def send_joint_positions(self, positions: list[float], command_id: str) -> HardwareCommandResult:
        """Simulate joint position command."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to hardware",
                error_code=1001,
            )

        self._is_moving = True
        self._joint_positions = positions.copy()

        # Simulate motion completion
        self._is_moving = False

        return HardwareCommandResult(
            success=True,
            command_id=command_id,
            message=f"Moved to joints: {positions}",
            positions=self._joint_positions.copy(),
            velocities=self._joint_velocities.copy(),
        )

    def send_pose_target(self, pose: PoseTarget, command_id: str) -> HardwareCommandResult:
        """Simulate pose target command."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to hardware",
                error_code=1001,
            )

        self._is_moving = True
        self._end_effector_pose = {"x": pose["x"], "y": pose["y"], "z": pose["z"],
                                   "rx": pose["rx"], "ry": pose["ry"], "rz": pose["rz"]}

        # Simulate motion completion
        self._is_moving = False

        return HardwareCommandResult(
            success=True,
            command_id=command_id,
            message=f"Moved to pose: ({pose['x']}, {pose['y']}, {pose['z']})",
            positions=self._joint_positions.copy(),
        )

    def send_gripper_command(self, command: GripperCommand, command_id: str) -> HardwareCommandResult:
        """Simulate gripper command."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to hardware",
                error_code=1001,
            )

        self._gripper_position = max(0.0, min(1.0, command["position"]))
        self._gripper_force = max(0.0, min(1.0, command["force"]))

        return HardwareCommandResult(
            success=True,
            command_id=command_id,
            message=f"Gripper set: position={self._gripper_position}, force={self._gripper_force}",
            sensor_data={"gripper_position": self._gripper_position, "gripper_force": self._gripper_force},
        )

    def send_stop_command(self, command: StopCommand, command_id: str) -> HardwareCommandResult:
        """Simulate stop command."""
        self._is_moving = False
        self._joint_velocities = [0.0] * 6

        return HardwareCommandResult(
            success=True,
            command_id=command_id,
            message="Robot stopped",
        )

    def execute_skill(self, command: ExecuteSkillCommand, command_id: str) -> HardwareCommandResult:
        """Simulate skill execution."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to hardware",
                error_code=1001,
            )

        skill_name = command["skill_name"]

        # Route to appropriate mock action
        if skill_name == "move_to":
            x = command["parameters"].get("x", 0.0)
            y = command["parameters"].get("y", 0.0)
            z = command["parameters"].get("z", 0.0)
            self._end_effector_pose = {"x": x, "y": y, "z": z, "rx": 0.0, "ry": 0.0, "rz": 0.0}

        elif skill_name == "grasp":
            self._gripper_position = 0.0
            self._gripper_force = command["parameters"].get("force", 0.5)

        elif skill_name == "release":
            self._gripper_position = 1.0
            self._gripper_force = 0.0

        return HardwareCommandResult(
            success=True,
            command_id=command_id,
            message=f"Skill '{skill_name}' executed",
        )

    def get_joint_feedback(self) -> JointFeedback:
        """Get simulated joint feedback."""
        return JointFeedback(
            positions=self._joint_positions.copy(),
            velocities=self._joint_velocities.copy(),
            torques=self._joint_torques.copy(),
        )

    def get_sensor_feedback(self) -> SensorFeedback:
        """Get simulated sensor feedback."""
        return SensorFeedback(
            imu={
                "ax": 0.0, "ay": 0.0, "az": 9.81,
                "gx": 0.0, "gy": 0.0, "gz": 0.0,
                "temperature": 25.0,
            },
            force_torque={"fx": 0.0, "fy": 0.0, "fz": 0.0, "tx": 0.0, "ty": 0.0, "tz": 0.0},
            proximity={"distance": 0.5, "is_object_detected": False},
            gripper={"width": self._gripper_position, "force": self._gripper_force},
        )

    def get_hardware_status(self) -> HardwareStatus:
        """Get simulated hardware status."""
        return HardwareStatus(
            is_connected=self._connected,
            is_moving=self._is_moving,
            error_code=self._error_code,
            error_message=self._error_message,
            timestamp=time.time(),
        )

    def reset_errors(self) -> bool:
        """Reset simulated errors."""
        self._error_code = 0
        self._error_message = ""
        return True

    def emergency_stop(self) -> HardwareCommandResult:
        """Simulate emergency stop."""
        self._is_moving = False
        self._joint_velocities = [0.0] * 6
        self._gripper_force = 0.0  # Release gripper

        return HardwareCommandResult(
            success=True,
            command_id="emergency_stop",
            message="EMERGENCY STOP ACTIVATED",
            error_code=9999,
        )
