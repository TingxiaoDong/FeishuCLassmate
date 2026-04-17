"""
Skill Executor for the robotics system.

Executes skills through the Robot API with precondition validation
and outcome tracking for MetaClaw integration.
"""

import time
from typing import Optional

from src.robot_api.robot_api import RobotAPI
from src.skill.skill_schemas import (
    SKILL_REGISTRY,
    get_skill_schema,
    SkillSchema,
)
from src.metaclaw.interfaces import (
    ExecutionOutcome,
    ExecutionStatus,
    SafetyViolation,
    SafetyConstraintType,
    SkillPreconditionValidator,
)


class SkillExecutor:
    """
    Executes skills with precondition validation and outcome tracking.

    This is the orchestrator layer that sits between skill requests
    and the Robot API. It:
    1. Validates preconditions against current world state
    2. Executes the skill through RobotAPI
    3. Tracks outcomes for MetaClaw learning
    """

    def __init__(self, robot_api: RobotAPI):
        """
        Initialize SkillExecutor.

        Args:
            robot_api: The RobotAPI instance for execution
        """
        self._robot_api = robot_api
        self._precondition_validator = SkillPreconditionValidator()

    def execute(
        self,
        skill_name: str,
        parameters: dict,
        task_description: str = "",
    ) -> ExecutionOutcome:
        """
        Execute a skill with full validation and tracking.

        Args:
            skill_name: Name of the skill to execute
            parameters: Skill-specific parameters
            task_description: Description of the task for learning

        Returns:
            ExecutionOutcome with full execution details
        """
        start_time = time.time()

        # Get skill schema
        schema = get_skill_schema(skill_name)
        if schema is None:
            return ExecutionOutcome(
                skill_name=skill_name,
                status=ExecutionStatus.FAILURE,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Unknown skill: {skill_name}",
            )

        # Get world state before execution
        world_state_before = self._robot_api.get_world_state().to_dict()

        # Validate preconditions
        all_valid, satisfied, failed = self._precondition_validator.validate(
            skill_name, world_state_before, schema
        )

        if not all_valid:
            return ExecutionOutcome(
                skill_name=skill_name,
                status=ExecutionStatus.PRECONDITION_FAILED,
                execution_time_ms=(time.time() - start_time) * 1000,
                preconditions_satisfied=satisfied,
                preconditions_failed=failed,
                world_state_before=world_state_before,
                world_state_after=world_state_before,
                error_message=f"Preconditions not met: {', '.join(failed)}",
            )

        # Check safety constraints before execution
        violations = self._check_safety_constraints(schema, world_state_before, parameters)
        if violations:
            # Execute anyway but record violations
            result = self._execute_skill(skill_name, parameters, start_time)
            result.safety_violations = violations
            result.preconditions_satisfied = satisfied
            result.world_state_before = world_state_before
            return result

        # Execute the skill
        return self._execute_skill(skill_name, parameters, start_time, satisfied, world_state_before)

    def _execute_skill(
        self,
        skill_name: str,
        parameters: dict,
        start_time: float,
        preconditions_satisfied: list[str] = None,
        world_state_before: dict = None,
    ) -> ExecutionOutcome:
        """Internal method to execute skill via RobotAPI."""
        if preconditions_satisfied is None:
            preconditions_satisfied = []
        if world_state_before is None:
            world_state_before = self._robot_api.get_world_state().to_dict()

        # Execute via RobotAPI
        status = self._robot_api.execute_skill(skill_name, parameters)

        # Get world state after execution
        world_state_after = self._robot_api.get_world_state().to_dict()

        # Map RobotAPI status to ExecutionStatus
        from src.shared.interfaces import RobotState
        if status.state == RobotState.COMPLETED:
            exec_status = ExecutionStatus.SUCCESS
        elif status.state == RobotState.ERROR:
            exec_status = ExecutionStatus.FAILURE
        else:
            exec_status = ExecutionStatus.FAILURE

        # Get schema for effects check
        schema = get_skill_schema(skill_name)
        effects_achieved = []
        effects_not_achieved = []

        if schema:
            for effect in schema.effects:
                if _check_effect(effect, world_state_before, world_state_after):
                    effects_achieved.append(effect)
                else:
                    effects_not_achieved.append(effect)

        return ExecutionOutcome(
            skill_name=skill_name,
            status=exec_status,
            execution_time_ms=(time.time() - start_time) * 1000,
            preconditions_satisfied=preconditions_satisfied,
            effects_achieved=effects_achieved,
            effects_not_achieved=effects_not_achieved,
            world_state_before=world_state_before,
            world_state_after=world_state_after,
            error_message=status.message if status.state == RobotState.ERROR else None,
        )

    def _check_safety_constraints(
        self,
        schema: SkillSchema,
        world_state: dict,
        parameters: dict,
    ) -> list[SafetyViolation]:
        """
        Check safety constraints before execution.

        Returns list of any violations found.
        """
        violations = []

        for constraint in schema.safety_constraints:
            violation = self._evaluate_safety_constraint(constraint, world_state, parameters)
            if violation:
                violations.append(violation)

        return violations

    def _evaluate_safety_constraint(
        self,
        constraint: str,
        world_state: dict,
        parameters: dict,
    ) -> Optional[SafetyViolation]:
        """
        Evaluate a single safety constraint.

        Returns SafetyViolation if constraint is violated, None otherwise.
        """
        import re

        # Check grip_force limit: "grip_force must be within safe limits (0-100N)"
        if "grip_force" in constraint.lower() and "safe limits" in constraint.lower():
            grip_force = parameters.get("grip_force", 0.0)
            if grip_force < 0 or grip_force > 100:
                return SafetyViolation(
                    constraint_type=SafetyConstraintType.FORCE_LIMIT,
                    description=f"Grip force {grip_force}N outside safe limits (0-100N)",
                    severity=0.8,
                    recovered=False,
                )

        # Check approach_height must be positive
        if "approach_height" in constraint.lower() and "positive" in constraint.lower():
            approach_height = parameters.get("approach_height", 0.0)
            if approach_height <= 0:
                return SafetyViolation(
                    constraint_type=SafetyConstraintType.WORKSPACE_BOUND,
                    description=f"approach_height {approach_height} must be positive",
                    severity=0.6,
                    recovered=False,
                )

        # Check workspace bounds
        if "workspace bounds" in constraint.lower():
            bounds = world_state.get("environment", {}).get("workspace_bounds", {})
            # Simplified - would check target position against bounds
            pass

        # Check collision-free path
        if "collision-free" in constraint.lower() or "collision" in constraint.lower():
            obstacles = world_state.get("environment", {}).get("obstacles", [])
            if obstacles:
                # Simplified - would check path against obstacles
                pass

        # Check speed limits
        if "speed" in constraint.lower() and "safe limits" in constraint.lower():
            speed = parameters.get("speed", 0.0)
            if speed < 0:
                return SafetyViolation(
                    constraint_type=SafetyConstraintType.GRIPPER_SPEED,
                    description=f"Speed {speed} is negative",
                    severity=0.7,
                    recovered=False,
                )

        return None

    def validate_only(self, skill_name: str, parameters: dict) -> tuple[bool, list[str], list[str]]:
        """
        Validate preconditions without executing.

        Returns:
            Tuple of (all_valid, satisfied_preconditions, failed_preconditions)
        """
        schema = get_skill_schema(skill_name)
        if schema is None:
            return False, [], [f"Unknown skill: {skill_name}"]

        world_state = self._robot_api.get_world_state().to_dict()
        return self._precondition_validator.validate(skill_name, world_state, schema)


def _check_effect(effect: str, world_before: dict, world_after: dict) -> bool:
    """
    Check if an effect was achieved after execution.

    Compares world state before and after to determine if
    the expected effect occurred.
    """
    import re

    # Parse "field.path == value" pattern
    match = re.match(r"(.+?)\s*==\s*(.+)", effect.strip())
    if match:
        field_path, expected_val = match.groups()
        before_val = _get_nested_value(world_before, field_path)
        after_val = _get_nested_value(world_after, field_path)

        # Check if the value changed to expected
        try:
            expected = float(expected_val.strip())
            return abs(after_val - expected) < 0.001 if after_val is not None else False
        except ValueError:
            return str(after_val).lower() == expected_val.strip().lower()

    # Handle "robot.gripper_force > 0" pattern
    comparison_match = re.match(r"(.+?)\s*(>|<|>=|<=|==|!=)\s*(.+)", effect.strip())
    if comparison_match:
        field_path, op, expected_val = comparison_match.groups()
        after_val = _get_nested_value(world_after, field_path)
        if after_val is None:
            return False

        try:
            expected = float(expected_val.strip())
            if op == ">":
                return after_val > expected
            elif op == "<":
                return after_val < expected
            elif op == ">=":
                return after_val >= expected
            elif op == "<=":
                return after_val <= expected
            elif op == "==":
                return abs(after_val - expected) < 0.001
        except ValueError:
            return str(after_val).lower() == expected_val.strip().lower()

    return True  # Default to achieved if pattern not recognized


def _get_nested_value(data: dict, path: str):
    """Get nested value from dict using dot notation."""
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
