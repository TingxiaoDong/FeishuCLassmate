"""
Pytest configuration and fixtures for skill tests.

This provides fixtures for skill execution testing with mocked RobotAPI.
"""
import pytest
import sys
from pathlib import Path

# Ensure src is in path
SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.robot_api.robot_api import RobotAPI
from src.hardware.simulator import RobotSimulator
from src.shared.world_state import (
    WorldState,
    RobotState as WS_RobotState,
    Pose,
    WorldObject,
    Environment,
    WorkspaceBounds,
    ObjectState,
)
from src.skill.skill_base import SkillContext


# ============================================================
# Sample Skill Inputs
# ============================================================

GRASP_INPUT = {
    "object_id": "test_block",
    "approach_height": 0.1,
    "grip_force": 50.0,
}

MOVE_TO_INPUT = {
    "target_x": 0.5,
    "target_y": 0.0,
    "target_z": 0.1,
    "target_rx": 0.0,
    "target_ry": 0.0,
    "target_rz": 0.0,
    "speed": 1.0,
    "motion_type": "linear",
}

PLACE_INPUT = {
    "object_id": "test_block",
    "target_x": 0.5,
    "target_y": 0.0,
    "target_z": 0.0,
    "approach_height": 0.1,
}

RELEASE_INPUT = {
    "object_id": "test_block",
    "gripper_open_width": 1.0,
}

ROTATE_INPUT = {
    "axis": "z",
    "angle": 1.57,  # 90 degrees
    "speed": 0.5,
}

STOP_INPUT = {
    "emergency": False,
}


# ============================================================
# World State Fixtures
# ============================================================

@pytest.fixture
def world_state_for_grasp():
    """WorldState with a visible object for grasp testing."""
    robot_state = WS_RobotState(
        joint_positions=[0.0] * 6,
        end_effector_pose=Pose(x=0.0, y=0.0, z=0.1),
        gripper_width=1.0,  # Open
        gripper_force=0.0,
    )
    objects = [
        WorldObject(
            id="test_block",
            type="block",
            pose=Pose(x=0.0, y=0.0, z=0.0),
            color="red",
            state=ObjectState.VISIBLE,
        ),
    ]
    environment = Environment(workspace_bounds=WorkspaceBounds())
    return WorldState(
        timestamp=0.0,
        robot=robot_state,
        objects=objects,
        environment=environment,
    )


@pytest.fixture
def world_state_for_place():
    """WorldState with a grasped object for place testing."""
    robot_state = WS_RobotState(
        joint_positions=[0.0] * 6,
        end_effector_pose=Pose(x=0.0, y=0.0, z=0.1),
        gripper_width=0.0,  # Closed - holding object
        gripper_force=50.0,
    )
    objects = [
        WorldObject(
            id="test_block",
            type="block",
            pose=Pose(x=0.0, y=0.0, z=0.0),
            color="red",
            state=ObjectState.GRASPED,
        ),
    ]
    environment = Environment(workspace_bounds=WorkspaceBounds())
    return WorldState(
        timestamp=0.0,
        robot=robot_state,
        objects=objects,
        environment=environment,
    )


# ============================================================
# RobotAPI Fixtures
# ============================================================

@pytest.fixture
def skill_robot_api():
    """RobotAPI configured for skill testing."""
    return RobotAPI()  # Uses MockHardwareAdapter


@pytest.fixture
def skill_robot_api_with_simulator():
    """RobotAPI connected to RobotSimulator for integration testing."""
    simulator = RobotSimulator()
    api = RobotAPI(hardware_adapter=simulator)
    return api, simulator


# ============================================================
# Skill Fixtures
# ============================================================

@pytest.fixture
def grasp_skill(skill_robot_api):
    """GraspSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import GraspSkill
    return GraspSkill(robot_api=skill_robot_api)


@pytest.fixture
def move_to_skill(skill_robot_api):
    """MoveToSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import MoveToSkill
    return MoveToSkill(robot_api=skill_robot_api)


@pytest.fixture
def place_skill(skill_robot_api):
    """PlaceSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import PlaceSkill
    return PlaceSkill(robot_api=skill_robot_api)


@pytest.fixture
def release_skill(skill_robot_api):
    """ReleaseSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import ReleaseSkill
    return ReleaseSkill(robot_api=skill_robot_api)


@pytest.fixture
def rotate_skill(skill_robot_api):
    """RotateSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import RotateSkill
    return RotateSkill(robot_api=skill_robot_api)


@pytest.fixture
def stop_skill(skill_robot_api):
    """StopSkill instance with mocked RobotAPI."""
    from src.skill.skill_implementations import StopSkill
    return StopSkill(robot_api=skill_robot_api)


# ============================================================
# Skill Context Fixture
# ============================================================

@pytest.fixture
def skill_context():
    """SkillContext for skill execution tests."""
    import time
    return SkillContext(
        command_id="test_cmd_123",
        timestamp=time.time(),
        metadata={"test_key": "test_value"}
    )
