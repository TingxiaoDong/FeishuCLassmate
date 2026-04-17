"""
Unit tests for SkillExecutor.

Tests the validation pipeline that validates skill preconditions
without executing the robot commands.

Authoritative source: src/metaclaw/skill_executor.py
"""
import pytest
from unittest.mock import Mock, patch

from src.metaclaw.skill_executor import SkillExecutor
from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus
from src.shared.world_state import WorldState, RobotState, Pose, Environment, WorkspaceBounds


def make_mock_world_state():
    """Create a valid WorldState for testing."""
    return WorldState(
        timestamp=0.0,
        robot=RobotState(
            joint_positions=[0.0] * 6,
            end_effector_pose=Pose(x=0.0, y=0.0, z=0.0),
            gripper_width=0.5,
            gripper_force=0.0,
        ),
        objects=[],
        environment=Environment(workspace_bounds=WorkspaceBounds()),
    )


class TestSkillExecutorInitialization:
    """Tests for SkillExecutor initialization."""

    def test_skill_executor_initializes_with_robot_api(self):
        """SkillExecutor should initialize with RobotAPI."""
        mock_api = Mock()
        executor = SkillExecutor(mock_api)
        assert executor._robot_api is mock_api

    def test_skill_executor_has_precondition_validator(self):
        """SkillExecutor should have a precondition validator."""
        executor = SkillExecutor(Mock())
        assert executor._precondition_validator is not None


class TestValidateOnly:
    """Tests for validate_only method - validates preconditions without execution."""

    def test_validate_only_returns_tuple(self):
        """validate_only should return tuple of (is_valid, satisfied, failed)."""
        mock_api = Mock()
        mock_api.get_world_state.return_value = make_mock_world_state()
        executor = SkillExecutor(mock_api)
        result = executor.validate_only("grasp", {"object_id": "test_block"})
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_validate_only_returns_false_for_unknown_skill(self):
        """validate_only should return False for unknown skill."""
        mock_api = Mock()
        mock_api.get_world_state.return_value = make_mock_world_state()
        executor = SkillExecutor(mock_api)
        is_valid, satisfied, failed = executor.validate_only("unknown_skill", {})
        assert is_valid is False
        assert "Unknown skill" in failed[0]


class TestExecuteValidation:
    """Tests for execute method validation behavior."""

    def test_execute_returns_execution_outcome(self):
        """execute should return ExecutionOutcome."""
        mock_api = Mock()
        mock_api.get_world_state.return_value = make_mock_world_state()
        executor = SkillExecutor(mock_api)
        result = executor.execute("grasp", {"object_id": "test_block"})
        assert isinstance(result, ExecutionOutcome)
        assert result.skill_name == "grasp"


class TestPreconditionValidator:
    """Tests for precondition validation logic."""

    def test_validator_imported_from_interfaces(self):
        """SkillPreconditionValidator should be importable."""
        from src.metaclaw.interfaces import SkillPreconditionValidator
        validator = SkillPreconditionValidator()
        assert validator is not None

    def test_validator_validate_returns_tuple(self):
        """validator.validate should return tuple."""
        from src.metaclaw.interfaces import SkillPreconditionValidator
        from src.skill.skill_schemas import get_skill_schema

        validator = SkillPreconditionValidator()
        schema = get_skill_schema("grasp")

        if schema:
            result = validator.validate("grasp", {}, schema)
            assert isinstance(result, tuple)
            assert len(result) == 3


class TestSkillExecutionOutcome:
    """Tests for ExecutionOutcome generation."""

    def test_successful_execution_has_correct_status(self):
        """Successful execution should have SUCCESS status."""
        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            effects_achieved=["object_grasped"],
        )
        assert outcome.status == ExecutionStatus.SUCCESS

    def test_failed_execution_has_correct_status(self):
        """Failed execution should have FAILURE status."""
        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.FAILURE,
            execution_time_ms=50.0,
            effects_not_achieved=["object_grasped"],
            error_message="Object not found",
        )
        assert outcome.status == ExecutionStatus.FAILURE

    def test_precondition_failed_execution(self):
        """Precondition failure should have PRECONDITION_FAILED status."""
        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.PRECONDITION_FAILED,
            execution_time_ms=10.0,
            preconditions_failed=["object exists in workspace"],
        )
        assert outcome.status == ExecutionStatus.PRECONDITION_FAILED

    def test_safety_violation_execution(self):
        """Safety violation should have SAFETY_VIOLATION status."""
        from src.metaclaw.interfaces import SafetyViolation, SafetyConstraintType

        outcome = ExecutionOutcome(
            skill_name="move",
            status=ExecutionStatus.SAFETY_VIOLATION,
            execution_time_ms=30.0,
            safety_violations=[
                SafetyViolation(
                    constraint_type=SafetyConstraintType.WORKSPACE_BOUND,
                    description="Workspace boundary exceeded",
                    severity=0.7,
                    recovered=True,
                )
            ],
        )
        assert outcome.status == ExecutionStatus.SAFETY_VIOLATION
        assert len(outcome.safety_violations) == 1
