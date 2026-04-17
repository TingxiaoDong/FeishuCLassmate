"""
Base hardware adapter interface.

Defines the contract that all hardware adapters must implement.
This ensures hardware-agnostic communication between the
Robot API layer and actual robot hardware.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypedDict
import time


# ============================================================
# TypedDicts for Adapter Communication
# ============================================================

class JointPositions(TypedDict):
    """Joint position command."""
    positions: list[float]  # radians


class PoseTarget(TypedDict):
    """Cartesian pose target."""
    x: float
    y: float
    z: float
    rx: float  # roll in radians
    ry: float  # pitch in radians
    rz: float  # yaw in radians


class GripperCommand(TypedDict):
    """Gripper control command."""
    position: float  # 0.0 (closed) to 1.0 (open)
    force: float  # 0.0 to 1.0


class StopCommand(TypedDict):
    """Stop motion command."""
    immediate: bool


class ExecuteSkillCommand(TypedDict):
    """Execute a named skill."""
    skill_name: str
    parameters: dict


class JointFeedback(TypedDict):
    """Joint state feedback."""
    positions: list[float]
    velocities: list[float]
    torques: list[float]


class SensorFeedback(TypedDict):
    """Sensor data feedback."""
    imu: dict | None
    force_torque: dict | None
    proximity: dict | None
    gripper: dict | None


class HardwareStatus(TypedDict):
    """Overall hardware status."""
    is_connected: bool
    is_moving: bool
    error_code: int
    error_message: str
    timestamp: float


@dataclass
class HardwareCommandResult:
    """Result of executing a hardware command."""
    success: bool
    command_id: str
    message: str
    positions: list[float] | None = None
    velocities: list[float] | None = None
    sensor_data: dict | None = None
    error_code: int = 0


# ============================================================
# Hardware Adapter Interface
# ============================================================

class IHardwareAdapter(ABC):
    """
    Abstract interface for hardware adapters.

    All robot hardware implementations must implement this interface.
    This ensures the Robot API layer remains hardware-agnostic.

    Implementation Notes:
    - Commands should be non-blocking (return immediately)
    - Use async patterns for actual hardware communication
    - Implement proper error handling and reconnection logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this adapter."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if adapter is connected to hardware."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to hardware.

        Returns:
            True if connection successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from hardware gracefully."""
        pass

    @abstractmethod
    def send_joint_positions(self, positions: list[float], command_id: str) -> HardwareCommandResult:
        """Send joint position command to robot.

        Args:
            positions: Target joint positions in radians
            command_id: Unique identifier for this command

        Returns:
            HardwareCommandResult with execution status
        """
        pass

    @abstractmethod
    def send_pose_target(self, pose: PoseTarget, command_id: str) -> HardwareCommandResult:
        """Send Cartesian pose target to robot.

        Args:
            pose: Target pose (position + orientation)
            command_id: Unique identifier for this command

        Returns:
            HardwareCommandResult with execution status
        """
        pass

    @abstractmethod
    def send_gripper_command(self, command: GripperCommand, command_id: str) -> HardwareCommandResult:
        """Send gripper control command.

        Args:
            command: Gripper position and force
            command_id: Unique identifier for this command

        Returns:
            HardwareCommandResult with execution status
        """
        pass

    @abstractmethod
    def send_stop_command(self, command: StopCommand, command_id: str) -> HardwareCommandResult:
        """Send stop command to robot.

        Args:
            command: Stop command with immediate flag
            command_id: Unique identifier for this command

        Returns:
            HardwareCommandResult with execution status
        """
        pass

    @abstractmethod
    def execute_skill(self, command: ExecuteSkillCommand, command_id: str) -> HardwareCommandResult:
        """Execute a named skill on the robot.

        Args:
            command: Skill name and parameters
            command_id: Unique identifier for this command

        Returns:
            HardwareCommandResult with execution status
        """
        pass

    @abstractmethod
    def get_joint_feedback(self) -> JointFeedback:
        """Get current joint state feedback.

        Returns:
            JointFeedback with positions, velocities, and torques
        """
        pass

    @abstractmethod
    def get_sensor_feedback(self) -> SensorFeedback:
        """Get current sensor data.

        Returns:
            SensorFeedback with IMU, force/torque, proximity, gripper data
        """
        pass

    @abstractmethod
    def get_hardware_status(self) -> HardwareStatus:
        """Get overall hardware status.

        Returns:
            HardwareStatus with connection state, error info, etc.
        """
        pass

    @abstractmethod
    def reset_errors(self) -> bool:
        """Reset any hardware errors and recover.

        Returns:
            True if reset successful, False otherwise
        """
        pass

    @abstractmethod
    def emergency_stop(self) -> HardwareCommandResult:
        """Trigger immediate emergency stop.

        This should stop all motion and disable actuators.

        Returns:
            HardwareCommandResult with emergency stop status
        """
        pass
