"""
Pytest configuration for robotics system tests.

This conftest.py sets up the Python path and provides shared fixtures
for all test modules.
"""
import sys
from pathlib import Path

# Add src directory to path for imports
# conftest.py is at tests/conftest.py, so parents[1] is project root
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Add project root for imports like src.module
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pytest
from src.hardware.simulator import RobotSimulator, get_robot_simulator
from src.robot_api.robot_api import RobotAPI
from src.hardware.simple_adapter import MockHardwareAdapter
from src.shared.world_state import (
    WorldState,
    RobotState as WS_RobotState,
    Pose,
    WorldObject,
    Environment,
    WorkspaceBounds,
    ObjectState,
)


@pytest.fixture
def robot_simulator():
    """Provide a fresh RobotSimulator instance for each test."""
    simulator = RobotSimulator()
    yield simulator
    # Cleanup: reset simulator after test
    simulator.reset()


@pytest.fixture
def robot_api():
    """Provide a RobotAPI with MockHardwareAdapter for testing."""
    api = RobotAPI()  # Uses MockHardwareAdapter by default
    yield api


@pytest.fixture
def fresh_world_state():
    """Provide a fresh WorldState instance."""
    robot_state = WS_RobotState(
        joint_positions=[0.0] * 6,
        end_effector_pose=Pose(x=0.0, y=0.0, z=0.0),
        gripper_width=0.0,
        gripper_force=0.0,
    )
    return WorldState(
        timestamp=0.0,
        robot=robot_state,
        objects=[],
        environment=Environment(workspace_bounds=WorkspaceBounds()),
    )


@pytest.fixture
def world_state_with_objects():
    """Provide a WorldState with test objects."""
    robot_state = WS_RobotState(
        joint_positions=[0.0] * 6,
        end_effector_pose=Pose(x=0.1, y=0.1, z=0.1),
        gripper_width=0.0,
        gripper_force=0.0,
    )
    objects = [
        WorldObject(
            id="block_1",
            type="block",
            pose=Pose(x=0.0, y=0.0, z=0.0),
            color="red",
            state=ObjectState.VISIBLE,
        ),
        WorldObject(
            id="block_2",
            type="block",
            pose=Pose(x=0.1, y=0.0, z=0.0),
            color="blue",
            state=ObjectState.VISIBLE,
        ),
    ]
    return WorldState(
        timestamp=0.0,
        robot=robot_state,
        objects=objects,
        environment=Environment(workspace_bounds=WorkspaceBounds()),
    )


@pytest.fixture
def get_default_simulator():
    """Provide the singleton default simulator."""
    return get_robot_simulator
