"""
Unit tests for Skill Schema validation.

Tests that skill schemas conform to the mandatory schema structure
and that preconditions/effects/safety_constraints are properly defined.

Authoritative source: src/skill/skill_schemas.py
"""
import pytest
from dataclasses import dataclass
from typing import TypedDict, get_type_hints

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.skill.skill_schemas import (
    SkillSchema,
    SkillType,
    SKILL_REGISTRY,
    get_skill_schema,
    list_skills,
    GRASP_SCHEMA,
    MOVE_TO_SCHEMA,
    PLACE_SCHEMA,
    RELEASE_SCHEMA,
    ROTATE_SCHEMA,
    STOP_SCHEMA,
    GraspInput,
    MoveToInput,
    PlaceInput,
    ReleaseInput,
    RotateInput,
    StopInput,
)


class TestSkillRegistry:
    """Tests for the skill registry."""

    def test_skill_registry_has_core_skills(self):
        """Registry should contain the 6 core skills."""
        expected = {"grasp", "move_to", "place", "release", "rotate", "stop"}
        actual = set(SKILL_REGISTRY.keys())
        # Check that all core skills are present (may have additional skills)
        assert expected.issubset(actual), f"Core skills missing: {expected - actual}"

    def test_list_skills_returns_core_skills(self):
        """list_skills should return at least the core skill names."""
        skills = list_skills()
        assert len(skills) >= 6  # May have additional skills
        assert "grasp" in skills
        assert "move_to" in skills
        assert "stop" in skills
        assert "place" in skills
        assert "release" in skills
        assert "rotate" in skills

    def test_get_skill_schema_returns_valid_schema(self):
        """get_skill_schema should return SkillSchema for known skills."""
        schema = get_skill_schema("grasp")
        assert schema is not None
        assert isinstance(schema, SkillSchema)

    def test_get_skill_schema_returns_none_for_unknown(self):
        """get_skill_schema should return None for unknown skills."""
        schema = get_skill_schema("unknown_skill")
        assert schema is None


class TestSkillSchemaStructure:
    """Tests for SkillSchema mandatory fields."""

    def test_skill_schema_has_mandatory_fields(self):
        """SkillSchema must have name, description, skill_type, inputs."""
        schema = GRASP_SCHEMA
        assert hasattr(schema, 'name')
        assert hasattr(schema, 'description')
        assert hasattr(schema, 'skill_type')
        assert hasattr(schema, 'inputs')
        assert hasattr(schema, 'preconditions')
        assert hasattr(schema, 'effects')
        assert hasattr(schema, 'safety_constraints')

    def test_skill_schema_name_is_string(self):
        """SkillSchema.name must be a string."""
        for schema in SKILL_REGISTRY.values():
            assert isinstance(schema.name, str)
            assert len(schema.name) > 0

    def test_skill_schema_description_is_string(self):
        """SkillSchema.description must be a non-empty string."""
        for schema in SKILL_REGISTRY.values():
            assert isinstance(schema.description, str)
            assert len(schema.description) > 0

    def test_skill_schema_skill_type_is_valid(self):
        """SkillSchema.skill_type must be a valid SkillType."""
        valid_types = {SkillType.MOTION, SkillType.MANIPULATION, SkillType.SENSING, SkillType.COMPOSITE}
        for schema in SKILL_REGISTRY.values():
            assert schema.skill_type in valid_types

    def test_skill_schema_inputs_is_typeddict(self):
        """SkillSchema.inputs must be a TypedDict subclass."""
        for schema in SKILL_REGISTRY.values():
            assert issubclass(schema.inputs, dict)

    def test_skill_schema_preconditions_is_list(self):
        """SkillSchema.preconditions must be a list of strings."""
        for schema in SKILL_REGISTRY.values():
            assert isinstance(schema.preconditions, list)
            for p in schema.preconditions:
                assert isinstance(p, str)

    def test_skill_schema_effects_is_list(self):
        """SkillSchema.effects must be a list of strings."""
        for schema in SKILL_REGISTRY.values():
            assert isinstance(schema.effects, list)
            for e in schema.effects:
                assert isinstance(e, str)

    def test_skill_schema_safety_constraints_is_list(self):
        """SkillSchema.safety_constraints must be a list of strings."""
        for schema in SKILL_REGISTRY.values():
            assert isinstance(schema.safety_constraints, list)
            for s in schema.safety_constraints:
                assert isinstance(s, str)


class TestGraspSkill:
    """Tests for grasp skill schema."""

    def test_grasp_schema_name(self):
        """GRASP_SCHEMA should have name 'grasp'."""
        assert GRASP_SCHEMA.name == "grasp"

    def test_grasp_schema_type(self):
        """GRASP_SCHEMA should be MANIPULATION type."""
        assert GRASP_SCHEMA.skill_type == SkillType.MANIPULATION

    def test_grasp_input_has_required_fields(self):
        """GraspInput must have object_id, approach_height, grip_force."""
        hints = get_type_hints(GraspInput)
        required = {"object_id", "approach_height", "grip_force"}
        assert set(hints.keys()) == required

    def test_grasp_preconditions_are_defined(self):
        """GRASP_SCHEMA should have preconditions."""
        assert len(GRASP_SCHEMA.preconditions) > 0

    def test_grasp_safety_constraints_are_defined(self):
        """GRASP_SCHEMA should have safety_constraints."""
        assert len(GRASP_SCHEMA.safety_constraints) > 0


class TestMoveToSkill:
    """Tests for move_to skill schema."""

    def test_move_to_schema_name(self):
        """MOVE_TO_SCHEMA should have name 'move_to'."""
        assert MOVE_TO_SCHEMA.name == "move_to"

    def test_move_to_schema_type(self):
        """MOVE_TO_SCHEMA should be MOTION type."""
        assert MOVE_TO_SCHEMA.skill_type == SkillType.MOTION

    def test_move_to_input_has_required_fields(self):
        """MoveToInput must have all required pose and motion fields."""
        hints = get_type_hints(MoveToInput)
        required = {
            "target_x", "target_y", "target_z",
            "target_rx", "target_ry", "target_rz",
            "speed", "motion_type"
        }
        assert set(hints.keys()) == required

    def test_move_to_motion_type_constraint(self):
        """move_to preconditions should specify valid motion_type."""
        motion_type_constraint = "robot.motion_type is valid (linear, joint, pose)"
        assert motion_type_constraint in MOVE_TO_SCHEMA.preconditions


class TestPlaceSkill:
    """Tests for place skill schema."""

    def test_place_schema_name(self):
        """PLACE_SCHEMA should have name 'place'."""
        assert PLACE_SCHEMA.name == "place"

    def test_place_schema_type(self):
        """PLACE_SCHEMA should be MANIPULATION type."""
        assert PLACE_SCHEMA.skill_type == SkillType.MANIPULATION

    def test_place_input_has_required_fields(self):
        """PlaceInput must have object_id, target position, approach_height."""
        hints = get_type_hints(PlaceInput)
        required = {"object_id", "target_x", "target_y", "target_z", "approach_height"}
        assert set(hints.keys()) == required

    def test_place_precondition_gripper_force(self):
        """place should require robot.gripper_force > 0 (object grasped)."""
        gripper_constraint = "robot.gripper_force > 0 (object is grasped)"
        assert gripper_constraint in PLACE_SCHEMA.preconditions


class TestReleaseSkill:
    """Tests for release skill schema."""

    def test_release_schema_name(self):
        """RELEASE_SCHEMA should have name 'release'."""
        assert RELEASE_SCHEMA.name == "release"

    def test_release_schema_type(self):
        """RELEASE_SCHEMA should be MANIPULATION type."""
        assert RELEASE_SCHEMA.skill_type == SkillType.MANIPULATION

    def test_release_input_has_required_fields(self):
        """ReleaseInput must have object_id and gripper_open_width."""
        hints = get_type_hints(ReleaseInput)
        required = {"object_id", "gripper_open_width"}
        assert set(hints.keys()) == required


class TestRotateSkill:
    """Tests for rotate skill schema."""

    def test_rotate_schema_name(self):
        """ROTATE_SCHEMA should have name 'rotate'."""
        assert ROTATE_SCHEMA.name == "rotate"

    def test_rotate_schema_type(self):
        """ROTATE_SCHEMA should be MOTION type."""
        assert ROTATE_SCHEMA.skill_type == SkillType.MOTION

    def test_rotate_input_has_required_fields(self):
        """RotateInput must have axis, angle, speed."""
        hints = get_type_hints(RotateInput)
        required = {"axis", "angle", "speed"}
        assert set(hints.keys()) == required

    def test_rotate_axis_constraint(self):
        """rotate preconditions should specify valid axis (x, y, z)."""
        axis_constraint = "robot.axis is valid (x, y, or z)"
        assert axis_constraint in ROTATE_SCHEMA.preconditions


class TestStopSkill:
    """Tests for stop skill schema."""

    def test_stop_schema_name(self):
        """STOP_SCHEMA should have name 'stop'."""
        assert STOP_SCHEMA.name == "stop"

    def test_stop_schema_type(self):
        """STOP_SCHEMA should be MOTION type."""
        assert STOP_SCHEMA.skill_type == SkillType.MOTION

    def test_stop_input_has_required_fields(self):
        """StopInput must have emergency boolean."""
        hints = get_type_hints(StopInput)
        required = {"emergency"}
        assert set(hints.keys()) == required

    def test_stop_safety_constraints_defined(self):
        """STOP_SCHEMA should have safety_constraints for emergency stop."""
        assert len(STOP_SCHEMA.safety_constraints) > 0
        # Should mention emergency stop availability
        safety_text = " ".join(STOP_SCHEMA.safety_constraints)
        assert "emergency stop" in safety_text.lower()


class TestSkillTypeEnum:
    """Tests for SkillType enum."""

    def test_skill_type_values(self):
        """SkillType should have MOTION, MANIPULATION, SENSING, COMPOSITE."""
        expected = {"MOTION", "MANIPULATION", "SENSING", "COMPOSITE"}
        actual = {t.name for t in SkillType}
        assert actual == expected

    def test_skill_type_values_are_strings(self):
        """SkillType values should be lowercase strings."""
        for t in SkillType:
            assert isinstance(t.value, str)
            assert t.value == t.name.lower()
