"""
Hardware Adapters Module.

Provides adapter implementations for connecting to real robot hardware.

Per locked architecture: Layer 4 - Hardware/Simulator Layer
This module should be imported by the Hardware Abstraction Layer,
not directly by the Robot API layer.
"""
from .base import IHardwareAdapter, HardwareCommandResult
from .mock_adapter import MockHardwareAdapter
from .serial_adapter import SerialHardwareAdapter
from .network_adapter import NetworkHardwareAdapter

__all__ = [
    "IHardwareAdapter",
    "HardwareCommandResult",
    "MockHardwareAdapter",
    "SerialHardwareAdapter",
    "NetworkHardwareAdapter",
]
