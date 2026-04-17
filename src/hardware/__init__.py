"""
Hardware/Simulator Layer.

Per locked architecture: Robot API Layer → Hardware/Simulator Layer
"""
from .simulator import RobotSimulator, get_robot_simulator
from .sensors import (
    SensorManager,
    SimulatedIMU,
    SimulatedForceTorque,
    SimulatedProximity,
    ISensor,
    SensorReading,
)
from .adapters import (
    IHardwareAdapter as IHardwareAdapterComplex,
    HardwareCommandResult,
    MockHardwareAdapter as MockHardwareAdapterComplex,
    SerialHardwareAdapter,
    NetworkHardwareAdapter,
)
from .simple_adapter import IHardwareAdapter, MockHardwareAdapter

__all__ = [
    # Simulator
    "RobotSimulator",
    "get_robot_simulator",
    # Sensors
    "SensorManager",
    "SimulatedIMU",
    "SimulatedForceTorque",
    "SimulatedProximity",
    "ISensor",
    "SensorReading",
    # Adapters (simple interface for RobotAPI layer)
    "IHardwareAdapter",
    "MockHardwareAdapter",
    # Adapters (complex interface for advanced hardware)
    "IHardwareAdapterComplex",
    "MockHardwareAdapterComplex",
    "HardwareCommandResult",
    "SerialHardwareAdapter",
    "NetworkHardwareAdapter",
]
