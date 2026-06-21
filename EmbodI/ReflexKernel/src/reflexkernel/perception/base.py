"""
Perception base classes and registry.

Design:
- Every sensor implements a small interface (start / stop / poll / collect).
- Sensors are polled every kernel tick (cheap) or run background threads for real hardware.
- All output is normalized to Stimulus objects.
- Registry makes enabling/disabling via config trivial and supports future hot-plug.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..types import Modality, Stimulus


class Sensor(ABC):
    """Abstract base for all perception sources."""

    name: str = "base"
    modality: Modality | str = Modality.OTHER

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self._running = False

    def start(self) -> None:
        """Start background threads, open devices, etc. Idempotent."""
        self._running = True

    def stop(self) -> None:
        """Stop cleanly. Idempotent."""
        self._running = False

    @abstractmethod
    def poll(self) -> List[Stimulus]:
        """
        Return zero or more new Stimulus events since last poll.
        Must be cheap and non-blocking.
        """
        ...

    def collect(self) -> List[Stimulus]:
        """Convenience wrapper that respects running state."""
        if not self._running:
            return []
        return self.poll()


class SensorRegistry:
    """
    Simple registry + batch collector.

    The kernel uses this to treat all sensors uniformly.
    """

    def __init__(self) -> None:
        self._sensors: Dict[str, Sensor] = {}

    def register(self, name: str, sensor: Sensor) -> None:
        sensor.name = name
        self._sensors[name] = sensor

    def get(self, name: str) -> Optional[Sensor]:
        return self._sensors.get(name)

    def start_all(self) -> None:
        for s in self._sensors.values():
            s.start()

    def stop_all(self) -> None:
        for s in self._sensors.values():
            s.stop()

    def collect_all(self) -> List[Stimulus]:
        out: List[Stimulus] = []
        for name, sensor in self._sensors.items():
            try:
                stims = sensor.collect()
                for st in stims:
                    if not st.source or st.source == "unknown":
                        st.source = name
                    out.append(st)
            except Exception as exc:
                # Never let a bad sensor kill the kernel
                print(f"[perception] sensor {name} error: {exc}")
        return out

    @property
    def active(self) -> List[str]:
        return list(self._sensors.keys())
