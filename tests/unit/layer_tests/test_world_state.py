"""
Unit tests for WorldState schema and serialization.
Tests the shared world state representation.

Authoritative source: src/shared/world_state.py
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.shared.world_state import (
    WorldState,
    RobotState,
    Pose,
    WorldObject,
    Obstacle,
    WorkspaceBounds,
    Environment,
    ObjectState,
    Size3D,
)


class TestPose:
    """Tests for Pose dataclass."""

    def test_pose_default_values(self):
        """Pose should have default values for rotation."""
        pose = Pose(x=0.1, y=0.2, z=0.3)
        assert pose.x == 0.1
        assert pose.y == 0.2
        assert pose.z == 0.3
        assert pose.rx == 0.0
        assert pose.ry == 0.0
        assert pose.rz == 0.0

    def test_pose_with_rotation(self):
        """Pose should accept rotation values."""
        pose = Pose(x=0.1, y=0.2, z=0.3, rx=0.5, ry=0.6, rz=0.7)
        assert pose.rx == 0.5
        assert pose.ry == 0.6
        assert pose.rz == 0.7


class TestRobotStateDataclass:
    """Tests for RobotState dataclass."""

    def test_robot_state_default_joints(self):
        """RobotState should have default 6 joint positions."""
        state = RobotState()
        assert state.joint_positions == [0.0] * 6

    def test_robot_state_with_joints(self):
        """RobotState should accept custom joint positions."""
        joints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        state = RobotState(joint_positions=joints)
        assert state.joint_positions == joints

    def test_robot_state_with_pose(self):
        """RobotState should accept end_effector_pose."""
        pose = Pose(x=0.1, y=0.2, z=0.3)
        state = RobotState(end_effector_pose=pose)
        assert state.end_effector_pose == pose

    def test_robot_state_default_gripper(self):
        """RobotState should have default gripper values."""
        state = RobotState()
        assert state.gripper_width == 0.0
        assert state.gripper_force == 0.0


class TestWorldObject:
    """Tests for WorldObject dataclass."""

    def test_world_object_required_fields(self):
        """WorldObject requires id, type, and pose."""
        pose = Pose(x=0.1, y=0.2, z=0.3)
        obj = WorldObject(id="obj1", type="block", pose=pose)
        assert obj.id == "obj1"
        assert obj.type == "block"
        assert obj.pose == pose

    def test_world_object_optional_fields(self):
        """WorldObject should have optional color and state."""
        pose = Pose(x=0.1, y=0.2, z=0.3)
        obj = WorldObject(
            id="obj1",
            type="block",
            pose=pose,
            color="red",
            state=ObjectState.GRASPED
        )
        assert obj.color == "red"
        assert obj.state == ObjectState.GRASPED


class TestObjectState:
    """Tests for ObjectState enum."""

    def test_object_state_values(self):
        """ObjectState should have expected values."""
        assert ObjectState.VISIBLE.value == "visible"
        assert ObjectState.GRASPED.value == "grasped"
        assert ObjectState.PLACED.value == "placed"
        assert ObjectState.HIDDEN.value == "hidden"


class TestObstacle:
    """Tests for Obstacle dataclass."""

    def test_obstacle_required_fields(self):
        """Obstacle requires id, pose, and shape."""
        pose = Pose(x=0.1, y=0.2, z=0.3)
        obstacle = Obstacle(id="obs1", pose=pose, shape="box")
        assert obstacle.id == "obs1"
        assert obstacle.pose == pose
        assert obstacle.shape == "box"


class TestWorkspaceBounds:
    """Tests for WorkspaceBounds dataclass."""

    def test_workspace_bounds_default_values(self):
        """WorkspaceBounds should have default values."""
        bounds = WorkspaceBounds()
        assert bounds.x_min == -0.5
        assert bounds.x_max == 0.5
        assert bounds.y_min == -0.5
        assert bounds.y_max == 0.5
        assert bounds.z_min == 0.0
        assert bounds.z_max == 0.5

    def test_workspace_bounds_custom_values(self):
        """WorkspaceBounds should accept custom values."""
        bounds = WorkspaceBounds(x_min=-1.0, x_max=1.0, y_min=-1.0, y_max=1.0, z_min=0.0, z_max=1.0)
        assert bounds.x_min == -1.0
        assert bounds.x_max == 1.0


class TestEnvironment:
    """Tests for Environment dataclass."""

    def test_environment_default_bounds(self):
        """Environment should have default workspace bounds."""
        env = Environment()
        assert env.workspace_bounds == WorkspaceBounds()

    def test_environment_with_obstacles(self):
        """Environment should accept obstacles list."""
        pose = Pose(x=0.1, y=0.2, z=0.0)
        obstacle = Obstacle(id="obs1", pose=pose, shape="box")
        env = Environment(obstacles=[obstacle])
        assert len(env.obstacles) == 1
        assert env.obstacles[0].id == "obs1"


class TestWorldState:
    """Tests for WorldState dataclass."""

    def test_world_state_required_fields(self):
        """WorldState requires timestamp and robot."""
        robot_state = RobotState()
        ws = WorldState(timestamp=123.45, robot=robot_state)
        assert ws.timestamp == 123.45
        assert ws.robot == robot_state

    def test_world_state_default_objects(self):
        """WorldState should have empty objects list by default."""
        ws = WorldState(timestamp=123.45, robot=RobotState())
        assert ws.objects == []

    def test_world_state_default_environment(self):
        """WorldState should have default environment by default."""
        ws = WorldState(timestamp=123.45, robot=RobotState())
        assert ws.environment == Environment()


class TestWorldStateSerialization:
    """Tests for WorldState to_dict and from_dict."""

    def test_world_state_to_dict(self):
        """WorldState should serialize to dictionary."""
        robot_state = RobotState(
            joint_positions=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            end_effector_pose=Pose(x=0.1, y=0.2, z=0.3),
            gripper_width=0.5,
            gripper_force=0.3
        )
        ws = WorldState(timestamp=123.45, robot=robot_state, objects=[], environment=Environment())

        result = ws.to_dict()

        assert result["timestamp"] == 123.45
        assert result["robot"]["joint_positions"] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        assert result["robot"]["gripper_width"] == 0.5
        assert result["robot"]["gripper_force"] == 0.3

    def test_world_state_to_dict_pose(self):
        """to_dict should serialize pose correctly."""
        robot_state = RobotState(end_effector_pose=Pose(x=0.1, y=0.2, z=0.3, rx=0.4, ry=0.5, rz=0.6))
        ws = WorldState(timestamp=123.45, robot=robot_state)

        result = ws.to_dict()

        assert result["robot"]["end_effector_pose"]["x"] == 0.1
        assert result["robot"]["end_effector_pose"]["y"] == 0.2
        assert result["robot"]["end_effector_pose"]["z"] == 0.3
        assert result["robot"]["end_effector_pose"]["rx"] == 0.4

    def test_world_state_from_dict(self):
        """WorldState should deserialize from dictionary."""
        data = {
            "timestamp": 123.45,
            "robot": {
                "joint_positions": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                "end_effector_pose": {"x": 0.1, "y": 0.2, "z": 0.3, "rx": 0.0, "ry": 0.0, "rz": 0.0},
                "gripper_width": 0.5,
                "gripper_force": 0.3
            },
            "objects": [],
            "environment": {"obstacles": [], "workspace_bounds": {}}
        }

        ws = WorldState.from_dict(data)

        assert ws.timestamp == 123.45
        assert ws.robot.joint_positions == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        assert ws.robot.gripper_width == 0.5

    def test_world_state_roundtrip(self):
        """WorldState should survive to_dict -> from_dict roundtrip."""
        robot_state = RobotState(
            joint_positions=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            end_effector_pose=Pose(x=0.1, y=0.2, z=0.3),
            gripper_width=0.5,
            gripper_force=0.3
        )
        world_object = WorldObject(id="obj1", type="block", pose=Pose(x=0.0, y=0.0, z=0.0))
        env = Environment(workspace_bounds=WorkspaceBounds(x_min=-1.0, x_max=1.0))

        original = WorldState(timestamp=123.45, robot=robot_state, objects=[world_object], environment=env)

        serialized = original.to_dict()
        restored = WorldState.from_dict(serialized)

        assert restored.timestamp == original.timestamp
        assert restored.robot.joint_positions == original.robot.joint_positions
        assert restored.robot.gripper_width == original.robot.gripper_width
        assert len(restored.objects) == 1
        assert restored.objects[0].id == "obj1"
        assert restored.environment.workspace_bounds.x_max == 1.0


class TestWorldStateWithObjects:
    """Tests for WorldState with world objects."""

    def test_world_state_objects_list(self):
        """WorldState should hold list of WorldObjects."""
        obj1 = WorldObject(id="obj1", type="block", pose=Pose(x=0.0, y=0.0, z=0.0))
        obj2 = WorldObject(id="obj2", type="sphere", pose=Pose(x=0.1, y=0.1, z=0.1))

        robot_state = RobotState()
        ws = WorldState(timestamp=time.time(), robot=robot_state, objects=[obj1, obj2])

        assert len(ws.objects) == 2
        assert ws.objects[0].id == "obj1"
        assert ws.objects[1].id == "obj2"

    def test_world_object_serialization(self):
        """WorldObjects should serialize correctly."""
        obj = WorldObject(
            id="obj1",
            type="block",
            pose=Pose(x=0.1, y=0.2, z=0.3),
            color="blue",
            state=ObjectState.PLACED,
            metadata={"weight": 0.5}
        )

        ws = WorldState(timestamp=123.45, robot=RobotState(), objects=[obj])
        result = ws.to_dict()

        assert result["objects"][0]["id"] == "obj1"
        assert result["objects"][0]["type"] == "block"
        assert result["objects"][0]["color"] == "blue"
        assert result["objects"][0]["state"] == "placed"
