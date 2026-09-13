"""
HardwareSensor — Tick-Door seat.

A real Perception `Sensor` so one poll hits kernel.step.
Physical reader is optional; missing chip / missing bus → empty poll (fail_open).
Tests inject raw packets via `force_raw` (no board).
Pad-Read (B): bind_backend(HardwareSensorReader); same poll updates feel-cache.
"""

from __future__ import annotations

import math
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
        self._afterglow_tau_s = float(c.get("afterglow_tau_s", 1.5))
        self._afterglow = 0.0
        self._afterglow_ts: Optional[float] = None
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

    def _advance_afterglow(self, fast: float, now: float) -> float:
        """Instant attack, exponential release. Same [0, 1] unit as Stimulus.value."""
        tau = max(1e-6, self._afterglow_tau_s)
        prev_ts = self._afterglow_ts
        self._afterglow_ts = now
        if fast >= self._afterglow:
            self._afterglow = fast
        elif prev_ts is not None:
            dt = max(0.0, now - prev_ts)
            self._afterglow *= math.exp(-dt / tau)
        if self._afterglow < 1e-3:
            self._afterglow = 0.0
        return self._afterglow

    def poll(self) -> List[Stimulus]:
        try:
            raw = self._read_raw()
            now = time.perf_counter()
            fast = 0.0
            if raw:
                fsr = raw.get("fsr") or []
                if isinstance(fsr, (list, tuple)) and fsr:
                    u = fsr_to_unit(fsr[0])
                    fast = 0.0 if u is None else u
            glow = self._advance_afterglow(fast, now)
            if not raw and glow <= self._fsr_threshold:
                if self._feel_cache is not None:
                    self._feel_cache([])
                return []
            packet: Dict[str, Any] = dict(raw) if raw else {"fsr": [fast, 0.0, 0.0, 0.0]}
            fsr = list(packet.get("fsr") or [fast, 0.0, 0.0, 0.0])
            while len(fsr) < 4:
                fsr.append(0.0)
            fsr[0] = fast
            packet["fsr"] = fsr
            packet["afterglow"] = glow
            stims = extract_tier1(
                packet, source=self.name, fsr_threshold=self._fsr_threshold
            )
            if self._feel_cache is not None:
                self._feel_cache(_feel_from_raw(packet, threshold=self._fsr_threshold))
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
    fast = fsr_to_unit(fsr[0])
    if fast is None:
        fast = 0.0
    glow = fsr_to_unit(raw.get("afterglow"))
    if glow is None:
        glow = fast
    felt = max(fast, glow)
    if felt <= threshold:
        return []
    lingering = fast <= threshold < felt
    return [
        Sensation(
            description=(
                f"Afterglow at the sternum ({felt:.2f})."
                if lingering
                else f"Pressure at the sternum ({felt:.2f})."
            ),
            zone="torso_front",
            intensity=felt,
            category=SensationCategory.CONTACT_PRESSURE,
            temporal_quality=(
                TemporalQuality.LINGERING if lingering else TemporalQuality.SUSTAINED
            ),
            source_features=["fsr.0"],
            ts=float(raw.get("ts") or time.perf_counter()),
            confidence=felt,
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
