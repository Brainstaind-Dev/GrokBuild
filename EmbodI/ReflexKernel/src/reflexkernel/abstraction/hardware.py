"""
Hardware sensor driver stubs for the Embodied Autonomic System.

This file will eventually contain real drivers for:
- FSR array (via ADS1115 or direct ADC on ESP32)
- MPU6050 (I2C)
- MAX9814 microphone (analog or I2S)
- DHT22 (1-wire)
- etc.

For now it contains only interface sketches so the rest of the system
can be developed against a stable contract.

When real hardware arrives, implement the `read_all()` method to return
the same shape that `VirtualSensorSimulator.read_all()` produces.
"""

from __future__ import annotations

from typing import Any, Dict

from .base import AbstractFeatureExtractor
from .schema import AbstractionOutput, DetailLevel


class HardwareSensorReader(AbstractFeatureExtractor):
    """
    Placeholder for real hardware-backed feature extraction.

    The expectation is that the ESP32 or Raspberry Pi will feed structured
    readings, and this class (or a subclass) will turn them into
    `AbstractionOutput` using the same logic as the virtual version.
    """

    name = "hardware_tier1"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        # In real implementation: open I2C, serial to ESP32, GPIO, etc.
        self._connected = False

    def connect(self) -> bool:
        """Establish connection to the sensor aggregation board (ESP32, etc.)."""
        # TODO: implement real connection
        self._connected = True
        return True

    def read_all(self) -> Dict[str, Any]:
        """Read raw values from physical sensors."""
        if not self._connected:
            raise RuntimeError("HardwareSensorReader not connected. Call connect() first.")

        # Placeholder return shape — must match VirtualSensorSimulator.read_all()
        return {
            "fsr": [0.0, 0.0, 0.0, 0.0],
            "mpu": {"accel": [0.0, 0.0, 1.0], "gyro": [0.0, 0.0, 0.0]},
            "microphone": {"energy": 0.03, "onset": False},
            "dht22": {"ambient_temp": 23.0, "body_temp": 31.5},
            "ts": 0.0,
        }

    def process(self, raw_data: Dict[str, Any] | None = None, detail_level: DetailLevel = DetailLevel.NORMAL) -> AbstractionOutput:
        if raw_data is None:
            raw_data = self.read_all()
        # TODO: Implement real feature extraction logic here (or reuse shared logic)
        # For now we return an empty output so the system doesn't break.
        from .schema import AbstractionOutput

        return AbstractionOutput(
            events=[],
            features=[],
            state_summary=None,
            ts=raw_data.get("ts", 0.0),
        )
