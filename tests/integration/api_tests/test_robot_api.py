"""
Integration tests for Robot API endpoints.

Tests the /api/robot/* endpoints using FastAPI dependency overrides.

Authoritative source: backend/api/robot.py
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient


# Create test users
TEST_USER_OPERATOR = {"username": "test", "role": "operator"}
TEST_USER_ENGINEER = {"username": "test", "role": "engineer"}


class TestRobotStatusEndpoint:
    """Tests for GET /api/robot/status."""

    def test_get_status_returns_robot_status(self):
        """Should return current robot status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user

        mock_service = Mock()
        mock_service.get_status = AsyncMock(return_value=RobotStatusResponse(
            command_id="status_1",
            state=RobotState.IDLE,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0] * 6,
            gripper_state=0.0,
            sensor_data={},
            message="Idle"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.get("/api/robot/status")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "idle"


class TestRobotWorldStateEndpoint:
    """Tests for GET /api/robot/world-state."""

    def test_get_world_state_returns_state(self):
        """Should return current world state."""
        from backend.api.robot import router
        from backend.models.schemas import WorldStateResponse
        from backend.services.auth import get_current_user
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user

        mock_service = Mock()
        mock_service.get_world_state = AsyncMock(return_value=WorldStateResponse(
            timestamp=12345.0,
            robot={"joint_positions": [0.0] * 6},
            objects=[],
            environment={}
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.get("/api/robot/world-state")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "robot" in data


class TestMoveJointsEndpoint:
    """Tests for POST /api/robot/move-joints."""

    def test_move_joints_success(self):
        """Should move joints and return status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user, require_role
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        mock_service = Mock()
        mock_service.move_joints = AsyncMock(return_value=RobotStatusResponse(
            command_id="move_joints_1",
            state=RobotState.COMPLETED,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            gripper_state=0.0,
            sensor_data={},
            message="Moved to joints"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.post(
            "/api/robot/move-joints",
            json={"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "speed": 0.5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


class TestMoveLinearEndpoint:
    """Tests for POST /api/robot/move-linear."""

    def test_move_linear_success(self):
        """Should move linearly and return status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user, require_role
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        mock_service = Mock()
        mock_service.move_linear = AsyncMock(return_value=RobotStatusResponse(
            command_id="move_linear_1",
            state=RobotState.COMPLETED,
            position={"x": 0.5, "y": 0.0, "z": 0.1},
            joints=[0.0] * 6,
            gripper_state=0.0,
            sensor_data={},
            message="Moved linearly"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.post(
            "/api/robot/move-linear",
            json={"target": {"x": 0.5, "y": 0.0, "z": 0.1}, "speed": 0.5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


class TestGripperEndpoint:
    """Tests for POST /api/robot/gripper."""

    def test_set_gripper_success(self):
        """Should set gripper and return status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user, require_role
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        mock_service = Mock()
        mock_service.set_gripper = AsyncMock(return_value=RobotStatusResponse(
            command_id="gripper_1",
            state=RobotState.COMPLETED,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0] * 6,
            gripper_state=0.8,
            sensor_data={},
            message="Gripper set"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.post(
            "/api/robot/gripper",
            json={"position": 0.8, "force": 50.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"


class TestStopEndpoint:
    """Tests for POST /api/robot/stop."""

    def test_stop_robot_success(self):
        """Should stop robot and return status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user, require_role
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_OPERATOR
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        mock_service = Mock()
        mock_service.stop = AsyncMock(return_value=RobotStatusResponse(
            command_id="stop_1",
            state=RobotState.IDLE,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0] * 6,
            gripper_state=0.0,
            sensor_data={},
            message="Stopped"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.post("/api/robot/stop", json={"immediate": False})

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "idle"


class TestExecuteSkillEndpoint:
    """Tests for POST /api/robot/execute-skill."""

    def test_execute_skill_success(self):
        """Should execute skill and return status."""
        from backend.api.robot import router
        from backend.models.schemas import RobotStatusResponse, RobotState
        from backend.services.auth import get_current_user, require_role
        from backend.services.robot import get_robot_service

        app = FastAPI()
        app.include_router(router)

        async def mock_user():
            return TEST_USER_ENGINEER
        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[require_role] = lambda role: mock_user

        mock_service = Mock()
        mock_service.execute_skill = AsyncMock(return_value=RobotStatusResponse(
            command_id="skill_1",
            state=RobotState.COMPLETED,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0] * 6,
            gripper_state=0.0,
            sensor_data={},
            message="Skill executed"
        ))

        async def mock_get_service():
            return mock_service

        app.dependency_overrides[get_robot_service] = mock_get_service

        client = TestClient(app)
        response = client.post(
            "/api/robot/execute-skill",
            json={"skill_name": "grasp", "parameters": {"object_id": "test"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"
