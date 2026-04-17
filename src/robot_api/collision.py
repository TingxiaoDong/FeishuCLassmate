"""
Collision detection utilities for robotics system.

Provides:
- Bounding box collision detection
- Sphere collision detection
- Capsule collision detection
- Collision checking for robot links
- Workspace boundary checking

Per architecture: This module is part of the Robot API layer,
providing collision detection utilities that don't modify IRobotAPI contract.
"""
from dataclasses import dataclass
from typing import Protocol
import math


# ============================================================
# Geometry Primitives
# ============================================================

@dataclass
class Vector3:
    """3D vector representation."""
    x: float
    y: float
    z: float

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Vector3":
        mag = self.magnitude()
        if mag < 1e-10:
            return Vector3(0, 0, 0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)

    def distance_to(self, other: "Vector3") -> float:
        return (self - other).magnitude()


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    center: Vector3
    size: Vector3  # half-extents (width/2, height/2, depth/2)

    def contains_point(self, point: Vector3) -> bool:
        """Check if point is inside the box."""
        dx = abs(point.x - self.center.x)
        dy = abs(point.y - self.center.y)
        dz = abs(point.z - self.center.z)
        return dx <= self.size.x and dy <= self.size.y and dz <= self.size.z

    def intersects_box(self, other: "BoundingBox") -> bool:
        """Check if this box intersects another."""
        dx = abs(self.center.x - other.center.x)
        dy = abs(self.center.y - other.center.y)
        dz = abs(self.center.z - other.center.z)

        combined_x = self.size.x + other.size.x
        combined_y = self.size.y + other.size.y
        combined_z = self.size.z + other.size.z

        return dx <= combined_x and dy <= combined_y and dz <= combined_z

    def intersects_sphere(self, sphere: "Sphere") -> bool:
        """Check if box intersects a sphere."""
        closest_x = max(self.center.x - self.size.x, min(sphere.center.x, self.center.x + self.size.x))
        closest_y = max(self.center.y - self.size.y, min(sphere.center.y, self.center.y + self.size.y))
        closest_z = max(self.center.z - self.size.z, min(sphere.center.z, self.center.z + self.size.z))

        closest = Vector3(closest_x, closest_y, closest_z)
        distance = closest.distance_to(sphere.center)

        return distance <= sphere.radius


@dataclass
class Sphere:
    """Sphere geometry for collision checking."""
    center: Vector3
    radius: float

    def intersects_sphere(self, other: "Sphere") -> bool:
        """Check if two spheres intersect."""
        distance = self.center.distance_to(other.center)
        return distance <= (self.radius + other.radius)

    def intersects_box(self, box: BoundingBox) -> bool:
        """Check if sphere intersects a box."""
        return box.intersects_sphere(self)

    def contains_point(self, point: Vector3) -> bool:
        """Check if point is inside sphere."""
        return self.center.distance_to(point) <= self.radius


@dataclass
class Capsule:
    """Capsule geometry (for robot links)."""
    start: Vector3
    end: Vector3
    radius: float

    def intersects_sphere(self, sphere: Sphere) -> bool:
        """Check if capsule intersects a sphere."""
        segment = self.end - self.start
        segment_length = segment.magnitude()

        if segment_length < 1e-10:
            return sphere.center.distance_to(self.start) <= (self.radius + sphere.radius)

        segment_normalized = segment.normalized()
        to_sphere = sphere.center - self.start
        projection = to_sphere.dot(segment_normalized)
        projection = max(0, min(segment_length, projection))

        closest = self.start + segment_normalized * projection
        return sphere.center.distance_to(closest) <= (self.radius + sphere.radius)

    def intersects_box(self, box: BoundingBox) -> bool:
        """Check if capsule intersects a box."""
        mid = Vector3(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
            (self.start.z + self.end.z) / 2,
        )
        segment_length = self.end.distance_to(self.start)
        effective_radius = self.radius + segment_length / 2

        sphere = Sphere(center=mid, radius=effective_radius)
        return sphere.intersects_box(box)


# ============================================================
# Collision Object Definitions
# ============================================================

@dataclass
class CollisionObject:
    """Base class for collidable objects."""
    name: str
    geometry: BoundingBox | Sphere | Capsule
    is_static: bool = True


@dataclass
class RobotLink:
    """Robot link for collision checking."""
    name: str
    start_position: Vector3
    end_position: Vector3
    radius: float = 0.05  # link thickness


# ============================================================
# Collision Detector
# ============================================================

class CollisionDetector:
    """
    Main collision detection system.

    Checks robot links against obstacles and self-collision.
    """

    def __init__(self):
        self._obstacles: list[CollisionObject] = []
        self._robot_links: list[RobotLink] = []
        self._workspace_bounds: BoundingBox | None = None

    def add_obstacle(self, obstacle: CollisionObject) -> None:
        """Add a static obstacle."""
        self._obstacles.append(obstacle)

    def remove_obstacle(self, name: str) -> bool:
        """Remove obstacle by name."""
        for i, obs in enumerate(self._obstacles):
            if obs.name == name:
                self._obstacles.pop(i)
                return True
        return False

    def clear_obstacles(self) -> None:
        """Remove all obstacles."""
        self._obstacles.clear()

    def set_robot_links(self, links: list[RobotLink]) -> None:
        """Set the current robot link configurations."""
        self._robot_links = links

    def set_workspace_bounds(self, bounds: BoundingBox) -> None:
        """Set workspace boundaries."""
        self._workspace_bounds = bounds

    def check_workspace_bounds(self, point: Vector3) -> tuple[bool, str]:
        """Check if point is within workspace bounds."""
        if self._workspace_bounds is None:
            return True, ""

        if not self._workspace_bounds.contains_point(point):
            return False, f"Point ({point.x:.4f}, {point.y:.4f}, {point.z:.4f}) outside workspace bounds"

        return True, ""

    def check_collision(self) -> tuple[bool, list[str]]:
        """Check for any collisions.

        Returns:
            Tuple of (collision_detected, list of collision descriptions)
        """
        collisions = []

        for link in self._robot_links:
            capsule = Capsule(
                start=link.start_position,
                end=link.end_position,
                radius=link.radius,
            )

            for obstacle in self._obstacles:
                if isinstance(obstacle.geometry, (BoundingBox, Sphere)):
                    if capsule.intersects_box(obstacle.geometry) or capsule.intersects_sphere(obstacle.geometry):
                        collisions.append(f"Link '{link.name}' collides with obstacle '{obstacle.name}'")

        for i, link1 in enumerate(self._robot_links):
            for link2 in self._robot_links[i + 1:]:
                if self._are_adjacent_links(link1, link2):
                    continue

                mid1 = Vector3(
                    (link1.start_position.x + link1.end_position.x) / 2,
                    (link1.start_position.y + link1.end_position.y) / 2,
                    (link1.start_position.z + link1.end_position.z) / 2,
                )
                mid2 = Vector3(
                    (link2.start_position.x + link2.end_position.x) / 2,
                    (link2.start_position.y + link2.end_position.y) / 2,
                    (link2.start_position.z + link2.end_position.z) / 2,
                )

                dist = mid1.distance_to(mid2)
                min_dist = link1.radius + link2.radius

                if dist <= min_dist:
                    collisions.append(f"Self-collision detected: link '{link1.name}' and link '{link2.name}'")

        return len(collisions) > 0, collisions

    def check_point_collision(self, point: Vector3) -> tuple[bool, list[str]]:
        """Check if a point collides with any obstacles."""
        collisions = []
        sphere = Sphere(center=point, radius=0.01)

        for obstacle in self._obstacles:
            if isinstance(obstacle.geometry, BoundingBox):
                if sphere.intersects_box(obstacle.geometry):
                    collisions.append(f"Point collides with obstacle '{obstacle.name}'")
            elif isinstance(obstacle.geometry, Sphere):
                if sphere.intersects_sphere(obstacle.geometry):
                    collisions.append(f"Point collides with obstacle '{obstacle.name}'")

        return len(collisions) > 0, collisions

    def check_path_collision(self, path: list[Vector3]) -> tuple[bool, list[str]]:
        """Check if a path collides with any obstacles."""
        collisions = []

        for i, point in enumerate(path):
            is_safe, msg = self.check_workspace_bounds(point)
            if not is_safe:
                collisions.append(f"Path point {i}: {msg}")

            is_colliding, collision_msgs = self.check_point_collision(point)
            collisions.extend(collision_msgs)

        return len(collisions) > 0, collisions

    def _are_adjacent_links(self, link1: RobotLink, link2: RobotLink) -> bool:
        """Check if two links are adjacent (share a joint)."""
        eps = 1e-6

        if link1.end_position.distance_to(link2.start_position) < eps:
            return True

        if link2.end_position.distance_to(link1.start_position) < eps:
            return True

        return False


# ============================================================
# Safety Checker
# ============================================================

class SafetyChecker:
    """
    High-level safety validation for robot operations.

    Provides safety checks before executing any robot command.
    """

    def __init__(self, collision_detector: CollisionDetector):
        self._collision_detector = collision_detector
        self._emergency_stop_active = False

    @property
    def emergency_stop_active(self) -> bool:
        """Check if emergency stop is triggered."""
        return self._emergency_stop_active

    def trigger_emergency_stop(self) -> None:
        """Trigger emergency stop."""
        self._emergency_stop_active = True

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop."""
        self._emergency_stop_active = False

    def pre_execution_check(
        self,
        target_positions: list[float],
        robot_links: list[RobotLink],
    ) -> tuple[bool, str]:
        """
        Run safety checks before executing a motion command.

        Returns:
            Tuple of (is_safe, error_message)
        """
        if self._emergency_stop_active:
            return False, "Emergency stop is active"

        self._collision_detector.set_robot_links(robot_links)

        has_collision, collisions = self._collision_detector.check_collision()
        if has_collision:
            return False, "; ".join(collisions)

        return True, ""

    def validate_workspace_target(
        self,
        x: float,
        y: float,
        z: float,
    ) -> tuple[bool, str]:
        """Validate that a target position is within workspace."""
        point = Vector3(x, y, z)
        return self._collision_detector.check_workspace_bounds(point)
