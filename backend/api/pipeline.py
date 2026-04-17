"""
Pipeline API endpoints for task execution.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.planner.execution_pipeline import ExecutionPipeline
from src.planner.openclaw_planner import OpenClawPlanner
from src.robot_api.mock_robot_api import MockRobotAPI
from backend.db.database import log_trajectory, get_trajectories
from backend.services.auth import get_current_user

router = APIRouter()


class ExecuteTaskRequest(BaseModel):
    """Request body for task execution."""
    task: str
    context: Optional[dict] = None


class PlanRequest(BaseModel):
    """Request body for planning only (no execution)."""
    task: str
    context: Optional[dict] = None


@router.post("/api/plan")
async def plan_task(request: PlanRequest) -> dict:
    """Plan a task and return skill sequence (no execution).

    This uses OpenClawPlanner to decompose the task into skills.
    """
    planner = OpenClawPlanner()
    skills = await planner.plan(request.task, request.context)
    return {
        "task": request.task,
        "intent": planner._classify_intent(request.task.lower()),
        "skills": skills,
    }


@router.post("/api/execute")
async def execute_task(request: ExecuteTaskRequest) -> dict:
    """Execute a task string through the full pipeline.

    Uses OpenClawPlanner to generate skill sequence,
    then executes each skill via the robot API.
    Trajectories are logged to database.
    """
    pipeline = ExecutionPipeline(MockRobotAPI(), OpenClawPlanner())
    pipeline.set_trajectory_logger(log_trajectory)
    result = await pipeline.execute(request.task, request.context)
    return result


@router.get("/api/trajectories")
async def list_trajectories(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get recent execution trajectories."""
    trajectories = await get_trajectories(limit=limit)
    return {"trajectories": trajectories, "count": len(trajectories)}


@router.get("/api/robot/status/public")
async def get_robot_status_public() -> dict:
    """Get robot status without authentication (for internal skill use).

    Returns basic robot state information including position, battery,
    and connection status. This endpoint is for internal skill use only.
    """
    from backend.services.robot import get_robot_service
    try:
        service = get_robot_service()
        status = await service.get_status()
        return {
            "connected": True,
            "position": status.position if hasattr(status, 'position') else {"x": 0, "y": 0, "z": 0},
            "battery": status.battery if hasattr(status, 'battery') else 100,
            "state": status.state.value if hasattr(status, 'state') else "unknown",
            "status": "ok"
        }
    except Exception as e:
        return {
            "connected": False,
            "position": {"x": 0, "y": 0, "z": 0},
            "battery": 0,
            "state": "unavailable",
            "status": str(e)
        }
