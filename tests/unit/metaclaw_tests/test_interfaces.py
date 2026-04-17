"""
Unit tests for MetaClaw interfaces.

Tests ExecutionOutcome, RobotSample, SkillPerformanceRecord,
and related dataclasses.

Authoritative source: src/metaclaw/interfaces.py
"""
import pytest
from dataclasses import dataclass


class TestExecutionOutcome:
    """Tests for ExecutionOutcome dataclass."""

    def test_execution_outcome_to_dict(self):
        """to_dict returns properly structured dictionary."""
        from src.metaclaw.interfaces import (
            ExecutionOutcome, ExecutionStatus, SafetyViolation, SafetyConstraintType
        )

        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            preconditions_satisfied=["robot.gripper_width > 0"],
            preconditions_failed=[],
            effects_achieved=["object_grasped"],
            effects_not_achieved=[],
            safety_violations=[
                SafetyViolation(
                    constraint_type=SafetyConstraintType.FORCE_LIMIT,
                    description="Force within limit",
                    severity=0.2,
                    recovered=True,
                )
            ],
            error_message=None,
        )

        result = outcome.to_dict()

        assert result["skill_name"] == "grasp"
        assert result["status"] == "success"
        assert result["execution_time_ms"] == 100.0
        assert result["preconditions_satisfied"] == ["robot.gripper_width > 0"]
        assert len(result["safety_violations"]) == 1
        assert result["safety_violations"][0]["severity"] == 0.2

    def test_execution_outcome_empty_lists_default(self):
        """Empty list fields default to empty lists."""
        from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus

        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.FAILURE,
            execution_time_ms=50.0,
        )

        assert outcome.preconditions_satisfied == []
        assert outcome.preconditions_failed == []
        assert outcome.effects_achieved == []
        assert outcome.effects_not_achieved == []
        assert outcome.safety_violations == []


class TestSkillPerformanceRecord:
    """Tests for SkillPerformanceRecord."""

    def test_record_update_success(self):
        """update() increments successful_executions on SUCCESS."""
        from src.metaclaw.interfaces import (
            SkillPerformanceRecord, ExecutionOutcome, ExecutionStatus
        )

        record = SkillPerformanceRecord(skill_name="test")
        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
        )

        record.update(outcome)

        assert record.total_executions == 1
        assert record.successful_executions == 1
        assert record.failed_executions == 0
        assert record.safety_violations == 0

    def test_record_update_failure(self):
        """update() increments failed_executions on FAILURE."""
        from src.metaclaw.interfaces import (
            SkillPerformanceRecord, ExecutionOutcome, ExecutionStatus
        )

        record = SkillPerformanceRecord(skill_name="test")
        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.FAILURE,
            execution_time_ms=50.0,
        )

        record.update(outcome)

        assert record.total_executions == 1
        assert record.successful_executions == 0
        assert record.failed_executions == 1

    def test_record_update_safety_violation(self):
        """update() increments safety_violations on SAFETY_VIOLATION."""
        from src.metaclaw.interfaces import (
            SkillPerformanceRecord, ExecutionOutcome, ExecutionStatus, SafetyViolation, SafetyConstraintType
        )

        record = SkillPerformanceRecord(skill_name="test")
        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.SAFETY_VIOLATION,
            execution_time_ms=50.0,
            safety_violations=[
                SafetyViolation(
                    constraint_type=SafetyConstraintType.WORKSPACE_BOUND,
                    description="Out of bounds",
                    severity=0.5,
                    recovered=False,
                )
            ],
        )

        record.update(outcome)

        assert record.total_executions == 1
        assert record.safety_violations == 1
        assert record.failed_executions == 0

    def test_record_success_rate_calculation(self):
        """success_rate = successful / total."""
        from src.metaclaw.interfaces import (
            SkillPerformanceRecord, ExecutionOutcome, ExecutionStatus
        )

        record = SkillPerformanceRecord(skill_name="test")
        for _ in range(3):
            record.update(ExecutionOutcome(
                skill_name="test",
                status=ExecutionStatus.SUCCESS,
                execution_time_ms=100.0,
            ))
        record.update(ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.FAILURE,
            execution_time_ms=50.0,
        ))

        assert record.total_executions == 4
        assert record.successful_executions == 3
        assert record.success_rate == 0.75

    def test_record_to_dict(self):
        """to_dict returns all metrics."""
        from src.metaclaw.interfaces import SkillPerformanceRecord

        record = SkillPerformanceRecord(
            skill_name="grasp",
            total_executions=10,
            successful_executions=8,
            failed_executions=2,
            safety_violations=0,
            avg_execution_time_ms=150.5,
            success_rate=0.8,
            last_execution_timestamp=1234567890.0,
        )

        result = record.to_dict()

        assert result["skill_name"] == "grasp"
        assert result["total_executions"] == 10
        assert result["successful_executions"] == 8
        assert result["success_rate"] == 0.8


class TestRobotSample:
    """Tests for RobotSample."""

    def test_robot_sample_prompt_builds(self):
        """RobotSample prompt includes task and world state info."""
        from src.metaclaw.interfaces import (
            RobotSample, ExecutionOutcome, ExecutionStatus
        )

        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            preconditions_satisfied=["gripper_open"],
            preconditions_failed=[],
            effects_achieved=["object_grasped"],
            effects_not_achieved=[],
            world_state_before={"robot": {"gripper_width": 1.0}},
            world_state_after={"robot": {"gripper_width": 0.0}},
        )

        sample = RobotSample(
            task_description="Grasp the red block",
            skill_name="grasp",
            outcome=outcome,
            reward=1.0,
        )

        assert "Grasp the red block" in sample.prompt_text
        assert "grasp" in sample.prompt_text
        assert "gripper_open" in sample.prompt_text

    def test_robot_sample_success_response(self):
        """RobotSample response for SUCCESS includes effects."""
        from src.metaclaw.interfaces import (
            RobotSample, ExecutionOutcome, ExecutionStatus
        )

        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            effects_achieved=["object_grasped", "stable_grasp"],
            effects_not_achieved=[],
        )

        sample = RobotSample(
            task_description="Grasp",
            skill_name="grasp",
            outcome=outcome,
            reward=1.0,
        )

        assert "SUCCESS" in sample.response_text
        assert "object_grasped" in sample.response_text

    def test_robot_sample_safety_violation_response(self):
        """RobotSample response for SAFETY_VIOLATION includes violation details."""
        from src.metaclaw.interfaces import (
            RobotSample, ExecutionOutcome, ExecutionStatus, SafetyViolation, SafetyConstraintType
        )

        outcome = ExecutionOutcome(
            skill_name="move",
            status=ExecutionStatus.SAFETY_VIOLATION,
            execution_time_ms=50.0,
            safety_violations=[
                SafetyViolation(
                    constraint_type=SafetyConstraintType.WORKSPACE_BOUND,
                    description="Workspace boundary exceeded",
                    severity=0.7,
                    recovered=True,
                )
            ],
        )

        sample = RobotSample(
            task_description="Move to target",
            skill_name="move",
            outcome=outcome,
            reward=-0.5,
        )

        assert "SAFETY VIOLATION" in sample.response_text
        assert "Workspace boundary exceeded" in sample.response_text

    def test_robot_sample_failure_response(self):
        """RobotSample response for FAILURE includes error message."""
        from src.metaclaw.interfaces import (
            RobotSample, ExecutionOutcome, ExecutionStatus
        )

        outcome = ExecutionOutcome(
            skill_name="grasp",
            status=ExecutionStatus.FAILURE,
            execution_time_ms=50.0,
            error_message="Object moved during grasp",
        )

        sample = RobotSample(
            task_description="Grasp",
            skill_name="grasp",
            outcome=outcome,
            reward=0.0,
        )

        assert "FAILURE" in sample.response_text
        assert "Object moved during grasp" in sample.response_text

    def test_robot_sample_to_dict(self):
        """to_dict includes all fields for serialization."""
        from src.metaclaw.interfaces import (
            RobotSample, ExecutionOutcome, ExecutionStatus
        )

        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
        )

        sample = RobotSample(
            task_description="Test task",
            skill_name="test",
            outcome=outcome,
            reward=1.0,
        )

        result = sample.to_dict()

        assert result["task_description"] == "Test task"
        assert result["skill_name"] == "test"
        assert result["reward"] == 1.0
        assert "outcome" in result
        assert "prompt_text" in result
        assert "response_text" in result


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_execution_status_values(self):
        """ExecutionStatus has expected values."""
        from src.metaclaw.interfaces import ExecutionStatus

        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILURE.value == "failure"
        assert ExecutionStatus.SAFETY_VIOLATION.value == "safety_violation"
        assert ExecutionStatus.PRECONDITION_FAILED.value == "precondition_failed"


class TestSafetyConstraintType:
    """Tests for SafetyConstraintType enum."""

    def test_safety_constraint_types(self):
        """SafetyConstraintType has expected values."""
        from src.metaclaw.interfaces import SafetyConstraintType

        assert SafetyConstraintType.FORCE_LIMIT.value == "force_limit"
        assert SafetyConstraintType.WORKSPACE_BOUND.value == "workspace_bound"
        assert SafetyConstraintType.COLLISION_AVOIDANCE.value == "collision_avoidance"
        assert SafetyConstraintType.GRIPPER_SPEED.value == "gripper_speed"
        assert SafetyConstraintType.EMERGENCY_STOP.value == "emergency_stop"
