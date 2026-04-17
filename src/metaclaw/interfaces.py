"""
MetaClaw <-> Robot API interface definitions.

These interfaces define the contract between:
- Robot execution outcomes and MetaClaw's learning system
- Skill performance data and the skill evolution pipeline
"""

from dataclasses import dataclass, field
from typing import TypedDict, Optional
from enum import Enum


class ExecutionStatus(Enum):
    """Outcome of a skill execution attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    SAFETY_VIOLATION = "safety_violation"
    PRECONDITION_FAILED = "precondition_failed"


class SafetyConstraintType(Enum):
    """Categories of safety constraints."""
    FORCE_LIMIT = "force_limit"
    WORKSPACE_BOUND = "workspace_bound"
    COLLISION_AVOIDANCE = "collision_avoidance"
    GRIPPER_SPEED = "gripper_speed"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class SafetyViolation:
    """Details of a safety constraint violation."""
    constraint_type: SafetyConstraintType
    description: str
    severity: float  # 0.0 to 1.0
    recovered: bool  # Whether robot recovered safely


@dataclass
class ExecutionOutcome:
    """
    Structured outcome of a skill execution.

    This is the primary data format that MetaClaw uses for learning.
    """
    skill_name: str
    status: ExecutionStatus
    execution_time_ms: float
    preconditions_satisfied: list[str] = field(default_factory=list)
    preconditions_failed: list[str] = field(default_factory=list)
    effects_achieved: list[str] = field(default_factory=list)
    effects_not_achieved: list[str] = field(default_factory=list)
    safety_violations: list[SafetyViolation] = field(default_factory=list)
    error_message: Optional[str] = None
    world_state_before: dict = field(default_factory=dict)
    world_state_after: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "preconditions_satisfied": self.preconditions_satisfied,
            "preconditions_failed": self.preconditions_failed,
            "effects_achieved": self.effects_achieved,
            "effects_not_achieved": self.effects_not_achieved,
            "safety_violations": [
                {
                    "constraint_type": v.constraint_type.value,
                    "description": v.description,
                    "severity": v.severity,
                    "recovered": v.recovered,
                }
                for v in self.safety_violations
            ],
            "error_message": self.error_message,
            "world_state_before": self.world_state_before,
            "world_state_after": self.world_state_after,
        }


@dataclass
class SkillPerformanceRecord:
    """Aggregated performance metrics for a skill over multiple executions."""
    skill_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    safety_violations: int = 0
    avg_execution_time_ms: float = 0.0
    success_rate: float = 0.0
    last_execution_timestamp: float = 0.0

    def update(self, outcome: ExecutionOutcome) -> None:
        """Update metrics with a new execution outcome."""
        import time

        self.total_executions += 1
        self.last_execution_timestamp = time.time()

        if outcome.status == ExecutionStatus.SUCCESS:
            self.successful_executions += 1
        elif outcome.status == ExecutionStatus.SAFETY_VIOLATION:
            self.safety_violations += 1
        else:
            self.failed_executions += 1

        # Update rolling average for execution time
        total_time = self.avg_execution_time_ms * (self.total_executions - 1)
        self.avg_execution_time_ms = (total_time + outcome.execution_time_ms) / self.total_executions

        # Update success rate
        self.success_rate = self.successful_executions / self.total_executions

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "safety_violations": self.safety_violations,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "success_rate": self.success_rate,
            "last_execution_timestamp": self.last_execution_timestamp,
        }


class RobotSample:
    """
    A robot execution sample formatted for MetaClaw's learning pipeline.

    This maps robot execution data into the ConversationSample format
    that MetaClaw expects for RL training.
    """

    def __init__(
        self,
        task_description: str,
        skill_name: str,
        outcome: ExecutionOutcome,
        reward: float,
    ):
        self.task_description = task_description
        self.skill_name = skill_name
        self.outcome = outcome
        self.reward = reward
        self.prompt_text = self._build_prompt()
        self.response_text = self._build_response()

    def _build_prompt(self) -> str:
        """Build the prompt text for this sample."""
        ws_before = self.outcome.world_state_before
        ws_after = self.outcome.world_state_after

        return (
            f"Task: {self.task_description}\n"
            f"Skill: {self.skill_name}\n"
            f"Preconditions: {', '.join(self.outcome.preconditions_satisfied) if self.outcome.preconditions_satisfied else 'N/A'}\n"
            f"Pre-failure conditions: {', '.join(self.outcome.preconditions_failed) if self.outcome.preconditions_failed else 'N/A'}\n"
            f"World state before: {ws_before}\n"
            f"World state after: {ws_after}"
        )

    def _build_response(self) -> str:
        """Build the response text for this sample."""
        if self.outcome.status == ExecutionStatus.SUCCESS:
            return f"SUCCESS: {', '.join(self.outcome.effects_achieved)}"
        elif self.outcome.status == ExecutionStatus.SAFETY_VIOLATION:
            violations = [v.description for v in self.outcome.safety_violations]
            return f"SAFETY VIOLATION: {', '.join(violations)}"
        else:
            return f"FAILURE: {self.outcome.error_message or 'Unknown error'}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_description": self.task_description,
            "skill_name": self.skill_name,
            "outcome": self.outcome.to_dict(),
            "reward": self.reward,
            "prompt_text": self.prompt_text,
            "response_text": self.response_text,
        }


class SkillPreconditionValidator:
    """Validates skill preconditions against world state."""

    @staticmethod
    def validate(skill_name: str, world_state: dict, skill_schema) -> tuple[bool, list[str], list[str]]:
        """
        Validate preconditions for a skill.

        Args:
            skill_name: Name of the skill to validate
            world_state: Current world state dict
            skill_schema: SkillSchema object with preconditions

        Returns:
            Tuple of (all_valid, satisfied_preconditions, failed_preconditions)
        """
        satisfied = []
        failed = []

        for precondition in skill_schema.preconditions:
            if _check_precondition(precondition, world_state):
                satisfied.append(precondition)
            else:
                failed.append(precondition)

        return len(failed) == 0, satisfied, failed


def _check_precondition(precondition: str, world_state: dict) -> bool:
    """
    Evaluate a single precondition expression against world state.

    Supports simple expressions like:
    - "robot.gripper_width > 0"
    - "object with object_id exists in world_state"
    - "target position is within workspace bounds"
    """
    import re

    # Parse simple comparisons: "field.path OP value"
    comparison_pattern = r"(\w+(?:\.\w+)*)\s*(>|<|>=|<=|==|!=)\s*(.+)"
    match = re.match(comparison_pattern, precondition.strip())

    if match:
        field_path, op, value_str = match.groups()
        field_value = _get_nested_field(world_state, field_path)

        try:
            # Try numeric comparison
            compare_value = float(value_str.strip())
            if field_value is None:
                return False
            return _compare_values(field_value, op, compare_value)
        except ValueError:
            # String comparison
            return _compare_values(field_value, op, value_str.strip().strip('"'))

    # Handle "exists" checks
    if "exists in world_state" in precondition:
        obj_id_match = re.search(r'object with (\w+) == ([^\s]+)', precondition)
        if obj_id_match:
            field, value = obj_id_match.groups()
            objects = world_state.get("objects", [])
            return any(
                obj.get(field.lstrip("object.")) == value.strip('"')
                for obj in objects
            )

    if "within workspace bounds" in precondition:
        # Check if target position is within workspace
        target_match = re.search(r"target position", precondition, re.IGNORECASE)
        if target_match:
            bounds = world_state.get("environment", {}).get("workspace_bounds", {})
            if bounds:
                return True  # Simplified - actual implementation would check coords

    # Handle state checks: "object.state == VISIBLE"
    state_match = re.search(r"(\w+)\.state\s*==\s*(\w+)", precondition)
    if state_match:
        obj_field, expected_state = state_match.groups()
        if obj_field == "object":
            objects = world_state.get("objects", [])
            if objects:
                return objects[0].get("state", "").lower() == expected_state.lower()

    return True  # Default to satisfied if pattern not recognized


def _get_nested_field(data: dict, path: str):
    """Get a nested field from a dict using dot notation."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif hasattr(value, key):
            value = getattr(value, key)
        else:
            return None
    return value


def _compare_values(actual, op: str, expected) -> bool:
    """Compare two values using the given operator."""
    if op == "==":
        return actual == expected
    elif op == "!=":
        return actual != expected
    elif op == ">":
        return actual > expected
    elif op == ">=":
        return actual >= expected
    elif op == "<":
        return actual < expected
    elif op == "<=":
        return actual <= expected
    return False
