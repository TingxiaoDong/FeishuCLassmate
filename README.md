# Robotics System Architecture

## 4-Layer Architecture

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Planner Layer (OpenClaw)** | `src/planner/` | High-level task decomposition, sequencing |
| **Skill Layer** | `src/skill/` | Translates skill invocations into motion primitives |
| **Robot Control API Layer** | `src/robot_api/` | Hardware-agnostic interface (navigation, manipulation, sensing) |
| **Hardware / Simulator Layer** | `src/hardware/` | Actual robot/simulator execution |

**Shared Components:** `src/shared/` - interfaces, enums, world state

---

## Key Interfaces

### Planner → Skill
```python
SkillRequest:
  task_id: str
  instruction: str
  context: dict

SkillResponse:
  task_id: str
  status: SkillStatus (SUCCESS/FAILED/PARTIAL)
  result: dict
  skill_name: str
```

### Skill → Robot API (IRobotAPI interface)
```python
RobotAction (Enum):
  MOVE_JOINTS, MOVE_POSE, MOVE_LINEAR, SET_GRIPPER, STOP, EXECUTE_SKILL

TypedDicts:
  MoveJointsParams, MovePoseParams, MoveLinearParams,
  SetGripperParams, StopParams, ExecuteSkillParams

RobotStatus:
  command_id: str
  state: RobotState (IDLE/EXECUTING/COMPLETED/ERROR)  # Enum!
  position: dict
  joints: list[float]
  gripper_state: float
  sensor_data: dict
  message: str
```

**IRobotAPI Methods:**
- `move_joints(joints: list[float], speed: float) -> RobotStatus`
- `move_pose(position: Position3D, orientation: Orientation3D, speed: float) -> RobotStatus`
- `move_linear(target: Position3D, speed: float) -> RobotStatus`
- `set_gripper(position: float, force: float) -> RobotStatus`
- `get_world_state() -> WorldState`
- `execute_skill(skill_name: str, parameters: dict) -> RobotStatus`
- `stop(immediate: bool = False) -> RobotStatus`

---

## Skill Schema (MANDATORY)

Every skill must have:
- **name**: Unique identifier
- **description**: What it does
- **inputs**: Parameter definitions
- **preconditions**: World state requirements before execution
- **effects**: World state changes after execution
- **safety_constraints**: Mandatory limits

**What skills CANNOT do:**
- Directly control motors (must go through Robot API)
- Access raw sensor streams (use abstracted World State only)
- Ignore safety constraints

---

## Robot API Capabilities

**Navigation:**
- `navigate_to(x, y, z, speed)` - Move to 3D position
- `move_relative(dx, dy, dz, speed)` - Relative movement
- `get_position()` - Query current position

**Manipulation:**
- `grip(force, position)` - Grip an object
- `release()` - Release held object
- `lift_to(height, speed)` - Lift arm
- `place_at(x, y, z)` - Place object
- `rotate(angle, axis)` - Rotate
- `stop_motion()` - Stop all motion

**Sensing:**
- `get_robot_status()` - Full status
- `get_sensor_data(sensor_type)` - Specific sensors
- `wait_for_state(target_state, timeout)` - State wait

**System:**
- `emergency_stop()` - Immediate halt
- `reset_robot()` - Reset to default

---

## Project Structure

```
FeishuCLassmate/
├── src/
│   ├── planner/        # OpenClaw integration
│   ├── skill/          # Skill implementations
│   ├── robot_api/      # Robot Control API
│   ├── hardware/       # Hardware/Simulator layer
│   └── shared/         # Interfaces, enums, world state
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── simulation/     # Simulation tests
├── MetaClaw/           # MetaClaw learning system (external)
└── README.md
```

---

## Branch Naming Convention

- `feature/planner-xxx`
- `feature/skill-xxx`
- `feature/robot-api-xxx`
- `feature/hardware-xxx`
- `feature/shared-xxx`

---

## Tag Structure

- `v0.1-planner`, `v0.2-skill`, etc.