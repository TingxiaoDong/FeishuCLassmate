"""
Robot control API routes.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import (
    MoveJointsRequest,
    MovePoseRequest,
    MoveLinearRequest,
    SetGripperRequest,
    StopRequest,
    ExecuteSkillRequest,
    RobotStatusResponse,
    WorldStateResponse,
)
from backend.services.robot import get_robot_service
from backend.services.auth import get_current_user, require_role

router = APIRouter(prefix="/api/robot", tags=["robot"])


@router.get("/status", response_model=RobotStatusResponse)
async def get_robot_status(
    current_user: dict = Depends(get_current_user)
):
    """Get current robot status."""
    service = get_robot_service()
    return await service.get_status()


@router.get("/world-state", response_model=WorldStateResponse)
async def get_world_state(
    current_user: dict = Depends(get_current_user)
):
    """Get current world state."""
    service = get_robot_service()
    return await service.get_world_state()


@router.post("/move-joints", response_model=RobotStatusResponse)
async def move_joints(
    request: MoveJointsRequest,
    current_user: dict = Depends(require_role("operator"))
):
    """Move robot to joint positions."""
    service = get_robot_service()
    return await service.move_joints(request)


@router.post("/move-pose", response_model=RobotStatusResponse)
async def move_pose(
    request: MovePoseRequest,
    current_user: dict = Depends(require_role("operator"))
):
    """Move robot end-effector to pose."""
    service = get_robot_service()
    return await service.move_pose(request)


@router.post("/move-linear", response_model=RobotStatusResponse)
async def move_linear(
    request: MoveLinearRequest,
    current_user: dict = Depends(require_role("operator"))
):
    """Move robot in a straight line."""
    service = get_robot_service()
    return await service.move_linear(request)


@router.post("/gripper", response_model=RobotStatusResponse)
async def set_gripper(
    request: SetGripperRequest,
    current_user: dict = Depends(require_role("operator"))
):
    """Control gripper position and force."""
    service = get_robot_service()
    return await service.set_gripper(request)


@router.post("/stop", response_model=RobotStatusResponse)
async def stop_robot(
    request: StopRequest,
    current_user: dict = Depends(require_role("operator"))
):
    """Stop robot motion."""
    service = get_robot_service()
    return await service.stop(request)


@router.post("/execute-skill", response_model=RobotStatusResponse)
async def execute_skill(
    request: ExecuteSkillRequest,
    current_user: dict = Depends(require_role("engineer"))
):
    """Execute a named skill with parameters."""
    service = get_robot_service()
    return await service.execute_skill(request)
