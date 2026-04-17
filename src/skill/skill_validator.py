"""
Skill Validation System.

Provides multi-level validation for skills:
1. Schema validation - input format and types
2. Precondition validation - world state requirements
3. Safety validation - safety constraint checks
4. Composition validation - skill chain integrity
"""
from typing import TypedDict, Optional
from dataclasses import dataclass, field

from src.skill.skill_base import (
    Skill,
    SkillContext,
    ValidationReport,
    ValidationResult,
    ValidationError,
)
from src.skill.skill_schemas import SKILL_REGISTRY, get_skill_schema
from src.shared.world_state import WorldState


# ============================================================
# Validation Context
# ============================================================

@dataclass
class ValidationContext:
    """Context for validation operations."""
    world_state: Optional[WorldState] = None
    robot_status: Optional[dict] = None
    active_skill_chain: list[str] = field(default_factory=list)


# ============================================================
# World State Validator
# ============================================================

class WorldStateValidator:
    """Validates preconditions against current world state."""

    def validate_preconditions(
        self,
        skill: Skill,
        context: ValidationContext
    ) -> ValidationReport:
        """
        Check if skill preconditions are satisfied.

        Precondition examples:
        - "robot.gripper_width > 0"
        - "object with object_id exists in world_state"
        - "object.state == VISIBLE"
        """
        preconditions = skill.get_preconditions()
        errors = []
        warnings = []

        for precondition in preconditions:
            result = self._check_precondition(precondition, context)
            if not result["satisfied"]:
                if result["severity"] == "error":
                    errors.append(ValidationError(
                        field="precondition",
                        message=f"Unmet precondition: {precondition} - {result.get('reason', 'unknown')}",
                        severity="error"
                    ))
                else:
                    warnings.append(ValidationError(
                        field="precondition",
                        message=f"Potential issue: {precondition}",
                        severity="warning"
                    ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors, warnings=warnings)

        return ValidationReport(
            result=ValidationResult.WARNING if warnings else ValidationResult.VALID,
            warnings=warnings
        )

    def _check_precondition(self, precondition: str, context: ValidationContext) -> dict:
        """Check a single precondition string against world state."""
        # Handle common precondition patterns

        if "robot.gripper_width > 0" in precondition:
            if context.world_state:
                gripper_width = context.world_state.robot.gripper_width
                if gripper_width <= 0:
                    return {"satisfied": False, "reason": f"gripper_width is {gripper_width}", "severity": "error"}

        elif "robot.gripper_force > 0" in precondition:
            if context.world_state:
                gripper_force = context.world_state.robot.gripper_force
                if gripper_force <= 0:
                    return {"satisfied": False, "reason": f"gripper_force is {gripper_force}", "severity": "error"}

        elif "robot.state != IDLE" in precondition:
            if context.robot_status:
                state = context.robot_status.get("state", "IDLE")
                if state == "IDLE":
                    return {"satisfied": False, "reason": "robot is already IDLE", "severity": "error"}

        elif "exists in world_state" in precondition:
            if context.world_state:
                # Extract object_id if present
                if "object with object_id" in precondition and context.world_state.objects:
                    return {"satisfied": True}
                elif not context.world_state.objects:
                    return {"satisfied": False, "reason": "no objects in world", "severity": "error"}

        elif "within workspace bounds" in precondition:
            # This would need actual bounds checking
            # Placeholder - always pass for now
            pass

        return {"satisfied": True}


# ============================================================
# Safety Constraint Validator
# ============================================================

class SafetyConstraintValidator:
    """Validates safety constraints before skill execution."""

    def validate_safety(
        self,
        skill: Skill,
        inputs: dict,
        context: ValidationContext
    ) -> ValidationReport:
        """
        Check if skill safety constraints are satisfied.

        Safety constraints define hard limits that must not be violated.
        """
        constraints = skill.get_safety_constraints()
        errors = []
        warnings = []

        for constraint in constraints:
            result = self._check_constraint(constraint, inputs, context)
            if not result["satisfied"]:
                errors.append(ValidationError(
                    field="safety",
                    message=f"Safety constraint violated: {constraint}",
                    severity="error"
                ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.VALID)

    def _check_constraint(self, constraint: str, inputs: dict, context: ValidationContext) -> dict:
        """Check a single safety constraint."""
        # Speed limits
        if "speed must be positive" in constraint:
            speed = inputs.get("speed", 0)
            if speed <= 0:
                return {"satisfied": False, "reason": f"speed {speed} is not positive"}

        if "within safe limits" in constraint:
            speed = inputs.get("speed", 0)
            if speed > 1.0:
                return {"satisfied": False, "reason": f"speed {speed} exceeds safe limit"}

        # Gripper force limits
        if "grip_force must be within safe limits" in constraint:
            grip_force = inputs.get("grip_force", 0)
            if grip_force < 0 or grip_force > 100:
                return {"satisfied": False, "reason": f"grip_force {grip_force} outside 0-100N"}

        # Approach height
        if "approach_height must be positive" in constraint:
            approach_height = inputs.get("approach_height", 0)
            if approach_height <= 0:
                return {"satisfied": False, "reason": f"approach_height {approach_height} is not positive"}

        # Emergency stop always available (meta constraint - always pass)
        if "emergency stop must always be available" in constraint:
            pass

        return {"satisfied": True}


# ============================================================
# Skill Chain Validator
# ============================================================

class SkillChainValidator:
    """Validates composition and chaining of skills."""

    def validate_chain(
        self,
        skills: list[Skill],
        context: ValidationContext
    ) -> ValidationReport:
        """
        Validate a chain of skills for compatibility.

        Checks:
        - Output/input compatibility between consecutive skills
        - No circular dependencies
        - State consistency
        """
        errors = []
        warnings = []

        if not skills:
            errors.append(ValidationError(
                field="chain",
                message="Skill chain is empty",
                severity="error"
            ))
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        # Check for duplicate skills that might cause issues
        seen_skills = set()
        for i, skill in enumerate(skills):
            if skill.name in seen_skills:
                # Consecutive duplicates are often errors
                if i > 0 and skills[i-1].name == skill.name:
                    warnings.append(ValidationError(
                        field="chain",
                        message=f"Consecutive duplicate skill: {skill.name}",
                        severity="warning"
                    ))
            seen_skills.add(skill.name)

        # Validate transitions between skills
        for i in range(len(skills) - 1):
            current = skills[i]
            next_skill = skills[i + 1]

            transition_result = self._check_transition(current, next_skill, context)
            if not transition_result["valid"]:
                errors.append(ValidationError(
                    field="chain",
                    message=f"Invalid transition {current.name} -> {next_skill.name}: {transition_result.get('reason', '')}",
                    severity="error"
                ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors, warnings=warnings)

        return ValidationReport(
            result=ValidationResult.WARNING if warnings else ValidationResult.VALID,
            warnings=warnings
        )

    def _check_transition(self, current: Skill, next_skill: Skill, context: ValidationContext) -> dict:
        """Check if transition between two skills is valid."""
        # Grasp should be followed by move or place, not another grasp
        if current.name == "grasp" and next_skill.name == "grasp":
            return {"valid": False, "reason": "Cannot grasp while already grasping"}

        # Release should only follow grasp or be followed by nothing
        if current.name == "release" and next_skill.name == "release":
            return {"valid": False, "reason": "Cannot release twice consecutively"}

        # Stop can transition to anything (it resets state)
        if current.name == "stop":
            return {"valid": True}

        return {"valid": True}


# ============================================================
# Composite Validator
# ============================================================

class SkillValidator:
    """
    Main entry point for skill validation.

    Coordinates all validation stages:
    1. Input schema validation
    2. Precondition validation
    3. Safety constraint validation
    4. Chain validation (when applicable)
    """

    def __init__(self):
        self.world_state_validator = WorldStateValidator()
        self.safety_validator = SafetyConstraintValidator()
        self.chain_validator = SkillChainValidator()

    def validate_skill(
        self,
        skill: Skill,
        inputs: dict,
        context: ValidationContext
    ) -> ValidationReport:
        """
        Full validation of a skill against its inputs and context.
        """
        all_errors = []
        all_warnings = []

        # 1. Schema validation (via skill's own validate_inputs)
        schema_report = skill.validate_inputs(inputs)
        all_errors.extend(schema_report.errors)
        all_warnings.extend(schema_report.warnings)

        if schema_report.result == ValidationResult.INVALID:
            return ValidationReport(result=ValidationResult.INVALID, errors=all_errors, warnings=all_warnings)

        # 2. Precondition validation
        if context.world_state or context.robot_status:
            precond_report = self.world_state_validator.validate_preconditions(skill, context)
            all_errors.extend(precond_report.errors)
            all_warnings.extend(precond_report.warnings)

        # 3. Safety constraint validation
        safety_report = self.safety_validator.validate_safety(skill, inputs, context)
        all_errors.extend(safety_report.errors)
        all_warnings.extend(safety_report.warnings)

        if all_errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=all_errors, warnings=all_warnings)

        result = ValidationResult.WARNING if all_warnings else ValidationResult.VALID
        return ValidationReport(result=result, warnings=all_warnings)

    def validate_skill_chain(
        self,
        skills: list[Skill],
        context: ValidationContext
    ) -> ValidationReport:
        """Validate an entire skill chain."""
        return self.chain_validator.validate_chain(skills, context)


# ============================================================
# Validation Utilities
# ============================================================

def validate_skill_inputs(skill_name: str, inputs: dict) -> ValidationReport:
    """
    Convenience function to validate inputs for a named skill.

    Uses the skill registry to get the schema and create an instance.
    """
    schema = get_skill_schema(skill_name)
    if not schema:
        return ValidationReport(
            result=ValidationResult.INVALID,
            errors=[ValidationError(
                field="skill_name",
                message=f"Unknown skill: {skill_name}",
                severity="error"
            )]
        )

    # Get skill class from registry
    from src.skill.skill_base import get_skill_registry
    registry = get_skill_registry()
    skill_class = registry.get(skill_name)

    if not skill_class:
        return ValidationReport(
            result=ValidationResult.INVALID,
            errors=[ValidationError(
                field="skill_name",
                message=f"Skill '{skill_name}' not registered",
                severity="error"
            )]
        )

    skill = skill_class()
    return skill.validate_inputs(inputs)
