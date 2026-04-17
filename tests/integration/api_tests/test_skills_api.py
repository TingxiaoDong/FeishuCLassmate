"""
Integration tests for Skills API endpoints.

Tests the /api/skills/* endpoints using FastAPI dependency overrides.

Authoritative source: backend/api/skills.py
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient


# Create test user
TEST_USER = {"username": "test", "role": "engineer"}


class TestSkillsListEndpoint:
    """Tests for GET /api/skills/list."""

    def test_list_skills_returns_skills(self):
        """Should return list of available skills."""
        from backend.api.skills import router

        app = FastAPI()
        app.include_router(router)

        # Override auth
        from backend.services.auth import get_current_user
        async def mock_user():
            return TEST_USER
        app.dependency_overrides[get_current_user] = mock_user

        client = TestClient(app)
        response = client.get("/api/skills/list")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert isinstance(data["skills"], list)


class TestSkillsExecuteEndpoint:
    """Tests for POST /api/skills/execute."""

    @pytest.mark.skip(reason="Robot service uses database logging - complex to mock")
    def test_execute_skill_success(self):
        """Should execute skill and return RobotStatusResponse."""
        pass

    def test_execute_skill_not_found(self):
        """Should return 404 for unknown skill."""
        from backend.api.skills import router

        app = FastAPI()
        app.include_router(router)

        from backend.services.auth import get_current_user, require_role
        async def mock_user():
            return TEST_USER
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        from backend.services.robot import get_robot_service
        app.dependency_overrides[get_robot_service] = lambda: Mock()

        client = TestClient(app)
        response = client.post(
            "/api/skills/execute",
            json={"skill_name": "unknown_skill", "parameters": {}}
        )

        assert response.status_code == 404


class TestSkillSchemaEndpoint:
    """Tests for GET /api/skills/{skill_name}/schema."""

    def test_get_schema_not_found(self):
        """Should return 404 for unknown skill."""
        from backend.api.skills import router

        app = FastAPI()
        app.include_router(router)

        from backend.services.auth import get_current_user
        async def mock_user():
            return TEST_USER
        app.dependency_overrides[get_current_user] = mock_user

        client = TestClient(app)
        response = client.get("/api/skills/unknown_skill/schema")

        assert response.status_code == 404


class TestSkillInfoEndpoint:
    """Tests for GET /api/skills/{skill_name}."""

    def test_get_skill_info_not_found(self):
        """Should return error for unknown skill."""
        from backend.api.skills import router

        app = FastAPI()
        app.include_router(router)

        from backend.services.auth import get_current_user
        async def mock_user():
            return TEST_USER
        app.dependency_overrides[get_current_user] = mock_user

        client = TestClient(app)
        response = client.get("/api/skills/unknown_skill")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
