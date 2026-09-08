"""
HardwareSensorReader — Pad-Read (B).

Tick-Door A already seats HardwareSensor on the tick. B attaches here:
a reader that can take a fake bus in tests, or a live ADS1115 when AIN0 ACKs.
Silence is not connected. Missing chip / missing bus fail_open at the Sensor.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Protocol

from .base import AbstractFeatureExtractor
from .schema import AbstractionOutput, DetailLevel


# ADS1115 single-ended full scale (PGA ±4.096 V → 15-bit magnitude).
ADC_FULL_SCALE_DEFAULT = 32767.0


def adc_to_unit(adc: float | int, full_scale: float = ADC_FULL_SCALE_DEFAULT) -> float:
    """Map a raw ADC count to FSR unit in [0, 1]. AIN0 only at B."""
    try:
        v = float(adc)
    except (TypeError, ValueError):
        return 0.0
    fs = float(full_scale) if full_scale else ADC_FULL_SCALE_DEFAULT
    if fs <= 0:
        return 0.0
    u = v / fs
    if u != u:  # NaN
        return 0.0
    return max(0.0, min(1.0, u))


class AIN0Bus(Protocol):
    """Narrow bus: one analog channel. Fake in tests; ADS1115 later."""

    def read_ain0(self) -> int: ...


class FakeAIN0Bus:
    """In-process bus. No smbus2. Tests set `ain0` to a known count."""

    def __init__(self, ain0: int = 0) -> None:
        self.ain0 = int(ain0)

    def read_ain0(self) -> int:
        return int(self.ain0)


# ADS1115 default address; config = AIN0 vs GND, PGA ±4.096 V, single-shot, 128 SPS.
ADS1115_ADDR = 0x48
ADS1115_REG_CONV = 0x00
ADS1115_REG_CONFIG = 0x01
ADS1115_CONFIG_AIN0 = 0xC383


class ADS1115AIN0Bus:
    """Live AIN0. Only constructed after a successful probe in connect()."""

    def __init__(self, smbus: Any, address: int = ADS1115_ADDR) -> None:
        self._smbus = smbus
        self._address = int(address)

    def read_ain0(self) -> int:
        cfg = ADS1115_CONFIG_AIN0
        self._smbus.write_i2c_block_data(
            self._address, ADS1115_REG_CONFIG, [(cfg >> 8) & 0xFF, cfg & 0xFF]
        )
        time.sleep(0.01)
        data = self._smbus.read_i2c_block_data(self._address, ADS1115_REG_CONV, 2)
        raw = (int(data[0]) << 8) | int(data[1])
        if raw > 32767:
            raw -= 65536
        return raw


class HardwareSensorReader(AbstractFeatureExtractor):
    """
    Physical reader with the same `read_all()` shape as VirtualSensorSimulator.

    `connect(bus=...)` is connected only after a successful AIN0 read.
    Never set connected on silence.
    """

    name = "hardware_tier1"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        c = self.config or {}
        self._fail_open = bool(c.get("fail_open", True))
        self._full_scale = float(c.get("adc_full_scale", ADC_FULL_SCALE_DEFAULT))
        self._bus: Optional[AIN0Bus] = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return bool(self._connected)

    def connect(self, bus: Optional[AIN0Bus] = None) -> bool:
        """
        Attach a bus. FakeAIN0Bus in tests; live chip only if a read succeeds.
        Returns True only when AIN0 can be read. Silence stays disconnected.
        """
        self._connected = False
        candidate: Optional[AIN0Bus] = bus
        if candidate is None:
            candidate = self._try_live_bus()
        if candidate is None:
            return False
        try:
            candidate.read_ain0()
        except Exception:
            self._bus = None
            self._connected = False
            return False
        self._bus = candidate
        self._connected = True
        return True

    def _try_live_bus(self) -> Optional[AIN0Bus]:
        """Optional ADS1115. No ACK / no smbus2 → None (fail_open at the Sensor)."""
        try:
            from smbus2 import SMBus  # type: ignore
        except Exception:
            return None
        bus_id = int((self.config or {}).get("i2c_bus", 1))
        addr = int((self.config or {}).get("i2c_address", ADS1115_ADDR))
        smbus = None
        try:
            smbus = SMBus(bus_id)
            live = ADS1115AIN0Bus(smbus, address=addr)
            live.read_ain0()
            return live
        except Exception:
            if smbus is not None:
                try:
                    smbus.close()
                except Exception:
                    pass
            return None

    def read_all(self) -> Dict[str, Any]:
        if not self._connected or self._bus is None:
            raise RuntimeError("HardwareSensorReader not connected. Call connect() first.")
        try:
            raw = self._bus.read_ain0()
        except Exception:
            self._connected = False
            raise
        unit = adc_to_unit(raw, self._full_scale)
        now = time.perf_counter()
        return {
            "fsr": [unit, 0.0, 0.0, 0.0],  # AIN0 only
            "mpu": {"accel": [0.0, 0.0, 1.0], "gyro": [0.0, 0.0, 0.0]},
            "microphone": {"energy": 0.0, "onset": False},
            "dht22": {"ambient_temp": 0.0, "body_temp": 0.0},
            "ts": now,
        }

    def process(
        self,
        raw_data: Dict[str, Any] | None = None,
        detail_level: DetailLevel = DetailLevel.NORMAL,
    ) -> AbstractionOutput:
        if raw_data is None:
            if not self._connected:
                raw_data = {
                    "fsr": [0.0, 0.0, 0.0, 0.0],
                    "ts": time.perf_counter(),
                }
            else:
                raw_data = self.read_all()
        return AbstractionOutput(
            events=[],
            features=[],
            state_summary=None,
            ts=float(raw_data.get("ts", 0.0) or 0.0),
        )
