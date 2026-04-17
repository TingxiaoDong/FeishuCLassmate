"""
Unit tests for interface schema compliance.
Tests that all interfaces match the locked architecture specification.

Authoritative source: src/shared/interfaces.py
"""
import pytest
from enum import Enum
from typing import TypedDict, get_type_hints, get_origin, get_args
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src", "shared"))

from interfaces import (
    RobotAction,
    RobotState,
    SkillStatus,
    MoveJointsParams,
    MovePoseParams,
    MoveLinearParams,
    SetGripperParams,
    StopParams,
    ExecuteSkillParams,
    Position3D,
    Orientation3D,
    RobotCommand,
    RobotStatus,
)


class TestRobotActionEnum:
    """Verify RobotAction Enum has exactly the required values."""

    def test_robot_action_has_correct_values(self):
        """RobotAction must have exactly: MOVE_JOINTS, MOVE_POSE, MOVE_LINEAR, SET_GRIPPER, STOP, EXECUTE_SKILL"""
        expected_actions = {"MOVE_JOINTS", "MOVE_POSE", "MOVE_LINEAR", "SET_GRIPPER", "STOP", "EXECUTE_SKILL"}
        actual_actions = {action.name for action in RobotAction}
        assert actual_actions == expected_actions, (
            f"RobotAction has {actual_actions}, expected {expected_actions}"
        )

    def test_robot_action_is_enum(self):
        """RobotAction must be an Enum."""
        assert issubclass(RobotAction, Enum)

    def test_robot_action_values_are_strings(self):
        """RobotAction values must be strings for serialization."""
        for action in RobotAction:
            assert isinstance(action.value, str), (
                f"RobotAction.{action.name} value must be string, got {type(action.value)}"
            )

    def test_robot_action_enum_values_match_spec(self):
        """RobotAction values must match spec exactly."""
        expected = {
            "MOVE_JOINTS": "move_joints",
            "MOVE_POSE": "move_pose",
            "MOVE_LINEAR": "move_linear",
            "SET_GRIPPER": "set_gripper",
            "STOP": "stop",
            "EXECUTE_SKILL": "execute_skill",
        }
        for name, expected_value in expected.items():
            assert RobotAction[name].value == expected_value


class TestRobotStateEnum:
    """Verify RobotState Enum has exactly the required values."""

    def test_robot_state_has_correct_values(self):
        """RobotState must have exactly: IDLE, EXECUTING, COMPLETED, ERROR"""
        expected_states = {"IDLE", "EXECUTING", "COMPLETED", "ERROR"}
        actual_states = {state.name for state in RobotState}
        assert actual_states == expected_states

    def test_robot_state_is_enum(self):
        """RobotState must be an Enum."""
        assert issubclass(RobotState, Enum)

    def test_robot_state_enum_values_match_spec(self):
        """RobotState values must match spec exactly."""
        expected = {
            "IDLE": "idle",
            "EXECUTING": "executing",
            "COMPLETED": "completed",
            "ERROR": "error",
        }
        for name, expected_value in expected.items():
            assert RobotState[name].value == expected_value


class TestSkillStatusEnum:
    """Verify SkillStatus Enum has exactly the required values."""

    def test_skill_status_has_correct_values(self):
        """SkillStatus must have exactly: SUCCESS, FAILED, PARTIAL"""
        expected_statuses = {"SUCCESS", "FAILED", "PARTIAL"}
        actual_statuses = {status.name for status in SkillStatus}
        assert actual_statuses == expected_statuses

    def test_skill_status_is_enum(self):
        """SkillStatus must be an Enum."""
        assert issubclass(SkillStatus, Enum)

    def test_skill_status_enum_values_match_spec(self):
        """SkillStatus values must match spec exactly."""
        expected = {
            "SUCCESS": "success",
            "FAILED": "failed",
            "PARTIAL": "partial",
        }
        for name, expected_value in expected.items():
            assert SkillStatus[name].value == expected_value


class TestTypedDictSchemas:
    """Verify all TypedDict params have required fields."""

    def test_move_joints_params_has_required_fields(self):
        """MoveJointsParams must have joints, speed fields."""
        required_fields = {"joints", "speed"}
        actual_fields = set(MoveJointsParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_move_pose_params_has_required_fields(self):
        """MovePoseParams must have position, orientation, speed fields."""
        required_fields = {"position", "orientation", "speed"}
        actual_fields = set(MovePoseParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_move_linear_params_has_required_fields(self):
        """MoveLinearParams must have target, speed fields."""
        required_fields = {"target", "speed"}
        actual_fields = set(MoveLinearParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_set_gripper_params_has_required_fields(self):
        """SetGripperParams must have position, force fields."""
        required_fields = {"position", "force"}
        actual_fields = set(SetGripperParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_stop_params_has_required_fields(self):
        """StopParams must have immediate field."""
        required_fields = {"immediate"}
        actual_fields = set(StopParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_execute_skill_params_has_required_fields(self):
        """ExecuteSkillParams must have skill_name, parameters fields."""
        required_fields = {"skill_name", "parameters"}
        actual_fields = set(ExecuteSkillParams.__annotations__.keys())
        assert actual_fields == required_fields

    def test_position_3d_has_required_fields(self):
        """Position3D must have x, y, z fields."""
        required_fields = {"x", "y", "z"}
        actual_fields = set(Position3D.__annotations__.keys())
        assert actual_fields == required_fields

    def test_orientation_3d_has_required_fields(self):
        """Orientation3D must have roll, pitch, yaw fields."""
        required_fields = {"roll", "pitch", "yaw"}
        actual_fields = set(Orientation3D.__annotations__.keys())
        assert actual_fields == required_fields


class TestRobotCommand:
    """Verify RobotCommand structure."""

    def test_robot_command_has_required_fields(self):
        """RobotCommand must have command_id, command, params fields."""
        required_fields = {"command_id", "command", "params"}
        actual_fields = set(RobotCommand.__annotations__.keys())
        assert actual_fields == required_fields

    def test_robot_command_command_is_robot_action_enum(self):
        """RobotCommand.command must be RobotAction Enum type."""
        hints = get_type_hints(RobotCommand)
        assert hints["command"] == RobotAction


class TestRobotStatus:
    """Verify RobotStatus structure."""

    def test_robot_status_has_required_fields(self):
        """RobotStatus must have command_id, state, position, joints, gripper_state, sensor_data, message."""
        required_fields = {"command_id", "state", "position", "joints", "gripper_state", "sensor_data", "message"}
        actual_fields = set(RobotStatus.__annotations__.keys())
        assert actual_fields == required_fields

    def test_robot_status_state_is_robot_state_enum(self):
        """RobotStatus.state must be RobotState Enum type."""
        hints = get_type_hints(RobotStatus)
        assert hints["state"] == RobotState


class TestInterfaceConstraints:
    """Verify architectural constraints."""

    def test_all_params_are_typeddict(self):
        """All param classes must be TypedDict (subclass of dict)."""
        param_classes = [
            MoveJointsParams,
            MovePoseParams,
            MoveLinearParams,
            SetGripperParams,
            StopParams,
            ExecuteSkillParams,
            Position3D,
            Orientation3D,
        ]
        for param_class in param_classes:
            assert issubclass(param_class, dict), (
                f"{param_class.__name__} must inherit from dict (TypedDict)"
            )

    def test_irobot_api_has_required_methods(self):
        """IRobotAPI must have all required methods."""
        required_methods = {
            "move_joints",
            "move_pose",
            "move_linear",
            "set_gripper",
            "get_world_state",
            "execute_skill",
            "stop",
        }
        from interfaces import IRobotAPI
        actual_methods = {name for name in dir(IRobotAPI) if not name.startswith("_")}
        # Interface methods are: move_joints, move_pose, move_linear, set_gripper, get_world_state, execute_skill, stop
        assert required_methods.issubset(actual_methods), (
            f"IRobotAPI missing methods: {required_methods - actual_methods}"
        )
