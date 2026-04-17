"""
Skill Base Classes for the robotics system.

Provides the foundation for all skill implementations with:
- Base Skill class with lifecycle management
- Skill execution context
- Skill validation interface
- Skill composition support
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict, Optional, Any
from enum import Enum
import time


class SkillState(Enum):
    """Possible states for a skill instance."""
    CREATED = "created"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationResult(Enum):
    """Result of skill validation."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class SkillContext:
    """Context passed to skill during execution."""
    command_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class ValidationError:
    """Represents a single validation error."""
    field: str
    message: str
    severity: str  # "error", "warning", "info"


@dataclass
class ValidationReport:
    """Report from validating a skill."""
    result: ValidationResult
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.result in (ValidationResult.VALID, ValidationResult.WARNING)


class ISkillValidator(ABC):
    """Interface for skill validators."""

    @abstractmethod
    def validate(self, skill: "Skill", inputs: dict) -> ValidationReport:
        """Validate skill inputs against schema and constraints."""
        ...


class Skill(ABC):
    """
    Abstract base class for all skills.

    All skill implementations must:
    1. Define their schema (from skill_schemas)
    2. Implement execute() method
    3. Implement validate_inputs() method
    4. Define required safety checks

    Lifecycle:
        created -> validated -> executing -> completed/failed
    """

    def __init__(self, name: str):
        self.name = name
        self.state = SkillState.CREATED
        self._context: Optional[SkillContext] = None
        self._last_result: Optional[dict] = None

    @abstractmethod
    def get_required_inputs(self) -> type[TypedDict]:
        """Return the TypedDict class for required inputs."""
        ...

    @abstractmethod
    def get_preconditions(self) -> list[str]:
        """Return list of precondition strings for this skill."""
        ...

    @abstractmethod
    def get_safety_constraints(self) -> list[str]:
        """Return list of safety constraint strings."""
        ...

    @abstractmethod
    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """
        Internal implementation of skill execution.

        Args:
            inputs: Validated input parameters
            context: Execution context

        Returns:
            dict with at minimum: {"status": "success"|"failed", "message": str}
        """
        ...

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        """
        Validate inputs against schema.

        Override this for custom validation logic.
        Default implementation checks required fields.
        """
        required_inputs = self.get_required_inputs()
        errors = []
        warnings = []

        # Check required fields exist
        for field_name in required_inputs.__annotations__.keys():
            if field_name not in inputs:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Missing required field: {field_name}",
                    severity="error"
                ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.VALID)

    def execute(self, inputs: dict, context: SkillContext) -> dict:
        """
        Main entry point for skill execution.

        Lifecycle: validate -> execute -> return result
        """
        # Validate first
        validation = self.validate_inputs(inputs)
        if not validation.is_valid:
            self.state = SkillState.FAILED
            return {
                "status": "failed",
                "message": f"Validation failed: {[e.message for e in validation.errors]}",
                "validation_report": validation
            }

        self.state = SkillState.EXECUTING
        self._context = context

        try:
            result = self._execute_impl(inputs, context)
            self._last_result = result

            if result.get("status") == "success":
                self.state = SkillState.COMPLETED
            else:
                self.state = SkillState.FAILED

            return result

        except Exception as e:
            self.state = SkillState.FAILED
            return {
                "status": "failed",
                "message": f"Execution error: {str(e)}",
                "exception": str(type(e).__name__)
            }

    def cancel(self) -> dict:
        """Cancel skill execution if supported."""
        if self.state == SkillState.EXECUTING:
            self.state = SkillState.CANCELLED
            return {"status": "cancelled", "message": f"Skill '{self.name}' cancelled"}
        return {"status": "failed", "message": f"Cannot cancel skill in state {self.state}"}


class CompositeSkill(Skill):
    """
    Base class for skills composed of other skills.

    Composite skills chain multiple primitive or composite skills together.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._subskills: list[Skill] = []

    def add_subskill(self, skill: Skill) -> None:
        """Add a subskill to this composite skill."""
        self._subskills.append(skill)

    def get_subskills(self) -> list["Skill"]:
        """Get list of subsills in execution order."""
        return self._subskills.copy()

    def get_required_inputs(self) -> type[TypedDict]:
        """Composites may have their own inputs in addition to subsills."""
        return self._get_composite_inputs()

    @abstractmethod
    def _get_composite_inputs(self) -> type[TypedDict]:
        """Define inputs for the composite skill itself."""
        ...

    @abstractmethod
    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute subsills in sequence or parallel as needed."""
        ...

    def get_preconditions(self) -> list[str]:
        """Combined preconditions from all subsills plus composite."""
        preconditions = []
        for subskill in self._subskills:
            preconditions.extend(subskill.get_preconditions())
        return preconditions

    def get_safety_constraints(self) -> list[str]:
        """Combined safety constraints from all subsills plus composite."""
        constraints = []
        for subskill in self._subskills:
            constraints.extend(subskill.get_safety_constraints())
        return constraints


class SkillRegistry:
    """
    Registry for managing available skills.

    Skills must be registered before they can be executed via the Robot API.
    """

    def __init__(self):
        self._skills: dict[str, type[Skill]] = {}
        self._schemas: dict[str, "SkillSchema"] = {}

    def register(self, skill_class: type[Skill], schema: "SkillSchema") -> None:
        """Register a skill class with its schema."""
        self._skills[schema.name] = skill_class
        self._schemas[schema.name] = schema

    def get(self, name: str) -> Optional[type[Skill]]:
        """Get skill class by name."""
        return self._skills.get(name)

    def get_schema(self, name: str) -> Optional["SkillSchema"]:
        """Get skill schema by name."""
        return self._schemas.get(name)

    def list_registered(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def create_instance(self, name: str) -> Optional[Skill]:
        """Create a new instance of a registered skill."""
        skill_class = self.get(name)
        if skill_class:
            return skill_class()
        return None


# Global registry instance
_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def register_skill(skill_class: type[Skill], schema: "SkillSchema") -> None:
    """Convenience function to register a skill in the global registry."""
    get_skill_registry().register(skill_class, schema)
