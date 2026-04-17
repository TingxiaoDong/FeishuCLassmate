"""
Skill schemas for the robotics system.

Each skill follows the mandatory schema:
- name: Unique identifier for the skill
- description: Human-readable description of what the skill does
- inputs: Required input parameters (TypedDict)
- preconditions: Conditions that must be true before execution
- effects: Expected outcomes after successful execution
- safety_constraints: Safety rules that must be observed
"""
from dataclasses import dataclass, field
from typing import TypedDict, Optional
from enum import Enum


class SkillType(Enum):
    """Categories of skills."""
    MOTION = "motion"
    MANIPULATION = "manipulation"
    SENSING = "sensing"
    COMPOSITE = "composite"


class SkillStatus(Enum):
    """Status of skill execution."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# ============================================================
# SkillRequest / SkillResponse (Planner-Skill Interface)
# ============================================================

class SkillRequest(TypedDict):
    """Request from Planner to Skill layer.

    This is the primary interface between the Planner layer and the Skill layer.
    """
    task_id: str           # Unique task identifier
    instruction: str         # Natural language instruction
    context: dict           # Additional context (world_state, etc.)


class SkillResponse(TypedDict):
    """Response from Skill layer to Planner.

    Contains execution results and status.
    """
    task_id: str           # Matches the request task_id
    status: SkillStatus    # SUCCESS | FAILED | PARTIAL
    result: dict           # Execution results (skill-specific)
    skill_name: str        # Which skill was executed
    message: str           # Human-readable status message


# ============================================================
# Skill Input TypedDicts
# ============================================================

class GraspInput(TypedDict):
    """Input for grasp skill."""
    object_id: str
    approach_height: float
    grip_force: float


class MoveToInput(TypedDict):
    """Input for move_to skill."""
    target_x: float
    target_y: float
    target_z: float
    target_rx: float
    target_ry: float
    target_rz: float
    speed: float
    motion_type: str  # "linear", "joint", "pose"


class PlaceInput(TypedDict):
    """Input for place skill."""
    object_id: str
    target_x: float
    target_y: float
    target_z: float
    approach_height: float


class ReleaseInput(TypedDict):
    """Input for release skill."""
    object_id: str
    gripper_open_width: float


class RotateInput(TypedDict):
    """Input for rotate skill."""
    axis: str  # "x", "y", "z"
    angle: float  # radians
    speed: float


class StopInput(TypedDict):
    """Input for stop skill."""
    emergency: bool


# ============================================================
# Composite Skill Input TypedDicts
# ============================================================

class ApproachAndGraspInput(TypedDict):
    """Input for approach_and_grasp composite skill."""
    object_id: str
    target_x: float
    target_y: float
    target_z: float
    approach_height: float
    grip_force: float
    speed: float


class PickAndPlaceInput(TypedDict):
    """Input for pick_and_place composite skill."""
    object_id: str
    target_x: float
    target_y: float
    target_z: float
    approach_height: float
    grip_force: float
    speed: float


# ============================================================
# Skill Schema Dataclass
# ============================================================

@dataclass
class SkillSchema:
    """Mandatory schema for all skills."""
    name: str
    description: str
    skill_type: SkillType
    inputs: type[TypedDict]
    preconditions: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    safety_constraints: list[str] = field(default_factory=list)


# ============================================================
# Initial Skill Schemas
# ============================================================

GRASP_SCHEMA = SkillSchema(
    name="grasp",
    description="Grasp an object at the specified location. Approaches the object, closes gripper with specified force.",
    skill_type=SkillType.MANIPULATION,
    inputs=GraspInput,
    preconditions=[
        "robot.gripper_width > 0",
        "object with object_id exists in world_state",
        "object.state == VISIBLE",
        "object not in Obstacle list",
        "target position is within workspace bounds",
    ],
    effects=[
        "object.state == GRASPED",
        "robot.gripper_force > 0",
        "robot.gripper_width == 0 (object held)",
    ],
    safety_constraints=[
        "grip_force must be within safe limits (0-100N)",
        "approach_height must be positive",
        "object must not be in Obstacle list",
        "gripper must not be moving when closing",
    ],
)

MOVE_TO_SCHEMA = SkillSchema(
    name="move_to",
    description="Move robot end-effector to a target pose. Supports linear, joint, and pose motion types.",
    skill_type=SkillType.MOTION,
    inputs=MoveToInput,
    preconditions=[
        "robot.state == IDLE or robot.state == EXECUTING",
        "robot.target position is within workspace bounds",
        "robot.path is collision-free (no Obstacles in way)",
        "robot.is not holding object that would collide",
        "robot.motion_type is valid (linear, joint, pose)",
    ],
    effects=[
        "robot.end_effector_pose matches target pose",
        "robot.state == COMPLETED",
    ],
    safety_constraints=[
        "speed must be positive and within safe limits",
        "target must be within workspace bounds",
        "motion must not cause self-collision",
        "motion must not cause collision with obstacles",
    ],
)

PLACE_SCHEMA = SkillSchema(
    name="place",
    description="Place a grasped object at the target location. Lowers object, opens gripper, retracts.",
    skill_type=SkillType.MANIPULATION,
    inputs=PlaceInput,
    preconditions=[
        "robot.gripper_force > 0 (object is grasped)",
        "object.state == GRASPED",
        "target position is within workspace bounds",
        "target location is empty (no obstacles)",
    ],
    effects=[
        "object.state == PLACED",
        "object.pose matches target",
        "robot.gripper_force == 0",
        "robot.gripper_width > 0",
    ],
    safety_constraints=[
        "approach_height must be positive",
        "target must be on a valid surface",
        "robot must not drop object too fast",
        "gripper opens only after object is at target",
    ],
)

RELEASE_SCHEMA = SkillSchema(
    name="release",
    description="Release a grasped object by opening the gripper to specified width.",
    skill_type=SkillType.MANIPULATION,
    inputs=ReleaseInput,
    preconditions=[
        "robot.gripper_force > 0 (object is held)",
        "object.state == GRASPED",
    ],
    effects=[
        "robot.gripper_force == 0",
        "robot.gripper_width >= gripper_open_width",
        "object.state == VISIBLE (object released)",
    ],
    safety_constraints=[
        "gripper_open_width must be positive",
        "gripper must not open too quickly",
        "object must be supported after release",
    ],
)

ROTATE_SCHEMA = SkillSchema(
    name="rotate",
    description="Rotate robot end-effector around specified axis by given angle.",
    skill_type=SkillType.MOTION,
    inputs=RotateInput,
    preconditions=[
        "robot.axis is valid (x, y, or z)",
        "robot.angle is within joint limits",
        "robot.rotation path is collision-free",
    ],
    effects=[
        "robot.end_effector_pose rz updated by angle (for z-axis rotation)",
        "robot.state == COMPLETED",
    ],
    safety_constraints=[
        "angle must be within safe joint limits",
        "rotation speed must be controlled",
        "axis must be valid (x, y, z)",
        "must not cause self-collision during rotation",
    ],
)

STOP_SCHEMA = SkillSchema(
    name="stop",
    description="Immediately stop all robot motion. Can be emergency or controlled stop.",
    skill_type=SkillType.MOTION,
    inputs=StopInput,
    preconditions=[
        "robot.state != IDLE",
    ],
    effects=[
        "robot.state == IDLE",
        "all motion commands cancelled",
        "if emergency: gripper forced open",
    ],
    safety_constraints=[
        "emergency stop must always be available",
        "controlled stop must decelerate safely",
        "stop action must complete within 100ms",
        "speed must be within safe limits during deceleration",
    ],
)


# ============================================================
# Composite Skill Schemas
# ============================================================

APPROACH_AND_GRASP_SCHEMA = SkillSchema(
    name="approach_and_grasp",
    description="Combined approach and grasp action. Moves to approach position above object, descends, then grasps with specified force.",
    skill_type=SkillType.COMPOSITE,
    inputs=ApproachAndGraspInput,
    preconditions=[
        "robot.gripper_width > 0 (gripper open)",
        "object with object_id exists in world_state",
        "object.state == VISIBLE",
        "target position is within workspace bounds",
    ],
    effects=[
        "object.state == GRASPED",
        "robot.gripper_force > 0",
        "robot.gripper_width == 0 (object held)",
    ],
    safety_constraints=[
        "grip_force must be within safe limits (0-100N)",
        "approach_height must be positive",
        "object must not be in Obstacle list",
        "motion must not cause collision with obstacles",
        "gripper must not be moving when closing",
    ],
)

PICK_AND_PLACE_SCHEMA = SkillSchema(
    name="pick_and_place",
    description="Complete pick and place operation. Grasps object at current location and places it at target location.",
    skill_type=SkillType.COMPOSITE,
    inputs=PickAndPlaceInput,
    preconditions=[
        "robot.gripper_width > 0 (gripper open)",
        "object with object_id exists in world_state",
        "object.state == VISIBLE",
        "grasp position is within workspace bounds",
        "target position is within workspace bounds",
        "target location is empty (no obstacles)",
    ],
    effects=[
        "object.state == PLACED",
        "object.pose matches target position",
        "robot.gripper_force == 0",
        "robot.gripper_width > 0",
    ],
    safety_constraints=[
        "grip_force must be within safe limits (0-100N)",
        "approach_height must be positive for both grasp and place",
        "object must not be in Obstacle list during motion",
        "motion must not cause collision with obstacles",
        "target must be on a valid surface",
        "robot must not drop object too fast",
    ],
)


# ============================================================
# Skill Registry
# ============================================================

SKILL_REGISTRY: dict[str, SkillSchema] = {
    "grasp": GRASP_SCHEMA,
    "move_to": MOVE_TO_SCHEMA,
    "place": PLACE_SCHEMA,
    "release": RELEASE_SCHEMA,
    "rotate": ROTATE_SCHEMA,
    "stop": STOP_SCHEMA,
    # Composite skills (Phase 2)
    "approach_and_grasp": APPROACH_AND_GRASP_SCHEMA,
    "pick_and_place": PICK_AND_PLACE_SCHEMA,
}


def get_skill_schema(skill_name: str) -> Optional[SkillSchema]:
    """Get skill schema by name."""
    return SKILL_REGISTRY.get(skill_name)


def list_skills() -> list[str]:
    """List all available skill names."""
    return list(SKILL_REGISTRY.keys())
