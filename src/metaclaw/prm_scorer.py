"""
RobotPRMScorer - Process Reward Model for Robotics

Maps robot execution to fine-grained process rewards for RL training.
Provides scores for:
- Path efficiency
- Gripper force compliance
- Collision avoidance
- Safety constraint satisfaction
"""

import math
from dataclasses import dataclass
from typing import Optional

from src.shared.world_state import WorldState, Pose
from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus, SafetyViolation


@dataclass
class ProcessRewardScore:
    """Fine-grained reward components for a skill execution."""
    # Component scores (0.0 to 1.0, higher is better)
    path_efficiency: float = 0.0
    gripper_force_compliance: float = 0.0
    collision_avoidance: float = 0.0
    safety_constraint_satisfaction: float = 0.0
    time_efficiency: float = 0.0

    # Overall weighted score
    overall: float = 0.0

    def to_dict(self) -> dict:
        return {
            "path_efficiency": self.path_efficiency,
            "gripper_force_compliance": self.gripper_force_compliance,
            "collision_avoidance": self.collision_avoidance,
            "safety_constraint_satisfaction": self.safety_constraint_satisfaction,
            "time_efficiency": self.time_efficiency,
            "overall": self.overall,
        }


class RobotPRMScorer:
    """
    Process Reward Model scorer for robot skill execution.

    Evaluates HOW a skill was executed, not just whether it succeeded.
    Used by MetaClaw for fine-grained RL training signals.
    """

    # Weights for combining component scores
    DEFAULT_WEIGHTS = {
        "path_efficiency": 0.20,
        "gripper_force_compliance": 0.15,
        "collision_avoidance": 0.25,
        "safety_constraint_satisfaction": 0.30,
        "time_efficiency": 0.10,
    }

    def __init__(
        self,
        weights: Optional[dict] = None,
        max_execution_time_ms: float = 5000.0,
        safe_force_range: tuple[float, float] = (0.0, 100.0),
    ):
        """
        Initialize the PRM scorer.

        Args:
            weights: Component weights for combining scores
            max_execution_time_ms: Maximum expected execution time for time efficiency
            safe_force_range: (min, max) acceptable gripper force in Newtons
        """
        self._weights = weights or self.DEFAULT_WEIGHTS
        self._max_execution_time_ms = max_execution_time_ms
        self._safe_force_range = safe_force_range

    def score(
        self,
        outcome: ExecutionOutcome,
        world_before: WorldState,
        world_after: WorldState,
    ) -> ProcessRewardScore:
        """
        Compute process reward scores for a skill execution.

        Args:
            outcome: Execution outcome from SkillExecutor
            world_before: World state before execution
            world_after: World state after execution

        Returns:
            ProcessRewardScore with fine-grained components
        """
        score = ProcessRewardScore()

        # Skip scoring if execution failed due to preconditions
        if outcome.status == ExecutionStatus.PRECONDITION_FAILED:
            score.safety_constraint_satisfaction = 1.0  # Didn't violate safety
            score.overall = self._compute_weighted_score(score)
            return score

        # Path efficiency
        score.path_efficiency = self._compute_path_efficiency(
            outcome, world_before, world_after
        )

        # Gripper force compliance
        score.gripper_force_compliance = self._compute_gripper_compliance(
            outcome, world_after
        )

        # Collision avoidance
        score.collision_avoidance = self._compute_collision_score(
            world_before, world_after
        )

        # Safety constraint satisfaction
        score.safety_constraint_satisfaction = self._compute_safety_score(outcome)

        # Time efficiency
        score.time_efficiency = self._compute_time_efficiency(outcome)

        # Compute overall weighted score
        score.overall = self._compute_weighted_score(score)

        return score

    def _compute_path_efficiency(
        self,
        outcome: ExecutionOutcome,
        world_before: WorldState,
        world_after: WorldState,
    ) -> float:
        """
        Compute path efficiency score.

        Ideal path is direct. Penalize:
        - Indirect paths (longer than minimum)
        - Unnecessary joint movements
        - Oscillation or retries
        """
        # Get positions
        before_pose = world_before.robot.end_effector_pose
        after_pose = world_after.robot.end_effector_pose

        if before_pose is None or after_pose is None:
            return 0.5  # Unknown state, neutral score

        # Calculate direct distance
        direct_distance = self._distance_3d(before_pose, after_pose)

        # If execution was successful without path violations, give full score
        if outcome.status == ExecutionStatus.SUCCESS and not outcome.safety_violations:
            # Check if execution was straightforward (direct path)
            if direct_distance < 0.01:  # Very small movement
                return 0.9
            # Full score for successful direct movement
            return 1.0

        # Penalize for failed execution
        if outcome.status == ExecutionStatus.FAILURE:
            return 0.3

        # Penalize for safety violations
        if outcome.safety_violations:
            return 0.2

        return 0.5  # Default neutral

    def _compute_gripper_compliance(
        self,
        outcome: ExecutionOutcome,
        world_after: WorldState,
    ) -> float:
        """
        Compute gripper force compliance score.

        Checks if gripper force was within safe operating range.
        """
        gripper_force = world_after.robot.gripper_force
        min_force, max_force = self._safe_force_range

        # Check if gripper force is within safe range
        if gripper_force < min_force or gripper_force > max_force:
            # Check if this was intentional (grasping)
            if outcome.skill_name == "grasp" and outcome.status == ExecutionStatus.SUCCESS:
                # For grasp, force should be > 0 when holding
                if gripper_force > 0 and gripper_force <= max_force:
                    return 0.9
            return 0.4  # Out of safe range

        # Force is within safe range
        if gripper_force == 0:
            return 1.0  # Relaxed (not grasping)

        # Force is positive and within range - good for grasping
        normalized = gripper_force / max_force
        if 0.3 <= normalized <= 0.8:
            return 1.0  # Optimal force range
        elif normalized < 0.3:
            return 0.7  # Low but safe
        else:
            return 0.8  # High but within limits

    def _compute_collision_score(
        self,
        world_before: WorldState,
        world_after: WorldState,
    ) -> float:
        """
        Compute collision avoidance score.

        Penalize paths that pass too close to obstacles.
        Reward clean separations.
        """
        obstacles = world_after.environment.obstacles

        if not obstacles:
            return 1.0  # No obstacles, no collision risk

        # Simplified: Check if end-effector is too close to any obstacle
        ee_pose = world_after.robot.end_effector_pose
        if ee_pose is None:
            return 0.5

        min_safe_distance = 0.05  # 5cm minimum

        for obstacle in obstacles:
            dist = self._distance_3d(ee_pose, obstacle.pose)
            # Get obstacle size for clearance check
            size = obstacle.size
            obstacle_radius = (size.x + size.y + size.z) / 6  # Approximate

            if dist < (min_safe_distance + obstacle_radius):
                return 0.2  # Too close

        return 1.0  # Clear of all obstacles

    def _compute_safety_score(self, outcome: ExecutionOutcome) -> float:
        """
        Compute safety constraint satisfaction score.

        Based on safety violations during execution.
        """
        if not outcome.safety_violations:
            return 1.0  # No violations

        # Compute weighted violation severity
        total_severity = sum(v.severity for v in outcome.safety_violations)
        recovered_count = sum(1 for v in outcome.safety_violations if v.recovered)

        # Average severity (0 to 1)
        avg_severity = total_severity / len(outcome.safety_violations)

        # If all recovered, reduce penalty
        if recovered_count == len(outcome.safety_violations):
            return 1.0 - (avg_severity * 0.5)  # Reduced penalty for recovery

        return 1.0 - avg_severity

    def _compute_time_efficiency(self, outcome: ExecutionOutcome) -> float:
        """
        Compute time efficiency score.

        Based on execution time vs expected maximum.
        """
        exec_time = outcome.execution_time_ms

        if exec_time <= 0:
            return 0.5  # Unknown time

        # Ratio of actual to max time
        ratio = exec_time / self._max_execution_time_ms

        if ratio <= 0.5:
            return 1.0  # Very fast
        elif ratio <= 0.8:
            return 0.9  # Good
        elif ratio <= 1.0:
            return 0.7  # Acceptable
        elif ratio <= 1.5:
            return 0.5  # Slow
        else:
            return 0.2  # Way too slow

    def _compute_weighted_score(self, score: ProcessRewardScore) -> float:
        """Compute weighted overall score from components."""
        return (
            score.path_efficiency * self._weights["path_efficiency"]
            + score.gripper_force_compliance * self._weights["gripper_force_compliance"]
            + score.collision_avoidance * self._weights["collision_avoidance"]
            + score.safety_constraint_satisfaction * self._weights["safety_constraint_satisfaction"]
            + score.time_efficiency * self._weights["time_efficiency"]
        )

    @staticmethod
    def _distance_3d(pose1: Pose, pose2: Pose) -> float:
        """Calculate 3D Euclidean distance between two poses."""
        dx = pose1.x - pose2.x
        dy = pose1.y - pose2.y
        dz = pose1.z - pose2.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def get_weights(self) -> dict:
        """Get current component weights."""
        return self._weights.copy()

    def set_weights(self, weights: dict) -> None:
        """Update component weights."""
        # Validate weights sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        self._weights = weights


class CompositePRMScorer:
    """
    Combines multiple PRM scorers for different skill types.

    Uses specialized scorers for different skill categories:
    - Motion skills: path efficiency weighted higher
    - Manipulation skills: gripper force weighted higher
    - Safety-critical: safety constraint weighted higher
    """

    def __init__(self):
        self._scorers = {
            "motion": RobotPRMScorer(weights={
                "path_efficiency": 0.35,
                "gripper_force_compliance": 0.05,
                "collision_avoidance": 0.30,
                "safety_constraint_satisfaction": 0.20,
                "time_efficiency": 0.10,
            }),
            "manipulation": RobotPRMScorer(weights={
                "path_efficiency": 0.10,
                "gripper_force_compliance": 0.30,
                "collision_avoidance": 0.20,
                "safety_constraint_satisfaction": 0.30,
                "time_efficiency": 0.10,
            }),
            "sensing": RobotPRMScorer(weights={
                "path_efficiency": 0.15,
                "gripper_force_compliance": 0.10,
                "collision_avoidance": 0.15,
                "safety_constraint_satisfaction": 0.40,
                "time_efficiency": 0.20,
            }),
            "default": RobotPRMScorer(),
        }

    def score_for_skill(
        self,
        skill_name: str,
        skill_type: str,
        outcome: ExecutionOutcome,
        world_before: WorldState,
        world_after: WorldState,
    ) -> ProcessRewardScore:
        """
        Score execution using the appropriate specialized scorer.

        Args:
            skill_name: Name of the skill
            skill_type: Type from SkillType enum
            outcome: Execution outcome
            world_before: World state before
            world_after: World state after

        Returns:
            ProcessRewardScore
        """
        scorer = self._scorers.get(skill_type, self._scorers["default"])
        return scorer.score(outcome, world_before, world_after)

    def get_scorer(self, skill_type: str) -> RobotPRMScorer:
        """Get the scorer for a specific skill type."""
        return self._scorers.get(skill_type, self._scorers["default"])
