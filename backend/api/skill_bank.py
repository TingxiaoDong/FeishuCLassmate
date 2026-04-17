"""
Skill Bank API - Version tracking and verification workflow.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, Depends, HTTPException

from backend.db.skill_bank import (
    get_skill_bank,
    initialize_skill_bank,
    is_skill_verified,
)
from backend.models.schemas import (
    SkillCandidateCreate,
    SkillCandidateResponse,
    SkillListResponse,
    SkillVerifyRequest,
)
from backend.services.auth import get_current_user, require_role

router = APIRouter(prefix="/api/skills", tags=["skill-bank"])


@router.on_event("startup")
async def startup_event():
    """Initialize skill bank with default skills on startup."""
    await initialize_skill_bank()


@router.get("", response_model=SkillListResponse)
async def list_verified_skills(current_user: dict = Depends(get_current_user)):
    """
    List all verified skills.

    Only verified skills can be used by the system.
    """
    bank = await get_skill_bank()
    skills = await bank.list_verified_skills()
    return {"skills": skills}


@router.get("/all", response_model=SkillListResponse)
async def list_all_skills(current_user: dict = Depends(get_current_user)):
    """List all skills including unverified candidates."""
    bank = await get_skill_bank()
    skills = await bank.list_all_skills(include_unverified=True)
    return {"skills": skills}


@router.post("/candidates", response_model=SkillCandidateResponse)
async def create_skill_candidate(
    candidate: SkillCandidateCreate,
    current_user: dict = Depends(require_role("engineer"))
):
    """
    Store a new skill candidate from MetaClaw.

    Skills are stored as unverified until Code Reviewer approves.
    """
    bank = await get_skill_bank()
    skill_id = await bank.add_skill_candidate(
        name=candidate.name,
        schema=candidate.schema,
        metadata=candidate.metadata
    )
    skill = await bank.get_skill(skill_id)
    return skill


@router.post("/verify/{skill_id}", response_model=SkillCandidateResponse)
async def verify_skill(
    skill_id: str,
    current_user: dict = Depends(require_role("reviewer"))
):
    """
    Mark a skill as verified (Code Reviewer only).

    Only verified skills are usable by the planner.
    """
    bank = await get_skill_bank()
    success = await bank.verify_skill(skill_id, current_user.get("username", "unknown"))
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill = await bank.get_skill(skill_id)
    return skill


@router.get("/{skill_name}", response_model=SkillCandidateResponse)
async def get_skill_by_name(
    skill_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get latest verified version of a skill by name."""
    bank = await get_skill_bank()
    skill = await bank.get_latest_skill(skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return skill
