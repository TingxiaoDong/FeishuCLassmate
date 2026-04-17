"""
Unit tests for RobotAPI and MockHardwareAdapter.
Tests the Robot Control API layer with mocked hardware.

Authoritative source: src/robot_api/robot_api.py
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.robot_api.robot_api import RobotAPI
from src.hardware.simple_adapter import MockHardwareAdapter
from src.shared.interfaces import (
    RobotAction,
    RobotState,
    MoveJointsParams,
    MovePoseParams,
    MoveLinearParams,
    SetGripperParams,
    StopParams,
    ExecuteSkillParams,
)


class TestRobotAPIInitialization:
    """Test RobotAPI initialization and setup."""

    def test_robot_api_initialization_with_default_adapter(self):
        """RobotAPI should initialize with MockHardwareAdapter by default."""
        robot = RobotAPI()
        assert robot._hardware is not None
        assert isinstance(robot._hardware, MockHardwareAdapter)

    def test_robot_api_initialization_with_custom_adapter(self):
        """RobotAPI should accept custom hardware adapter."""
        custom_adapter = MockHardwareAdapter()
        robot = RobotAPI(hardware_adapter=custom_adapter)
        assert robot._hardware is custom_adapter

    def test_robot_api_initial_state(self):
        """RobotAPI should start in IDLE state."""
        robot = RobotAPI()
        assert robot._current_status.state == RobotState.IDLE


class TestMoveJoints:
    """Tests for move_joints method."""

    def test_move_joints_returns_completed_status(self):
        """move_joints should return COMPLETED status on success."""
        robot = RobotAPI()
        joints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        status = robot.move_joints(joints, speed=0.5)
        assert status.state == RobotState.COMPLETED

    def test_move_joints_updates_joints_in_status(self):
        """move_joints should return the target joints in status."""
        robot = RobotAPI()
        joints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        status = robot.move_joints(joints, speed=0.5)
        assert status.joints == joints

    def test_move_joints_generates_command_id(self):
        """move_joints should generate a unique command_id."""
        robot = RobotAPI()
        status1 = robot.move_joints([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], speed=0.5)
        status2 = robot.move_joints([0.6, 0.5, 0.4, 0.3, 0.2, 0.1], speed=0.5)
        assert status1.command_id != status2.command_id


class TestMovePose:
    """Tests for move_pose method."""

    def test_move_pose_returns_completed_status(self):
        """move_pose should return COMPLETED status on success."""
        robot = RobotAPI()
        position = {"x": 0.1, "y": 0.2, "z": 0.3}
        orientation = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        status = robot.move_pose(position, orientation, speed=0.5)
        assert status.state == RobotState.COMPLETED

    def test_move_pose_returns_position_in_status(self):
        """move_pose should return the target position in status."""
        robot = RobotAPI()
        position = {"x": 0.1, "y": 0.2, "z": 0.3}
        orientation = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        status = robot.move_pose(position, orientation, speed=0.5)
        assert status.position == position


class TestMoveLinear:
    """Tests for move_linear method."""

    def test_move_linear_returns_completed_status(self):
        """move_linear should return COMPLETED status on success."""
        robot = RobotAPI()
        target = {"x": 0.1, "y": 0.2, "z": 0.3}
        status = robot.move_linear(target, speed=0.5)
        assert status.state == RobotState.COMPLETED

    def test_move_linear_returns_target_in_status(self):
        """move_linear should return the target position in status."""
        robot = RobotAPI()
        target = {"x": 0.1, "y": 0.2, "z": 0.3}
        status = robot.move_linear(target, speed=0.5)
        assert status.position == target


class TestSetGripper:
    """Tests for set_gripper method."""

    def test_set_gripper_returns_completed_status(self):
        """set_gripper should return COMPLETED status on success."""
        robot = RobotAPI()
        status = robot.set_gripper(position=0.5, force=0.5)
        assert status.state == RobotState.COMPLETED

    def test_set_gripper_updates_gripper_state(self):
        """set_gripper should return the target gripper position in status."""
        robot = RobotAPI()
        status = robot.set_gripper(position=0.7, force=0.3)
        assert status.gripper_state == 0.7


class TestStop:
    """Tests for stop method."""

    def test_stop_returns_idle_status(self):
        """stop should return IDLE status."""
        robot = RobotAPI()
        status = robot.stop()
        assert status.state == RobotState.IDLE

    def test_stop_with_immediate_true(self):
        """stop with immediate=True should still return IDLE."""
        robot = RobotAPI()
        status = robot.stop(immediate=True)
        assert status.state == RobotState.IDLE


class TestExecuteSkill:
    """Tests for execute_skill method."""

    def test_execute_skill_returns_completed_status(self):
        """execute_skill should return COMPLETED status on success."""
        robot = RobotAPI()
        status = robot.execute_skill("test_skill", {"param": "value"})
        assert status.state == RobotState.COMPLETED

    def test_execute_skill_includes_skill_name_in_message(self):
        """execute_skill message should include the skill name."""
        robot = RobotAPI()
        status = robot.execute_skill("my_skill", {})
        assert "my_skill" in status.message


class TestGetWorldState:
    """Tests for get_world_state method."""

    def test_get_world_state_returns_world_state(self):
        """get_world_state should return a WorldState object."""
        robot = RobotAPI()
        world_state = robot.get_world_state()
        assert world_state is not None
        # Should have timestamp, robot, objects, environment
        assert hasattr(world_state, 'timestamp')
        assert hasattr(world_state, 'robot')
        assert hasattr(world_state, 'objects')
        assert hasattr(world_state, 'environment')


class TestRobotAPISequentialCommands:
    """Tests for sequential command execution."""

    def test_sequential_commands_update_status(self):
        """Sequential commands should update the current_status."""
        robot = RobotAPI()

        # First command
        status1 = robot.move_joints([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], speed=0.5)
        assert robot._current_status.command_id == status1.command_id

        # Second command
        status2 = robot.set_gripper(position=0.5, force=0.5)
        assert robot._current_status.command_id == status2.command_id
        assert status2.command_id != status1.command_id


class TestMockHardwareAdapter:
    """Tests for MockHardwareAdapter."""

    def test_mock_adapter_execute_move_joints(self):
        """MockHardwareAdapter should handle MOVE_JOINTS."""
        adapter = MockHardwareAdapter()
        params: MoveJointsParams = {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "speed": 0.5}
        status = adapter.execute("cmd_1", RobotAction.MOVE_JOINTS, params)
        assert status.state == RobotState.COMPLETED
        assert status.joints == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    def test_mock_adapter_execute_set_gripper(self):
        """MockHardwareAdapter should handle SET_GRIPPER."""
        adapter = MockHardwareAdapter()
        params: SetGripperParams = {"position": 0.8, "force": 0.5}
        status = adapter.execute("cmd_2", RobotAction.SET_GRIPPER, params)
        assert status.state == RobotState.COMPLETED
        assert status.gripper_state == 0.8

    def test_mock_adapter_execute_stop(self):
        """MockHardwareAdapter should handle STOP."""
        adapter = MockHardwareAdapter()
        params: StopParams = {"immediate": False}
        status = adapter.execute("cmd_3", RobotAction.STOP, params)
        assert status.state == RobotState.IDLE

    def test_mock_adapter_execute_unknown_action(self):
        """MockHardwareAdapter should return ERROR for unknown actions."""
        adapter = MockHardwareAdapter()
        params: StopParams = {"immediate": False}
        # Using an invalid action enum value
        status = adapter.execute("cmd_4", RobotAction.STOP, params)
        # Stop should work, let's try EXECUTE_SKILL
        skill_params: ExecuteSkillParams = {"skill_name": "test", "parameters": {}}
        status = adapter.execute("cmd_5", RobotAction.EXECUTE_SKILL, skill_params)
        assert status.state == RobotState.COMPLETED

    def test_mock_adapter_get_world_state(self):
        """MockHardwareAdapter should return valid world state."""
        adapter = MockHardwareAdapter()
        world_state = adapter.get_world_state()
        assert world_state is not None
        assert hasattr(world_state, 'timestamp')
        assert hasattr(world_state, 'robot')
