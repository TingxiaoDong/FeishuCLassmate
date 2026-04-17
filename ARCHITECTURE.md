# OpenClaw Robot Learning System - Architecture

## Table of Contents
1. [System Overview](#system-overview)
2. [Layer Architecture](#layer-architecture)
3. [Interface Contracts](#interface-contracts)
4. [Data Flow](#data-flow)
5. [Skill System](#skill-system)
6. [Safety Mechanisms](#safety-mechanisms)
7. [MetaClaw Integration](#metaclaw-integration)
8. [Project Structure](#project-structure)
9. [Development Workflow](#development-workflow)

---

## System Overview

The OpenClaw Robot Learning System is a **layered robot control architecture** designed for safe, scalable, and continuously improving robot behavior. The system implements a strict abstraction hierarchy where each layer communicates only with adjacent layers through well-defined interfaces.

### Design Principles

1. **Layer Isolation**: Each layer can only communicate with adjacent layers
2. **Safety First**: Safety constraints are enforced at every layer
3. **Hardware Agnostic**: Upper layers are independent of actual hardware
4. **Skill Reusability**: Skills are composable and learnable
5. **Reproducibility**: All experiments and executions are traceable

---

## Layer Architecture

The system consists of **4 main layers** plus **shared components**:

```
┌─────────────────────────────────────────────────────────────┐
│                    PLANNER LAYER (OpenClaw)                 │
│         High-level task decomposition & sequencing         │
└─────────────────────────────┬───────────────────────────────┘
                              │ SkillRequest
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       SKILL LAYER                           │
│    Translates skill invocations into motion primitives     │
│    Skill execution, validation, composition                │
└─────────────────────────────┬───────────────────────────────┘
                              │ RobotAction + Parameters
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ROBOT CONTROL API LAYER                    │
│           Hardware-agnostic interface (IRobotAPI)           │
│      Navigation, manipulation, sensing, system control     │
└─────────────────────────────┬───────────────────────────────┘
                              │ Hardware-specific commands
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 HARDWARE / SIMULATOR LAYER                  │
│          Real robot communication or simulation             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      SHARED COMPONENTS                       │
│     Interfaces, enums, TypedDicts, World State, utils       │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

#### 1. Planner Layer (`src/planner/`)
- **Responsibility**: High-level task decomposition
- **Inputs**: User commands, task descriptions
- **Outputs**: Sequence of SkillRequests
- **Key Components**:
  - Task decomposition engine
  - Skill sequencing logic
  - Execution planning
- **Dependencies**: MetaClaw for learning

#### 2. Skill Layer (`src/skill/`)
- **Responsibility**: Skill execution and management
- **Inputs**: SkillRequest (task_id, instruction, context)
- **Outputs**: SkillResponse (status, result)
- **Key Components**:
  - SkillBase abstract class
  - Skill registry and validation
  - Skill composition (sequential, parallel)
- **Constraints**: Must use IRobotAPI only

#### 3. Robot Control API Layer (`src/robot_api/`)
- **Responsibility**: Hardware-agnostic robot control
- **Inputs**: Atomic commands (move_joints, move_pose, etc.)
- **Outputs**: RobotStatus
- **Key Components**:
  - IRobotAPI interface
  - RobotAPI concrete implementation
  - Hardware adapter abstraction
- **Enforces**: Joint limits, velocity limits, safety checks

#### 4. Hardware/Simulator Layer (`src/hardware/`)
- **Responsibility**: Actual robot or simulation execution
- **Inputs**: Hardware-specific commands
- **Outputs**: Sensor data, execution status
- **Key Components**:
  - RobotSimulator (for testing)
  - Hardware adapters (for real robots)
  - Sensor data processing

### Shared Components (`src/shared/`)

| Component | File | Purpose |
|-----------|------|---------|
| Interfaces | `interfaces.py` | IRobotAPI, enums, TypedDicts |
| World State | `world_state.py` | Central state representation |

---

## Interface Contracts

### SkillRequest / SkillResponse

```python
class SkillRequest(TypedDict):
    task_id: str              # Unique task identifier
    instruction: str          # Natural language instruction
    context: dict              # Additional context

class SkillResponse(TypedDict):
    task_id: str
    status: SkillStatus       # SUCCESS | FAILED | PARTIAL
    result: dict              # Execution results
    skill_name: str           # Which skill was executed
    message: str              # Human-readable status
```

### IRobotAPI Interface

```python
class IRobotAPI(Protocol):
    # Motion Commands
    def move_joints(self, joints: list[float], speed: float) -> RobotStatus
    def move_pose(self, position: Position3D, orientation: Orientation3D, speed: float) -> RobotStatus
    def move_linear(self, target: Position3D, speed: float) -> RobotStatus

    # Manipulation
    def set_gripper(self, position: float, force: float) -> RobotStatus

    # State
    def get_world_state(self) -> WorldState
    def execute_skill(self, skill_name: str, parameters: dict) -> RobotStatus
    def stop(self, immediate: bool = False) -> RobotStatus
```

### TypedDicts

```python
# Positions
class Position3D(TypedDict):
    x: float
    y: float
    z: float

class Orientation3D(TypedDict):
    roll: float
    pitch: float
    yaw: float

# Robot Status
class RobotStatus(TypedDict):
    command_id: str
    state: RobotState          # IDLE | EXECUTING | COMPLETED | ERROR
    position: dict
    joints: list[float]
    gripper_state: float
    sensor_data: dict
    message: str

# Enums
class RobotState(Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"

class RobotAction(Enum):
    MOVE_JOINTS = "move_joints"
    MOVE_POSE = "move_pose"
    MOVE_LINEAR = "move_linear"
    SET_GRIPPER = "set_gripper"
    STOP = "stop"
    EXECUTE_SKILL = "execute_skill"

class SkillStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
```

### World State Schema

```python
@dataclass
class WorldState:
    timestamp: float
    robot: RobotState           # Current robot state
    objects: list[WorldObject]  # Known objects
    environment: Environment    # Workspace info

@dataclass
class RobotState:
    joint_positions: list[float]
    end_effector_pose: Pose
    gripper_width: float
    gripper_force: float

@dataclass
class WorldObject:
    id: str
    type: str                   # "block", "sphere", "tool"
    pose: Pose
    state: ObjectState          # VISIBLE, GRASPED, PLACED
```

---

## Data Flow

### Skill Execution Flow

```
1. Planner Layer
   └─► SkillRequest {task_id, instruction, context}
       │
2. Skill Layer
   ├─► Validate preconditions against WorldState
   ├─► Check safety constraints
   ├─► Generate RobotAction sequence
   └─► SkillResponse {status, result, skill_name}
       │
3. Robot API Layer
   ├─► Route action to hardware adapter
   ├─► Apply joint/velocity limits
   ├─► Return RobotStatus
       │
4. Hardware Layer
   ├─► Execute on robot/simulator
   ├─► Update WorldState
   └─► Return sensor data
```

### Query Flow (World State)

```
Frontend ──GET /world_state──► Backend ──► RobotAPI
                                         │
                                         ▼
                                   Hardware Layer
                                         │
                                         ▼
                                   WorldState ◄── Updated by sensors
                                         │
                                         ▼
                                   RobotStatus
```

---

## Skill System

### Mandatory Skill Schema

Every skill MUST define:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique identifier |
| `description` | str | Human-readable description |
| `skill_type` | SkillType | MOTION, MANIPULATION, SENSING, COMPOSITE |
| `inputs` | TypedDict | Input parameter definitions |
| `preconditions` | list[str] | World state requirements before execution |
| `effects` | list[str] | Expected world state changes after execution |
| `safety_constraints` | list[str] | Mandatory safety rules |

### Predefined Skills

| Skill | Type | Description | Key Parameters |
|-------|------|-------------|----------------|
| `grasp` | MANIPULATION | Approach and grip object | object_id, approach_height, grip_force |
| `move_to` | MOTION | Move to target pose | target_{x,y,z,rx,ry,rz}, speed, motion_type |
| `place` | MANIPULATION | Place object at target | object_id, target_{x,y,z}, approach_height |
| `release` | MANIPULATION | Open gripper | object_id, gripper_open_width |
| `rotate` | MOTION | Rotate end-effector | axis, angle, speed |
| `stop` | MOTION | Stop all motion | emergency: bool |

### Skill Constraints

**Skills CANNOT:**
- Directly control motors (must use IRobotAPI)
- Access raw sensor streams (use WorldState only)
- Ignore safety constraints
- Execute without precondition validation

**Skills MUST:**
- Return SkillStatus (SUCCESS/FAILED/PARTIAL)
- Validate preconditions before execution
- Log all safety constraint checks
- Be reversible when possible

### Skill Composition

Skills can be composed into sequences:

```python
class CompositeSkill:
    skills: list[SkillBase]           # Sequential skills
    parallel_skills: list[list[SkillBase]]  # Parallel groups
    fallback: Optional[SkillBase]     # On failure

    def validate_all(self) -> bool     # Validate entire composition
    def execute_all(self) -> SkillResponse
```

---

## Safety Mechanisms

### Layer-Specific Safety

#### Skill Layer
- Precondition validation before ANY execution
- Safety constraint checker
- Maximum execution time limits
- Rollback on failure

#### Robot API Layer
- Joint limit enforcement
- Velocity/acceleration limits
- Collision detection hooks
- Emergency stop capability

#### Hardware Layer
- Real-time safety monitoring
- Force limits
- Proximity detection
- Physical limit switches

### Safety Constraint Examples

```python
GRASP_SCHEMA.safety_constraints = [
    "grip_force must be within safe limits (0-100N)",
    "approach_height must be positive",
    "object must not be in Obstacle list",
    "gripper must not be moving when closing",
]

MOVE_TO_SCHEMA.safety_constraints = [
    "speed must be positive and within safe limits",
    "target must be within workspace bounds",
    "motion must not cause self-collision",
    "motion must not cause collision with obstacles",
]
```

### Emergency Stop Hierarchy

1. **Hardware E-Stop**: Physical emergency stop (highest priority)
2. **Software E-Stop**: Immediate motion halt via `stop(immediate=True)`
3. **Controlled Stop**: Graceful deceleration via `stop(immediate=False)`
4. **Skill-Level Stop**: Skill execution cancellation

---

## MetaClaw Integration

### Architecture - Dual Adapter Pattern

The MetaClaw integration uses a dual adapter pattern to maintain separation of concerns:

```
Planner Layer
    └── src/planner/metaclaw_adapter.py    # Thin interface to MetaClaw
            │
            └── src/metaclaw/              # Core MetaClaw integration
                ├── robot_claw_adapter.py  # Main MetaClaw bridge
                ├── skill_executor.py      # Precondition validation + execution
                ├── performance_tracker.py # Metrics + reward computation
                ├── prm_scorer.py         # Process reward model
                └── skill_converter.py    # SkillSchema ↔ SKILL.md conversion
```

**Why Dual Adapter?**
- `src/planner/metaclaw_adapter.py`: What PLANNER sees - thin adapter for reporting executions and receiving suggestions
- `src/metaclaw/`: Heavy integration logic - PerformanceTracker, PRMScorer, SkillConverter - kept encapsulated and reusable
- Planner doesn't need to know MetaClaw internals

### Data Flow

```
SkillExecutor.execute(skill)
    → RobotAPI.execute_skill()
    → ExecutionOutcome recorded
    → PerformanceTracker records
    → RobotSample created for MetaClaw
    → if success_rate < 0.4:
        → SkillEvolver.evolve(failed_samples)
        → Suggestion added to pending
```

### Integration Points

| Interface | Direction | Purpose |
|-----------|-----------|---------|
| Planner → MetaClaw | Feedback | Send execution results via `report_execution()` |
| MetaClaw → Planner | Suggest | Receive suggestions via `request_skill_suggestions()` |
| MetaClaw → Skill | Review | New skills validated before deployment |

### Skill Export Pipeline

Robot skills are exported to MetaClaw SKILL.md format:

```
SKILL_REGISTRY (src/skill/skill_schemas.py)
    ↓ RobotSkillConverter.export_all_skills()
MetaClaw/memory_data/skills/robotics/
    ├── grasp/SKILL.md
    ├── move_to/SKILL.md
    ├── approach_and_grasp/SKILL.md  (Phase 2 composite)
    └── pick_and_place/SKILL.md     (Phase 2 composite)
```

**Category Mapping:**
| SkillType | MetaClaw Category |
|-----------|-------------------|
| MOTION | robotics/motion |
| MANIPULATION | robotics/manipulation |
| SENSING | robotics/sensing |
| COMPOSITE | robotics/composite |

### Critical Constraint

> **MetaClaw CANNOT directly execute unverified skills.**

All skill execution MUST flow through:
```
MetaClaw → Planner → Skill Layer → Robot API → Hardware
```

New or modified skills from MetaClaw require:
1. Safety validation in Skill Layer
2. Review by Code Reviewer
3. Integration testing
4. Approval before deployment

---

## Project Structure

```
FeishuCLassmate/
├── src/
│   ├── planner/              # OpenClaw integration
│   │   ├── __init__.py
│   │   ├── planner.py        # Task decomposition
│   │   └── metaclaw_adapter.py  # Planner ↔ MetaClaw interface
│   │
│   ├── metaclaw/            # MetaClaw integration layer
│   │   ├── __init__.py
│   │   ├── robot_claw_adapter.py  # Main MetaClaw bridge
│   │   ├── skill_executor.py      # Precondition validation
│   │   ├── performance_tracker.py # Metrics + rewards
│   │   ├── prm_scorer.py         # Process reward model
│   │   └── skill_converter.py     # Schema ↔ SKILL.md
│   │
│   ├── skill/                # Skill implementations
│   │   ├── __init__.py
│   │   ├── skill_base.py     # Abstract base class
│   │   ├── skill_schemas.py  # Schema definitions
│   │   ├── grasp.py
│   │   ├── move_to.py
│   │   ├── place.py
│   │   ├── release.py
│   │   ├── rotate.py
│   │   └── stop.py
│   │
│   ├── robot_api/           # Robot Control API
│   │   ├── __init__.py
│   │   ├── robot_api.py      # IRobotAPI implementation
│   │   └── hardware_adapter.py
│   │
│   ├── hardware/            # Hardware/Simulator
│   │   ├── __init__.py
│   │   ├── simulator.py      # RobotSimulator
│   │   └── real_robot_adapter.py
│   │
│   └── shared/              # Shared components
│       ├── __init__.py
│       ├── interfaces.py    # IRobotAPI, enums, TypedDicts
│       └── world_state.py  # WorldState schema
│
├── backend/                  # FastAPI backend (to be created)
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── robot.py         # Robot endpoints
│   │   ├── skills.py        # Skill endpoints
│   │   └── websocket.py     # Real-time updates
│   └── services/
│       └── robot_service.py
│
├── frontend/                # Web UI
│   ├── index.html
│   ├── css/
│   └── js/
│
├── tests/                   # Test suite
│   ├── unit/
│   │   └── layer_tests/
│   │       ├── test_interfaces.py
│   │       ├── test_robot_api.py
│   │       ├── test_robot_simulator.py
│   │       └── test_world_state.py
│   ├── integration/
│   └── simulation/
│
├── MetaClaw/                 # External MetaClaw (submodule)
│
├── docs/                     # Documentation (to be created)
│   ├── architecture.md       # This file
│   ├── api_reference.md
│   └── skill_authoring.md
│
├── ARCHITECTURE.md           # This document
└── README.md                 # Project overview
```

---

## Development Workflow

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/{layer}-{name}` | `feature/skill-grasp-implementation` |
| Bug Fix | `fix/{layer}-{issue}` | `fix/robot-api-collision-detection` |
| Refactor | `refactor/{component}` | `refactor-skill-base-class` |
| Docs | `docs/{topic}` | `docs-api-reference` |

### Commit Message Format

```
{type}({layer}): {description}

[optional body with details]

[optional footer with ticket/issue]
```

**Types**: feat, fix, refactor, docs, test, chore

**Examples**:
```
feat(skill): implement grasp skill with force control

fix(robot-api): correct joint limit validation

test(hardware): add collision detection tests
```

### Tag Structure

```
v{phase}.{layer}-{description}
```

**Examples**:
- `v0.1-planner` - Planner layer complete
- `v0.2-skill` - Skill layer complete
- `v0.3-robot-api` - Robot API complete
- `v0.4-integration` - Full system integration

### Review Requirements

| Component | Reviews Required | Special Requirements |
|-----------|------------------|---------------------|
| IRobotAPI implementations | 2+ | Must test with RobotSimulator |
| Skill implementations | 2+ | Must validate against schema |
| Safety-critical code | 2+ | Must include safety analysis |
| MetaClaw adapter | 2+ | Must verify isolation |

---

## Appendix: File Index

### Core Interfaces
- `src/shared/interfaces.py` - IRobotAPI, enums, TypedDicts
- `src/shared/world_state.py` - WorldState, RobotState, WorldObject

### Implementations
- `src/robot_api/robot_api.py` - RobotAPI, MockHardwareAdapter
- `src/hardware/simulator.py` - RobotSimulator
- `src/skill/skill_schemas.py` - SkillSchema, SKILL_REGISTRY

### Tests
- `tests/unit/layer_tests/test_interfaces.py`
- `tests/unit/layer_tests/test_robot_api.py`
- `tests/unit/layer_tests/test_robot_simulator.py`
- `tests/unit/layer_tests/test_world_state.py`
