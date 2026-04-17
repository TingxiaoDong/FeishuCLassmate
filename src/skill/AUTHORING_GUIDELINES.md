# Skill Authoring Guidelines

## Overview

This document defines the standards and patterns for creating skills in the OpenClaw Robot Learning System. Skills are the fundamental building blocks of robot behavior, providing an abstraction layer between high-level task planning and low-level robot control.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Task Planner                         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Skill System (This Module)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Skill     │  │  Validator  │  │    Composer     │ │
│  │   Base      │  │             │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Robot Control API (IRobotAPI)              │
└─────────────────────────────────────────────────────────┘
```

## Skill Lifecycle

```
┌──────────┐    validate()    ┌───────────┐   execute()   ┌───────────┐
│ CREATED  │ ───────────────▶│ VALIDATED │ ─────────────▶│ EXECUTING │
└──────────┘                 └───────────┘               └───────────┘
                                                                   │
                                                                   ▼
┌────────────┐    cancel()      ┌───────────┐               ┌───────────┐
│ CANCELLED  │ ◀─────────────── │ EXECUTING │ ◀─────────────│ COMPLETED │
└────────────┘                   └───────────┘               └───────────┘
                                     │
                                     ▼
                               ┌───────────┐
                               │  FAILED   │
                               └───────────┘
```

## Creating a New Skill

### Step 1: Define the Input TypedDict

Every skill must define its input schema as a TypedDict:

```python
from typing import TypedDict

class MySkillInput(TypedDict):
    """Input for my custom skill."""
    param1: str
    param2: float
    optional_param: int  # Optional fields can have defaults
```

### Step 2: Create the Skill Class

```python
from src.skill.skill_base import Skill, SkillContext, ValidationReport, ValidationResult, ValidationError

class MySkill(Skill):
    """Description of what this skill does."""

    def __init__(self, robot_api=None):
        super().__init__("my_skill")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return MySkillInput

    def get_preconditions(self) -> list[str]:
        return [
            "precondition 1",
            "precondition 2",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "safety constraint 1",
            "safety constraint 2",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        """Override to add custom validation logic."""
        errors = []

        # Check required fields exist and are valid
        if inputs.get("param2", 0) < 0:
            errors.append(ValidationError(
                field="param2",
                message="param2 must be non-negative",
                severity="error"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        # Return WARNING if there are concerns but not blockers
        return ValidationReport(result=ValidationResult.VALID)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """
        Implement the skill's actual behavior.

        Returns a dict with at minimum:
        - status: "success" or "failed"
        - message: Human-readable description
        """
        # Access robot API
        api = self._robot_api

        # Execute robot commands
        status = api.some_command(inputs)

        if status.state.value == "completed":
            return {
                "status": "success",
                "message": "Skill executed successfully",
            }

        return {
            "status": "failed",
            "message": f"Skill failed: {status.message}",
        }
```

### Step 3: Register the Skill

```python
from src.skill.skill_base import register_skill
from src.skill.skill_schemas import SkillSchema, SkillType

MY_SKILL_SCHEMA = SkillSchema(
    name="my_skill",
    description="What my skill does",
    skill_type=SkillType.MANIPULATION,  # or MOTION, SENSING, COMPOSITE
    inputs=MySkillInput,
    preconditions=[...],
    effects=[...],
    safety_constraints=[...],
)

register_skill(MySkill, MY_SKILL_SCHEMA)
```

## Skill Schema Definition

Each skill MUST have a schema that documents:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | Unique identifier |
| `description` | str | Yes | Human-readable description |
| `skill_type` | SkillType | Yes | Category (MOTION, MANIPULATION, SENSING, COMPOSITE) |
| `inputs` | TypedDict | Yes | Input parameter types |
| `preconditions` | list[str] | No | World state requirements |
| `effects` | list[str] | No | Expected outcomes |
| `safety_constraints` | list[str] | No | Safety rules to observe |

## Validation Requirements

### Input Validation

All skills must validate their inputs:

1. **Type checking** - Ensure correct types for all parameters
2. **Range checking** - Ensure values are within valid ranges
3. **Required fields** - Ensure all required fields are present

### Precondition Validation

Preconditions describe the world state requirements. Use the `WorldStateValidator`:

```python
# Example preconditions
"robot.gripper_width > 0"           # Gripper is open
"object with object_id exists"      # Object is known
"target is within workspace"        # Target is reachable
```

### Safety Constraint Validation

Safety constraints are hard requirements that must be met:

```python
# Example safety constraints
"speed must be positive and <= 1.0"
"grip_force must be between 0 and 100N"
"approach_height must be positive"
```

## Skill Composition

### Using SkillChain

```python
from src.skill.skill_composer import SkillChain

chain = (SkillChain(name="my_task")
    .add_step(GraspSkill(), {"object_id": "box", "grip_force": 50})
    .add_step(MoveToSkill(), {"target_x": 0.5, ...})
    .add_step(PlaceSkill(), {"object_id": "box", ...}))

result = chain.build().execute()
```

### Using SkillComposer

```python
from src.skill.skill_composer import SkillComposer

composer = SkillComposer(robot_api)
pick_place = composer.compose_pick_and_place(
    object_id="box",
    target_position={"x": 0.5, "y": 0.3, "z": 0.1},
    grip_force=50.0
)

result = pick_place.build().execute()
```

## Best Practices

### 1. Keep Skills Focused

Each skill should do one thing well. Complex behaviors should be composed from multiple skills.

### 2. Always Return Meaningful Results

```python
# Good
return {
    "status": "success",
    "message": "Object 'box' placed at (0.5, 0.3, 0.1)",
    "object_id": "box",
    "position": {"x": 0.5, "y": 0.3, "z": 0.1},
}

# Bad
return {"status": "success"}
```

### 3. Validate Early, Fail Fast

Perform validation before any robot commands are executed.

### 4. Handle Errors Gracefully

```python
try:
    status = api.move_to(target)
except RobotConnectionError as e:
    return {"status": "failed", "message": f"Connection error: {e}"}
```

### 5. Document Preconditions Clearly

Use clear, evaluable precondition strings:

```python
# Good
"robot.gripper_width > 0"
"object.state == VISIBLE"

# Bad
"gripper is open"
"object is visible"
```

## Testing Skills

### Unit Test Template

```python
import pytest
from src.skill.skill_base import SkillContext
from src.skill.skill_validator import SkillValidator, ValidationContext

def test_my_skill_validation():
    validator = SkillValidator()

    # Test valid inputs
    skill = MySkill()
    report = validator.validate_skill(
        skill,
        {"param1": "value", "param2": 1.0},
        ValidationContext()
    )
    assert report.is_valid

def test_my_skill_execution():
    skill = MySkill(mock_api)
    context = SkillContext(command_id="test_123")

    result = skill.execute({"param1": "value", "param2": 1.0}, context)
    assert result["status"] == "success"
```

## Security Considerations

1. **Never trust user input** - Always validate
2. **Limit force/speed parameters** - Enforce safe ranges
3. **Check workspace bounds** - Prevent unsafe movements
4. **Require explicit object IDs** - Never use inferred object references

## Performance Guidelines

1. **Minimize blocking calls** - Return quickly, execute async
2. **Cache world state** - Avoid repeated queries
3. **Batch commands** - Combine when possible

## Further Reference

- `skill_base.py` - Base class definitions
- `skill_schemas.py` - Schema definitions for 6 predefined skills
- `skill_validator.py` - Validation system
- `skill_composer.py` - Composition utilities
- `skill_implementations.py` - Reference implementations
