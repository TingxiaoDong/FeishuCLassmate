"""
Safety constraint validation tests.

Tests that the system properly validates safety constraints for skills
and that dangerous operations are prevented.

Authoritative source: src/skill/skill_schemas.py
"""
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.skill.skill_schemas import (
    SKILL_REGISTRY,
    GRASP_SCHEMA,
    MOVE_TO_SCHEMA,
    PLACE_SCHEMA,
    RELEASE_SCHEMA,
    STOP_SCHEMA,
    SkillSchema,
)


class TestSafetyConstraintValidation:
    """Tests for safety constraint presence and format."""

    def test_all_skills_have_safety_constraints(self):
        """Every skill must have at least one safety constraint."""
        for name, schema in SKILL_REGISTRY.items():
            assert len(schema.safety_constraints) > 0, f"{name} has no safety_constraints"

    def test_all_skills_have_preconditions(self):
        """Every skill must have at least one precondition."""
        for name, schema in SKILL_REGISTRY.items():
            assert len(schema.preconditions) > 0, f"{name} has no preconditions"

    def test_all_skills_have_effects(self):
        """Every skill must have at least one effect."""
        for name, schema in SKILL_REGISTRY.items():
            assert len(schema.effects) > 0, f"{name} has no effects"

    def test_safety_constraints_are_non_empty_strings(self):
        """All safety constraints must be non-empty strings."""
        for name, schema in SKILL_REGISTRY.items():
            for constraint in schema.safety_constraints:
                assert isinstance(constraint, str), f"{name} has non-string constraint"
                assert len(constraint) > 0, f"{name} has empty constraint"

    def test_preconditions_reference_robot_state(self):
        """Preconditions should reference robot state properties."""
        motion_skills = ["move_to", "rotate", "stop"]
        for name in motion_skills:
            schema = SKILL_REGISTRY.get(name)
            if schema:
                # Should reference robot state
                all_preconditions = " ".join(schema.preconditions)
                assert "robot." in all_preconditions or "state" in all_preconditions.lower()


class TestGraspSafetyConstraints:
    """Safety constraint tests for grasp skill."""

    def test_grasp_has_grip_force_limit(self):
        """grasp should specify grip force must be within safe limits."""
        constraints = " ".join(GRASP_SCHEMA.safety_constraints)
        assert "force" in constraints.lower()
        assert "safe" in constraints.lower() or "limit" in constraints.lower()

    def test_grasp_has_approach_height_constraint(self):
        """grasp should require positive approach_height."""
        constraints = " ".join(GRASP_SCHEMA.safety_constraints)
        assert "approach_height" in constraints
        assert "positive" in constraints.lower()

    def test_grasp_checks_obstacle_collision(self):
        """grasp should ensure object is not in Obstacle list."""
        preconditions = " ".join(GRASP_SCHEMA.preconditions)
        assert "obstacle" in preconditions.lower()


class TestMoveToSafetyConstraints:
    """Safety constraint tests for move_to skill."""

    def test_move_to_has_speed_limit(self):
        """move_to should specify speed must be within safe limits."""
        constraints = " ".join(MOVE_TO_SCHEMA.safety_constraints)
        assert "speed" in constraints.lower()

    def test_move_to_checks_workspace_bounds(self):
        """move_to should ensure target is within workspace bounds."""
        constraints = " ".join(MOVE_TO_SCHEMA.safety_constraints)
        assert "workspace" in constraints.lower() or "bounds" in constraints.lower()

    def test_move_to_checks_collision_free_path(self):
        """move_to should check for collision-free path."""
        preconditions = " ".join(MOVE_TO_SCHEMA.preconditions)
        assert "collision" in preconditions.lower()

    def test_move_to_checks_self_collision(self):
        """move_to should check for self-collision possibility."""
        constraints = " ".join(MOVE_TO_SCHEMA.safety_constraints)
        assert "self-collision" in constraints.lower() or "self collision" in constraints.lower()


class TestPlaceSafetyConstraints:
    """Safety constraint tests for place skill."""

    def test_place_has_approach_height_constraint(self):
        """place should require positive approach_height."""
        constraints = " ".join(PLACE_SCHEMA.safety_constraints)
        assert "approach_height" in constraints
        assert "positive" in constraints.lower()

    def test_place_checks_valid_surface(self):
        """place should ensure target is on valid surface."""
        constraints = " ".join(PLACE_SCHEMA.safety_constraints)
        assert "surface" in constraints.lower()

    def test_place_checks_drop_speed(self):
        """place should prevent dropping object too fast."""
        constraints = " ".join(PLACE_SCHEMA.safety_constraints)
        assert "drop" in constraints.lower() or "fast" in constraints.lower()


class TestStopSafetyConstraints:
    """Safety constraint tests for stop skill."""

    def test_stop_emergency_always_available(self):
        """stop skill must have emergency stop always available."""
        constraints = " ".join(STOP_SCHEMA.safety_constraints)
        assert "emergency stop" in constraints.lower()
        assert "always" in constraints.lower() or "available" in constraints.lower()

    def test_stop_has_max_completion_time(self):
        """stop should complete within 100ms as specified in architecture."""
        constraints = " ".join(STOP_SCHEMA.safety_constraints)
        assert "100ms" in constraints or "100 msec" in constraints.lower()


class TestWorkspaceBoundsValidation:
    """Tests for workspace bounds safety."""

    def test_move_to_checks_workspace_bounds_in_precondition(self):
        """move_to preconditions should include workspace bounds check."""
        precondition_text = " ".join(MOVE_TO_SCHEMA.preconditions)
        assert "workspace bounds" in precondition_text.lower() or "bounds" in precondition_text.lower()

    def test_grasp_checks_workspace_bounds(self):
        """grasp should check workspace bounds in preconditions."""
        precondition_text = " ".join(GRASP_SCHEMA.preconditions)
        assert "workspace" in precondition_text.lower() or "bounds" in precondition_text.lower()


class TestSafetyConstraintCompleteness:
    """Tests for overall safety constraint coverage."""

    def test_motion_skills_check_speed_limits(self):
        """All MOTION type skills should have speed-related safety constraints."""
        from src.skill.skill_schemas import SkillType

        for name, schema in SKILL_REGISTRY.items():
            if schema.skill_type == SkillType.MOTION:
                constraints = " ".join(schema.safety_constraints)
                assert "speed" in constraints.lower(), f"{name} motion skill missing speed constraint"

    def test_manipulation_skills_check_gripper_state(self):
        """MANIPULATION type skills should have gripper-related constraints."""
        from src.skill.skill_schemas import SkillType

        for name, schema in SKILL_REGISTRY.items():
            if schema.skill_type == SkillType.MANIPULATION:
                all_text = " ".join(schema.preconditions + schema.safety_constraints)
                assert "gripper" in all_text.lower(), f"{name} manipulation skill missing gripper constraint"

    def test_all_skills_reference_world_state(self):
        """All skills should reference world state (robot, objects, environment)."""
        for name, schema in SKILL_REGISTRY.items():
            all_text = " ".join(
                schema.preconditions +
                schema.effects +
                schema.safety_constraints
            )
            # Should reference some aspect of world state
            has_world_ref = (
                "robot" in all_text.lower() or
                "object" in all_text.lower() or
                "environment" in all_text.lower() or
                "workspace" in all_text.lower()
            )
            assert has_world_ref, f"{name} does not reference world state"
