"""
Network hardware adapter for robots with TCP/IP communication.

Provides connection to robot controllers over Ethernet/WiFi.
"""
import json
import socket
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


class NetworkHardwareAdapter(IHardwareAdapter):
    """
    Hardware adapter for TCP/IP network communication.

    Supports robot controllers with Ethernet/WiFi connectivity.

    Note: This is a stub implementation. Actual protocol implementation
    depends on specific robot manufacturer's API.
    """

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 5000,
        timeout: float = 5.0,
    ):
        """
        Initialize network adapter.

        Args:
            host: Robot controller IP address
            port: TCP port number
            timeout: Connection/read timeout in seconds
        """
        self._name = f"network_{host}:{port}"
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._is_moving = False
        self._error_code = 0
        self._error_message = ""
        self._lock = threading.Lock()
        self._command_id_counter = 0

        # Simulated state
        self._joint_positions = [0.0] * 6
        self._joint_velocities = [0.0] * 6
        self._joint_torques = [0.0] * 6
        self._gripper_position = 0.0
        self._gripper_force = 0.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """
        Establish TCP connection to robot.

        Returns:
            True if connection successful
        """
        with self._lock:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(self._timeout)
                self._socket.connect((self._host, self._port))
                self._connected = True

                # Send handshake
                handshake = self._create_message("handshake", {})
                response = self._send_and_receive(handshake)

                if response and response.get("status") == "ok":
                    return True
                else:
                    self._error_message = "Handshake failed"
                    self._connected = False
                    return False

            except socket.timeout:
                self._error_message = "Connection timeout"
                self._error_code = 1001
                return False
            except socket.error as e:
                self._error_message = f"Connection error: {str(e)}"
                self._error_code = 1001
                return False

    def disconnect(self) -> None:
        """Close TCP connection."""
        with self._lock:
            if self._socket:
                try:
                    # Send disconnect message
                    disconnect_msg = self._create_message("disconnect", {})
                    self._send_raw(disconnect_msg)
                    self._socket.close()
                except Exception:
                    pass
            self._connected = False
            self._socket = None

    def send_joint_positions(self, positions: list[float], command_id: str) -> HardwareCommandResult:
        """Send joint positions over network."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                payload = {"positions": positions}
                message = self._create_message("move_joints", payload, command_id)
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    self._joint_positions = positions.copy()
                    self._is_moving = True
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message="Joints moved successfully",
                        positions=self._joint_positions.copy(),
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message=response.get("error", "Move failed"),
                        error_code=response.get("error_code", 2001),
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=2002,
                )

    def send_pose_target(self, pose: PoseTarget, command_id: str) -> HardwareCommandResult:
        """Send Cartesian pose target over network."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                payload = dict(pose)
                message = self._create_message("move_pose", payload, command_id)
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message="Pose reached successfully",
                        positions=self._joint_positions.copy(),
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message=response.get("error", "Move failed"),
                        error_code=response.get("error_code", 2001),
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=2002,
                )

    def send_gripper_command(self, command: GripperCommand, command_id: str) -> HardwareCommandResult:
        """Send gripper command over network."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                payload = {"position": command["position"], "force": command["force"]}
                message = self._create_message("gripper", payload, command_id)
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    self._gripper_position = command["position"]
                    self._gripper_force = command["force"]
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message="Gripper command executed",
                        sensor_data={"gripper_position": self._gripper_position, "gripper_force": self._gripper_force},
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message=response.get("error", "Gripper command failed"),
                        error_code=response.get("error_code", 2001),
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Command failed: {str(e)}",
                    error_code=2002,
                )

    def send_stop_command(self, command: StopCommand, command_id: str) -> HardwareCommandResult:
        """Send stop command over network."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                payload = {"immediate": command["immediate"]}
                message = self._create_message("stop", payload, command_id)
                response = self._send_and_receive(message)

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
                    error_code=2002,
                )

    def execute_skill(self, command: ExecuteSkillCommand, command_id: str) -> HardwareCommandResult:
        """Execute named skill over network."""
        if not self._connected:
            return self._not_connected_error(command_id)

        with self._lock:
            try:
                payload = {"skill_name": command["skill_name"], "parameters": command["parameters"]}
                message = self._create_message("execute_skill", payload, command_id)
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    return HardwareCommandResult(
                        success=True,
                        command_id=command_id,
                        message=f"Skill '{command['skill_name']}' executed",
                    )
                else:
                    return HardwareCommandResult(
                        success=False,
                        command_id=command_id,
                        message=response.get("error", "Skill execution failed"),
                        error_code=response.get("error_code", 2001),
                    )
            except Exception as e:
                return HardwareCommandResult(
                    success=False,
                    command_id=command_id,
                    message=f"Skill execution failed: {str(e)}",
                    error_code=2002,
                )

    def get_joint_feedback(self) -> JointFeedback:
        """Query joint state over network."""
        if not self._connected:
            return JointFeedback(positions=[0.0]*6, velocities=[0.0]*6, torques=[0.0]*6)

        with self._lock:
            try:
                message = self._create_message("get_joints", {})
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    data = response.get("data", {})
                    self._joint_positions = data.get("positions", self._joint_positions)
                    self._joint_velocities = data.get("velocities", self._joint_velocities)
                    self._joint_torques = data.get("torques", self._joint_torques)

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
        """Query sensor data over network."""
        if not self._connected:
            return SensorFeedback(imu=None, force_torque=None, proximity=None, gripper=None)

        with self._lock:
            try:
                message = self._create_message("get_sensors", {})
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    return response.get("data", {})
            except Exception:
                pass

            # Return simulated values on failure
            return SensorFeedback(
                imu={"ax": 0.0, "ay": 0.0, "az": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.0, "temperature": 25.0},
                force_torque={"fx": 0.0, "fy": 0.0, "fz": 0.0, "tx": 0.0, "ty": 0.0, "tz": 0.0},
                proximity={"distance": 0.5, "is_object_detected": False},
                gripper={"width": self._gripper_position, "force": self._gripper_force},
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
            try:
                message = self._create_message("reset_errors", {})
                response = self._send_and_receive(message)

                if response and response.get("status") == "ok":
                    self._error_code = 0
                    self._error_message = ""
                    return True
                return False
            except Exception:
                return False

    def emergency_stop(self) -> HardwareCommandResult:
        """Send emergency stop command."""
        with self._lock:
            try:
                message = self._create_message("emergency_stop", {})
                response = self._send_and_receive(message)

                self._is_moving = False
                self._joint_velocities = [0.0] * 6
                self._gripper_force = 0.0

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

    def _create_message(self, command: str, payload: dict, custom_id: str | None = None) -> str:
        """Create JSON message for sending."""
        self._command_id_counter += 1
        message = {
            "cmd": command,
            "id": custom_id or f"{self._command_id_counter}",
            "ts": time.time(),
            "data": payload,
        }
        return json.dumps(message)

    def _send_raw(self, message: str) -> None:
        """Send raw message over socket."""
        if self._socket:
            self._socket.sendall((message + "\n").encode("utf-8"))

    def _receive_raw(self) -> str:
        """Receive raw message from socket."""
        if not self._socket:
            return ""
        data = self._socket.recv(4096).decode("utf-8")
        return data.strip()

    def _send_and_receive(self, message: str) -> Optional[dict]:
        """Send message and wait for response."""
        self._send_raw(message)
        response_str = self._receive_raw()
        if response_str:
            return json.loads(response_str)
        return None
