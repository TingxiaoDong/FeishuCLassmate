"""
Database configuration and connection management.
"""
import aiosqlite
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "robotics.db")


async def init_database():
    """Initialize database with schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Skill execution logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # World state history
        await db.execute("""
            CREATE TABLE IF NOT EXISTS world_state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                state_json TEXT NOT NULL
            )
        """)

        # Robot control sessions
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT
            )
        """)

        # Users table for authentication
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT DEFAULT 'operator',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trajectory logs for full execution tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trajectories (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                skill_sequence TEXT NOT NULL,
                state_changes TEXT,
                final_result TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms REAL
            )
        """)

        # Skill Bank - version tracking and verification
        await db.execute("""
            CREATE TABLE IF NOT EXISTS skill_banks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT '1.0.0',
                schema_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unverified',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                verified_by TEXT,
                metadata_json TEXT
            )
        """)

        await db.commit()


@asynccontextmanager
async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def log_trajectory(
    trajectory_id: str,
    task: str,
    skill_sequence: list,
    state_changes: list,
    final_result: dict,
    duration_ms: float = None
):
    """Log a full execution trajectory to the database."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO trajectories
            (id, task, skill_sequence, state_changes, final_result, duration_ms, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                trajectory_id,
                task,
                json.dumps(skill_sequence),
                json.dumps(state_changes) if state_changes else None,
                json.dumps(final_result),
                duration_ms
            )
        )
        await db.commit()


async def get_trajectory(trajectory_id: str) -> dict:
    """Get a trajectory by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM trajectories WHERE id = ?", (trajectory_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "task": row["task"],
            "skill_sequence": json.loads(row["skill_sequence"]),
            "state_changes": json.loads(row["state_changes"]) if row["state_changes"] else [],
            "final_result": json.loads(row["final_result"]),
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "duration_ms": row["duration_ms"]
        }


async def get_trajectories(limit: int = 50) -> list:
    """Get recent trajectories."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM trajectories ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "task": row["task"],
                "skill_sequence": json.loads(row["skill_sequence"]),
                "final_result": json.loads(row["final_result"]),
                "started_at": row["started_at"],
                "duration_ms": row["duration_ms"]
            }
            for row in rows
        ]
