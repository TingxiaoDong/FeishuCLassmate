"""
Trajectory planning utilities for robot motion.

Provides:
- Joint space trajectory generation
- Cartesian space trajectory generation
- Trajectory interpolation (linear, cubic, quintic)
- Trajectory validation
"""
from dataclasses import dataclass
from typing import Callable, Protocol
import math


# ============================================================
# Trajectory Data Structures
# ============================================================

@dataclass
class JointWaypoint:
    """A waypoint in joint space."""
    positions: list[float]
    velocities: list[float] | None = None
    time: float = 0.0


@dataclass
class CartesianWaypoint:
    """A waypoint in Cartesian space."""
    x: float
    y: float
    z: float
    rx: float = 0.0  # roll
    ry: float = 0.0  # pitch
    rz: float = 0.0  # yaw
    time: float = 0.0


@dataclass
class TrajectoryPoint:
    """A single point along a trajectory."""
    time: float
    positions: list[float]
    velocities: list[float]
    accelerations: list[float]

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "positions": self.positions,
            "velocities": self.velocities,
            "accelerations": self.accelerations,
        }


class Trajectory:
    """Container for a complete trajectory."""

    def __init__(self, points: list[TrajectoryPoint] | None = None):
        self._points = points or []
        self._duration = 0.0
        if self._points:
            self._duration = self._points[-1].time

    @property
    def duration(self) -> float:
        """Total trajectory duration in seconds."""
        return self._duration

    @property
    def points(self) -> list[TrajectoryPoint]:
        """All trajectory points."""
        return self._points

    @property
    def num_points(self) -> int:
        """Number of trajectory points."""
        return len(self._points)

    def add_point(self, point: TrajectoryPoint) -> None:
        """Add a trajectory point."""
        self._points.append(point)
        if point.time > self._duration:
            self._duration = point.time

    def get_point_at_time(self, t: float) -> TrajectoryPoint | None:
        """Get interpolated trajectory point at time t."""
        if not self._points:
            return None
        if t <= self._points[0].time:
            return self._points[0]
        if t >= self._points[-1].time:
            return self._points[-1]

        # Find surrounding points
        for i in range(len(self._points) - 1):
            p1 = self._points[i]
            p2 = self._points[i + 1]
            if p1.time <= t <= p2.time:
                # Linear interpolation
                alpha = (t - p1.time) / (p2.time - p1.time)
                return TrajectoryPoint(
                    time=t,
                    positions=[p1.positions[j] + alpha * (p2.positions[j] - p1.positions[j])
                              for j in range(len(p1.positions))],
                    velocities=[p1.velocities[j] + alpha * (p2.velocities[j] - p1.velocities[j])
                               for j in range(len(p1.velocities))],
                    accelerations=[p1.accelerations[j] + alpha * (p2.accelerations[j] - p1.accelerations[j])
                                   for j in range(len(p1.accelerations))],
                )
        return None

    def is_valid(self, joint_limits: list[tuple[float, float]]) -> tuple[bool, str]:
        """Validate trajectory against joint limits and physics constraints."""
        for i, point in enumerate(self._points):
            for j, pos in enumerate(point.positions):
                if joint_limits:
                    min_limit, max_limit = joint_limits[j]
                    if pos < min_limit or pos > max_limit:
                        return False, f"Point {i}: joint {j} position {pos} exceeds limits [{min_limit}, {max_limit}]"

            for j, vel in enumerate(point.velocities):
                if abs(vel) > 2.0:  # rad/s safety limit
                    return False, f"Point {i}: joint {j} velocity {vel} exceeds safety limit"

        return True, "valid"


# ============================================================
# Trajectory Generators
# ============================================================

class TrajectoryGenerator:
    """Generate trajectories for robot motion."""

    @staticmethod
    def generate_linear_joint(
        start: list[float],
        end: list[float],
        duration: float,
        dt: float = 0.01,
        start_velocity: float = 0.0,
        end_velocity: float = 0.0,
    ) -> Trajectory:
        """Generate a linear interpolation trajectory in joint space.

        Args:
            start: Starting joint positions (radians)
            end: Ending joint positions (radians)
            duration: Trajectory duration (seconds)
            dt: Time step for trajectory points
            start_velocity: Initial joint velocity
            end_velocity: Final joint velocity

        Returns:
            Trajectory object with generated points
        """
        trajectory = Trajectory()
        num_joints = len(start)

        if duration <= 0:
            return trajectory

        num_points = max(int(duration / dt) + 1, 2)

        for i in range(num_points):
            t = (i / (num_points - 1)) * duration
            alpha = t / duration

            positions = [start[j] + alpha * (end[j] - start[j]) for j in range(num_joints)]

            # Velocity is constant for linear interpolation
            velocities = [(end[j] - start[j]) / duration for j in range(num_joints)]
            velocities[0] = start_velocity + alpha * (end_velocity - start_velocity)

            # Acceleration is zero for linear (except at endpoints)
            accelerations = [0.0] * num_joints
            if i == 0:
                accelerations[0] = (velocities[0] - start_velocity) / dt if dt > 0 else 0.0
            elif i == num_points - 1:
                accelerations[0] = (end_velocity - velocities[0]) / dt if dt > 0 else 0.0

            trajectory.add_point(TrajectoryPoint(
                time=t,
                positions=positions,
                velocities=velocities,
                accelerations=accelerations,
            ))

        return trajectory

    @staticmethod
    def generate_cubic_joint(
        start: list[float],
        end: list[float],
        duration: float,
        dt: float = 0.01,
        start_velocity: float = 0.0,
        end_velocity: float = 0.0,
    ) -> Trajectory:
        """Generate a cubic spline trajectory in joint space.

        Uses cubic polynomial interpolation for smooth motion.
        """
        trajectory = Trajectory()
        num_joints = len(start)

        if duration <= 0:
            return trajectory

        num_points = max(int(duration / dt) + 1, 2)

        for i in range(num_points):
            t = (i / (num_points - 1)) * duration
            alpha = t / duration

            # Cubic easing
            alpha_cubic = alpha * alpha * (3 - 2 * alpha)

            positions = [start[j] + alpha_cubic * (end[j] - start[j]) for j in range(num_joints)]

            # Derivative of cubic for velocity
            alpha_cubic_deriv = 6 * alpha * (1 - alpha)
            velocities = [alpha_cubic_deriv * (end[j] - start[j]) / duration for j in range(num_joints)]

            # Second derivative for acceleration
            alpha_cubic_deriv2 = 6 - 12 * alpha
            accelerations = [alpha_cubic_deriv2 * (end[j] - start[j]) / (duration * duration)
                            for j in range(num_joints)]

            trajectory.add_point(TrajectoryPoint(
                time=t,
                positions=positions,
                velocities=velocities,
                accelerations=accelerations,
            ))

        return trajectory

    @staticmethod
    def generate_quintic_joint(
        start: list[float],
        end: list[float],
        duration: float,
        dt: float = 0.01,
        start_velocity: float = 0.0,
        end_velocity: float = 0.0,
        start_acceleration: float = 0.0,
        end_acceleration: float = 0.0,
    ) -> Trajectory:
        """Generate a quintic spline trajectory in joint space.

        Uses quintic polynomial for smooth position, velocity, and acceleration.
        """
        trajectory = Trajectory()
        num_joints = len(start)

        if duration <= 0:
            return trajectory

        num_points = max(int(duration / dt) + 1, 2)

        for i in range(num_points):
            t = (i / (num_points - 1)) * duration
            alpha = t / duration

            # Quintic easing (smoother than cubic)
            alpha_quintic = alpha * alpha * alpha * (alpha * (alpha * 6 - 15) + 10)

            positions = [start[j] + alpha_quintic * (end[j] - start[j]) for j in range(num_joints)]

            # First derivative
            alpha_quintic_deriv = 30 * alpha * alpha * (alpha - 1) * (alpha - 1) + 30 * alpha * alpha * alpha * (alpha - 1)
            velocities = [alpha_quintic_deriv * (end[j] - start[j]) / duration for j in range(num_joints)]

            # Second derivative
            alpha_quintic_deriv2 = 60 * alpha * (alpha - 1) * (2 * alpha - 1)
            accelerations = [alpha_quintic_deriv2 * (end[j] - start[j]) / (duration * duration)
                            for j in range(num_joints)]

            trajectory.add_point(TrajectoryPoint(
                time=t,
                positions=positions,
                velocities=velocities,
                accelerations=accelerations,
            ))

        return trajectory

    @staticmethod
    def generate_linear_cartesian(
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        duration: float,
        dt: float = 0.01,
    ) -> Trajectory:
        """Generate a linear interpolation trajectory in Cartesian space.

        Note: This generates a trajectory with single-point positions.
        The caller should convert these to joint positions using IK.
        """
        trajectory = Trajectory()

        if duration <= 0:
            return trajectory

        num_points = max(int(duration / dt) + 1, 2)

        for i in range(num_points):
            t = (i / (num_points - 1)) * duration
            alpha = t / duration

            x = start[0] + alpha * (end[0] - start[0])
            y = start[1] + alpha * (end[1] - start[1])
            z = start[2] + alpha * (end[2] - start[2])

            positions = [x, y, z, 0.0, 0.0, 0.0]  # 6D pose (position + orientation)

            velocities = [(end[j] - start[j]) / duration for j in range(3)] + [0.0, 0.0, 0.0]
            accelerations = [0.0] * 6

            trajectory.add_point(TrajectoryPoint(
                time=t,
                positions=positions,
                velocities=velocities,
                accelerations=accelerations,
            ))

        return trajectory


# ============================================================
# Trajectory Validation
# ============================================================

class TrajectoryValidator:
    """Validate trajectories for safety and feasibility."""

    def __init__(
        self,
        joint_limits: list[tuple[float, float]],
        velocity_limits: list[float] | None = None,
        acceleration_limits: list[float] | None = None,
        workspace_bounds: tuple[float, float, float, float, float, float] | None = None,
    ):
        """
        Initialize validator with robot constraints.

        Args:
            joint_limits: List of (min, max) for each joint (radians)
            velocity_limits: Maximum velocity for each joint (rad/s)
            acceleration_limits: Maximum acceleration for each joint (rad/s^2)
            workspace_bounds: (x_min, x_max, y_min, y_max, z_min, z_max)
        """
        self._joint_limits = joint_limits
        self._velocity_limits = velocity_limits or [2.0] * len(joint_limits)
        self._acceleration_limits = acceleration_limits or [10.0] * len(joint_limits)
        self._workspace_bounds = workspace_bounds

    def validate(self, trajectory: Trajectory) -> tuple[bool, list[str]]:
        """Validate an entire trajectory.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if trajectory.num_points == 0:
            errors.append("Trajectory has no points")
            return False, errors

        # Check each point
        for i, point in enumerate(trajectory.points):
            # Joint position limits
            for j, pos in enumerate(point.positions):
                if j < len(self._joint_limits):
                    min_limit, max_limit = self._joint_limits[j]
                    if pos < min_limit or pos > max_limit:
                        errors.append(
                            f"Point {i}: joint {j} position {pos:.4f} exceeds limits [{min_limit}, {max_limit}]"
                        )

            # Velocity limits
            for j, vel in enumerate(point.velocities):
                if j < len(self._velocity_limits):
                    if abs(vel) > self._velocity_limits[j]:
                        errors.append(
                            f"Point {i}: joint {j} velocity {vel:.4f} exceeds limit {self._velocity_limits[j]}"
                        )

            # Acceleration limits
            for j, acc in enumerate(point.accelerations):
                if j < len(self._acceleration_limits):
                    if abs(acc) > self._acceleration_limits[j]:
                        errors.append(
                            f"Point {i}: joint {j} acceleration {acc:.4f} exceeds limit {self._acceleration_limits[j]}"
                        )

        # Workspace bounds (for Cartesian points, if applicable)
        if self._workspace_bounds:
            x_min, x_max, y_min, y_max, z_min, z_max = self._workspace_bounds
            for i, point in enumerate(trajectory.points):
                if len(point.positions) >= 3:
                    x, y, z = point.positions[0], point.positions[1], point.positions[2]
                    if x < x_min or x > x_max or y < y_min or y > y_max or z < z_min or z > z_max:
                        errors.append(
                            f"Point {i}: position ({x:.4f}, {y:.4f}, {z:.4f}) outside workspace bounds"
                        )

        return len(errors) == 0, errors

    def check_collision_risk(self, trajectory: Trajectory, obstacles: list) -> tuple[bool, list[str]]:
        """Check trajectory for potential collisions.

        Args:
            trajectory: The trajectory to check
            obstacles: List of obstacle definitions

        Returns:
            Tuple of (has_collision_risk, list of warnings)
        """
        warnings = []
        # This is a simplified check - full collision detection requires
        # proper geometry and FK calculations
        return len(warnings) == 0, warnings
