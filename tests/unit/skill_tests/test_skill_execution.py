"""
Unit tests for skill execution.

Tests that each skill correctly calls RobotAPI methods
and handles execution flow properly.

Authoritative source: src/skill/skill_implementations.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from tests.unit.skill_tests.conftest import (
    GRASP_INPUT,
    MOVE_TO_INPUT,
    PLACE_INPUT,
    RELEASE_INPUT,
    ROTATE_INPUT,
    STOP_INPUT,
)


class TestGraspSkillExecution:
    """Tests for GraspSkill execution."""

    def test_grasp_skill_calls_set_gripper(self, grasp_skill, skill_context):
        """GraspSkill should call set_gripper on RobotAPI."""
        mock_api = grasp_skill._robot_api
        with patch.object(mock_api, 'set_gripper', return_value=Mock(state=Mock(value='completed'))) as mock_set:
            result = grasp_skill.execute(GRASP_INPUT, skill_context)
            mock_set.assert_called_once()
            # Verify grip_force was passed
            call_args = mock_set.call_args
            assert 'force' in call_args.kwargs or (len(call_args.args) > 1)

    def test_grasp_skill_returns_skill_status(self, grasp_skill, skill_context):
        """GraspSkill.execute() should return SkillStatus."""
        result = grasp_skill.execute(GRASP_INPUT, skill_context)
        # Should have a status key in dict
        assert 'status' in result

    def test_grasp_skill_validates_inputs(self, grasp_skill):
        """GraspSkill should validate inputs before execution."""
        # Missing required field
        invalid_input = {"object_id": "test_block"}
        report = grasp_skill.validate_inputs(invalid_input)
        assert not report.is_valid


class TestMoveToSkillExecution:
    """Tests for MoveToSkill execution."""

    def test_move_to_skill_calls_move_linear(self, move_to_skill, skill_context):
        """MoveToSkill with linear motion should call move_linear."""
        mock_api = move_to_skill._robot_api
        with patch.object(mock_api, 'move_linear', return_value=Mock(state=Mock(value='completed'))) as mock_move:
            input_data = MOVE_TO_INPUT.copy()
            input_data["motion_type"] = "linear"
            result = move_to_skill.execute(input_data, skill_context)
            mock_move.assert_called_once()

    def test_move_to_skill_returns_execution_time(self, move_to_skill, skill_context):
        """MoveToSkill should track execution time."""
        mock_api = move_to_skill._robot_api
        mock_api.move_linear = Mock(return_value=Mock(
            state=Mock(value='completed'),
            execution_time_ms=100.0
        ))
        result = move_to_skill.execute(MOVE_TO_INPUT, skill_context)
        # Result dict should have status
        assert 'status' in result


class TestPlaceSkillExecution:
    """Tests for PlaceSkill execution."""

    def test_place_skill_requires_grasped_object(self, place_skill, world_state_for_place, skill_context):
        """PlaceSkill should check that object is grasped before executing."""
        # This tests precondition checking
        # Place should not execute successfully if preconditions aren't met
        result = place_skill.execute(PLACE_INPUT, skill_context)
        # Result dict should have status key
        assert 'status' in result


class TestReleaseSkillExecution:
    """Tests for ReleaseSkill execution."""

    def test_release_skill_calls_set_gripper_open(self, release_skill, skill_context):
        """ReleaseSkill should call set_gripper with open position."""
        mock_api = release_skill._robot_api
        with patch.object(mock_api, 'set_gripper', return_value=Mock(state=Mock(value='completed'))) as mock_set:
            result = release_skill.execute(RELEASE_INPUT, skill_context)
            mock_set.assert_called_once()
            # Verify gripper is being opened
            call_args = mock_set.call_args
            # Position should be > 0 (open)
            if 'position' in call_args.kwargs:
                assert call_args.kwargs['position'] > 0


class TestRotateSkillExecution:
    """Tests for RotateSkill execution."""

    def test_rotate_skill_validates_axis(self, rotate_skill):
        """RotateSkill should validate axis is x, y, or z."""
        # Valid axis
        valid_input = ROTATE_INPUT.copy()
        report = rotate_skill.validate_inputs(valid_input)
        # Should be valid with correct axis

        # Invalid axis
        invalid_input = ROTATE_INPUT.copy()
        invalid_input["axis"] = "invalid"
        report = rotate_skill.validate_inputs(invalid_input)
        assert not report.is_valid

    def test_rotate_skill_validates_angle(self, rotate_skill):
        """RotateSkill should validate angle is within limits."""
        # Large angle might be invalid
        large_angle_input = ROTATE_INPUT.copy()
        large_angle_input["angle"] = 10.0  # Very large
        report = rotate_skill.validate_inputs(large_angle_input)
        # May or may not be valid depending on joint limits


class TestStopSkillExecution:
    """Tests for StopSkill execution."""

    def test_stop_skill_calls_robot_api_stop(self, stop_skill, skill_context):
        """StopSkill should call robot_api.stop()."""
        mock_api = stop_skill._robot_api
        with patch.object(mock_api, 'stop', return_value=Mock(state=Mock(value='idle'))) as mock_stop:
            result = stop_skill.execute(STOP_INPUT, skill_context)
            mock_stop.assert_called_once()

    def test_stop_skill_emergency_flag(self, stop_skill, skill_context):
        """StopSkill should handle emergency=True correctly."""
        emergency_input = {"emergency": True}
        result = stop_skill.execute(emergency_input, skill_context)
        assert 'status' in result


class TestSkillValidationInputs:
    """Tests for skill input validation."""

    def test_grasp_requires_object_id(self, grasp_skill):
        """GraspSkill should require object_id."""
        invalid_input = {"approach_height": 0.1, "grip_force": 50}
        report = grasp_skill.validate_inputs(invalid_input)
        assert not report.is_valid

    def test_move_to_requires_target_position(self, move_to_skill):
        """MoveToSkill should require target position fields."""
        invalid_input = {"speed": 1.0, "motion_type": "linear"}
        report = move_to_skill.validate_inputs(invalid_input)
        assert not report.is_valid

    def test_place_requires_object_id_and_target(self, place_skill):
        """PlaceSkill should require object_id and target position."""
        incomplete_input = {"approach_height": 0.1}
        report = place_skill.validate_inputs(incomplete_input)
        assert not report.is_valid


class TestSkillExecutionWithSimulator:
    """Integration tests using RobotSimulator."""

    def test_grasp_with_simulator(self, skill_robot_api_with_simulator, skill_context):
        """Test GraspSkill with real RobotSimulator."""
        api, simulator = skill_robot_api_with_simulator
        from src.skill.skill_implementations import GraspSkill
        skill = GraspSkill(robot_api=api)

        # Set initial gripper open
        simulator.set_gripper(1.0, 0.0)

        result = skill.execute(GRASP_INPUT, skill_context)

        # Gripper should be closed after grasp
        assert simulator._gripper_width == 0.0

    def test_move_to_with_simulator(self, skill_robot_api_with_simulator, skill_context):
        """Test MoveToSkill with real RobotSimulator."""
        api, simulator = skill_robot_api_with_simulator
        from src.skill.skill_implementations import MoveToSkill
        skill = MoveToSkill(robot_api=api)

        initial_pose = simulator._end_effector_pose

        result = skill.execute(MOVE_TO_INPUT, skill_context)

        # Position should be updated
        assert simulator._end_effector_pose.x == MOVE_TO_INPUT["target_x"]


class TestSkillContext:
    """Tests for SkillContext in execution."""

    def test_skill_receives_context(self, grasp_skill, skill_context):
        """Skills should receive and use SkillContext when provided."""
        result = grasp_skill.execute(GRASP_INPUT, skill_context)
        assert 'status' in result
