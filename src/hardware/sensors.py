"""
Sensor interfaces and implementations for robotics system.

This module provides:
- Base sensor interfaces
- Specific sensor types (IMU, force/torque, proximity, joint encoders)
- Sensor data processing utilities

Per locked architecture: Layer 2 - Hardware Abstraction
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict
import time
import math


# ============================================================
# Base Sensor Interfaces
# ============================================================

class ISensor(ABC):
    """Base interface for all sensors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Sensor name identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if sensor is available and connected."""
        pass

    @abstractmethod
    def read(self) -> "SensorReading":
        """Read current sensor value."""
        pass

    @abstractmethod
    def calibrate(self) -> bool:
        """Calibrate the sensor."""
        pass


@dataclass
class SensorReading:
    """Container for sensor reading with metadata."""
    timestamp: float
    sensor_name: str
    values: dict
    unit: str
    is_valid: bool = True
    error_message: str = ""

    @classmethod
    def create_invalid(cls, sensor_name: str, error: str) -> "SensorReading":
        """Create an invalid reading with error info."""
        return cls(
            timestamp=time.time(),
            sensor_name=sensor_name,
            values={},
            unit="",
            is_valid=False,
            error_message=error
        )


# ============================================================
# Specific Sensor Types
# ============================================================

class IMUReading(TypedDict):
    """IMU sensor reading format."""
    ax: float  # acceleration x (m/s^2)
    ay: float  # acceleration y (m/s^2)
    az: float  # acceleration z (m/s^2)
    gx: float  # gyro x (rad/s)
    gy: float  # gyro y (rad/s)
    gz: float  # gyro z (rad/s)
    mx: float  # magnetometer x (microtesla)
    my: float  # magnetometer y (microtesla)
    mz: float  # magnetometer z (microtesla)
    temperature: float  # temperature (Celsius)


class IIMUSensor(ISensor):
    """Interface for Inertial Measurement Unit sensors."""

    @property
    def name(self) -> str:
        return "imu"

    @abstractmethod
    def read(self) -> SensorReading:
        """Read IMU data."""
        pass

    @abstractmethod
    def get_orientation(self) -> tuple[float, float, float]:
        """Get orientation as (roll, pitch, yaw) in radians."""
        pass

    @abstractmethod
    def get_linear_acceleration(self) -> tuple[float, float, float]:
        """Get linear acceleration (m/s^2)."""
        pass

    @abstractmethod
    def get_angular_velocity(self) -> tuple[float, float, float]:
        """Get angular velocity (rad/s)."""
        pass


class ForceTorqueReading(TypedDict):
    """Force/Torque sensor reading format."""
    fx: float  # force x (N)
    fy: float  # force y (N)
    fz: float  # force z (N)
    tx: float  # torque x (Nm)
    ty: float  # torque y (Nm)
    tz: float  # torque z (Nm)


class IForceTorqueSensor(ISensor):
    """Interface for Force/Torque sensors."""

    @property
    def name(self) -> str:
        return "force_torque"

    @abstractmethod
    def read(self) -> SensorReading:
        """Read force/torque data."""
        pass

    @abstractmethod
    def get_total_force(self) -> float:
        """Get magnitude of total force (N)."""
        pass

    @abstractmethod
    def get_total_torque(self) -> float:
        """Get magnitude of total torque (Nm)."""
        pass

    @abstractmethod
    def is_exceeding_threshold(self, force_threshold: float, torque_threshold: float) -> bool:
        """Check if readings exceed safety thresholds."""
        pass


class ProximityReading(TypedDict):
    """Proximity sensor reading format."""
    distance: float  # distance in meters
    is_object_detected: bool
    confidence: float  # 0.0 to 1.0


class IProximitySensor(ISensor):
    """Interface for proximity sensors."""

    @property
    def name(self) -> str:
        return "proximity"

    @abstractmethod
    def read(self) -> SensorReading:
        """Read proximity data."""
        pass

    @abstractmethod
    def get_distance(self) -> float:
        """Get distance to nearest object (meters)."""
        pass

    @abstractmethod
    def is_object_detected(self, min_distance: float = 0.01) -> bool:
        """Check if object is within specified distance."""
        pass


class JointEncoderReading(TypedDict):
    """Joint encoder reading format."""
    joint_index: int
    position: float  # radians
    velocity: float  # rad/s
    torque: float  # Nm


class IJointEncoder(ISensor):
    """Interface for joint encoders."""

    @property
    def name(self) -> str:
        return "joint_encoder"

    @abstractmethod
    def read(self, joint_index: int) -> SensorReading:
        """Read encoder data for specific joint."""
        pass

    @abstractmethod
    def read_all(self) -> list[JointEncoderReading]:
        """Read all joint encoders."""
        pass


class GripperSensorReading(TypedDict):
    """Gripper sensor reading format."""
    width: float  # gripper opening width (m)
    force: float  # gripping force (N)
    is_object_grasped: bool
    object_mass_estimate: float  # kg


class IGripperSensor(ISensor):
    """Interface for gripper sensors."""

    @property
    def name(self) -> str:
        return "gripper"

    @abstractmethod
    def read(self) -> SensorReading:
        """Read gripper sensor data."""
        pass

    @abstractmethod
    def get_gripper_width(self) -> float:
        """Get current gripper width (meters)."""
        pass

    @abstractmethod
    def get_gripping_force(self) -> float:
        """Get current gripping force (N)."""
        pass

    @abstractmethod
    def detect_grasped_object(self) -> bool:
        """Detect if an object is currently grasped."""
        pass


# ============================================================
# Simulated Sensors (for testing without hardware)
# ============================================================

class SimulatedIMU(IIMUSensor):
    """Simulated IMU for testing."""

    def __init__(self, noise_level: float = 0.01):
        self._name = "sim_imu"
        self._available = True
        self._noise_level = noise_level
        self._orientation = [0.0, 0.0, 0.0]  # roll, pitch, yaw
        self._linear_accel = [0.0, 0.0, 9.81]  # assume stationary
        self._angular_vel = [0.0, 0.0, 0.0]

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return self._available

    def read(self) -> SensorReading:
        if not self._available:
            return SensorReading.create_invalid(self._name, "IMU not available")
        return SensorReading(
            timestamp=time.time(),
            sensor_name=self._name,
            values=IMUReading(
                ax=self._linear_accel[0] + self._add_noise(),
                ay=self._linear_accel[1] + self._add_noise(),
                az=self._linear_accel[2] + self._add_noise(),
                gx=self._angular_vel[0] + self._add_noise() * 0.1,
                gy=self._angular_vel[1] + self._add_noise() * 0.1,
                gz=self._angular_vel[2] + self._add_noise() * 0.1,
                mx=25.0 + self._add_noise(),
                my=25.0 + self._add_noise(),
                mz=25.0 + self._add_noise(),
                temperature=25.0 + self._add_noise() * 5,
            ),
            unit="m/s^2, rad/s, uT, C"
        )

    def get_orientation(self) -> tuple[float, float, float]:
        return tuple(self._orientation)

    def get_linear_acceleration(self) -> tuple[float, float, float]:
        return tuple(self._linear_accel)

    def get_angular_velocity(self) -> tuple[float, float, float]:
        return tuple(self._angular_vel)

    def calibrate(self) -> bool:
        self._orientation = [0.0, 0.0, 0.0]
        self._linear_accel = [0.0, 0.0, 9.81]
        self._angular_vel = [0.0, 0.0, 0.0]
        return True

    def update(self, accel: list[float], gyro: list[float]) -> None:
        """Update simulated IMU with actual values from simulator."""
        self._linear_accel = accel
        self._angular_vel = gyro

    def _add_noise(self) -> float:
        import random
        return random.gauss(0, self._noise_level)


class SimulatedForceTorque(IForceTorqueSensor):
    """Simulated Force/Torque sensor for testing."""

    def __init__(self, noise_level: float = 0.1):
        self._name = "sim_force_torque"
        self._available = True
        self._noise_level = noise_level
        self._readings = ForceTorqueReading(fx=0.0, fy=0.0, fz=0.0, tx=0.0, ty=0.0, tz=0.0)

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return self._available

    def read(self) -> SensorReading:
        if not self._available:
            return SensorReading.create_invalid(self._name, "Force/Torque sensor not available")
        return SensorReading(
            timestamp=time.time(),
            sensor_name=self._name,
            values=self._readings,
            unit="N, Nm"
        )

    def get_total_force(self) -> float:
        f = self._readings
        return math.sqrt(f['fx']**2 + f['fy']**2 + f['fz']**2)

    def get_total_torque(self) -> float:
        t = self._readings
        return math.sqrt(t['tx']**2 + t['ty']**2 + t['tz']**2)

    def is_exceeding_threshold(self, force_threshold: float, torque_threshold: float) -> bool:
        return self.get_total_force() > force_threshold or self.get_total_torque() > torque_threshold

    def calibrate(self) -> bool:
        self._readings = ForceTorqueReading(fx=0.0, fy=0.0, fz=0.0, tx=0.0, ty=0.0, tz=0.0)
        return True

    def update(self, fx: float, fy: float, fz: float, tx: float, ty: float, tz: float) -> None:
        """Update with actual force/torque values."""
        self._readings = ForceTorqueReading(fx=fx, fy=fy, fz=fz, tx=tx, ty=ty, tz=tz)


class SimulatedProximity(IProximitySensor):
    """Simulated proximity sensor for testing."""

    def __init__(self, max_range: float = 0.5):
        self._name = "sim_proximity"
        self._available = True
        self._max_range = max_range
        self._distance = max_range
        self._object_detected = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return self._available

    def read(self) -> SensorReading:
        if not self._available:
            return SensorReading.create_invalid(self._name, "Proximity sensor not available")
        return SensorReading(
            timestamp=time.time(),
            sensor_name=self._name,
            values=ProximityReading(
                distance=self._distance,
                is_object_detected=self._object_detected,
                confidence=0.95 if self._object_detected else 0.0
            ),
            unit="m"
        )

    def get_distance(self) -> float:
        return self._distance

    def is_object_detected(self, min_distance: float = 0.01) -> bool:
        return self._object_detected and self._distance < min_distance

    def calibrate(self) -> bool:
        self._distance = self._max_range
        self._object_detected = False
        return True

    def update(self, distance: float) -> None:
        """Update with actual proximity reading."""
        self._distance = min(distance, self._max_range)
        self._object_detected = distance < self._max_range


class SensorManager:
    """
    Central manager for all sensors.

    Provides a unified interface to access all sensors and
    handles sensor data fusion and processing.
    """

    def __init__(self):
        self._sensors: dict[str, ISensor] = {}
        self._sensor_history: dict[str, list[SensorReading]] = {}
        self._max_history_size = 1000

    def register_sensor(self, sensor: ISensor) -> None:
        """Register a sensor with the manager."""
        self._sensors[sensor.name] = sensor
        self._sensor_history[sensor.name] = []

    def get_sensor(self, name: str) -> ISensor | None:
        """Get sensor by name."""
        return self._sensors.get(name)

    def read_all(self) -> dict[str, SensorReading]:
        """Read all registered sensors."""
        results = {}
        for name, sensor in self._sensors.items():
            reading = sensor.read()
            results[name] = reading
            self._add_to_history(name, reading)
        return results

    def is_all_available(self) -> bool:
        """Check if all sensors are available."""
        return all(s.is_available for s in self._sensors.values())

    def calibrate_all(self) -> dict[str, bool]:
        """Calibrate all sensors."""
        results = {}
        for name, sensor in self._sensors.items():
            results[name] = sensor.calibrate()
        return results

    def get_history(self, sensor_name: str, limit: int = 100) -> list[SensorReading]:
        """Get sensor reading history."""
        history = self._sensor_history.get(sensor_name, [])
        return history[-limit:]

    def _add_to_history(self, sensor_name: str, reading: SensorReading) -> None:
        """Add reading to history with size limit."""
        if sensor_name not in self._sensor_history:
            self._sensor_history[sensor_name] = []
        self._sensor_history[sensor_name].append(reading)
        if len(self._sensor_history[sensor_name]) > self._max_history_size:
            self._sensor_history[sensor_name] = self._sensor_history[sensor_name][-self._max_history_size:]
