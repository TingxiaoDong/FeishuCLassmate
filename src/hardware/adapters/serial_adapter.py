"""
Serial hardware adapter for robots with serial communication.

Provides connection to robots that use serial protocols (RS-232, USB-Serial).
"""
import threading
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


class SerialHardwareAdapter(IHardwareAdapter):
    """
    Hardware adapter for serial communication.

    Supports RS-232 and USB-Serial connections to robot controllers.

    Note: This is a stub implementation. Actual serial communication
    requires the pyserial library and specific robot protocol implementation.
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        timeout: float = 1.0,
    ):
        """
        Initialize serial adapter.

        Args:
            port: Serial port device path
            baudrate: Communication speed
            timeout: Read timeout in seconds
        """
        self._name = f"serial_{port}"
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial = None  # Would be serial.Serial in actual implementation
        self._connected = False
        self._is_moving = False
        self._error_code = 0
        self._error_message = ""
        self._lock = threading.Lock()

        # Simulated state
        self._joint_positions = [0.0] * 6
        self._joint_velocities = [0.0] * 6
        self._joint_torques = [0.0] * 6

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """
        Establish serial connection to robot.

        Returns:
            True if connection successful
        """
        with self._lock:
            try:
                # Actual implementation would use:
                # import serial
                # self._serial = serial.Serial(
                #     port=self._port,
                #     baudrate=self._baudrate,
                #     timeout=self._timeout,
                # )
                # self._connected = self._serial.is_open

                # Stub: always succeeds
                self._connected = True
                return True
            except Exception as e:
                self._error_message = f"Connection failed: {str(e)}"
                self._error_code = 1001
                return False

    def disconnect(self) -> None:
        """Close serial connection."""
        with self._lock:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
            self._connected = False
            self._serial = None

    def send_joint_positions(self, positions: list[float], command_id: str) -> HardwareCommandResult:
        """Send joint positions over serial."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                # Format: "$J," + positions + "*checksum\r\n"
                cmd = self._format_joint_command(positions)
                self._send_raw(cmd)

                # Wait for acknowledgment
                response = self._read_response()

                if self._validate_response(response):
                    self._joint_positions = positions.copy()
                    self._is_moving = True
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message=f"Joints sent: {positions}",
                        positions=self._joint_positions.copy(),
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message="Invalid response from robot",
                        error_code=1002,
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=1003,
                )

    def send_pose_target(self, pose: PoseTarget, command_id: str) -> HardwareCommandResult:
        """Send Cartesian pose target over serial."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                # Format: "$P," + x + "," + y + "," + z + "," + rx + "," + ry + "," + rz + "*checksum\r\n"
                cmd = self._format_pose_command(pose)
                self._send_raw(cmd)

                response = self._read_response()

                if self._validate_response(response):
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message=f"Pose sent: ({pose['x']}, {pose['y']}, {pose['z']})",
                        positions=self._joint_positions.copy(),
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message="Invalid response from robot",
                        error_code=1002,
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=1003,
                )

    def send_gripper_command(self, command: GripperCommand, command_id: str) -> HardwareCommandResult:
        """Send gripper command over serial."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                # Format gripper command
                pos = command["position"]
                force = command["force"]
                cmd = f"$G,{pos:.3f},{force:.3f}*"
                cmd += self._calculate_checksum(cmd)
                cmd += "\r\n"

                self._send_raw(cmd)
                response = self._read_response()

                if self._validate_response(response):
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message=f"Gripper: pos={pos}, force={force}",
                        sensor_data={"gripper_position": pos, "gripper_force": force},
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message="Invalid response from robot",
                        error_code=1002,
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=1003,
                )

    def send_stop_command(self, command: StopCommand, command_id: str) -> HardwareCommandResult:
        """Send stop command over serial."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                stop_type = "1" if command["immediate"] else "0"
                cmd = f"$S,{stop_type}*\r\n"
                self._send_raw(cmd)

                self._is_moving = False
                self._joint_velocities = [0.0] * 6

                return HardwareCommandResult(
                    success=True,
                    command_id=command_id,
                    message="Stop command executed",
                )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Stop failed: {str(e)}",
                    error_code=1003,
                )

    def execute_skill(self, command: ExecuteSkillCommand, command_id: str) -> HardwareCommandResult:
        """Execute named skill over serial."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                skill_name = command["skill_name"]
                params = command["parameters"]

                # Format skill command
                params_str = ",".join(f"{k}={v}" for k, v in params.items())
                cmd = f"$SK,{skill_name},{params_str}*\r\n"

                self._send_raw(cmd)
                response = self._read_response()

                if self._validate_response(response):
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message=f"Skill '{skill_name}' executed",
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message="Invalid response from robot",
                        error_code=1002,
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Skill execution failed: {str(e)}",
                    error_code=1003,
                )

    def get_joint_feedback(self) -> JointFeedback:
        """Query joint state over serial."""
        if not self._connected:
            return JointFeedback(positions=[0.0]*6, velocities=[0.0]*6, torques=[0.0]*6)

        with self._lock:
            try:
                cmd = "$FJ*\r\n"
                self._send_raw(cmd)
                response = self._read_response()

                # Parse joint feedback response
                # Format would be: "$FJ," + positions + "," + velocities + "," + torques + "*"
                # Stub returns simulated values
                return JointFeedback(
                    positions=self._joint_positions.copy(),
                    velocities=self._joint_velocities.copy(),
                    torques=self._joint_torques.copy(),
                )
            except Exception:
                return JointFeedback(
                    positions=self._joint_positions.copy(),
                    velocities=self._joint_velocities.copy(),
                    torques=self._joint_torques.copy(),
                )

    def get_sensor_feedback(self) -> SensorFeedback:
        """Query sensor data over serial."""
        if not self._connected:
            return SensorFeedback(imu=None, force_torque=None, proximity=None, gripper=None)

        with self._lock:
            # Stub implementation - actual would query sensors
            return SensorFeedback(
                imu={"ax": 0.0, "ay": 0.0, "az": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.0, "temperature": 25.0},
                force_torque={"fx": 0.0, "fy": 0.0, "fz": 0.0, "tx": 0.0, "ty": 0.0, "tz": 0.0},
                proximity={"distance": 0.5, "is_object_detected": False},
                gripper={"width": 0.0, "force": 0.0},
            )

    def get_hardware_status(self) -> HardwareStatus:
        """Get hardware status."""
        return HardwareStatus(
            is_connected=self._connected,
            is_moving=self._is_moving,
            error_code=self._error_code,
            error_message=self._error_message,
            timestamp=time.time(),
        )

    def reset_errors(self) -> bool:
        """Reset hardware errors."""
        with self._lock:
            self._error_code = 0
            self._error_message = ""
            try:
                cmd = "$RST*\r\n"
                self._send_raw(cmd)
                return True
            except Exception:
                return False

    def emergency_stop(self) -> HardwareCommandResult:
        """Send emergency stop command."""
        with self._lock:
            try:
                cmd = "$EST*\r\n"
                self._send_raw(cmd)

                self._is_moving = False
                self._joint_velocities = [0.0] * 6

                return HardwareCommandResult(
                    success=True,
                    command_id="emergency_stop",
                    message="EMERGENCY STOP ACTIVATED",
                    error_code=9999,
                )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id="emergency_stop",
                    message=f"Emergency stop failed: {str(e)}",
                    error_code=9998,
                )

    # ============================================================
    # Helper Methods
    # ============================================================

    def _not_connected_error(self, command_id: str) -> HardwareCommandResult:
        """Create not-connected error result."""
        return HardwareCommandResult(
            success=False,
            command_id=command_id,
            message="Not connected to robot",
            error_code=1001,
        )

    def _format_joint_command(self, positions: list[float]) -> str:
        """Format joint position command."""
        pos_str = ",".join(f"{p:.4f}" for p in positions)
        cmd = f"$J,{pos_str}*"
        cmd += self._calculate_checksum(cmd)
        cmd += "\r\n"
        return cmd

    def _format_pose_command(self, pose: PoseTarget) -> str:
        """Format pose target command."""
        cmd = f"$P,{pose['x']:.4f},{pose['y']:.4f},{pose['z']:.4f},{pose['rx']:.4f},{pose['ry']:.4f},{pose['rz']:.4f}*"
        cmd += self._calculate_checksum(cmd)
        cmd += "\r\n"
        return cmd

    def _calculate_checksum(self, data: str) -> str:
        """Calculate NMEA-style checksum."""
        checksum = 0
        for char in data:
            checksum ^= ord(char)
        return f"{checksum:02X}"

    def _send_raw(self, data: str) -> None:
        """Send raw data over serial."""
        # Stub: actual would write to self._serial
        pass

    def _read_response(self) -> str:
        """Read response from serial."""
        # Stub: actual would read from self._serial
        # Timeout handling would be implemented
        return "$ACK*"

    def _validate_response(self, response: str) -> bool:
        """Validate response checksum."""
        if not response or response[0] != "$":
            return False
        if "*" not in response:
            return False

        data, checksum_str = response.split("*")
        if len(checksum_str) < 2:
            return False

        calculated = self._calculate_checksum(data[1:])  # Skip $
        return calculated == checksum_str[:2]
