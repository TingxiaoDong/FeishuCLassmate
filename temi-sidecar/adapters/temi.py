"""
Temi robot WebSocket adapter.

Ported from FeishuClassmate/src/hardware/adapters/temi_adapter.py (TemiWebSocketClient).
This module is self-contained — it does NOT import from the original repo.

Protocol: ws://TEMI_IP:8175
Messages: JSON, e.g.
  {"command": "speak",  "sentence": "Hello", "id": "<uuid>"}
  {"command": "goto",   "location": "入口", "id": "<uuid>"}
  {"command": "stop"}

The tongji-cdi temi-woz-android app requires an "id" string on speak / ask / goto
(see TemiWebsocketServer.java); omitting it causes JSONException and the command
is ignored. Completion is broadcast as JSON {"id": "<same-uuid>"}.

Phase-2 stubs (detect_person, rfid_scan, monitor_focus, gesture) raise
NotImplementedError in real mode and return sample data in mock mode.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chinese location-name fallback mapping (same as the original adapter)
# ---------------------------------------------------------------------------
# Maps Chinese location names to the English names Temi understands
LOCATION_TO_TEMI: dict[str, str] = {
    "入口": "Entrance",
    "entrance": "Entrance",
    "厨房": "Kitchen",
    "kitchen": "Kitchen",
    "沙发": "Sofa",
    "sofa": "Sofa",
    "couch": "Sofa",
    "电视柜": "TV Stand",
    "tv stand": "TV Stand",
    "tv": "TV Stand",
    "餐桌": "Dining Table",
    "dining table": "Dining Table",
    "table": "Dining Table",
    "bed": "Bed",
    "bed": "Bed",
    "充电桩": "Charging Station",
    "charging station": "Charging Station",
    "home": "Entrance",
    "工位1": "Workstation 1",
    "工位2": "Workstation 2",
    "工位3": "Workstation 3",
}

TEMI_LOCATION_NAMES: set[str] = {
    "Entrance", "Kitchen", "Sofa", "TV Stand", "Dining Table",
    "Bed", "Charging Station", "Workstation 1", "Workstation 2", "Workstation 3",
}

def resolve_location(name: str) -> str:
    """Return the location name as-is. Temi expects the exact name saved on the robot."""
    return name


# ---------------------------------------------------------------------------
# WebSocket client
# ---------------------------------------------------------------------------

class TemiWebSocketClient:
    """Async WebSocket client for Temi robot control.

    Lifecycle:
        client = TemiWebSocketClient("192.168.1.10")
        connected = await client.connect()
        ...
        await client.disconnect()
    """

    def __init__(self, ip: str, port: int = 8175) -> None:
        self._ip = ip
        self._port = port
        self._ws: Any = None  # websockets.WebSocketClientProtocol
        self._listener_task: asyncio.Task[None] | None = None
        # Pending response futures keyed by command type
        self._response_futures: dict[str, asyncio.Future[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Open WebSocket connection to Temi.  Returns True on success."""
        uri = f"ws://{self._ip}:{self._port}"
        try:
            self._ws = await websockets.connect(uri, ping_interval=None)
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("Connected to Temi at %s", uri)
            return True
        except (OSError, WebSocketException, asyncio.TimeoutError) as exc:
            logger.warning("Failed to connect to Temi at %s: %s", uri, exc)
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection cleanly."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        logger.info("Disconnected from Temi")

    # ------------------------------------------------------------------
    # Internal listener
    # ------------------------------------------------------------------

    async def _listen(self) -> None:
        """Background task: read incoming messages and resolve pending futures."""
        try:
            async for raw in self._ws:
                try:
                    data: dict[str, Any] = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("[Temi] Non-JSON message: %r", raw)
                    continue

                logger.debug("[Temi] Received: %s", data)

                event_type: str = data.get("event", "")

                # Resolve the first pending future whose key matches or any if event matches
                if self._response_futures:
                    for key, fut in list(self._response_futures.items()):
                        if not fut.done():
                            fut.set_result(data)
                            del self._response_futures[key]
                            break

                # Log notable events
                if event_type == "onTTSCompleted":
                    logger.debug("[Temi] TTS completed")
                elif event_type == "onASRCompleted":
                    logger.debug("[Temi] ASR completed")
                elif event_type == "onDetectionStateChanged":
                    logger.debug("[Temi] Detection state: %s", data.get("state"))
                elif event_type == "onNavigationCompleted":
                    logger.debug("[Temi] Navigation completed")

        except asyncio.CancelledError:
            pass
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] Listen loop ended: %s", exc)

    # ------------------------------------------------------------------
    # Low-level send
    # ------------------------------------------------------------------

    async def send_command(
        self,
        command: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Send a command dict and await the next Temi response (or timeout)."""
        if not self._ws:
            raise RuntimeError("Not connected to Temi")

        payload = dict(command)
        if "id" not in payload:
            payload["id"] = str(uuid.uuid4())

        cmd_type: str = payload.get("command", "unknown")
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._response_futures[cmd_type] = future

        await self._ws.send(json.dumps(payload, ensure_ascii=False))
        logger.info("[Temi] → WS: %s", json.dumps(payload, ensure_ascii=False))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # Temi often completes without sending an explicit response event;
            # treat timeout as success for navigation/TTS/stop commands.
            self._response_futures.pop(cmd_type, None)
            if cmd_type == "goto":
                return {"status": "ok", "event": "NavigationCompleted"}
            if cmd_type == "speak":
                return {"status": "ok", "event": "TTSCompleted"}
            if cmd_type == "stop":
                return {"status": "ok", "event": "Stopped"}
            return {"status": "timeout", "message": f"Command timed out after {timeout}s"}

    # ------------------------------------------------------------------
    # High-level commands (real mode)
    # ------------------------------------------------------------------

    async def speak(self, text: str, voice: str = "friendly") -> bool:
        """Send TTS command.  voice is advisory (Temi has one voice)."""
        result = await self.send_command({"command": "speak", "sentence": text})
        return result.get("status") != "error"

    async def goto(self, location: str) -> bool:
        """Navigate to a saved location by name."""
        result = await self.send_command(
            {"command": "goto", "location": resolve_location(location)},
            timeout=60.0,
        )
        return result.get("status") != "error"

    async def stop(self, immediate: bool = False) -> bool:
        """Stop all robot motion."""
        try:
            await self._ws.send(json.dumps({"command": "stop"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] stop() failed: %s", exc)
            return False

    async def turnBy(self, degrees: int, speed: float = 0.5) -> bool:
        """Rotate robot by `degrees` (positive=left, negative=right).

        Args:
            degrees: Rotation angle in degrees. Positive = counter-clockwise (left),
                     negative = clockwise (right).
            speed:    Rotation speed in range [0, 1].
        """
        result = await self.send_command(
            {"command": "turnBy", "degrees": degrees, "speed": speed}
        )
        return result.get("status") != "error"

    async def tiltAngle(self, degrees: int, speed: float = 0.5) -> bool:
        """Tilt robot head to absolute `degrees` (-30 ~ 55).

        Args:
            degrees: Absolute tilt angle. Range -30 (down) to +55 (up).
            speed:   Tilt speed in range [0, 1].
        """
        result = await self.send_command(
            {"command": "tiltAngle", "degrees": degrees, "speed": speed}
        )
        return result.get("status") != "error"

    async def tiltBy(self, degrees: int, speed: float = 0.5) -> bool:
        """Tilt robot head by relative `degrees` from current position.

        Args:
            degrees: Relative tilt change in degrees.
            speed:   Tilt speed in range [0, 1].
        """
        result = await self.send_command(
            {"command": "tiltBy", "degrees": degrees, "speed": speed}
        )
        return result.get("status") != "error"

    async def skidJoy(self, x: float, y: float, smart: bool = False) -> bool:
        """Omni-directional movement using speed vector.

        Args:
            x:     Forward/back speed in [-1, 1]. Positive = forward.
            y:     Left/right speed in [-1, 1]. Positive = left (strafe).
            smart: Enable obstacle avoidance (requires firmware 0.10.79+).
        """
        result = await self.send_command(
            {"command": "skidJoy", "x": x, "y": y, "smart": smart}
        )
        return result.get("status") != "error"

    async def askQuestion(self, text: str) -> bool:
        """Send TTS and wait for voice response (conversational turn).

        Unlike speak(), this waits for the user to answer.
        """
        result = await self.send_command(
            {"command": "ask", "sentence": text},
            timeout=60.0,
        )
        return result.get("status") != "error"

    async def wakeup(self) -> bool:
        """Wake up temi from sleep / activate listening."""
        try:
            await self._ws.send(json.dumps({"command": "wakeup"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] wakeup() failed: %s", exc)
            return False

    async def startFollow(self) -> bool:
        """Start follow-me mode."""
        try:
            await self._ws.send(json.dumps({"command": "followMode", "mode": "start"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] startFollow() failed: %s", exc)
            return False

    async def stopFollow(self) -> bool:
        """Stop follow-me mode."""
        try:
            await self._ws.send(json.dumps({"command": "followMode", "mode": "stop"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] stopFollow() failed: %s", exc)
            return False

    async def startDetecting(self) -> bool:
        """Start people detection."""
        try:
            await self._ws.send(json.dumps({"command": "startDetection"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] startDetecting() failed: %s", exc)
            return False

    async def stopDetecting(self) -> bool:
        """Stop people detection."""
        try:
            await self._ws.send(json.dumps({"command": "stopDetection"}))
            return True
        except (WebSocketException, OSError) as exc:
            logger.warning("[Temi] stopDetecting() failed: %s", exc)
            return False

    async def saveLocation(self, name: str) -> bool:
        """Save the current position as a named location."""
        result = await self.send_command(
            {"command": "saveLocation", "location": name}
        )
        return result.get("status") != "error"

    async def deleteLocation(self, name: str) -> bool:
        """Delete a saved location by name."""
        result = await self.send_command(
            {"command": "deleteLocation", "location": name}
        )
        return result.get("status") != "error"

    # ------------------------------------------------------------------
    # Phase-2 stubs — raise NotImplementedError in real mode
    # ------------------------------------------------------------------

    async def detect_person(self, timeout_ms: int) -> tuple[str | None, float]:
        """Phase 2: identify person from camera.  Returns (open_id, confidence)."""
        raise NotImplementedError(
            "detect_person is a Phase-2 feature; vision pipeline not yet integrated"
        )

    async def rfid_scan(self, route: list[str] | None = None) -> list[dict[str, Any]]:
        """Phase 2: scan RFID tags along optional route."""
        raise NotImplementedError(
            "rfid_scan is a Phase-2 feature; RFID hardware not yet integrated"
        )

    async def monitor_focus(
        self,
        student_open_id: str,
        duration_s: int,
    ) -> list[dict[str, Any]]:
        """Phase 2: monitor student focus via camera for duration_s seconds."""
        raise NotImplementedError(
            "monitor_focus is a Phase-2 feature; vision pipeline not yet integrated"
        )

    async def gesture(self, gesture_type: str) -> bool:
        """Phase 2: perform a physical gesture (encourage / poke / applause / nod)."""
        raise NotImplementedError(
            "gesture is a Phase-2 feature; motion primitives not yet integrated"
        )
