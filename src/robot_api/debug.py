"""
Debugging tools for robotics system.

Provides:
- Log inspection and filtering
- Trajectory visualization data generation
- Sensor data debugging utilities
- Performance monitoring

Per architecture: This module is part of the Robot API layer.
"""
import time
from dataclasses import dataclass, field
from typing import Any
from collections import deque


# ============================================================
# Command Log Entry
# ============================================================

@dataclass
class CommandLogEntry:
    """A logged robot command for debugging."""
    timestamp: float
    command_type: str
    command_id: str
    parameters: dict
    result_state: str
    execution_time_ms: float
    safety_check_passed: bool
    message: str


# ============================================================
# Trajectory Visualization Data
# ============================================================

@dataclass
class TrajectoryVisualizationData:
    """Data format for trajectory visualization."""
    positions: list[dict]
    velocities: list[dict]
    accelerations: list[dict]
    timestamps: list[float]
    duration: float
    trajectory_type: str


# ============================================================
# Sensor Data Debug Snapshot
# ============================================================

@dataclass
class SensorDebugSnapshot:
    """A snapshot of sensor data for debugging."""
    timestamp: float
    joint_positions: list[float]
    joint_velocities: list[float]
    end_effector_pose: dict
    gripper_width: float
    gripper_force: float
    sensor_readings: dict


# ============================================================
# Robot Debugger
# ============================================================

class RobotDebugger:
    """
    Debugging utilities for robot operations.

    Provides:
    - Command logging with filtering
    - Trajectory data export for visualization
    - Sensor data snapshots
    - Performance metrics
    """

    def __init__(self, max_log_entries: int = 1000):
        self._max_log_entries = max_log_entries
        self._command_log: deque[CommandLogEntry] = deque(maxlen=max_log_entries)
        self._trajectory_history: deque[TrajectoryVisualizationData] = deque(maxlen=100)
        self._snapshot_history: deque[SensorDebugSnapshot] = deque(maxlen=max_log_entries)
        self._command_timings: dict[str, list[float]] = {}

    def log_command(
        self,
        command_type: str,
        command_id: str,
        parameters: dict,
        result_state: str,
        execution_time_ms: float,
        safety_check_passed: bool,
        message: str,
    ) -> None:
        """Log a robot command for debugging."""
        entry = CommandLogEntry(
            timestamp=time.time(),
            command_type=command_type,
            command_id=command_id,
            parameters=parameters,
            result_state=result_state,
            execution_time_ms=execution_time_ms,
            safety_check_passed=safety_check_passed,
            message=message,
        )
        self._command_log.append(entry)

        # Track timing stats
        if command_type not in self._command_timings:
            self._command_timings[command_type] = []
        self._command_timings[command_type].append(execution_time_ms)
        if len(self._command_timings[command_type]) > 100:
            self._command_timings[command_type] = self._command_timings[command_type][-100:]

    def get_command_log(
        self,
        command_type: str | None = None,
        limit: int = 100,
    ) -> list[CommandLogEntry]:
        """Get command log entries, optionally filtered by type."""
        entries = list(self._command_log)
        if command_type:
            entries = [e for e in entries if e.command_type == command_type]
        return entries[-limit:]

    def get_timing_stats(self, command_type: str | None = None) -> dict[str, Any]:
        """Get timing statistics for commands."""
        if command_type:
            timings = self._command_timings.get(command_type, [])
            return {
                command_type: {
                    "count": len(timings),
                    "avg_ms": sum(timings) / len(timings) if timings else 0,
                    "min_ms": min(timings) if timings else 0,
                    "max_ms": max(timings) if timings else 0,
                }
            }

        stats = {}
        for cmd_type, timings in self._command_timings.items():
            stats[cmd_type] = {
                "count": len(timings),
                "avg_ms": sum(timings) / len(timings) if timings else 0,
                "min_ms": min(timings) if timings else 0,
                "max_ms": max(timings) if timings else 0,
            }
        return stats

    def log_trajectory(self, trajectory_data: TrajectoryVisualizationData) -> None:
        """Log trajectory data for visualization."""
        self._trajectory_history.append(trajectory_data)

    def get_trajectory_for_visualization(
        self,
        trajectory_type: str | None = None,
        limit: int = 10,
    ) -> list[TrajectoryVisualizationData]:
        """Get trajectory data for visualization."""
        trajectories = list(self._trajectory_history)
        if trajectory_type:
            trajectories = [t for t in trajectories if t.trajectory_type == trajectory_type]
        return trajectories[-limit:]

    def snapshot_sensors(
        self,
        joint_positions: list[float],
        joint_velocities: list[float],
        end_effector_pose: dict,
        gripper_width: float,
        gripper_force: float,
        sensor_readings: dict,
    ) -> None:
        """Take a sensor data snapshot for debugging."""
        snapshot = SensorDebugSnapshot(
            timestamp=time.time(),
            joint_positions=joint_positions,
            joint_velocities=joint_velocities,
            end_effector_pose=end_effector_pose,
            gripper_width=gripper_width,
            gripper_force=gripper_force,
            sensor_readings=sensor_readings,
        )
        self._snapshot_history.append(snapshot)

    def get_sensor_history(self, limit: int = 100) -> list[SensorDebugSnapshot]:
        """Get recent sensor snapshots."""
        return list(self._snapshot_history)[-limit:]

    def get_debug_report(self) -> dict[str, Any]:
        """Generate a comprehensive debug report."""
        return {
            "command_log_count": len(self._command_log),
            "trajectory_count": len(self._trajectory_history),
            "snapshot_count": len(self._snapshot_history),
            "timing_stats": self.get_timing_stats(),
            "recent_commands": [
                {
                    "timestamp": e.timestamp,
                    "type": e.command_type,
                    "id": e.command_id,
                    "state": e.result_state,
                    "exec_time_ms": e.execution_time_ms,
                    "safety_ok": e.safety_check_passed,
                }
                for e in list(self._command_log)[-10:]
            ],
        }

    def clear_logs(self) -> None:
        """Clear all debug logs."""
        self._command_log.clear()
        self._trajectory_history.clear()
        self._snapshot_history.clear()
        self._command_timings.clear()


# Singleton debugger instance
_debugger: RobotDebugger | None = None


def get_robot_debugger() -> RobotDebugger:
    """Get the global robot debugger instance."""
    global _debugger
    if _debugger is None:
        _debugger = RobotDebugger()
    return _debugger
