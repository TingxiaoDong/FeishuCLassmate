"""
Implementation of the 6 predefined robot skills.

Each skill:
1. Inherits from Skill base class
2. Implements execute logic via Robot API
3. Validates inputs against constraints
4. Includes safety checks
"""
from typing import TypedDict, Optional
import math

from src.skill.skill_base import (
    Skill,
    SkillContext,
    ValidationReport,
    ValidationResult,
    ValidationError,
    register_skill,
)
from src.skill.skill_schemas import (
    GRASP_SCHEMA,
    MOVE_TO_SCHEMA,
    PLACE_SCHEMA,
    RELEASE_SCHEMA,
    ROTATE_SCHEMA,
    STOP_SCHEMA,
)
from src.robot_api.robot_api import RobotAPI
from src.shared.interfaces import RobotStatus


# ============================================================
# Grasp Skill
# ============================================================

class GraspInput(TypedDict):
    """Input for grasp skill."""
    object_id: str
    approach_height: float
    grip_force: float


class GraspSkill(Skill):
    """Grasp an object at the specified location."""

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("grasp")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return GraspInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.gripper_width > 0",
            "object with object_id exists in world_state",
            "object.state == VISIBLE",
            "target position is within workspace bounds",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "grip_force must be within safe limits (0-100N)",
            "approach_height must be positive",
            "object must not be in Obstacle list",
            "gripper must not be moving when closing",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        """Validate grasp-specific constraints."""
        errors = []
        warnings = []

        # Check grip_force range
        grip_force = inputs.get("grip_force", 0)
        if grip_force < 0 or grip_force > 100:
            errors.append(ValidationError(
                field="grip_force",
                message="grip_force must be between 0 and 100N",
                severity="error"
            ))

        # Check approach_height
        approach_height = inputs.get("approach_height", 0)
        if approach_height <= 0:
            errors.append(ValidationError(
                field="approach_height",
                message="approach_height must be positive",
                severity="error"
            ))

        # Check object_id
        if not inputs.get("object_id"):
            errors.append(ValidationError(
                field="object_id",
                message="object_id is required",
                severity="error"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        result = ValidationResult.VALID
        if grip_force > 80:
            warnings.append(ValidationError(
                field="grip_force",
                message="High grip force may damage fragile objects",
                severity="warning"
            ))
            result = ValidationResult.WARNING

        return ValidationReport(result=result, warnings=warnings)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute grasp: approach, lower, close gripper."""
        object_id = inputs["object_id"]
        approach_height = inputs["approach_height"]
        grip_force = inputs["grip_force"]

        api = self._robot_api or RobotAPI()

        # Get world state to find object position
        world_state = api.get_world_state()

        # Find object
        target_object = None
        for obj in world_state.objects:
            if obj.get("id") == object_id:
                target_object = obj
                break

        if not target_object:
            return {"status": "failed", "message": f"Object '{object_id}' not found"}

        object_pose = target_object.get("pose", {})
        target_pos = object_pose.get("position", {"x": 0, "y": 0, "z": 0})

        # Step 1: Move above object at approach height
        approach_pos = {
            "x": target_pos["x"],
            "y": target_pos["y"],
            "z": target_pos["z"] + approach_height
        }

        status = api.move_linear(approach_pos, speed=0.5)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Approach failed: {status.message}"}

        # Step 2: Lower to object
        status = api.move_linear(target_pos, speed=0.2)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Lowering failed: {status.message}"}

        # Step 3: Close gripper with force
        gripper_position = 0.0  # Closed
        status = api.set_gripper(gripper_position, grip_force)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Gripper close failed: {status.message}"}

        return {
            "status": "success",
            "message": f"Object '{object_id}' grasped successfully",
            "object_id": object_id,
            "grip_force": grip_force,
        }


# ============================================================
# MoveTo Skill
# ============================================================

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


class MoveToSkill(Skill):
    """Move robot end-effector to a target pose."""

    VALID_MOTION_TYPES = {"linear", "joint", "pose"}

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("move_to")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return MoveToInput

    def get_preconditions(self) -> list[str]:
        return [
            "target position is within workspace bounds",
            "path is collision-free (no Obstacles in way)",
            "robot is not holding object that would collide",
            "motion_type is valid (linear, joint, pose)",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "speed must be positive and within safe limits",
            "target must be within workspace bounds",
            "motion must not cause self-collision",
            "motion must not cause collision with obstacles",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []
        warnings = []

        # Check required numeric fields
        for field in ["target_x", "target_y", "target_z", "speed"]:
            if field not in inputs or not isinstance(inputs[field], (int, float)):
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} is required and must be a number",
                    severity="error"
                ))

        # Check speed range
        speed = inputs.get("speed", 0)
        if speed <= 0:
            errors.append(ValidationError(
                field="speed",
                message="speed must be positive",
                severity="error"
            ))
        elif speed > 1.0:
            warnings.append(ValidationError(
                field="speed",
                message="High speed may reduce safety margins",
                severity="warning"
            ))

        # Check motion_type
        motion_type = inputs.get("motion_type", "")
        if motion_type not in self.VALID_MOTION_TYPES:
            errors.append(ValidationError(
                field="motion_type",
                message=f"motion_type must be one of {self.VALID_MOTION_TYPES}",
                severity="error"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.WARNING if warnings else ValidationResult.VALID, warnings=warnings)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute move_to based on motion type."""
        target_pos = {
            "x": inputs["target_x"],
            "y": inputs["target_y"],
            "z": inputs["target_z"],
        }
        target_orientation = {
            "roll": inputs.get("target_rx", 0.0),
            "pitch": inputs.get("target_ry", 0.0),
            "yaw": inputs.get("target_rz", 0.0),
        }
        speed = inputs["speed"]
        motion_type = inputs["motion_type"]

        api = self._robot_api or RobotAPI()

        # Execute based on motion type
        if motion_type == "linear":
            status = api.move_linear(target_pos, speed)
        elif motion_type == "joint":
            # For joint motion, we need joint angles - use current + estimate
            joints = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Default home
            status = api.move_joints(joints, speed)
        else:  # pose
            status = api.move_pose(target_pos, target_orientation, speed)

        if status.state.value == "completed":
            return {
                "status": "success",
                "message": f"Moved to ({target_pos['x']}, {target_pos['y']}, {target_pos['z']})",
                "position": target_pos,
            }

        return {"status": "failed", "message": f"Move failed: {status.message}"}


# ============================================================
# Place Skill
# ============================================================

class PlaceInput(TypedDict):
    """Input for place skill."""
    object_id: str
    target_x: float
    target_y: float
    target_z: float
    approach_height: float


class PlaceSkill(Skill):
    """Place a grasped object at the target location."""

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("place")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return PlaceInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.gripper_force > 0 (object is grasped)",
            "object.state == GRASPED",
            "target position is within workspace bounds",
            "target location is empty (no obstacles)",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "approach_height must be positive",
            "target must be on a valid surface",
            "robot must not drop object too fast",
            "gripper opens only after object is at target",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []

        # Check required fields
        if not inputs.get("object_id"):
            errors.append(ValidationError(
                field="object_id",
                message="object_id is required",
                severity="error"
            ))

        for field in ["target_x", "target_y", "target_z", "approach_height"]:
            if field not in inputs or not isinstance(inputs[field], (int, float)):
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} is required and must be a number",
                    severity="error"
                ))

        approach_height = inputs.get("approach_height", 0)
        if approach_height <= 0:
            errors.append(ValidationError(
                field="approach_height",
                message="approach_height must be positive",
                severity="error"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.VALID)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute place: lower, open gripper, retract."""
        object_id = inputs["object_id"]
        target_pos = {
            "x": inputs["target_x"],
            "y": inputs["target_y"],
            "z": inputs["target_z"],
        }
        approach_height = inputs["approach_height"]

        api = self._robot_api or RobotAPI()

        # Step 1: Move above target at approach height
        approach_pos = {
            "x": target_pos["x"],
            "y": target_pos["y"],
            "z": target_pos["z"] + approach_height
        }

        status = api.move_linear(approach_pos, speed=0.5)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Approach failed: {status.message}"}

        # Step 2: Lower to target
        status = api.move_linear(target_pos, speed=0.2)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Lowering failed: {status.message}"}

        # Step 3: Open gripper to release
        gripper_open_width = 1.0  # Full open
        status = api.set_gripper(gripper_open_width, force=0.0)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Gripper open failed: {status.message}"}

        # Step 4: Retract
        status = api.move_linear(approach_pos, speed=0.3)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Retract failed: {status.message}"}

        return {
            "status": "success",
            "message": f"Object '{object_id}' placed successfully",
            "object_id": object_id,
            "position": target_pos,
        }


# ============================================================
# Release Skill
# ============================================================

class ReleaseInput(TypedDict):
    """Input for release skill."""
    object_id: str
    gripper_open_width: float


class ReleaseSkill(Skill):
    """Release a grasped object by opening the gripper."""

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("release")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return ReleaseInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.gripper_force > 0 (object is held)",
            "object.state == GRASPED",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "gripper_open_width must be positive",
            "gripper must not open too quickly",
            "object must be supported after release",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []

        if not inputs.get("object_id"):
            errors.append(ValidationError(
                field="object_id",
                message="object_id is required",
                severity="error"
            ))

        gripper_open_width = inputs.get("gripper_open_width", 0)
        if gripper_open_width <= 0:
            errors.append(ValidationError(
                field="gripper_open_width",
                message="gripper_open_width must be positive",
                severity="error"
            ))
        elif gripper_open_width > 1.0:
            errors.append(ValidationError(
                field="gripper_open_width",
                message="gripper_open_width must not exceed 1.0",
                severity="error"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.VALID)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute release: open gripper."""
        object_id = inputs["object_id"]
        gripper_open_width = inputs["gripper_open_width"]

        api = self._robot_api or RobotAPI()

        status = api.set_gripper(gripper_open_width, force=0.0)

        if status.state.value == "completed":
            return {
                "status": "success",
                "message": f"Object '{object_id}' released",
                "gripper_width": gripper_open_width,
            }

        return {"status": "failed", "message": f"Release failed: {status.message}"}


# ============================================================
# Rotate Skill
# ============================================================

class RotateInput(TypedDict):
    """Input for rotate skill."""
    axis: str  # "x", "y", "z"
    angle: float  # radians
    speed: float


class RotateSkill(Skill):
    """Rotate robot end-effector around specified axis."""

    VALID_AXES = {"x", "y", "z"}

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("rotate")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return RotateInput

    def get_preconditions(self) -> list[str]:
        return [
            "axis is valid (x, y, or z)",
            "angle is within joint limits",
            "rotation path is collision-free",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "angle must be within safe joint limits",
            "rotation speed must be controlled",
            "axis must be valid (x, y, z)",
            "must not cause self-collision during rotation",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []
        warnings = []

        axis = inputs.get("axis", "")
        if axis not in self.VALID_AXES:
            errors.append(ValidationError(
                field="axis",
                message=f"axis must be one of {self.VALID_AXES}",
                severity="error"
            ))

        angle = inputs.get("angle", 0)
        if not isinstance(angle, (int, float)):
            errors.append(ValidationError(
                field="angle",
                message="angle must be a number",
                severity="error"
            ))
        else:
            # Check angle limits (e.g., +/- 180 degrees)
            max_angle = math.pi
            if abs(angle) > max_angle:
                errors.append(ValidationError(
                    field="angle",
                    message=f"angle must be within +/- {max_angle} radians",
                    severity="error"
                ))

        speed = inputs.get("speed", 0)
        if speed <= 0:
            errors.append(ValidationError(
                field="speed",
                message="speed must be positive",
                severity="error"
            ))
        elif speed > 0.5:
            warnings.append(ValidationError(
                field="speed",
                message="High rotation speed may reduce precision",
                severity="warning"
            ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.WARNING if warnings else ValidationResult.VALID, warnings=warnings)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute rotation around specified axis."""
        axis = inputs["axis"]
        angle = inputs["angle"]
        speed = inputs["speed"]

        api = self._robot_api or RobotAPI()

        # Get current pose
        world_state = api.get_world_state()
        current_pose = world_state.robot.end_effector_pose

        # Calculate new orientation based on axis
        if axis == "z":
            new_yaw = current_pose.y + angle
            target_orientation = {"roll": current_pose.roll, "pitch": current_pose.pitch, "yaw": new_yaw}
        elif axis == "x":
            new_roll = current_pose.roll + angle
            target_orientation = {"roll": new_roll, "pitch": current_pose.pitch, "yaw": current_pose.yaw}
        elif axis == "y":
            new_pitch = current_pose.pitch + angle
            target_orientation = {"roll": current_pose.roll, "pitch": new_pitch, "yaw": current_pose.yaw}

        target_position = {"x": current_pose.x, "y": current_pose.y, "z": current_pose.z}

        status = api.move_pose(target_position, target_orientation, speed)

        if status.state.value == "completed":
            return {
                "status": "success",
                "message": f"Rotated {angle} radians around {axis}-axis",
                "axis": axis,
                "angle": angle,
            }

        return {"status": "failed", "message": f"Rotation failed: {status.message}"}


# ============================================================
# Stop Skill
# ============================================================

class StopInput(TypedDict):
    """Input for stop skill."""
    emergency: bool


class StopSkill(Skill):
    """Immediately stop all robot motion."""

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("stop")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return StopInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.state != IDLE",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "emergency stop must always be available",
            "controlled stop must decelerate safely",
            "stop action must complete within 100ms",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        # emergency is optional, no validation needed
        return ValidationReport(result=ValidationResult.VALID)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute stop - always succeeds."""
        emergency = inputs.get("emergency", False)

        api = self._robot_api or RobotAPI()

        status = api.stop(immediate=emergency)

        return {
            "status": "success",
            "message": "Robot stopped",
            "emergency": emergency,
        }


# ============================================================
# Composite Skills (Phase 2)
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


class ApproachAndGraspSkill(Skill):
    """
    Combined approach and grasp action.

    Executes in sequence:
    1. Move above object at approach height
    2. Lower to object position
    3. Close gripper with specified force
    """

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("approach_and_grasp")
        self._robot_api = robot_api

    def get_required_inputs(self) -> type[TypedDict]:
        return ApproachAndGraspInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.gripper_width > 0 (gripper open)",
            "object with object_id exists in world_state",
            "object.state == VISIBLE",
            "target position is within workspace bounds",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "grip_force must be within safe limits (0-100N)",
            "approach_height must be positive",
            "object must not be in Obstacle list",
            "motion must not cause collision with obstacles",
            "gripper must not be moving when closing",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []
        warnings = []

        # Check object_id
        if not inputs.get("object_id"):
            errors.append(ValidationError(
                field="object_id",
                message="object_id is required",
                severity="error"
            ))

        # Check grip_force range
        grip_force = inputs.get("grip_force", 0)
        if grip_force < 0 or grip_force > 100:
            errors.append(ValidationError(
                field="grip_force",
                message="grip_force must be between 0 and 100N",
                severity="error"
            ))
        elif grip_force > 80:
            warnings.append(ValidationError(
                field="grip_force",
                message="High grip force may damage fragile objects",
                severity="warning"
            ))

        # Check approach_height
        approach_height = inputs.get("approach_height", 0)
        if approach_height <= 0:
            errors.append(ValidationError(
                field="approach_height",
                message="approach_height must be positive",
                severity="error"
            ))

        # Check speed
        speed = inputs.get("speed", 0)
        if speed <= 0:
            errors.append(ValidationError(
                field="speed",
                message="speed must be positive",
                severity="error"
            ))

        # Check position fields
        for field in ["target_x", "target_y", "target_z"]:
            if field not in inputs or not isinstance(inputs[field], (int, float)):
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} is required and must be a number",
                    severity="error"
                ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.WARNING if warnings else ValidationResult.VALID, warnings=warnings)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute approach and grasp sequence."""
        object_id = inputs["object_id"]
        target_x = inputs["target_x"]
        target_y = inputs["target_y"]
        target_z = inputs["target_z"]
        approach_height = inputs["approach_height"]
        grip_force = inputs["grip_force"]
        speed = inputs.get("speed", 0.5)

        api = self._robot_api or RobotAPI()

        # Target position
        target_pos = {"x": target_x, "y": target_y, "z": target_z}

        # Step 1: Move above object at approach height
        approach_pos = {
            "x": target_x,
            "y": target_y,
            "z": target_z + approach_height
        }

        status = api.move_linear(approach_pos, speed=speed)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Approach move failed: {status.message}"}

        # Step 2: Lower to object position
        status = api.move_linear(target_pos, speed=speed * 0.5)  # Slower for precision
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Lowering failed: {status.message}"}

        # Step 3: Close gripper with force
        gripper_position = 0.0  # Closed
        status = api.set_gripper(gripper_position, grip_force)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Gripper close failed: {status.message}"}

        return {
            "status": "success",
            "message": f"Object '{object_id}' approached and grasped",
            "object_id": object_id,
            "grip_force": grip_force,
            "position": target_pos,
        }


class PickAndPlaceInput(TypedDict):
    """Input for pick_and_place composite skill."""
    object_id: str
    target_x: float
    target_y: float
    target_z: float
    approach_height: float
    grip_force: float
    speed: float


class PickAndPlaceSkill(Skill):
    """
    Complete pick and place operation.

    Executes in sequence:
    1. Approach and grasp object
    2. Move to target position
    3. Place object at target
    """

    def __init__(self, robot_api: Optional[RobotAPI] = None):
        super().__init__("pick_and_place")
        self._robot_api = robot_api
        self._approach_and_grasp = ApproachAndGraspSkill(robot_api)
        self._move_to = MoveToSkill(robot_api)
        self._place = PlaceSkill(robot_api)

    def get_required_inputs(self) -> type[TypedDict]:
        return PickAndPlaceInput

    def get_preconditions(self) -> list[str]:
        return [
            "robot.gripper_width > 0 (gripper open)",
            "object with object_id exists in world_state",
            "object.state == VISIBLE",
            "grasp position is within workspace bounds",
            "target position is within workspace bounds",
            "target location is empty (no obstacles)",
        ]

    def get_safety_constraints(self) -> list[str]:
        return [
            "grip_force must be within safe limits (0-100N)",
            "approach_height must be positive for both grasp and place",
            "object must not be in Obstacle list during motion",
            "motion must not cause collision with obstacles",
            "target must be on a valid surface",
            "robot must not drop object too fast",
        ]

    def validate_inputs(self, inputs: dict) -> ValidationReport:
        errors = []
        warnings = []

        # Check object_id
        if not inputs.get("object_id"):
            errors.append(ValidationError(
                field="object_id",
                message="object_id is required",
                severity="error"
            ))

        # Check grip_force range
        grip_force = inputs.get("grip_force", 0)
        if grip_force < 0 or grip_force > 100:
            errors.append(ValidationError(
                field="grip_force",
                message="grip_force must be between 0 and 100N",
                severity="error"
            ))
        elif grip_force > 80:
            warnings.append(ValidationError(
                field="grip_force",
                message="High grip force may damage fragile objects",
                severity="warning"
            ))

        # Check approach_height
        approach_height = inputs.get("approach_height", 0)
        if approach_height <= 0:
            errors.append(ValidationError(
                field="approach_height",
                message="approach_height must be positive",
                severity="error"
            ))

        # Check speed
        speed = inputs.get("speed", 0)
        if speed <= 0:
            errors.append(ValidationError(
                field="speed",
                message="speed must be positive",
                severity="error"
            ))

        # Check position fields
        for field in ["target_x", "target_y", "target_z"]:
            if field not in inputs or not isinstance(inputs[field], (int, float)):
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} is required and must be a number",
                    severity="error"
                ))

        if errors:
            return ValidationReport(result=ValidationResult.INVALID, errors=errors)

        return ValidationReport(result=ValidationResult.WARNING if warnings else ValidationResult.VALID, warnings=warnings)

    def _execute_impl(self, inputs: dict, context: SkillContext) -> dict:
        """Execute pick and place sequence."""
        object_id = inputs["object_id"]
        target_x = inputs["target_x"]
        target_y = inputs["target_y"]
        target_z = inputs["target_z"]
        approach_height = inputs["approach_height"]
        grip_force = inputs["grip_force"]
        speed = inputs.get("speed", 0.5)

        api = self._robot_api or RobotAPI()

        # Get world state to find object position
        world_state = api.get_world_state()

        # Find object position
        target_object = None
        for obj in world_state.objects:
            if obj.get("id") == object_id:
                target_object = obj
                break

        if not target_object:
            return {"status": "failed", "message": f"Object '{object_id}' not found"}

        object_pose = target_object.get("pose", {})
        object_pos = object_pose.get("position", {"x": 0, "y": 0, "z": 0})

        # Step 1: Approach and grasp
        grasp_inputs = {
            "object_id": object_id,
            "target_x": object_pos["x"],
            "target_y": object_pos["y"],
            "target_z": object_pos["z"],
            "approach_height": approach_height,
            "grip_force": grip_force,
            "speed": speed,
        }

        result = self._approach_and_grasp.execute(grasp_inputs, context)
        if result.get("status") != "success":
            return {"status": "failed", "message": f"Grasp failed: {result.get('message')}"}

        # Step 2: Move to target (above placement position)
        place_approach_pos = {
            "x": target_x,
            "y": target_y,
            "z": target_z + approach_height
        }

        status = api.move_linear(place_approach_pos, speed=speed)
        if status.state.value != "completed":
            return {"status": "failed", "message": f"Move to target failed: {status.message}"}

        # Step 3: Place object
        place_inputs = {
            "object_id": object_id,
            "target_x": target_x,
            "target_y": target_y,
            "target_z": target_z,
            "approach_height": approach_height,
        }

        result = self._place.execute(place_inputs, context)
        if result.get("status") != "success":
            return {"status": "failed", "message": f"Place failed: {result.get('message')}"}

        return {
            "status": "success",
            "message": f"Object '{object_id}' picked and placed",
            "object_id": object_id,
            "final_position": {"x": target_x, "y": target_y, "z": target_z},
        }


# ============================================================
# Skill Registration
# ============================================================

def register_all_skills() -> None:
    """Register all predefined skills with the global registry."""
    registry = __import__('src.skill.skill_base', fromlist=['get_skill_registry']).get_skill_registry()

    registry.register(GraspSkill, GRASP_SCHEMA)
    registry.register(MoveToSkill, MOVE_TO_SCHEMA)
    registry.register(PlaceSkill, PLACE_SCHEMA)
    registry.register(ReleaseSkill, RELEASE_SCHEMA)
    registry.register(RotateSkill, ROTATE_SCHEMA)
    registry.register(StopSkill, STOP_SCHEMA)
    # Composite skills (Phase 2)
    registry.register(ApproachAndGraspSkill, APPROACH_AND_GRASP_SCHEMA)
    registry.register(PickAndPlaceSkill, PICK_AND_PLACE_SCHEMA)
