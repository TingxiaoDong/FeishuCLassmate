"""
Skill Bank - Database operations for skill version tracking and verification.
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from backend.db.database import get_db


class SkillBank:
    """Manages skill version tracking and verification status."""

    def __init__(self):
        pass  # No longer holds db connection

    async def _with_db(self, func):
        """Execute a function with a database connection."""
        async with get_db() as db:
            return await func(db)

    async def add_skill_candidate(
        self,
        name: str,
        schema: dict,
        metadata: dict = None
    ) -> str:
        """
        Add a new skill candidate (unverified).

        Args:
            name: Skill name
            schema: Skill schema dictionary
            metadata: Optional metadata

        Returns:
            Skill ID
        """
        skill_id = str(uuid.uuid4())

        async def _do_insert(db):
            await db.execute(
                """
                INSERT INTO skill_banks (id, name, version, schema_json, status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    name,
                    "1.0.0",
                    json.dumps(schema),
                    "unverified",
                    json.dumps(metadata) if metadata else None
                )
            )
            await db.commit()
            return skill_id

        return await self._with_db(_do_insert)

    async def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get skill by ID."""
        async def _do_get(db):
            cursor = await db.execute(
                "SELECT * FROM skill_banks WHERE id = ?", (skill_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        return await self._with_db(_do_get)

    async def get_skill_by_name_version(self, name: str, version: str) -> Optional[dict]:
        """Get skill by name and version."""
        async def _do_get(db):
            cursor = await db.execute(
                "SELECT * FROM skill_banks WHERE name = ? AND version = ?",
                (name, version)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        return await self._with_db(_do_get)

    async def get_latest_skill(self, name: str) -> Optional[dict]:
        """Get latest version of a skill by name."""
        async def _do_get(db):
            cursor = await db.execute(
                """
                SELECT * FROM skill_banks
                WHERE name = ? AND status = 'verified'
                ORDER BY created_at DESC LIMIT 1
                """,
                (name,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)
        return await self._with_db(_do_get)

    async def list_verified_skills(self) -> list:
        """List all verified skills (latest version only)."""
        async def _do_list(db):
            cursor = await db.execute(
                """
                SELECT * FROM skill_banks s1
                WHERE status = 'verified'
                AND version = (
                    SELECT MAX(version) FROM skill_banks s2
                    WHERE s2.name = s1.name AND s2.status = 'verified'
                )
                ORDER BY name, created_at DESC
                """
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        return await self._with_db(_do_list)

    async def list_all_skills(self, include_unverified: bool = True) -> list:
        """List all skills."""
        async def _do_list(db):
            if include_unverified:
                cursor = await db.execute(
                    "SELECT * FROM skill_banks ORDER BY name, created_at DESC"
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM skill_banks WHERE status = 'verified' ORDER BY name, created_at DESC"
                )
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
        return await self._with_db(_do_list)

    async def verify_skill(self, skill_id: str, verified_by: str) -> bool:
        """
        Mark a skill as verified.

        Args:
            skill_id: Skill ID to verify
            verified_by: Username of verifier

        Returns:
            True if successful
        """
        skill = await self.get_skill(skill_id)
        if skill is None:
            return False

        async def _do_update(db):
            await db.execute(
                """
                UPDATE skill_banks
                SET status = 'verified', verified_at = ?, verified_by = ?
                WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), verified_by, skill_id)
            )
            await db.commit()
            return True

        return await self._with_db(_do_update)

    async def reject_skill(self, skill_id: str) -> bool:
        """Mark a skill as rejected (soft delete)."""
        skill = await self.get_skill(skill_id)
        if skill is None:
            return False

        async def _do_update(db):
            await db.execute(
                """
                UPDATE skill_banks
                SET status = 'rejected'
                WHERE id = ?
                """,
                (skill_id,)
            )
            await db.commit()
            return True

        return await self._with_db(_do_update)

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary."""
        return {
            "id": row["id"],
            "name": row["name"],
            "version": row["version"],
            "schema": json.loads(row["schema_json"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "verified_at": row["verified_at"],
            "verified_by": row["verified_by"],
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else None
        }


# Global instance
_skill_bank: Optional[SkillBank] = None


async def get_skill_bank() -> SkillBank:
    """Get or create the global SkillBank instance."""
    global _skill_bank
    if _skill_bank is None:
        _skill_bank = SkillBank()
    return _skill_bank


async def initialize_skill_bank():
    """Initialize skill bank with default skills from SKILL_REGISTRY."""
    from src.skill.skill_schemas import SKILL_REGISTRY, get_skill_schema

    bank = await get_skill_bank()

    for name, schema in SKILL_REGISTRY.items():
        # Check if already exists
        existing = await bank.get_latest_skill(name)
        if existing:
            continue

        schema_dict = {
            "name": schema.name,
            "description": schema.description,
            "skill_type": schema.skill_type.value,
            "inputs": {k: str(v) for k, v in schema.inputs.__annotations__.items()},
            "preconditions": schema.preconditions,
            "effects": schema.effects,
            "safety_constraints": schema.safety_constraints,
        }

        skill_id = await bank.add_skill_candidate(
            name=name,
            schema=schema_dict,
            metadata={"source": "SKILL_REGISTRY"}
        )

        # Auto-verify skills from SKILL_REGISTRY
        await bank.verify_skill(skill_id, "system")


# ---------- Helper Functions ----------

async def is_skill_verified(skill_name: str) -> bool:
    """Check if a skill is verified and usable."""
    bank = await get_skill_bank()
    skill = await bank.get_latest_skill(skill_name)
    return skill is not None and skill["status"] == "verified"
