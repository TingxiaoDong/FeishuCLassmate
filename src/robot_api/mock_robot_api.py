"""Mock Robot Control API with state simulation."""

import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MockRobotState:
    """Internal state of the mock robot."""
    position: dict = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    gripper_open: bool = True
    gripper_width: float = 0.1  # meters
    holding: Optional[str] = None  # object_id if holding
    joints: list = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])


@dataclass
class MockWorldState:
    """Mock world state with objects."""
    objects: dict = field(default_factory=dict)  # object_id -> {position, state}

    def __post_init__(self):
        # Initialize some default objects
        self.objects = {
            "red_box": {"position": {"x": 0.5, "y": 0.0, "z": 0.05}, "state": "visible"},
            "blue_box": {"position": {"x": 0.6, "y": 0.1, "z": 0.05}, "state": "visible"},
            "green_box": {"position": {"x": 0.4, "y": -0.1, "z": 0.05}, "state": "visible"},
        }


@dataclass
class RobotResult:
    """Result of a robot operation."""
    success: bool
    message: str
    state: MockRobotState
    world: MockWorldState


class MockRobotControlAPI:
    """
    Mock Robot Control API for testing.

    Simulates:
    - move_to(location) - move to target position
    - pick(object) - pick up an object
    - place(location) - place object at location

    Maintains internal state and returns success/failure with updated state.
    """

    # Workspace boundaries
    WORKSPACE_BOUNDS = {
        "x": (-1.0, 1.0),
        "y": (-1.0, 1.0),
        "z": (0.0, 0.5),
    }

    def __init__(self, failure_rate: float = 0.05):
        """
        Initialize Mock Robot Control API.

        Args:
            failure_rate: Probability of simulated failure (0.0 to 1.0)
        """
        self._state = MockRobotState()
        self._world = MockWorldState()
        self._failure_rate = failure_rate

    @property
    def state(self) -> MockRobotState:
        """Current robot state."""
        return self._state

    @property
    def world(self) -> MockWorldState:
        """Current world state."""
        return self._world

    def _check_workspace(self, position: dict) -> bool:
        """Check if position is within workspace bounds."""
        for axis in ["x", "y", "z"]:
            if axis in position:
                lo, hi = self.WORKSPACE_BOUNDS[axis]
                if not (lo <= position[axis] <= hi):
                    return False
        return True

    def _simulate_failure(self) -> bool:
        """Determine if this operation should fail."""
        return random.random() < self._failure_rate

    async def move_to(self, location: dict, speed: float = 0.5) -> RobotResult:
        """
        Move robot end-effector to target location.

        Args:
            location: Target position dict with x, y, z keys
            speed: Movement speed (0.0 to 1.0)

        Returns:
            RobotResult with success/failure and updated state
        """
        await asyncio.sleep(0.05)  # Simulate movement time

        # Validate workspace bounds
        if not self._check_workspace(location):
            return RobotResult(
                success=False,
                message=f"Target outside workspace bounds: {location}",
                state=self._state,
                world=self._world,
            )

        # Simulate random failure
        if self._simulate_failure():
            return RobotResult(
                success=False,
                message="Simulated move_to failure (hardware glitch)",
                state=self._state,
                world=self._world,
            )

        # Update position
        self._state.position = location.copy()

        return RobotResult(
            success=True,
            message=f"Moved to ({location['x']}, {location['y']}, {location['z']})",
            state=self._state,
            world=self._world,
        )

    async def pick(self, object_id: str) -> RobotResult:
        """
        Pick up an object.

        Args:
            object_id: ID of object to pick

        Returns:
            RobotResult with success/failure and updated state
        """
        await asyncio.sleep(0.03)  # Simulate pick action

        # Check if already holding something
        if self._state.holding is not None:
            return RobotResult(
                success=False,
                message=f"Already holding {self._state.holding}",
                state=self._state,
                world=self._world,
            )

        # Check if object exists
        if object_id not in self._world.objects:
            return RobotResult(
                success=False,
                message=f"Object '{object_id}' not found in world",
                state=self._state,
                world=self._world,
            )

        # Check object state
        obj = self._world.objects[object_id]
        if obj["state"] != "visible":
            return RobotResult(
                success=False,
                message=f"Object '{object_id}' is not pickable (state: {obj['state']})",
                state=self._state,
                world=self._world,
            )

        # Simulate random failure
        if self._simulate_failure():
            return RobotResult(
                success=False,
                message=f"Simulated pick failure for {object_id}",
                state=self._state,
                world=self._world,
            )

        # Update gripper state
        self._state.gripper_open = False
        self._state.gripper_width = 0.0
        self._state.holding = object_id

        # Update object state
        obj["state"] = "grasped"

        return RobotResult(
            success=True,
            message=f"Picked up {object_id}",
            state=self._state,
            world=self._world,
        )

    async def place(self, location: dict) -> RobotResult:
        """
        Place held object at target location.

        Args:
            location: Target position dict with x, y, z keys

        Returns:
            RobotResult with success/failure and updated state
        """
        await asyncio.sleep(0.03)  # Simulate place action

        # Check if holding something
        if self._state.holding is None:
            return RobotResult(
                success=False,
                message="Not holding any object",
                state=self._state,
                world=self._world,
            )

        # Validate workspace bounds
        if not self._check_workspace(location):
            return RobotResult(
                success=False,
                message=f"Target outside workspace bounds: {location}",
                state=self._state,
                world=self._world,
            )

        # Simulate random failure
        if self._simulate_failure():
            return RobotResult(
                success=False,
                message="Simulated place failure (hardware glitch)",
                state=self._state,
                world=self._world,
            )

        # Get held object
        object_id = self._state.holding
        obj = self._world.objects[object_id]

        # Update object position and state
        obj["position"] = location.copy()
        obj["state"] = "visible"

        # Update gripper state
        self._state.gripper_open = True
        self._state.gripper_width = 0.1
        self._state.holding = None

        return RobotResult(
            success=True,
            message=f"Placed {object_id} at ({location['x']}, {location['y']}, {location['z']})",
            state=self._state,
            world=self._world,
        )

    async def execute_skill(self, skill_name: str, params: dict) -> RobotResult:
        """
        Execute a named skill with parameters.

        Args:
            skill_name: Name of skill ("move_to", "pick", "place")
            params: Skill parameters

        Returns:
            RobotResult with success/failure and updated state
        """
        if skill_name == "move_to":
            return await self.move_to(params.get("target", {"x": 0, "y": 0, "z": 0}), params.get("speed", 0.5))
        elif skill_name in ("pick", "grasp", "approach_and_grasp"):
            return await self.pick(params.get("object_id", "unknown_object"))
        elif skill_name in ("place", "release", "pick_and_place"):
            return await self.place(params.get("target", {"x": 0, "y": 0, "z": 0}))
        elif skill_name == "speak":
            return RobotResult(
                success=True,
                message=f"Mock: spoke '{params.get('message', '')}'",
                state=self._state,
                world=self._world,
            )
        elif skill_name == "stop":
            return RobotResult(
                success=True,
                message="Mock: stopped",
                state=self._state,
                world=self._world,
            )
        elif skill_name == "rotate":
            return RobotResult(
                success=True,
                message=f"Mock: rotated {params.get('angle', 0)} degrees on {params.get('axis', 'z')}",
                state=self._state,
                world=self._world,
            )
        else:
            return RobotResult(
                success=False,
                message=f"Unknown skill: {skill_name}",
                state=self._state,
                world=self._world,
            )

    def get_state(self) -> dict:
        """Get current robot state as dict."""
        return {
            "position": self._state.position.copy(),
            "gripper_open": self._state.gripper_open,
            "gripper_width": self._state.gripper_width,
            "holding": self._state.holding,
        }

    def get_world_objects(self) -> dict:
        """Get all world objects."""
        return {k: v.copy() for k, v in self._world.objects.items()}


# Backward compatibility alias
MockRobotAPI = MockRobotControlAPI


# Convenience functions for quick testing
async def demo():
    """Demo the mock robot API."""
    robot = MockRobotControlAPI(failure_rate=0.0)  # No failures for demo

    print("=== Mock Robot Control API Demo ===\n")

    # Initial state
    print(f"Initial state: {robot.get_state()}")
    print(f"Objects: {robot.get_world_objects()}\n")

    # Move to object
    result = await robot.move_to({"x": 0.5, "y": 0.0, "z": 0.1})
    print(f"move_to(red_box): {result.message} - Success: {result.success}")

    # Pick object
    result = await robot.pick("red_box")
    print(f"pick(red_box): {result.message} - Success: {result.success}")
    print(f"  Now holding: {robot.state.holding}")

    # Move to place location
    result = await robot.move_to({"x": 0.0, "y": 0.5, "z": 0.1})
    print(f"move_to(place_loc): {result.message} - Success: {result.success}")

    # Place object
    result = await robot.place({"x": 0.0, "y": 0.5, "z": 0.05})
    print(f"place(): {result.message} - Success: {result.success}")
    print(f"  Now holding: {robot.state.holding}")

    print("\n=== Final State ===")
    print(f"Robot: {robot.get_state()}")
    print(f"Objects: {robot.get_world_objects()}")


if __name__ == "__main__":
    asyncio.run(demo())
