"""
Pytest configuration and fixtures for MetaClaw performance tracker tests.
"""
import pytest
import sys
from pathlib import Path

# Ensure src is in path
SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.metaclaw.interfaces import (
    ExecutionOutcome,
    ExecutionStatus,
    SafetyViolation,
    SafetyConstraintType,
    SkillPerformanceRecord,
    RobotSample,
)
from src.metaclaw.performance_tracker import SkillPerformanceTracker


# ============================================================
# Sample Execution Outcomes
# ============================================================

def make_success_outcome(skill_name: str = "grasp", execution_time_ms: float = 100.0):
    """Create a successful execution outcome."""
    return ExecutionOutcome(
        skill_name=skill_name,
        status=ExecutionStatus.SUCCESS,
        execution_time_ms=execution_time_ms,
        preconditions_satisfied=["robot.gripper_width > 0", "object exists"],
        preconditions_failed=[],
        effects_achieved=["object_grasped"],
        effects_not_achieved=[],
        safety_violations=[],
    )


def make_failure_outcome(skill_name: str = "grasp", execution_time_ms: float = 50.0):
    """Create a failed execution outcome."""
    return ExecutionOutcome(
        skill_name=skill_name,
        status=ExecutionStatus.FAILURE,
        execution_time_ms=execution_time_ms,
        preconditions_satisfied=["robot.gripper_width > 0"],
        preconditions_failed=["object exists"],
        effects_achieved=[],
        effects_not_achieved=["object_grasped"],
        safety_violations=[],
        error_message="Object not found in workspace",
    )


def make_safety_violation_outcome(skill_name: str = "grasp", severity: float = 0.8):
    """Create an outcome with safety violation."""
    return ExecutionOutcome(
        skill_name=skill_name,
        status=ExecutionStatus.SAFETY_VIOLATION,
        execution_time_ms=50.0,
        preconditions_satisfied=[],
        preconditions_failed=["workspace_bounds_respected"],
        effects_achieved=[],
        effects_not_achieved=["position_achieved"],
        safety_violations=[
            SafetyViolation(
                constraint_type=SafetyConstraintType.WORKSPACE_BOUND,
                description="Robot exceeded workspace boundary",
                severity=severity,
                recovered=True,
            )
        ],
        error_message="Workspace boundary violation detected",
    )


def make_precondition_failed_outcome(skill_name: str = "place"):
    """Create a precondition-failed outcome."""
    return ExecutionOutcome(
        skill_name=skill_name,
        status=ExecutionStatus.PRECONDITION_FAILED,
        execution_time_ms=10.0,
        preconditions_satisfied=[],
        preconditions_failed=["object_in_gripper"],
        effects_achieved=[],
        effects_not_achieved=["object_placed"],
        safety_violations=[],
        error_message="No object in gripper",
    )


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def tracker():
    """SkillPerformanceTracker without persistence."""
    return SkillPerformanceTracker(storage_dir=None)


@pytest.fixture
def tracker_with_storage(tmp_path):
    """SkillPerformanceTracker with temporary storage."""
    return SkillPerformanceTracker(storage_dir=str(tmp_path / "test_data"))


@pytest.fixture
def success_outcome():
    """A successful execution outcome."""
    return make_success_outcome()


@pytest.fixture
def failure_outcome():
    """A failed execution outcome."""
    return make_failure_outcome()


@pytest.fixture
def safety_violation_outcome():
    """An outcome with safety violation."""
    return make_safety_violation_outcome()


@pytest.fixture
def precondition_failed_outcome():
    """An outcome where preconditions failed."""
    return make_precondition_failed_outcome()
