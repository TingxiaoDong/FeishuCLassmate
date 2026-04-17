"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RobotState(str, Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class SkillStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# ---------- Robot API Models ----------

class Position3D(BaseModel):
    x: float
    y: float
    z: float


class Orientation3D(BaseModel):
    roll: float
    pitch: float
    yaw: float


class MoveJointsRequest(BaseModel):
    joints: list[float] = Field(..., min_length=6, max_length=6)
    speed: float = Field(default=0.5, gt=0, le=1.0)


class MovePoseRequest(BaseModel):
    position: Position3D
    orientation: Orientation3D
    speed: float = Field(default=0.5, gt=0, le=1.0)


class MoveLinearRequest(BaseModel):
    target: Position3D
    speed: float = Field(default=0.5, gt=0, le=1.0)


class SetGripperRequest(BaseModel):
    position: float = Field(..., ge=0, le=1.0)
    force: float = Field(default=50.0, ge=0, le=100.0)


class StopRequest(BaseModel):
    immediate: bool = False


class ExecuteSkillRequest(BaseModel):
    skill_name: str
    parameters: dict = Field(default_factory=dict)


class RobotStatusResponse(BaseModel):
    command_id: str
    state: RobotState
    position: dict
    joints: list[float]
    gripper_state: float
    sensor_data: dict
    message: str


class WorldStateResponse(BaseModel):
    timestamp: float
    robot: dict
    objects: list[dict]
    environment: dict


# ---------- Session Models ----------

class SessionCreate(BaseModel):
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    user_id: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    status: str


# ---------- Auth Models ----------

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UserResponse(BaseModel):
    id: str
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
