"""
Skill-related API routes.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.services.auth import get_current_user, require_role
from backend.services.robot import get_robot_service
from backend.models.schemas import ExecuteSkillRequest, RobotStatusResponse
from src.skill.skill_schemas import SKILL_REGISTRY, get_skill_schema, list_skills

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("/list")
async def list_all_skills(current_user: dict = Depends(get_current_user)):
    """List all available skills."""
    return {"skills": list_skills()}


@router.post("/execute", response_model=RobotStatusResponse)
async def execute_skill(
    request: ExecuteSkillRequest,
    current_user: dict = Depends(require_role("engineer"))
):
    """Execute a named skill with parameters.

    This endpoint provides an alternative to /api/robot/execute-skill
    as specified in the architecture document.
    """
    # Validate skill exists
    schema = get_skill_schema(request.skill_name)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Skill '{request.skill_name}' not found")

    service = get_robot_service()
    return await service.execute_skill(request)


@router.get("/{skill_name}/schema")
async def get_skill_schema_endpoint(skill_name: str, current_user: dict = Depends(get_current_user)):
    """Get detailed schema for a specific skill.

    Alias for /api/skills/{skill_name} to match frontend expectations.
    """
    schema = get_skill_schema(skill_name)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {
        "name": schema.name,
        "description": schema.description,
        "skill_type": schema.skill_type.value,
        "inputs": schema.inputs.__annotations__,
        "preconditions": schema.preconditions,
        "effects": schema.effects,
        "safety_constraints": schema.safety_constraints,
    }


@router.get("/{skill_name}")
async def get_skill_info(skill_name: str, current_user: dict = Depends(get_current_user)):
    """Get detailed information about a specific skill."""
    schema = get_skill_schema(skill_name)
    if schema is None:
        return {"error": f"Skill '{skill_name}' not found"}
    return {
        "name": schema.name,
        "description": schema.description,
        "skill_type": schema.skill_type.value,
        "inputs": schema.inputs.__annotations__,
        "preconditions": schema.preconditions,
        "effects": schema.effects,
        "safety_constraints": schema.safety_constraints,
    }
