"""
HardwareSensor — Tick-Door seat.

A real Perception `Sensor` so one poll hits kernel.step.
Physical reader is optional; missing chip / missing bus → empty poll (fail_open).
Tests inject raw packets via `force_raw` (no board).
Pad-Read (B): bind_backend(HardwareSensorReader); same poll updates feel-cache.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Mapping, Optional

from ..types import Modality, Stimulus
from .base import Sensor
from .extract_tier1 import extract_tier1


class HardwareSensor(Sensor):
    name = "hardware"
    modality = Modality.TOUCH

    def __init__(self, config: Optional[dict | object] = None) -> None:
        super().__init__(config)
        c = (
            self.config
            if isinstance(self.config, dict)
            else (
                self.config.model_dump()
                if hasattr(self.config, "model_dump")
                else dict(self.config or {})
            )
        )
        self._fail_open = bool(c.get("fail_open", True))
        self._fsr_threshold = float(c.get("fsr_threshold", 0.0))
        self._forced: Optional[Dict[str, Any]] = None
        self._backend: Any = None
        self._feel_cache: Optional[Callable[[List[Any]], None]] = None

    def bind_backend(self, backend: Any) -> None:
        """Pad-Read: HardwareSensorReader (fake bus or live chip). Same read_all() shape as Virtual."""
        self._backend = backend

    def bind_feel_cache(self, setter: Callable[[List[Any]], None]) -> None:
        """Same poll writes feel-cache. No second Sensor. No twin."""
        self._feel_cache = setter

    def force_raw(self, raw: Optional[Mapping[str, Any]]) -> None:
        """Test / bench inject. None clears."""
        self._forced = dict(raw) if raw is not None else None

    def _read_raw(self) -> Optional[Dict[str, Any]]:
        if self._forced is not None:
            return dict(self._forced)
        if self._backend is None:
            return None
        if hasattr(self._backend, "connected") and not self._backend.connected:
            return None
        try:
            if hasattr(self._backend, "read_all"):
                return dict(self._backend.read_all() or {})
        except Exception:
            if not self._fail_open:
                raise
            return None
        return None

    def poll(self) -> List[Stimulus]:
        try:
            raw = self._read_raw()
            if not raw:
                return []
            stims = extract_tier1(
                raw, source=self.name, fsr_threshold=self._fsr_threshold
            )
            if self._feel_cache is not None:
                self._feel_cache(_feel_from_raw(raw, threshold=self._fsr_threshold))
            return stims
        except Exception:
            if not self._fail_open:
                raise
            return []


def _feel_from_raw(raw: Mapping[str, Any], *, threshold: float = 0.0) -> List[Any]:
    """Sternum / torso_front sensation from the same AIN0 poll. No second extract fork."""
    try:
        from ..abstraction.schema import Sensation, SensationCategory, TemporalQuality
    except Exception:
        return []
    fsr = raw.get("fsr") or []
    if not isinstance(fsr, (list, tuple)) or not fsr:
        return []
    try:
        v = float(fsr[0])
    except (TypeError, ValueError):
        return []
    if v != v or v <= threshold:
        return []
    v = max(0.0, min(1.0, v))
    return [
        Sensation(
            description=f"Pressure at the sternum ({v:.2f}).",
            zone="torso_front",
            intensity=v,
            category=SensationCategory.CONTACT_PRESSURE,
            temporal_quality=TemporalQuality.SUSTAINED,
            source_features=["fsr.0"],
            ts=float(raw.get("ts") or time.perf_counter()),
            confidence=v,
        )
    ]
