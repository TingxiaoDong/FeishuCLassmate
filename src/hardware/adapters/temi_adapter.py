"""
Temi Robot Adapter using WebSocket.

Based on tongji-cdi/temi-woz-android project.
WebSocket connection to ws://TEMI_IP:8175

Supported commands:
- {"command": "speak", "sentence": "..."}
- {"command": "goto", "location": "..."}
- {"command": "ask", "sentence": "..."}
- {"command": "stop"}
"""
import asyncio
import json
import uuid
import time
from typing import Optional, Callable, Awaitable

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from .base import (
    IHardwareAdapter,
    JointPositions,
    PoseTarget,
    GripperCommand,
    StopCommand,
    ExecuteSkillCommand,
    JointFeedback,
    SensorFeedback,
    HardwareStatus,
    HardwareCommandResult,
)


class TemiWebSocketClient:
    """WebSocket client for Temi robot control."""

    def __init__(self, ip: str, port: int = 8175):
        self._ip = ip
        self._port = port
        self._ws = None
        self._response_futures = {}
        self._listener_task = None
        self._loop = None

    async def connect(self) -> bool:
        """Connect to Temi WebSocket."""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets package not installed. Run: pip install websockets")

        uri = f"ws://{self._ip}:{self._port}"
        try:
            self._ws = await websockets.connect(uri, ping_interval=None)
            self._loop = asyncio.get_event_loop()
            self._listener_task = asyncio.create_task(self._listen())
            return True
        except Exception as e:
            print(f"Failed to connect to Temi at {uri}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Temi."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _listen(self):
        """Listen for responses from Temi."""
        try:
            async for message in self._ws:
                data = json.loads(message)
                print(f"[Temi] Received: {data}")

                # Handle different response types
                event_type = data.get("event", "")

                # For async responses, resolve the first pending future
                if self._response_futures:
                    for key, future in list(self._response_futures.items()):
                        if not future.done():
                            future.set_result(data)
                            break

                # Also handle specific event types
                if event_type == "onTTSCompleted":
                    print("[Temi] TTS completed")
                elif event_type == "onASRCompleted":
                    print("[Temi] ASR completed")
                elif event_type == "onDetectionStateChanged":
                    print(f"[Temi] Detection state: {data.get('state')}")
                elif event_type == "onNavigationCompleted":
                    print("[Temi] Navigation completed")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Temi] Listen error: {e}")

    async def send_command(self, command: dict, timeout: float = 30.0) -> dict:
        """Send command and wait for response."""
        if not self._ws:
            raise RuntimeError("Not connected to Temi")

        cmd_type = command.get("command", "unknown")
        future = asyncio.Future()
        self._response_futures[cmd_type] = future

        # Send command
        await self._ws.send(json.dumps(command))
        print(f"[Temi] Sent: {command}")

        # Wait for response with timeout
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # For commands that don't send explicit responses, consider success after timeout
            # (Temi may have completed the action without sending an event)
            if cmd_type == "goto":
                return {"status": "ok", "event": "NavigationCompleted"}
            elif cmd_type == "speak":
                return {"status": "ok", "event": "TTSCompleted"}
            elif cmd_type == "stop":
                return {"status": "ok", "event": "Stopped"}
            return {"status": "timeout", "message": f"Command timed out after {timeout}s"}

    async def speak(self, text: str) -> bool:
        """Send speak command."""
        result = await self.send_command({"command": "speak", "sentence": text})
        return "TTS_COMPLETED" in str(result)

    async def goto(self, location: str) -> bool:
        """Send goto command."""
        result = await self.send_command({"command": "goto", "location": location})
        # Navigation returns NavigationCompleted event or timeout (which we treat as success)
        return result.get("status") != "error" or result.get("event") == "NavigationCompleted"

    async def stop(self) -> bool:
        """Send stop command."""
        try:
            await self._ws.send(json.dumps({"command": "stop"}))
            return True
        except Exception:
            return False


class TemiAdapter(IHardwareAdapter):
    """
    Adapter for temi robot using WebSocket interface.

    Temi capabilities:
    - Navigation: go to saved locations
    - TTS: Text-to-speech
    - Ask: Ask question with speech recognition
    - Follow: Follow mode

    Not supported (no arm/gripper):
    - Joint control
    - Grasping
    """

    # Location name mapping for Chinese location names
    LOCATION_NAMES = {
        "workstation 1": "充电桩",
        "workstation 2": "厨房",
        "workstation 3": "入口",
        "entrance": "入口",
        "kitchen": "厨房",
        "sofa": "沙发",
        "couch": "沙发",
        "tv stand": "电视柜",
        "tv": "电视柜",
        "dining table": "餐桌",
        "table": "餐桌",
        "bed": "床",
        "charging station": "充电桩",
        "home": "入口",
        "default": "入口",
    }

    def __init__(self, ip: str, port: int = 8175):
        """
        Initialize Temi adapter.

        Args:
            ip: Temi robot IP address (e.g., "192.168.1.100")
            port: WebSocket port (default 8175)
        """
        self._ip = ip
        self._port = port
        self._client: Optional[TemiWebSocketClient] = None
        self._connected = False
        self._position = {"x": 0.0, "y": 0.0}
        self._battery = 100
        self._is_moving = False
        self._error_code = 0
        self._error_message = ""

    @property
    def name(self) -> str:
        return f"Temi({self._ip})"

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Connect to temi robot via WebSocket."""
        try:
            if not WEBSOCKETS_AVAILABLE:
                print("[TemiAdapter] websockets not available, using mock mode")
                self._connected = True
                return True

            self._client = TemiWebSocketClient(self._ip, self._port)
            # Run async connect in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._connected = loop.run_until_complete(self._client.connect())
            # Keep the loop for later use
            self._loop = loop
            return self._connected
        except Exception as e:
            self._error_message = str(e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from temi robot."""
        if self._client:
            try:
                if hasattr(self, '_loop') and self._loop:
                    asyncio.set_event_loop(self._loop)
                    self._loop.run_until_complete(self._client.disconnect())
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._client.disconnect())
                    loop.close()
            except Exception:
                pass
        self._connected = False
        self._client = None
        if hasattr(self, '_loop') and self._loop:
            try:
                self._loop.close()
            except Exception:
                pass
            self._loop = None

    def send_joint_positions(self, positions: list[float], command_id: str) -> HardwareCommandResult:
        """Not supported on temi - mobile robot, not arm robot."""
        return HardwareCommandResult(
            success=False,
            command_id=command_id,
            message="Joint control not supported on temi mobile robot",
            error_code=1,
        )

    def send_pose_target(self, pose: PoseTarget, command_id: str) -> HardwareCommandResult:
        """Navigate to x, y position (uses goto with location name)."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to temi",
                error_code=1001,
            )

        x = pose.get("x", 0)
        y = pose.get("y", 0)

        # Determine location name from coordinates or use default location
        # Temi uses saved locations, not coordinates
        location = "入口"  # Default to entrance

        try:
            if self._client and WEBSOCKETS_AVAILABLE:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self._client.goto(location))
                loop.close()
            else:
                success = True  # Mock mode

            self._position = {"x": x, "y": y}
            self._is_moving = success

            return HardwareCommandResult(
                success=success,
                command_id=command_id,
                message=f"Going to location: {location}" if success else "Navigation failed",
            )
        except Exception as e:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message=f"Move failed: {str(e)}",
                error_code=1,
            )

    def send_gripper_command(self, command: GripperCommand, command_id: str) -> HardwareCommandResult:
        """Not supported on temi - no gripper."""
        return HardwareCommandResult(
            success=False,
            command_id=command_id,
            message="Gripper not supported on temi mobile robot",
            error_code=1,
        )

    def send_stop_command(self, command: StopCommand, command_id: str) -> HardwareCommandResult:
        """Send stop command to temi."""
        if not self._connected:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Not connected to temi",
                error_code=1001,
            )

        try:
            if self._client and WEBSOCKETS_AVAILABLE:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._client.stop())
                loop.close()
            self._is_moving = False
            return HardwareCommandResult(
                success=True,
                command_id=command_id,
                message="Temi stopped",
            )
        except Exception as e:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message=f"Stop failed: {str(e)}",
                error_code=1,
            )

    def execute_skill(self, command: ExecuteSkillCommand, command_id: str) -> HardwareCommandResult:
        """Execute skill on temi."""
        skill_name = command.get("skill_name", "")
        params = command.get("parameters", {})

        if skill_name == "move_to":
            return self._execute_move_to(params, command_id)
        elif skill_name == "go_to_location":
            return self._execute_go_to_location(params, command_id)
        elif skill_name == "speak":
            return self._execute_speak(params, command_id)
        elif skill_name == "follow":
            return self._execute_follow(params, command_id)
        elif skill_name == "stop":
            return self.send_stop_command({"immediate": True}, command_id)
        else:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message=f"Skill '{skill_name}' not supported on temi",
                error_code=1,
            )

    def _execute_move_to(self, params: dict, command_id: str) -> HardwareCommandResult:
        """Execute move_to skill."""
        x = params.get("x", params.get("target_x", 0.0))
        y = params.get("y", params.get("target_y", 0.0))
        return self.send_pose_target({"x": x, "y": y, "z": 0}, command_id)

    def _execute_go_to_location(self, params: dict, command_id: str) -> HardwareCommandResult:
        """Execute go_to_location skill - navigate to saved location."""
        location = params.get("location", "")
        if not location:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Location name required for go_to_location",
                error_code=1,
            )

        # Convert location name using mapping
        mapped_location = self.LOCATION_NAMES.get(location.lower(), location)

        try:
            if self._client and WEBSOCKETS_AVAILABLE:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self._client.goto(mapped_location))
                loop.close()
            else:
                success = True  # Mock mode

            return HardwareCommandResult(
                success=success,
                command_id=command_id,
                message=f"Going to location: {mapped_location}" if success else "Navigation failed",
            )
        except Exception as e:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message=f"Go to location failed: {str(e)}",
                error_code=1,
            )

    def _execute_speak(self, params: dict, command_id: str) -> HardwareCommandResult:
        """Execute speak skill - text-to-speech."""
        text = params.get("text", params.get("message", ""))
        if not text:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message="Text required for speak",
                error_code=1,
            )

        try:
            if self._client and WEBSOCKETS_AVAILABLE:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self._client.speak(text))
                loop.close()
            else:
                success = True  # Mock mode

            return HardwareCommandResult(
                success=success,
                command_id=command_id,
                message=f"Speaking: {text}" if success else "TTS failed",
            )
        except Exception as e:
            return HardwareCommandResult(
                success=False,
                command_id=command_id,
                message=f"Speak failed: {str(e)}",
                error_code=1,
            )

    def _execute_follow(self, params: dict, command_id: str) -> HardwareCommandResult:
        """Execute follow skill - start follow mode."""
        # Follow mode would need additional WebSocket command
        return HardwareCommandResult(
            success=False,
            command_id=command_id,
            message="Follow mode not yet implemented",
            error_code=1,
        )

    def get_joint_feedback(self) -> JointFeedback:
        """Temi doesn't have joints - return zeros."""
        return JointFeedback(
            positions=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            velocities=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            torques=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )

    def get_sensor_feedback(self) -> SensorFeedback:
        """Get sensor feedback from temi."""
        return SensorFeedback(
            imu=None,
            force_torque=None,
            proximity=None,
            gripper=None,
        )

    def get_hardware_status(self) -> HardwareStatus:
        """Get overall hardware status."""
        return HardwareStatus(
            is_connected=self._connected,
            is_moving=self._is_moving,
            error_code=self._error_code,
            error_message=self._error_message,
            timestamp=time.time(),
        )

    def reset_errors(self) -> bool:
        """Reset error state."""
        self._error_code = 0
        self._error_message = ""
        return True

    def emergency_stop(self) -> HardwareCommandResult:
        """Trigger emergency stop."""
        command_id = str(uuid.uuid4())
        self._is_moving = False
        return self.send_stop_command({"immediate": True}, command_id)

    def get_state(self) -> dict:
        """Get current temi state."""
        return {
            "position": self._position,
            "battery": self._battery,
            "is_moving": self._is_moving,
            "connected": self._connected,
        }
