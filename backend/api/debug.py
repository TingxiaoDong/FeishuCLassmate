"""
Debug and diagnostic API routes.
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.services.auth import get_current_user, require_role
from backend.db.database import get_db
from backend.services.robot import get_robot_service

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/world-state/history")
async def get_world_state_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_role("engineer"))
):
    """Get world state history for debugging."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, timestamp, state_json
            FROM world_state_history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = await cursor.fetchall()

    return {
        "history": [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "state": row["state_json"]
            }
            for row in rows
        ],
        "count": len(rows)
    }


@router.get("/robot/debug-status")
async def get_robot_debug_status(
    current_user: dict = Depends(require_role("engineer"))
):
    """Get detailed robot debug information."""
    service = get_robot_service()

    async with get_db() as db:
        # Get recent executions for this session
        cursor = await db.execute(
            """
            SELECT command_id, skill_name, status, message, started_at
            FROM skill_executions
            ORDER BY started_at DESC
            LIMIT 10
            """
        )
        recent = await cursor.fetchall()

    return {
        "robot_api": {
            "status": "operational",
            "hardware_adapter": "MockHardwareAdapter"
        },
        "recent_commands": [
            {
                "command_id": row["command_id"],
                "skill_name": row["skill_name"],
                "status": row["status"],
                "message": row["message"],
                "started_at": row["started_at"]
            }
            for row in recent
        ],
        "timestamp": time.time()
    }


@router.post("/reset-session")
async def reset_session(
    session_id: str,
    current_user: dict = Depends(require_role("admin"))
):
    """Reset/clear a session (admin only)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET status = 'reset' WHERE id = ?",
            (session_id,)
        )
        await db.commit()

    return {"message": f"Session {session_id} reset"}


@router.get("/stats/skill-usage")
async def get_skill_usage_stats(
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """Get skill usage statistics over time period."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                skill_name,
                COUNT(*) as execution_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failure_count
            FROM skill_executions
            WHERE started_at > ?
            GROUP BY skill_name
            ORDER BY execution_count DESC
            """,
            (time.time() - (days * 86400),)
        )
        rows = await cursor.fetchall()

    return {
        "period_days": days,
        "skill_stats": [
            {
                "skill_name": row["skill_name"],
                "total_executions": row["execution_count"],
                "successes": row["success_count"],
                "failures": row["failure_count"],
                "success_rate": row["success_count"] / row["execution_count"] if row["execution_count"] > 0 else 0
            }
            for row in rows
        ]
    }
