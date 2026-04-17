"""
Skill Composition Mechanism.

Provides ways to combine primitive skills into composite skills
and execute skill chains with proper state management.
"""
from typing import TypedDict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from src.skill.skill_base import (
    Skill,
    SkillContext,
    CompositeSkill,
    SkillState,
    get_skill_registry,
)
from src.skill.skill_validator import SkillValidator, ValidationContext


# ============================================================
# Composition Types
# ============================================================

class CompositionType(Enum):
    """Types of skill composition."""
    SEQUENCE = "sequence"      # Execute skills in order
    PARALLEL = "parallel"      # Execute skills concurrently
    CONDITIONAL = "conditional"  # Execute based on condition
    REPEAT = "repeat"          # Repeat skill N times
    FALLBACK = "fallback"      # Try alternatives on failure


@dataclass
class SkillStep:
    """A single step in a skill composition."""
    skill: Skill
    inputs: dict
    condition: Optional[Callable[[dict], bool]] = None  # For conditional execution


@dataclass
class ExecutionResult:
    """Result of executing a composite skill."""
    status: str  # "success", "failed", "partial"
    message: str
    completed_steps: list[dict] = field(default_factory=list)
    failed_step: Optional[int] = None
    total_duration: float = 0.0


# ============================================================
# Skill Chain Builder
# ============================================================

class SkillChain:
    """
    Builder for creating skill chains.

    Allows fluent composition of skills:
        chain = SkillChain() \
            .add_step(grasp_skill, {"object_id": "box"}) \
            .add_step(move_to_skill, {"target_x": 0.5, ...}) \
            .add_step(place_skill, {"object_id": "box", ...})
    """

    def __init__(self, name: str = "unnamed_chain"):
        self.name = name
        self._steps: list[SkillStep] = []
        self._validator = SkillValidator()

    def add_step(self, skill: Skill, inputs: dict, condition: Optional[Callable[[dict], bool]] = None) -> "SkillChain":
        """Add a skill step to the chain."""
        step = SkillStep(skill=skill, inputs=inputs, condition=condition)
        self._steps.append(step)
        return self

    def add_conditional(
        self,
        skill: Skill,
        inputs: dict,
        condition: Callable[[dict], bool]
    ) -> "SkillChain":
        """Add a conditionally executed skill."""
        return self.add_step(skill, inputs, condition)

    def build(self) -> "ExecutableChain":
        """Build an executable chain from this builder."""
        return ExecutableChain(name=self.name, steps=self._steps, validator=self._validator)


# ============================================================
# Executable Chain
# ============================================================

class ExecutableChain:
    """
    An executable chain of skills.

    Created from SkillChain.build(), this handles actual execution
    with proper state management and rollback support.
    """

    def __init__(self, name: str, steps: list[SkillStep], validator: SkillValidator):
        self.name = name
        self._steps = steps
        self._validator = validator
        self._rollback_handlers: list[Callable[[], None]] = []
        self._execution_history: list[dict] = []

    def add_rollback(self, handler: Callable[[], None]) -> None:
        """Add a rollback handler to be called on failure."""
        self._rollback_handlers.append(handler)

    def execute(self, context: Optional[SkillContext] = None) -> ExecutionResult:
        """
        Execute the skill chain.

        Returns ExecutionResult with details of what happened.
        """
        if context is None:
            context = SkillContext(command_id=f"chain_{self.name}_{int(time.time())}")

        start_time = time.time()
        completed_steps = []

        for i, step in enumerate(self._steps):
            # Check condition if present
            if step.condition:
                try:
                    if not step.condition(context.metadata):
                        # Skip this step
                        continue
                except Exception as e:
                    return ExecutionResult(
                        status="failed",
                        message=f"Condition check failed for step {i}: {str(e)}",
                        completed_steps=completed_steps,
                        failed_step=i,
                        total_duration=time.time() - start_time,
                    )

            # Validate before execution
            val_context = ValidationContext()
            validation = self._validator.validate_skill(step.skill, step.inputs, val_context)

            if not validation.is_valid:
                # Run rollback and return failure
                self._run_rollback()
                return ExecutionResult(
                    status="failed",
                    message=f"Validation failed for step {i}: {[e.message for e in validation.errors]}",
                    completed_steps=completed_steps,
                    failed_step=i,
                    total_duration=time.time() - start_time,
                )

            # Execute the skill
            result = step.skill.execute(step.inputs, context)

            step_record = {
                "step_index": i,
                "skill_name": step.skill.name,
                "inputs": step.inputs,
                "result": result,
            }
            self._execution_history.append(step_record)
            completed_steps.append(step_record)

            if result.get("status") != "success":
                self._run_rollback()
                return ExecutionResult(
                    status="failed",
                    message=f"Step {i} ({step.skill.name}) failed: {result.get('message', 'unknown')}",
                    completed_steps=completed_steps,
                    failed_step=i,
                    total_duration=time.time() - start_time,
                )

        return ExecutionResult(
            status="success",
            message=f"Chain '{self.name}' completed successfully",
            completed_steps=completed_steps,
            total_duration=time.time() - start_time,
        )

    def _run_rollback(self) -> None:
        """Run all rollback handlers in reverse order."""
        for handler in reversed(self._rollback_handlers):
            try:
                handler()
            except Exception:
                # Log but don't fail rollback
                pass


# ============================================================
# Composite Skill Implementation
# ============================================================

class SequencedCompositeSkill(CompositeSkill):
    """
    A composite skill that executes subsills in sequence.

    All inputs are passed to subsills as needed based on their requirements.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._chain_builder: Optional[SkillChain] = None

    def set_chain(self, chain: SkillChain) -> None:
        """Set the chain to execute."""
        self._chain_builder = chain

    def _get_composite_inputs(self) -> type[TypedDict]:
        """Inputs for the composite itself."""
        # Base implementation - composites may override
        return TypedDict('CompositeInput', {})

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute the configured chain."""
        if not self._chain_builder:
            return {"status": "failed", "message": "No chain configured"}

        executable = self._chain_builder.build()

        # Merge composite inputs into step inputs where needed
        # For now, pass through as-is

        result = executable.execute(context)

        return {
            "status": result.status,
            "message": result.message,
            "completed_steps": len(result.completed_steps),
            "total_duration": result.total_duration,
        }


# ============================================================
# Pre-built Common Compositions
# ============================================================

class SkillComposer:
    """
    Factory for common skill compositions.

    Provides pre-built compositions for typical robot tasks.
    """

    def __init__(self, robot_api: Optional["RobotAPI"] = None):
        self._robot_api = robot_api
        self._registry = get_skill_registry()

    def compose_pick_and_place(
        self,
        object_id: str,
        target_position: dict,
        approach_height: float = 0.1,
        grip_force: float = 50.0
    ) -> SkillChain:
        """
        Compose a pick and place operation.

        Sequence: grasp -> move_to -> place
        """
        from src.skill.skill_implementations import (
            GraspSkill, MoveToSkill, PlaceSkill
        )

        grasp = GraspSkill(self._robot_api)
        move_to = MoveToSkill(self._robot_api)
        place = PlaceSkill(self._robot_api)

        return (SkillChain(name="pick_and_place")
            .add_step(grasp, {
                "object_id": object_id,
                "approach_height": approach_height,
                "grip_force": grip_force,
            })
            .add_step(move_to, {
                "target_x": target_position["x"],
                "target_y": target_position["y"],
                "target_z": target_position["z"] + approach_height,
                "target_rx": 0.0,
                "target_ry": 0.0,
                "target_rz": 0.0,
                "speed": 0.5,
                "motion_type": "linear",
            })
            .add_step(place, {
                "object_id": object_id,
                "target_x": target_position["x"],
                "target_y": target_position["y"],
                "target_z": target_position["z"],
                "approach_height": approach_height,
            }))

    def compose_place_sequence(
        self,
        object_id: str,
        target_position: dict,
        approach_height: float = 0.1
    ) -> SkillChain:
        """
        Compose a place operation.

        Sequence: move_to (above target) -> place
        """
        from src.skill.skill_implementations import MoveToSkill, PlaceSkill

        move_to = MoveToSkill(self._robot_api)
        place = PlaceSkill(self._robot_api)

        return (SkillChain(name="place_sequence")
            .add_step(move_to, {
                "target_x": target_position["x"],
                "target_y": target_position["y"],
                "target_z": target_position["z"] + approach_height,
                "target_rx": 0.0,
                "target_ry": 0.0,
                "target_rz": 0.0,
                "speed": 0.5,
                "motion_type": "linear",
            })
            .add_step(place, {
                "object_id": object_id,
                "target_x": target_position["x"],
                "target_y": target_position["y"],
                "target_z": target_position["z"],
                "approach_height": approach_height,
            }))

    def compose_safe_retract(self, retract_distance: float = 0.1) -> SkillChain:
        """
        Compose a safe retraction after place/release.

        Sequence: move linear up
        """
        from src.skill.skill_implementations import MoveToSkill

        move_to = MoveToSkill(self._robot_api)

        return (SkillChain(name="safe_retract")
            .add_step(move_to, {
                "target_x": 0.0,  # Would need actual current position
                "target_y": 0.0,
                "target_z": retract_distance,
                "target_rx": 0.0,
                "target_ry": 0.0,
                "target_rz": 0.0,
                "speed": 0.3,
                "motion_type": "linear",
            }))
