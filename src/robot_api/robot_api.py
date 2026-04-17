"""
Robot Control API - Concrete Implementation.

Layer 3: Robot Control API Layer
Implements IRobotAPI interface.
"""
import uuid
from typing import Optional

from src.shared.interfaces import (
    IRobotAPI,
    RobotStatus,
    RobotState,
    RobotAction,
    MoveJointsParams,
    MovePoseParams,
    MoveLinearParams,
    SetGripperParams,
    StopParams,
    ExecuteSkillParams,
)
from src.shared.world_state import WorldState
from src.hardware.simple_adapter import IHardwareAdapter, MockHardwareAdapter


class RobotAPI(IRobotAPI):
    """
    Concrete implementation of Robot Control API.

    This class provides the hardware-agnostic interface for robot control.
    Actual hardware communication is delegated to the Hardware layer.
    """

    def __init__(self, hardware_adapter: Optional[IHardwareAdapter] = None):
        """
        Initialize Robot API.

        Args:
            hardware_adapter: Optional hardware adapter for actual robot communication.
                             If None, a mock adapter is used.
        """
        self._hardware = hardware_adapter or MockHardwareAdapter()
        self._current_status = RobotStatus(
            command_id="",
            state=RobotState.IDLE,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
            joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            gripper_state=0.0,
            sensor_data={},
            message="Ready",
        )

    def move_joints(self, joints: list[float], speed: float) -> RobotStatus:
        """Move robot to joint positions."""
        command_id = str(uuid.uuid4())
        params: MoveJointsParams = {"joints": joints, "speed": speed}
        return self._execute_command(command_id, RobotAction.MOVE_JOINTS, params)

    def move_pose(self, position: dict, orientation: dict, speed: float) -> RobotStatus:
        """Move robot end-effector to pose."""
        command_id = str(uuid.uuid4())
        params: MovePoseParams = {
            "position": position,
            "orientation": orientation,
            "speed": speed,
        }
        return self._execute_command(command_id, RobotAction.MOVE_POSE, params)

    def move_linear(self, target: dict, speed: float) -> RobotStatus:
        """Move robot in a straight line."""
        command_id = str(uuid.uuid4())
        params: MoveLinearParams = {"target": target, "speed": speed}
        return self._execute_command(command_id, RobotAction.MOVE_LINEAR, params)

    def set_gripper(self, position: float, force: float) -> RobotStatus:
        """Control gripper position and force."""
        command_id = str(uuid.uuid4())
        params: SetGripperParams = {"position": position, "force": force}
        return self._execute_command(command_id, RobotAction.SET_GRIPPER, params)

    def get_world_state(self) -> WorldState:
        """Get current world state from hardware."""
        return self._hardware.get_world_state()

    def execute_skill(self, skill_name: str, parameters: dict) -> RobotStatus:
        """Execute a named skill with parameters."""
        command_id = str(uuid.uuid4())
        params: ExecuteSkillParams = {"skill_name": skill_name, "parameters": parameters}
        return self._execute_command(command_id, RobotAction.EXECUTE_SKILL, params)

    def stop(self, immediate: bool = False) -> RobotStatus:
        """Stop robot motion."""
        command_id = str(uuid.uuid4())
        params: StopParams = {"immediate": immediate}
        return self._execute_command(command_id, RobotAction.STOP, params)

    def _execute_command(
        self,
        command_id: str,
        action: RobotAction,
        params: MoveJointsParams | MovePoseParams | MoveLinearParams | SetGripperParams | StopParams | ExecuteSkillParams,
    ) -> RobotStatus:
        """Internal method to execute commands via hardware adapter."""
        self._current_status = RobotStatus(
            command_id=command_id,
            state=RobotState.EXECUTING,
            position=self._current_status.position,
            joints=self._current_status.joints,
            gripper_state=self._current_status.gripper_state,
            sensor_data=self._current_status.sensor_data,
            message=f"Executing {action.value}",
        )

        result = self._hardware.execute(command_id, action, params)

        self._current_status = result
        return result
