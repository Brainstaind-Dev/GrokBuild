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
from .extract_tier1 import extract_tier1, fsr_to_unit


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
        force_fsr = c.get("force_fsr")
        if force_fsr is not None:
            self.force_raw({"fsr": [float(force_fsr), 0.0, 0.0, 0.0]})

    def bind_backend(self, backend: Any) -> None:
        """Pad-Read: HardwareSensorReader (fake bus or live chip). Same read_all() shape as Virtual."""
        self._backend = backend

    def bind_feel_cache(self, setter: Callable[[List[Any]], None]) -> None:
        """Same poll writes feel-cache. No second Sensor. No twin."""
        self._feel_cache = setter

    def force_raw(self, raw: Optional[Mapping[str, Any]]) -> None:
        """Bench inject in unit [0, 1]. None clears. Out-of-range FSR saturates; never leaks raw."""
        if raw is None:
            self._forced = None
            return
        d = dict(raw)
        fsr = d.get("fsr")
        if isinstance(fsr, (list, tuple)):
            units: List[float] = []
            for x in fsr:
                u = fsr_to_unit(x)
                units.append(0.0 if u is None else u)
            while len(units) < 4:
                units.append(0.0)
            d["fsr"] = units[:4]
        self._forced = d

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
    v = fsr_to_unit(fsr[0])
    if v is None or v <= threshold:
        return []
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


def merge_feel_cache(physical: List[Any], virtual: List[Any], max_count: int = 3) -> List[Any]:
    """Physical Tick-Door / Pad-Read first; virtual theater fills remaining slots. No twin."""
    n = max(0, int(max_count))
    merged: List[Any] = list(physical or [])
    for s in virtual or []:
        if len(merged) >= n:
            break
        merged.append(s)
    return merged[:n]
