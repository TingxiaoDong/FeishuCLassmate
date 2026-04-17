"""
Pipeline API endpoints for task execution.
"""
from fastapi import APIRouter

from src.planner.execution_pipeline import ExecutionPipeline
from src.robot_api.mock_robot_api import MockRobotAPI

router = APIRouter()


@router.post("/api/execute")
async def execute_task(task: str) -> dict:
    """Execute a task string through the pipeline."""
    pipeline = ExecutionPipeline(MockRobotAPI())
    result = await pipeline.execute(task)
    return result
