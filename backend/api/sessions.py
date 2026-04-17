"""
Session management API routes.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.db.database import get_db
from backend.models.schemas import SessionCreate, SessionResponse
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new robot control session."""
    session_id = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO sessions (id, user_id, status)
            VALUES (?, ?, 'active')
            """,
            (session_id, request.user_id or current_user.get("username"))
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT id, user_id, started_at, ended_at, status FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()

    return SessionResponse(
        id=row["id"],
        user_id=row["user_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        status=row["status"]
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get session details."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, user_id, started_at, ended_at, status FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        id=row["id"],
        user_id=row["user_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        status=row["status"]
    )


@router.delete("/{session_id}")
async def end_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End a robot control session."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT status FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if row["status"] == "ended":
            raise HTTPException(status_code=400, detail="Session already ended")

        await db.execute(
            """
            UPDATE sessions SET status = 'ended', ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session_id,)
        )
        await db.commit()

    return {"message": "Session ended successfully"}


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user)
):
    """List all sessions for current user."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, started_at, ended_at, status
            FROM sessions
            WHERE user_id = ?
            ORDER BY started_at DESC
            """,
            (current_user.get("username"),)
        )
        rows = await cursor.fetchall()

    return [
        SessionResponse(
            id=row["id"],
            user_id=row["user_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"]
        )
        for row in rows
    ]
