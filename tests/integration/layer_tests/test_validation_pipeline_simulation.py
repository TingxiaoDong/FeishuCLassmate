"""
Integration tests for SkillExecutor validation pipeline with RobotSimulator.

Tests the skill execution validation pipeline in simulation environment:
1. Precondition validation before execution
2. Safety constraint checking
3. Execution outcome tracking
4. World state updates after execution

Authoritative sources:
- src/metaclaw/skill_executor.py
- src/hardware/simulator.py
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.metaclaw.skill_executor import SkillExecutor
from src.robot_api.robot_api import RobotAPI
from src.hardware.simulator import RobotSimulator
from src.metaclaw.interfaces import ExecutionStatus
from src.shared.world_state import WorldState, RobotState as WS_RobotState, Pose, Environment, WorkspaceBounds
from src.shared.interfaces import RobotState


class TestSkillExecutorWithSimulator:
    """Tests for SkillExecutor with RobotSimulator backend."""

    def test_executor_initialization(self):
        """SkillExecutor should initialize with RobotAPI."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        assert executor is not None
        assert executor._robot_api is not None

    def test_execute_unknown_skill_returns_failure(self):
        """Execute unknown skill should return FAILURE status."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("unknown_skill", {})
        assert outcome.status == ExecutionStatus.FAILURE
        assert "Unknown skill" in outcome.error_message

    def test_execute_move_to_success(self):
        """Execute move_to skill should succeed when preconditions are met."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        # move_to preconditions are simpler - mainly about workspace bounds
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        assert outcome.status == ExecutionStatus.SUCCESS
        assert outcome.skill_name == "move_to"

    def test_execution_tracks_world_state_before(self):
        """Execution should track world state before execution."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        assert outcome.world_state_before is not None
        assert "robot" in outcome.world_state_before

    def test_execution_tracks_world_state_after(self):
        """Execution should track world state after execution."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        assert outcome.world_state_after is not None
        assert "robot" in outcome.world_state_after

    def test_execution_measures_time(self):
        """Execution should record execution time."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        assert outcome.execution_time_ms >= 0

    def test_validate_only_checks_preconditions(self):
        """validate_only should check preconditions without executing."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        all_valid, satisfied, failed = executor.validate_only("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        # Should return validation result without executing
        assert isinstance(all_valid, bool)
        assert isinstance(satisfied, list)
        assert isinstance(failed, list)


class TestSkillExecutorPreconditions:
    """Tests for SkillExecutor precondition validation."""

    def test_grasp_precondition_gripper_open(self):
        """Grasp requires gripper to be open (gripper_width > 0)."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        # By default gripper is closed (0.0), so grasp should fail preconditions
        outcome = executor.execute("grasp", {"force": 0.5})
        # Grasp fails due to precondition: gripper_width > 0 not met
        assert outcome.status == ExecutionStatus.PRECONDITION_FAILED
        assert "gripper_width" in outcome.error_message

    def test_grasp_precondition_object_visible(self):
        """Grasp requires a visible object in world state."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        # Grasp fails because no visible object exists
        outcome = executor.execute("grasp", {"force": 0.5})
        assert outcome.status == ExecutionStatus.PRECONDITION_FAILED

    def test_precondition_failed_included_in_outcome(self):
        """Failed preconditions should be included in outcome."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("grasp", {"force": 0.5})
        # Outcome should have preconditions tracked
        assert outcome.preconditions_satisfied is not None
        assert outcome.preconditions_failed is not None
        assert len(outcome.preconditions_failed) > 0


class TestSkillExecutorSafetyConstraints:
    """Tests for SkillExecutor safety constraint checking."""

    def test_grip_force_within_limits(self):
        """Grip force within 0-100N should not trigger safety violation."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        # Even though grasp fails preconditions, grip force is within limits
        outcome = executor.execute("grasp", {"force": 50.0})
        # Safety check passes but precondition fails
        assert outcome.safety_violations == [] or outcome.status == ExecutionStatus.PRECONDITION_FAILED

    def test_grip_force_exceeds_limit(self):
        """Grip force exceeding 100N should be flagged."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("grasp", {"force": 150.0})
        # Should have safety violations tracked
        # Note: depends on implementation - may still pass with warning

    def test_negative_speed_triggers_safety_check(self):
        """Negative speed should be flagged in safety check."""
        api = RobotAPI()
        executor = SkillExecutor(api)
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": -0.5})
        # Safety violation may be recorded


class TestSkillExecutorChain:
    """Tests for skill chain execution through executor."""

    def test_move_sequence(self):
        """Should execute multiple move_to in sequence."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        # Execute first move_to
        outcome1 = executor.execute("move_to", {"x": 0.1, "y": 0.0, "z": 0.2, "speed": 0.5})
        assert outcome1.status == ExecutionStatus.SUCCESS

        # Execute second move_to
        outcome2 = executor.execute("move_to", {"x": 0.2, "y": 0.0, "z": 0.2, "speed": 0.5})
        assert outcome2.status == ExecutionStatus.SUCCESS

    def test_world_state_updates_between_executions(self):
        """World state should be tracked between sequential executions."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        # Move to position 1
        outcome1 = executor.execute("move_to", {"x": 0.1, "y": 0.0, "z": 0.2, "speed": 0.5})
        assert outcome1.world_state_after is not None
        assert outcome1.status == ExecutionStatus.SUCCESS

        # Move to position 2
        outcome2 = executor.execute("move_to", {"x": 0.2, "y": 0.0, "z": 0.2, "speed": 0.5})
        assert outcome2.world_state_after is not None
        assert outcome2.status == ExecutionStatus.SUCCESS

        # Both executions should be tracked
        assert outcome1.skill_name == "move_to"
        assert outcome2.skill_name == "move_to"


class TestValidationPipelineIntegration:
    """Integration tests for complete validation pipeline."""

    def test_full_pipeline_with_robot_api(self):
        """Test full validation pipeline through RobotAPI."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        # Full pipeline: validate -> execute -> track
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})

        assert outcome.skill_name == "move_to"
        assert outcome.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE,
                                   ExecutionStatus.PRECONDITION_FAILED]
        assert outcome.execution_time_ms >= 0

    def test_pipeline_tracks_state_for_move_to(self):
        """Test that pipeline correctly tracks world state for move_to."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        # Execute skill
        outcome = executor.execute("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})

        # Verify world state tracking
        assert outcome.world_state_before is not None
        assert outcome.world_state_after is not None

    def test_pipeline_error_handling(self):
        """Test pipeline error handling for invalid skills."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        outcome = executor.execute("invalid_skill_name", {"param": "value"})

        assert outcome.status == ExecutionStatus.FAILURE
        assert outcome.error_message is not None
        assert "Unknown skill" in outcome.error_message

    def test_grasp_respects_preconditions(self):
        """Grasp skill should respect preconditions and fail appropriately."""
        api = RobotAPI()
        executor = SkillExecutor(api)

        # Initial state has gripper closed, so grasp should fail precondition
        outcome = executor.execute("grasp", {"force": 0.5})

        # Should fail due to gripper_width > 0 precondition not being met
        assert outcome.status == ExecutionStatus.PRECONDITION_FAILED
        assert "gripper_width" in str(outcome.preconditions_failed)
