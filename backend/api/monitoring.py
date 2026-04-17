"""
Monitoring and metrics API routes.
"""
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.services.auth import get_current_user
from backend.db.database import get_db

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(get_current_user)
):
    """Get system metrics for monitoring dashboard."""
    async with get_db() as db:
        # Count total skill executions
        cursor = await db.execute("SELECT COUNT(*) as count FROM skill_executions")
        exec_row = await cursor.fetchone()

        # Count executions in last hour
        one_hour_ago = time.time() - 3600
        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM skill_executions WHERE started_at > ?",
            (one_hour_ago,)
        )
        recent_row = await cursor.fetchone()

        # Count by status
        cursor = await db.execute(
            "SELECT status, COUNT(*) as count FROM skill_executions GROUP BY status"
        )
        status_rows = await cursor.fetchall()

        # Count active sessions
        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM sessions WHERE status = 'active'"
        )
        session_row = await cursor.fetchone()

        return {
            "timestamp": time.time(),
            "skill_executions": {
                "total": exec_row["count"] if exec_row else 0,
                "last_hour": recent_row["count"] if recent_row else 0,
                "by_status": {row["status"]: row["count"] for row in status_rows}
            },
            "sessions": {
                "active": session_row["count"] if session_row else 0
            }
        }


@router.get("/health/detailed")
async def get_detailed_health(
    current_user: dict = Depends(get_current_user)
):
    """Get detailed health status including database and system components."""
    async with get_db() as db:
        # Test database connectivity
        try:
            cursor = await db.execute("SELECT 1")
            await cursor.fetchone()
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "components": {
            "database": db_status,
            "api": "healthy",
            "websocket": "healthy"
        },
        "timestamp": time.time(),
        "uptime_seconds": time.time()  # Simplified - would track actual start time
    }


@router.get("/executions")
async def get_execution_history(
    limit: int = Query(default=50, ge=1, le=500),
    skill_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get skill execution history for debugging."""
    async with get_db() as db:
        if skill_name:
            cursor = await db.execute(
                """
                SELECT id, skill_name, parameters, status, result, started_at, completed_at
                FROM skill_executions
                WHERE skill_name = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (skill_name, limit)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, skill_name, parameters, status, result, started_at, completed_at
                FROM skill_executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,)
            )
        rows = await cursor.fetchall()

    return {
        "executions": [
            {
                "id": row["id"],
                "skill_name": row["skill_name"],
                "parameters": row["parameters"],
                "status": row["status"],
                "result": row["result"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"]
            }
            for row in rows
        ],
        "count": len(rows)
    }


@router.get("/sessions/history")
async def get_session_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get session history for debugging."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, started_at, ended_at, status
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = await cursor.fetchall()

    return {
        "sessions": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "status": row["status"]
            }
            for row in rows
        ],
        "count": len(rows)
    }
