"""
Unit tests for RobotSimulator.
Tests the Hardware/Simulator layer.

Authoritative source: src/hardware/simulator.py
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "src"))

from src.hardware.simulator import RobotSimulator, get_robot_simulator
from src.shared.interfaces import RobotAction, RobotState


class TestRobotSimulatorInitialization:
    """Test RobotSimulator initialization."""

    def test_robot_simulator_initial_state(self):
        """RobotSimulator should start with default joint positions."""
        simulator = RobotSimulator()
        assert simulator._joint_positions == [0.0] * 6

    def test_robot_simulator_initial_gripper(self):
        """RobotSimulator should start with gripper closed."""
        simulator = RobotSimulator()
        assert simulator._gripper_width == 0.0
        assert simulator._gripper_force == 0.0

    def test_robot_simulator_initial_state_idle(self):
        """RobotSimulator should start in IDLE state."""
        simulator = RobotSimulator()
        assert simulator._state == RobotState.IDLE


class TestSimulatorMoveJoints:
    """Tests for move_joints in RobotSimulator."""

    def test_move_joints_updates_joint_positions(self):
        """move_joints should update internal joint positions."""
        simulator = RobotSimulator()
        target_joints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        status = simulator.move_joints(target_joints, speed=0.5)
        assert simulator._joint_positions == target_joints
        assert status.state == RobotState.COMPLETED

    def test_move_joints_returns_completed_status(self):
        """move_joints should return COMPLETED status."""
        simulator = RobotSimulator()
        status = simulator.move_joints([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], speed=0.5)
        assert status.state == RobotState.COMPLETED

    def test_move_joints_includes_joints_in_message(self):
        """move_joints status message should include target joints."""
        simulator = RobotSimulator()
        target_joints = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        status = simulator.move_joints(target_joints, speed=0.5)
        assert "0.1" in status.message or "0.1, 0.2" in status.message


class TestSimulatorMovePose:
    """Tests for move_pose in RobotSimulator."""

    def test_move_pose_updates_end_effector_pose(self):
        """move_pose should update internal end-effector pose."""
        simulator = RobotSimulator()
        position = {"x": 0.1, "y": 0.2, "z": 0.3}
        orientation = {"roll": 0.1, "pitch": 0.2, "yaw": 0.3}
        status = simulator.move_pose(position, orientation, speed=0.5)
        assert simulator._end_effector_pose.x == 0.1
        assert simulator._end_effector_pose.y == 0.2
        assert simulator._end_effector_pose.z == 0.3

    def test_move_pose_returns_completed_status(self):
        """move_pose should return COMPLETED status."""
        simulator = RobotSimulator()
        status = simulator.move_pose({"x": 0.1, "y": 0.2, "z": 0.3}, {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}, speed=0.5)
        assert status.state == RobotState.COMPLETED


class TestSimulatorMoveLinear:
    """Tests for move_linear in RobotSimulator."""

    def test_move_linear_updates_position(self):
        """move_linear should update end-effector position."""
        simulator = RobotSimulator()
        target = {"x": 0.3, "y": 0.2, "z": 0.1}
        status = simulator.move_linear(target, speed=0.5)
        assert simulator._end_effector_pose.x == 0.3
        assert simulator._end_effector_pose.y == 0.2
        assert simulator._end_effector_pose.z == 0.1

    def test_move_linear_returns_completed_status(self):
        """move_linear should return COMPLETED status."""
        simulator = RobotSimulator()
        status = simulator.move_linear({"x": 0.1, "y": 0.2, "z": 0.3}, speed=0.5)
        assert status.state == RobotState.COMPLETED


class TestSimulatorSetGripper:
    """Tests for set_gripper in RobotSimulator."""

    def test_set_gripper_updates_gripper_state(self):
        """set_gripper should update gripper width and force."""
        simulator = RobotSimulator()
        status = simulator.set_gripper(position=0.8, force=0.6)
        assert simulator._gripper_width == 0.8
        assert simulator._gripper_force == 0.6

    def test_set_gripper_clamps_values(self):
        """set_gripper should clamp values to 0.0-1.0 range."""
        simulator = RobotSimulator()
        simulator.set_gripper(position=1.5, force=1.5)  # Values above 1.0
        assert simulator._gripper_width == 1.0
        assert simulator._gripper_force == 1.0

        simulator.set_gripper(position=-0.5, force=-0.5)  # Values below 0.0
        assert simulator._gripper_width == 0.0
        assert simulator._gripper_force == 0.0

    def test_set_gripper_returns_completed_status(self):
        """set_gripper should return COMPLETED status."""
        simulator = RobotSimulator()
        status = simulator.set_gripper(position=0.5, force=0.5)
        assert status.state == RobotState.COMPLETED


class TestSimulatorExecuteSkill:
    """Tests for execute_skill in RobotSimulator."""

    def test_execute_skill_move_to(self):
        """execute_skill with 'move_to' should call move_linear."""
        simulator = RobotSimulator()
        status = simulator.execute_skill("move_to", {"x": 0.1, "y": 0.2, "z": 0.3, "speed": 0.5})
        assert status.state == RobotState.COMPLETED
        assert simulator._end_effector_pose.x == 0.1

    def test_execute_skill_grasp(self):
        """execute_skill with 'grasp' should close gripper."""
        simulator = RobotSimulator()
        status = simulator.execute_skill("grasp", {"force": 0.7})
        assert status.state == RobotState.COMPLETED
        assert simulator._gripper_width == 0.0  # Grasping closes gripper

    def test_execute_skill_release(self):
        """execute_skill with 'release' should open gripper."""
        simulator = RobotSimulator()
        simulator.set_gripper(0.0, 0.5)  # Close gripper first
        status = simulator.execute_skill("release", {})
        assert status.state == RobotState.COMPLETED
        assert simulator._gripper_width == 1.0  # Release opens gripper

    def test_execute_skill_lift(self):
        """execute_skill with 'lift' should move up."""
        simulator = RobotSimulator()
        simulator._end_effector_pose.x = 0.1
        simulator._end_effector_pose.y = 0.2
        simulator._end_effector_pose.z = 0.0
        status = simulator.execute_skill("lift", {"height": 0.3, "speed": 0.5})
        assert status.state == RobotState.COMPLETED
        assert simulator._end_effector_pose.z == 0.3

    def test_execute_skill_place(self):
        """execute_skill with 'place' should move to position."""
        simulator = RobotSimulator()
        status = simulator.execute_skill("place", {"x": 0.1, "y": 0.2, "z": 0.0, "speed": 0.5})
        assert status.state == RobotState.COMPLETED

    def test_execute_skill_unknown_returns_error(self):
        """execute_skill with unknown skill should return ERROR."""
        simulator = RobotSimulator()
        status = simulator.execute_skill("unknown_skill", {})
        assert status.state == RobotState.ERROR


class TestSimulatorStop:
    """Tests for stop in RobotSimulator."""

    def test_stop_returns_idle_status(self):
        """stop should return IDLE status."""
        simulator = RobotSimulator()
        status = simulator.stop()
        assert status.state == RobotState.IDLE

    def test_stop_changes_internal_state(self):
        """stop should change internal state to IDLE."""
        simulator = RobotSimulator()
        simulator._state = RobotState.EXECUTING
        simulator.stop()
        assert simulator._state == RobotState.IDLE


class TestSimulatorEmergencyStop:
    """Tests for emergency_stop in RobotSimulator."""

    def test_emergency_stop_returns_error_state(self):
        """emergency_stop should return ERROR status."""
        simulator = RobotSimulator()
        status = simulator.emergency_stop()
        assert status.state == RobotState.ERROR

    def test_emergency_stop_changes_internal_state(self):
        """emergency_stop should change internal state to ERROR."""
        simulator = RobotSimulator()
        simulator.emergency_stop()
        assert simulator._state == RobotState.ERROR


class TestSimulatorReset:
    """Tests for reset in RobotSimulator."""

    def test_reset_returns_idle_status(self):
        """reset should return IDLE status."""
        simulator = RobotSimulator()
        status = simulator.reset()
        assert status.state == RobotState.IDLE

    def test_reset_restores_default_joints(self):
        """reset should restore default joint positions."""
        simulator = RobotSimulator()
        simulator._joint_positions = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        simulator.reset()
        assert simulator._joint_positions == [0.0] * 6

    def test_reset_restores_default_pose(self):
        """reset should restore default end-effector pose."""
        simulator = RobotSimulator()
        simulator._end_effector_pose.x = 0.5
        simulator._end_effector_pose.y = 0.5
        simulator._end_effector_pose.z = 0.5
        simulator.reset()
        assert simulator._end_effector_pose.x == 0.0
        assert simulator._end_effector_pose.y == 0.0
        assert simulator._end_effector_pose.z == 0.0


class TestSimulatorGetWorldState:
    """Tests for get_world_state in RobotSimulator."""

    def test_get_world_state_returns_valid_state(self):
        """get_world_state should return a valid WorldState."""
        simulator = RobotSimulator()
        world_state = simulator.get_world_state()
        assert world_state is not None
        assert hasattr(world_state, 'timestamp')
        assert hasattr(world_state, 'robot')
        assert hasattr(world_state, 'objects')

    def test_get_world_state_reflects_current_pose(self):
        """get_world_state should reflect current robot pose."""
        simulator = RobotSimulator()
        simulator._end_effector_pose.x = 0.3
        simulator._end_effector_pose.y = 0.2
        simulator._end_effector_pose.z = 0.1
        world_state = simulator.get_world_state()
        # The world_state should have robot with end_effector_pose
        assert world_state.robot.end_effector_pose.x == 0.3


class TestGetRobotSimulator:
    """Tests for get_robot_simulator singleton."""

    def test_get_robot_simulator_returns_simulator(self):
        """get_robot_simulator should return a RobotSimulator."""
        simulator = get_robot_simulator()
        assert isinstance(simulator, RobotSimulator)

    def test_get_robot_simulator_returns_same_instance(self):
        """get_robot_simulator should return the same instance (singleton)."""
        sim1 = get_robot_simulator()
        sim2 = get_robot_simulator()
        assert sim1 is sim2


class TestSimulatorErrorHandling:
    """Tests for error handling in RobotSimulator."""

    def test_commands_return_error_when_in_error_state(self):
        """Commands should return ERROR when robot is in error state."""
        simulator = RobotSimulator()
        simulator._state = RobotState.ERROR  # Force error state
        status = simulator.move_joints([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], speed=0.5)
        assert status.state == RobotState.ERROR
        assert "error" in status.message.lower()

    def test_execute_skill_in_error_state_returns_error(self):
        """execute_skill should return ERROR when in error state."""
        simulator = RobotSimulator()
        simulator._state = RobotState.ERROR
        status = simulator.execute_skill("move_to", {"x": 0.1, "y": 0.2, "z": 0.3})
        assert status.state == RobotState.ERROR
