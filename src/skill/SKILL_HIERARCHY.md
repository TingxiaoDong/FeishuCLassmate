# Robot Skill Hierarchy Specification

## Overview

This document defines the multi-level skill abstraction hierarchy for the OpenClaw Robot Learning System. The hierarchy provides a scalable architecture for robot skills, from low-level primitive actions to high-level task-level skills.

## Skill Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TASK-LEVEL SKILLS                            │
│  (Highest abstraction - Define complete robot behaviors)           │
│  Examples: pick_and_place, sort_objects, stack_blocks              │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       COMPOSITE SKILLS                               │
│  (Mid abstraction - Combine primitives into sequences/patterns)     │
│  Examples: approach_and_grasp, place_and_retract, align_and_insert   │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PRIMITIVE SKILLS                                │
│  (Lowest abstraction - Direct robot API commands)                  │
│  Examples: grasp, move_to, place, release, rotate, stop              │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ROBOT CONTROL API                               │
│  (Hardware abstraction - move_joints, move_pose, set_gripper, etc.) │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer 1: Primitive Skills

Primitive skills are the atomic building blocks that map directly to Robot Control API calls. They cannot be decomposed into smaller skills.

### Current Primitive Skills

| Skill | Type | Description | Robot API Calls |
|-------|------|-------------|----------------|
| `grasp` | MANIPULATION | Grasp an object at specified location | move_linear, set_gripper |
| `move_to` | MOTION | Move end-effector to target pose | move_linear, move_joints, move_pose |
| `place` | MANIPULATION | Place grasped object at target | move_linear, set_gripper |
| `release` | MANIPULATION | Release gripped object | set_gripper |
| `rotate` | MOTION | Rotate end-effector around axis | move_pose |
| `stop` | MOTION | Immediately stop all motion | stop |

### Primitive Skill Contract

Each primitive skill MUST implement:

```python
class PrimitiveSkill(Skill):
    def get_required_inputs(self) -> type[TypedDict]:
        """Return TypedDict defining input schema."""
        ...

    def get_preconditions(self) -> list[str]:
        """Return list of precondition strings."""
        ...

    def get_safety_constraints(self) -> list[str]:
        """Return list of safety constraint strings."""
        ...

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        """Validate inputs against schema and constraints."""
        ...

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute skill using Robot API."""
        ...
```

### Primitive Skill Naming Convention

- Use lowercase with underscores: `move_to`, `place_object`
- Use action verbs: `grasp`, `push`, `pull`, `rotate`
- Avoid generic names that could conflict with future skills

## Layer 2: Composite Skills

Composite skills combine multiple primitive or other composite skills into reusable sequences. They provide mid-level abstraction for common patterns.

### Composite Skill Types

#### 2.1 Sequence Composites

Execute skills in order (A -> B -> C):

```python
class ApproachAndGrasp(CompositeSkill):
    """Approach object and grasp it in one motion."""

    def __init__(self, robot_api=None):
        super().__init__("approach_and_grasp")
        self.add_subskill(MoveToSkill(robot_api))  # Approach
        self.add_subskill(GraspSkill(robot_api))     # Grasp

    def _get_composite_inputs(self) -> type[TypedDict]:
        return TypedDict('ApproachAndGraspInput', {
            'object_id': str,
            'target_x': float,
            'target_y': float,
            'target_z': float,
            'approach_height': float,
            'grip_force': float,
        })
```

#### 2.2 Conditional Composites

Execute skills based on conditions:

```python
class ConditionalPlace(CompositeSkill):
    """Place object only if gripper has object."""

    def _execute_impl(self, inputs, context):
        world_state = context.metadata.get('world_state')
        if world_state.robot.gripper_force > 0:
            # Execute place sequence
            ...
        else:
            return {"status": "failed", "message": "No object in gripper"}
```

#### 2.3 Fallback Composites

Try primary, fall back to alternative on failure:

```python
class GraspWithRetry(CompositeSkill):
    """Try high-speed grasp, fall back to slow if it fails."""

    def _execute_impl(self, inputs, context):
        # Try fast grasp
        result = self._fast_grasp.execute(inputs, context)
        if result["status"] == "failed":
            # Fall back to slow, careful grasp
            return self._slow_grasp.execute(inputs, context)
        return result
```

### Pre-defined Composite Skills (Phase 2)

| Composite | Primitives | Description |
|-----------|------------|-------------|
| `approach_and_grasp` | move_to + grasp | Combined approach and grasp |
| `place_and_retract` | place + move_to | Place and move away |
| `pick_and_place` | grasp + move_to + place | Full pick and place cycle |
| `safe_release` | release + move_to | Release and retract |

## Layer 3: Task-Level Skills

Task-level skills define complete robot behaviors that achieve specific goals. They compose composites and primitives with planning and state management.

### Task Skill Characteristics

- **Goal-oriented**: Achieve a specific task objective
- **State-aware**: Monitor world state during execution
- **Adaptable**: Can adjust behavior based on conditions
- **Recoverable**: Handle failures gracefully

### Task Skill Structure

```python
class TaskSkill(Skill):
    """Base class for task-level skills."""

    def __init__(self, name, robot_api=None):
        super().__init__(name)
        self._skill_chain_builder = SkillChain(name)
        self._validator = SkillValidator()
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        """Task-level inputs may be higher-level (e.g., object types vs coordinates)."""
        ...

    def get_preconditions(self) -> list[str]:
        ...

    def get_safety_constraints(self) -> list[str]:
        ...

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """
        Execute the task using composed skills.

        Tasks should:
        1. Validate high-level goal
        2. Plan skill chain
        3. Execute with monitoring
        4. Handle exceptions and report
        """
        ...
```

### Pre-defined Task Skills (Phase 3)

| Task | Composites/Primitives | Description |
|------|----------------------|-------------|
| `pick_object` | approach_and_grasp | Pick up a specific object |
| `place_object` | place_and_retract | Place object at target location |
| `sort_by_color` | pick_object (x3) | Sort objects by color |
| `stack_blocks` | pick_object + place_object (x4) | Stack blocks |
| `clear_area` | pick_object + place_object (loop) | Clear workspace |

## Skill Registry Hierarchy

```
SKILL_REGISTRY
├── Primitive Skills (Layer 1)
│   ├── grasp
│   ├── move_to
│   ├── place
│   ├── release
│   ├── rotate
│   └── stop
│
├── Composite Skills (Layer 2)
│   ├── approach_and_grasp
│   ├── place_and_retract
│   ├── pick_and_place
│   └── safe_release
│
└── Task Skills (Layer 3)
    ├── pick_object
    ├── place_object
    ├── sort_by_color
    └── stack_blocks
```

## Skill Metadata Schema

Each skill maintains metadata for the learning system:

```yaml
skill_metadata:
  name: string
  version: string
  layer: "primitive" | "composite" | "task"
  category: string
  author: string
  created_date: ISO8601
  modified_date: ISO8601
  success_rate: float  # From MetaClaw learning
  avg_duration: float   # In seconds
  failure_modes: list[string]
  prerequisites: list[string]  # Skills that should be learned first
```

## MetaClaw Integration

### Skill Representation for MetaClaw

Robot skills must be exportable to MetaClaw SKILL.md format:

```markdown
---
name: {skill_name}
description: {skill.description}
category: robotics/{skill_type}
layer: {primitive|composite|task}
version: 1.0.0
---

# {Skill Title}

## Preconditions
{list of preconditions}

## Effects
{list of effects}

## Safety Constraints
{list of safety constraints}

## Usage Examples
```python
{example code}
```
```

### Learning Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Skill     │ ──▶ │  MetaClaw     │ ──▶ │  Learned Skill  │
│  Execution  │     │  Analysis    │     │  Enhancement    │
└─────────────┘     └──────────────┘     └─────────────────┘
      │                    │                       │
      │                    ▼                       │
      │            ┌──────────────┐               │
      │            │  Success/    │               │
      └──────────▶ │  Failure Log │ ◀─────────────┘
                   └──────────────┘
```

MetaClaw monitors skill executions and can:
1. Adjust default parameters (e.g., optimal grip_force)
2. Suggest skill composition improvements
3. Detect failure patterns and recommend alternatives

## Skill Composition API

### Using SkillChain

```python
from src.skill.skill_composer import SkillChain
from src.skill.skill_implementations import (
    GraspSkill, MoveToSkill, PlaceSkill
)

# Build a custom composite
chain = (SkillChain(name="custom_pick_place")
    .add_step(GraspSkill(), {"object_id": "box", "grip_force": 50})
    .add_step(MoveToSkill(), {
        "target_x": 0.5, "target_y": 0.3, "target_z": 0.1,
        "speed": 0.5, "motion_type": "linear"
    })
    .add_step(PlaceSkill(), {"object_id": "box", ...}))

result = chain.build().execute()
```

### Using SkillComposer Factory

```python
from src.skill.skill_composer import SkillComposer

composer = SkillComposer(robot_api)

# Pre-built pick and place
pick_place = composer.compose_pick_and_place(
    object_id="red_block",
    target_position={"x": 0.3, "y": 0.0, "z": 0.0},
    grip_force=50.0
)
result = pick_place.build().execute()
```

## Safety Integration

Each layer enforces safety:

| Layer | Safety Mechanism |
|-------|-----------------|
| Primitive | Input validation, force limits, workspace bounds |
| Composite | Transition validation, rollback on failure |
| Task | Goal validation, real-time monitoring, abort capability |

### Safety Interlock Points

```
Task Level ──▶ Safety Check ──▶ Composite Level ──▶ Safety Check ──▶ Primitive Level
                      │                                       │
                      ▼                                       ▼
                 [ABORT]                                 [ABORT]
```

## Implementation Status

### Phase 1 (Complete)
- [x] Primitive skill base class
- [x] 6 predefined primitive skills
- [x] Skill schema definitions
- [x] Basic validation

### Phase 2 (In Progress)
- [x] Skill composition mechanism
- [x] SkillChain builder
- [ ] Pre-defined composite skills
- [ ] Composition validation

### Phase 3 (Planned)
- [ ] Task-level skill base class
- [ ] Pre-defined task skills
- [ ] MetaClaw integration
- [ ] Learning pipeline

## Testing Requirements

### Unit Tests
- Primitive skill validation
- Primitive skill execution (mocked RobotAPI)
- Composite skill chain building
- ValidationReport generation

### Integration Tests
- Skill execution with RobotSimulator
- Chain execution with state changes
- Error handling and rollback

### System Tests
- Full task execution
- MetaClaw learning loop
- Safety constraint enforcement

## Future Extensions

### Dynamic Skill Loading
Skills can be loaded from external modules:
```python
registry.load_from_module("custom_skills.pick_place")
registry.load_from_directory("./skills")
```

### Skill Versioning
```python
registry.register(GraspSkillV2, GRASP_V2_SCHEMA, version="2.0.0")
registry.get_latest("grasp")  # Returns V2
registry.get_version("grasp", "1.0.0")  # Returns V1
```

### Distributed Skills
Skills can execute across multiple robots:
```python
distributed_chain = SkillChain().add_remote_step(
    "lift", robot_id="arm_1"
).add_remote_step(
    "carry", robot_id="mobile_base"
)
```

---

*Document Version: 1.0.0*
*Last Updated: 2026-04-17*
*Author: Skill Designer*
