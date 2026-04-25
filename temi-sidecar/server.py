"""
Temi Sidecar — FastAPI HTTP server bridging the feishu-classmate TypeScript
plugin to the Temi robot's WebSocket protocol.

Environment variables
---------------------
TEMI_MOCK     If set to any non-empty, non-"0" value, run in mock mode from startup.
              If unset, the server tries the real robot; falls back to mock on failure.
TEMI_IP       Temi robot IP address (required in real mode).
TEMI_PORT     Temi WebSocket port (default: 8175).
SIDECAR_PORT  Port this HTTP server listens on (default: 8091; used by run block only).
LOG_LEVEL     Python logging level string, e.g. DEBUG / INFO / WARNING (default: INFO).
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import signal
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from adapters.temi import TemiWebSocketClient, resolve_location

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("temi-sidecar")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

TEMI_IP: str = os.getenv("TEMI_IP", "")
TEMI_PORT: int = int(os.getenv("TEMI_PORT", "8175"))
SIDECAR_PORT: int = int(os.getenv("SIDECAR_PORT", "8091"))

_mock_env = os.getenv("TEMI_MOCK", "")
_FORCE_MOCK: bool = bool(_mock_env and _mock_env != "0")

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

class AppState:
    def __init__(self) -> None:
        self.mock_mode: bool = _FORCE_MOCK
        self.client: TemiWebSocketClient | None = None
        # Simulated state for mock / status tracking
        self.battery: int = 87
        self.position: dict[str, float] = {"x": 1.2, "y": 0.5}
        self.is_moving: bool = False
        self.connected: bool = False


_state = AppState()

# ---------------------------------------------------------------------------
# Lifespan — connect/disconnect WebSocket on startup/shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ---- startup ----
    if _state.mock_mode:
        logger.info("TEMI_MOCK=1 — starting in mock mode (no real robot connection)")
    elif not TEMI_IP:
        logger.warning(
            "TEMI_IP not set — cannot connect to real Temi; falling back to mock mode"
        )
        _state.mock_mode = True
    else:
        logger.info("Connecting to Temi at %s:%d …", TEMI_IP, TEMI_PORT)
        _state.client = TemiWebSocketClient(TEMI_IP, TEMI_PORT)
        ok = await _state.client.connect()
        if ok:
            _state.connected = True
            logger.info("Temi connected successfully")
        else:
            logger.warning(
                "Could not reach Temi at %s:%d — falling back to mock mode",
                TEMI_IP,
                TEMI_PORT,
            )
            _state.mock_mode = True
            _state.client = None

    # Register graceful shutdown on SIGTERM (in addition to FastAPI's own handling)
    loop = asyncio.get_event_loop()

    def _handle_sigterm() -> None:
        logger.info("SIGTERM received — scheduling shutdown")
        loop.create_task(_shutdown())

    try:
        loop.add_signal_handler(signal.SIGTERM, _handle_sigterm)
    except (NotImplementedError, RuntimeError):
        # Windows or non-main thread — skip
        pass

    yield

    # ---- shutdown ----
    await _shutdown()


async def _shutdown() -> None:
    if _state.client:
        logger.info("Closing Temi WebSocket connection …")
        await _state.client.disconnect()
        _state.client = None
        _state.connected = False
    logger.info("Temi sidecar shut down cleanly")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Temi Sidecar",
    version="0.1.0",
    description="HTTP bridge from feishu-classmate plugin to Temi robot WebSocket",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _is_mock() -> bool:
    return _state.mock_mode


def _temi_error(message: str) -> dict[str, Any]:
    """Return a standard application-level error payload (HTTP 200, ok=false)."""
    return {"ok": False, "error": message}


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class GotoRequest(BaseModel):
    location: str


class GotoResponse(BaseModel):
    ok: bool
    message: str
    mock: bool = False


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    voice: Literal["friendly", "professional"] = "friendly"


class SpeakResponse(BaseModel):
    ok: bool
    mock: bool = False
    error: str | None = None


class StopRequest(BaseModel):
    immediate: bool = False


class StopResponse(BaseModel):
    ok: bool
    mock: bool = False
    error: str | None = None


class DetectPersonRequest(BaseModel):
    timeout_ms: int = Field(..., ge=500, le=15_000)


class DetectPersonResponse(BaseModel):
    open_id: str | None
    confidence: float
    mock: bool = False
    error: str | None = None


class Position(BaseModel):
    x: float
    y: float


class StatusResponse(BaseModel):
    connected: bool
    battery: int
    position: Position
    is_moving: bool
    mock: bool = False


class RfidTag(BaseModel):
    tag_id: str
    location_estimate: str
    rssi: int


class RfidScanRequest(BaseModel):
    route: list[str] | None = None


class RfidScanResponse(BaseModel):
    tags: list[RfidTag]
    mock: bool = False
    error: str | None = None


class FocusSample(BaseModel):
    ts: float
    focused: bool
    score: float


class MonitorFocusRequest(BaseModel):
    student_open_id: str
    duration_s: int = Field(..., ge=1, le=3600)


class MonitorFocusResponse(BaseModel):
    samples: list[FocusSample]
    mock: bool = False
    error: str | None = None


class GestureRequest(BaseModel):
    type: Literal["encourage", "poke", "applause", "nod"]


class GestureResponse(BaseModel):
    ok: bool
    mock: bool = False
    error: str | None = None


# ---- Movement extensions ----
class TurnRequest(BaseModel):
    degrees: int = Field(..., description="Rotation angle in degrees. Positive=left, negative=right.")
    speed: float = Field(default=0.5, ge=0.0, le=1.0, description="Rotation speed [0, 1]")


class TurnResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False


class TiltRequest(BaseModel):
    degrees: int = Field(..., ge=-30, le=55, description="Absolute tilt angle [-30=down, +55=up]")
    speed: float = Field(default=0.5, ge=0.0, le=1.0, description="Tilt speed [0, 1]")


class TiltResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False


class MoveRequest(BaseModel):
    x: float = Field(default=0.0, ge=-1.0, le=1.0, description="Forward/back speed [-1, 1]")
    y: float = Field(default=0.0, ge=-1.0, le=1.0, description="Left/right speed [-1, 1] (positive=left)")
    smart: bool = Field(default=False, description="Enable obstacle avoidance (firmware 0.10.79+)")


class MoveResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False


class AskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Question text for temi to ask")


class AskResponse(BaseModel):
    ok: bool
    mock: bool = False
    error: str | None = None


class WakeupResponse(BaseModel):
    ok: bool
    mock: bool = False


class FollowResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False


class DetectionResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False


class SaveLocationRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name for the saved location")


class SaveLocationResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False
    error: str | None = None


class DeleteLocationRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the location to delete")


class DeleteLocationResponse(BaseModel):
    ok: bool
    message: str = ""
    mock: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/")
async def health() -> dict[str, Any]:
    """Health check — always returns 200."""
    return {
        "status": "ok",
        "mock": _is_mock(),
        "connected": _state.connected,
    }


# ---------------------------------------------------------------------------
# /goto
# ---------------------------------------------------------------------------

@app.post("/goto", response_model=GotoResponse)
async def goto(req: GotoRequest) -> GotoResponse:
    """Navigate Temi to a saved location by name."""
    if _is_mock():
        resolved = resolve_location(req.location)
        logger.info("[mock] /goto location=%r → %r", req.location, resolved)
        return GotoResponse(
            ok=True,
            message=f"(mock) Temi 已导航到 {resolved}",
            mock=True,
        )

    assert _state.client is not None
    resolved = resolve_location(req.location)
    try:
        ok = await _state.client.goto(resolved)
        _state.is_moving = False
        return GotoResponse(
            ok=ok,
            message=f"Temi 已导航到 {resolved}" if ok else "Navigation failed",
        )
    except Exception as exc:
        logger.exception("/goto failed")
        return GotoResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /speak
# ---------------------------------------------------------------------------

@app.post("/speak", response_model=SpeakResponse)
async def speak(req: SpeakRequest) -> SpeakResponse:
    """Send TTS command to Temi."""
    if _is_mock():
        logger.info("[mock] /speak text=%r voice=%r", req.text, req.voice)
        return SpeakResponse(ok=True, mock=True)

    assert _state.client is not None
    try:
        ok = await _state.client.speak(req.text, req.voice)
        return SpeakResponse(ok=ok, error=None if ok else "TTS command failed")
    except Exception as exc:
        logger.exception("/speak failed")
        return SpeakResponse(ok=False, error=str(exc))


# ---------------------------------------------------------------------------
# /stop
# ---------------------------------------------------------------------------

@app.post("/stop", response_model=StopResponse)
async def stop(req: StopRequest) -> StopResponse:
    """Stop all Temi motion."""
    if _is_mock():
        logger.info("[mock] /stop immediate=%r", req.immediate)
        _state.is_moving = False
        return StopResponse(ok=True, mock=True)

    assert _state.client is not None
    try:
        ok = await _state.client.stop(immediate=req.immediate)
        _state.is_moving = False
        return StopResponse(ok=ok, error=None if ok else "Stop command failed")
    except Exception as exc:
        logger.exception("/stop failed")
        return StopResponse(ok=False, error=str(exc))


# ---------------------------------------------------------------------------
# /detect-person
# ---------------------------------------------------------------------------

@app.post("/detect-person", response_model=DetectPersonResponse)
async def detect_person(req: DetectPersonRequest) -> DetectPersonResponse:
    """Try to identify a person in Temi's camera view.

    Phase 1: always returns open_id=null (no vision pipeline yet).
    Phase 2: will integrate face / badge recognition.
    """
    if _is_mock():
        logger.info("[mock] /detect-person timeout_ms=%d", req.timeout_ms)
        return DetectPersonResponse(open_id=None, confidence=0.0, mock=True)

    # Real mode — Phase 1: return null; Phase 2 will call detect_person()
    logger.info("/detect-person called (real mode, Phase 1 stub) timeout_ms=%d", req.timeout_ms)
    return DetectPersonResponse(open_id=None, confidence=0.0)


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------

@app.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Return current Temi status (battery, position, movement)."""
    if _is_mock():
        return StatusResponse(
            connected=False,
            battery=_state.battery,
            position=Position(x=_state.position["x"], y=_state.position["y"]),
            is_moving=_state.is_moving,
            mock=True,
        )

    return StatusResponse(
        connected=_state.connected,
        battery=_state.battery,
        position=Position(x=_state.position["x"], y=_state.position["y"]),
        is_moving=_state.is_moving,
        mock=False,
    )


# ---------------------------------------------------------------------------
# /rfid-scan
# ---------------------------------------------------------------------------

@app.post("/rfid-scan", response_model=RfidScanResponse)
async def rfid_scan(req: RfidScanRequest) -> RfidScanResponse:
    """Scan RFID tags along an optional route.

    Phase 2 feature — real mode raises NotImplementedError (returned as error payload).
    Mock mode returns plausible sample data.
    """
    if _is_mock():
        logger.info("[mock] /rfid-scan route=%r", req.route)
        mock_tags = [
            RfidTag(tag_id="TAG-001A", location_estimate="工位区-A3", rssi=-62),
            RfidTag(tag_id="TAG-002B", location_estimate="生活仿真区", rssi=-71),
            RfidTag(tag_id="TAG-003C", location_estimate="入口", rssi=-55),
        ]
        # If a specific route was requested, filter to matching tags
        if req.route:
            mock_tags = [t for t in mock_tags if t.location_estimate in req.route] or mock_tags[:1]
        return RfidScanResponse(tags=mock_tags, mock=True)

    # Real mode
    assert _state.client is not None
    try:
        await _state.client.rfid_scan(req.route)
    except NotImplementedError as exc:
        return RfidScanResponse(tags=[], error=str(exc))
    except Exception as exc:
        logger.exception("/rfid-scan failed")
        return RfidScanResponse(tags=[], error=str(exc))

    return RfidScanResponse(tags=[])  # unreachable in Phase 1 but keeps type checker happy


# ---------------------------------------------------------------------------
# /monitor-focus
# ---------------------------------------------------------------------------

@app.post("/monitor-focus", response_model=MonitorFocusResponse)
async def monitor_focus(req: MonitorFocusRequest) -> MonitorFocusResponse:
    """Monitor student focus for duration_s seconds via Temi's camera.

    Phase 2 feature — real mode returns an error.
    Mock mode produces a realistic mostly-focused pattern with a dip in the middle.
    """
    if _is_mock():
        logger.info(
            "[mock] /monitor-focus open_id=%r duration_s=%d",
            req.student_open_id,
            req.duration_s,
        )
        samples = _generate_mock_focus_samples(req.duration_s)
        return MonitorFocusResponse(samples=samples, mock=True)

    # Real mode
    assert _state.client is not None
    try:
        await _state.client.monitor_focus(req.student_open_id, req.duration_s)
    except NotImplementedError as exc:
        return MonitorFocusResponse(samples=[], error=str(exc))
    except Exception as exc:
        logger.exception("/monitor-focus failed")
        return MonitorFocusResponse(samples=[], error=str(exc))

    return MonitorFocusResponse(samples=[])


def _generate_mock_focus_samples(duration_s: int) -> list[FocusSample]:
    """Generate a mock focus trace: high focus → mid-session dip → recovery.

    Uses cos(2π·elapsed) so the score is high at t=0, dips around the
    midpoint (t=0.5), and recovers toward the end — a realistic classroom
    attention pattern.
    """
    samples: list[FocusSample] = []
    sample_interval = 5  # one sample every 5 seconds
    n = max(1, duration_s // sample_interval)
    base_ts = time.time()
    for i in range(n):
        elapsed = i / max(n - 1, 1)  # 0.0 → 1.0
        # cos(2π·t): 1 at start, -1 at midpoint, 1 at end
        # Scaled to roughly 0.55–0.95 range
        score = round(0.75 + 0.20 * math.cos(2 * math.pi * elapsed), 3)
        # A sample counts as "focused" when score > 0.6
        focused = score > 0.6
        samples.append(
            FocusSample(
                ts=round(base_ts + i * sample_interval, 3),
                focused=focused,
                score=score,
            )
        )
    return samples


# ---------------------------------------------------------------------------
# /turn
# ---------------------------------------------------------------------------

@app.post("/turn", response_model=TurnResponse)
async def turn(req: TurnRequest) -> TurnResponse:
    """Rotate the robot by a given angle (positive=left, negative=right)."""
    if _is_mock():
        logger.info("[mock] /turn degrees=%d speed=%.2f", req.degrees, req.speed)
        return TurnResponse(ok=True, message=f"(mock) Temi 向{'左' if req.degrees > 0 else '右'}转 {abs(req.degrees)}°", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.turnBy(req.degrees, req.speed)
        direction = "左" if req.degrees > 0 else "右"
        return TurnResponse(
            ok=ok,
            message=f"Temi 向{direction}转 {abs(req.degrees)}°" if ok else "Rotation failed",
        )
    except Exception as exc:
        logger.exception("/turn failed")
        return TurnResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /tilt
# ---------------------------------------------------------------------------

@app.post("/tilt", response_model=TiltResponse)
async def tilt(req: TiltRequest) -> TiltResponse:
    """Tilt the robot head to an absolute angle (-30 ~ 55)."""
    if _is_mock():
        direction = "抬头" if req.degrees > 0 else "低头"
        logger.info("[mock] /tilt degrees=%d speed=%.2f", req.degrees, req.speed)
        return TiltResponse(ok=True, message=f"(mock) Temi {direction}至 {req.degrees}°", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.tiltAngle(req.degrees, req.speed)
        direction = "抬头" if req.degrees > 0 else "低头"
        return TiltResponse(
            ok=ok,
            message=f"Temi {direction}至 {req.degrees}°" if ok else "Tilt failed",
        )
    except Exception as exc:
        logger.exception("/tilt failed")
        return TiltResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /move
# ---------------------------------------------------------------------------

@app.post("/move", response_model=MoveResponse)
async def move(req: MoveRequest) -> MoveResponse:
    """Omni-directional movement via skidJoy (x=forward/back, y=left/right)."""
    if _is_mock():
        logger.info("[mock] /move x=%.2f y=%.2f smart=%s", req.x, req.y, req.smart)
        parts = []
        if req.x > 0: parts.append("前进")
        elif req.x < 0: parts.append("后退")
        if req.y > 0: parts.append("向左")
        elif req.y < 0: parts.append("向右")
        msg = "(mock) Temi " + ("、".join(parts) if parts else "静止")
        return MoveResponse(ok=True, message=msg, mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.skidJoy(req.x, req.y, req.smart)
        parts = []
        if req.x > 0: parts.append("前进")
        elif req.x < 0: parts.append("后退")
        if req.y > 0: parts.append("向左")
        elif req.y < 0: parts.append("向右")
        msg = "、".join(parts) if parts else "移动完成"
        return MoveResponse(ok=ok, message=msg)
    except Exception as exc:
        logger.exception("/move failed")
        return MoveResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /ask
# ---------------------------------------------------------------------------

@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Send a question to temi and wait for the user's voice response."""
    if _is_mock():
        logger.info("[mock] /ask text=%r", req.text)
        return AskResponse(ok=True, mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.askQuestion(req.text)
        return AskResponse(ok=ok, error=None if ok else "askQuestion failed")
    except Exception as exc:
        logger.exception("/ask failed")
        return AskResponse(ok=False, error=str(exc))


# ---------------------------------------------------------------------------
# /wakeup
# ---------------------------------------------------------------------------

@app.post("/wakeup", response_model=WakeupResponse)
async def wakeup() -> WakeupResponse:
    """Wake up temi (activate listening / come out of sleep)."""
    if _is_mock():
        logger.info("[mock] /wakeup")
        return WakeupResponse(ok=True, mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.wakeup()
        return WakeupResponse(ok=ok)
    except Exception as exc:
        logger.exception("/wakeup failed")
        return WakeupResponse(ok=False)


# ---------------------------------------------------------------------------
# /follow-start  /follow-stop
# ---------------------------------------------------------------------------

@app.post("/follow-start", response_model=FollowResponse)
async def follow_start() -> FollowResponse:
    """Start follow-me mode."""
    if _is_mock():
        logger.info("[mock] /follow-start")
        return FollowResponse(ok=True, message="(mock) Temi 进入跟随模式", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.startFollow()
        return FollowResponse(ok=ok, message="Temi 进入跟随模式" if ok else "Follow start failed")
    except Exception as exc:
        logger.exception("/follow-start failed")
        return FollowResponse(ok=False, message=str(exc))


@app.post("/follow-stop", response_model=FollowResponse)
async def follow_stop() -> FollowResponse:
    """Stop follow-me mode."""
    if _is_mock():
        logger.info("[mock] /follow-stop")
        return FollowResponse(ok=True, message="(mock) Temi 退出跟随模式", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.stopFollow()
        return FollowResponse(ok=ok, message="Temi 退出跟随模式" if ok else "Follow stop failed")
    except Exception as exc:
        logger.exception("/follow-stop failed")
        return FollowResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /detection-start  /detection-stop
# ---------------------------------------------------------------------------

@app.post("/detection-start", response_model=DetectionResponse)
async def detection_start() -> DetectionResponse:
    """Start people detection."""
    if _is_mock():
        logger.info("[mock] /detection-start")
        return DetectionResponse(ok=True, message="(mock) 人员检测已开启", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.startDetecting()
        return DetectionResponse(ok=ok, message="人员检测已开启" if ok else "Detection start failed")
    except Exception as exc:
        logger.exception("/detection-start failed")
        return DetectionResponse(ok=False, message=str(exc))


@app.post("/detection-stop", response_model=DetectionResponse)
async def detection_stop() -> DetectionResponse:
    """Stop people detection."""
    if _is_mock():
        logger.info("[mock] /detection-stop")
        return DetectionResponse(ok=True, message="(mock) 人员检测已关闭", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.stopDetecting()
        return DetectionResponse(ok=ok, message="人员检测已关闭" if ok else "Detection stop failed")
    except Exception as exc:
        logger.exception("/detection-stop failed")
        return DetectionResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /save-location  /delete-location
# ---------------------------------------------------------------------------

@app.post("/save-location", response_model=SaveLocationResponse)
async def save_location(req: SaveLocationRequest) -> SaveLocationResponse:
    """Save the current position as a named location."""
    if _is_mock():
        logger.info("[mock] /save-location name=%r", req.name)
        return SaveLocationResponse(ok=True, message=f"(mock) 位置已保存为「{req.name}」", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.saveLocation(req.name)
        return SaveLocationResponse(
            ok=ok,
            message=f"位置已保存为「{req.name}」" if ok else "Save location failed",
        )
    except Exception as exc:
        logger.exception("/save-location failed")
        return SaveLocationResponse(ok=False, message=str(exc))


@app.post("/delete-location", response_model=DeleteLocationResponse)
async def delete_location(req: DeleteLocationRequest) -> DeleteLocationResponse:
    """Delete a saved location by name."""
    if _is_mock():
        logger.info("[mock] /delete-location name=%r", req.name)
        return DeleteLocationResponse(ok=True, message=f"(mock) 已删除位置「{req.name}」", mock=True)
    assert _state.client is not None
    try:
        ok = await _state.client.deleteLocation(req.name)
        return DeleteLocationResponse(
            ok=ok,
            message=f"已删除位置「{req.name}」" if ok else "Delete location failed",
        )
    except Exception as exc:
        logger.exception("/delete-location failed")
        return DeleteLocationResponse(ok=False, message=str(exc))


# ---------------------------------------------------------------------------
# /gesture
# ---------------------------------------------------------------------------


@app.post("/gesture", response_model=GestureResponse)
async def gesture(req: GestureRequest) -> GestureResponse:
    """Trigger a physical gesture on Temi.

    Phase 2 feature — real mode returns an error.
    Mock mode acknowledges immediately.
    """
    if _is_mock():
        logger.info("[mock] /gesture type=%r", req.type)
        return GestureResponse(ok=True, mock=True)

    # Real mode
    assert _state.client is not None
    try:
        await _state.client.gesture(req.type)
    except NotImplementedError as exc:
        return GestureResponse(ok=False, error=str(exc))
    except Exception as exc:
        logger.exception("/gesture failed")
        return GestureResponse(ok=False, error=str(exc))

    return GestureResponse(ok=True)


# ---------------------------------------------------------------------------
# Entry point (for direct `python server.py` execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=SIDECAR_PORT,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
