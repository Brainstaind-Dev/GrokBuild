"""
HardwareSensor — Tick-Door seat.

A real Perception `Sensor` so one poll hits kernel.step.
Physical reader is optional; missing chip / missing bus → empty poll (fail_open).
Tests inject raw packets via `force_raw` (no board).
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

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
        self._backend: Any = None  # optional HardwareSensorReader later (Pad-Read)

    def bind_backend(self, backend: Any) -> None:
        """Optional physical reader (same read_all() shape as Virtual)."""
        self._backend = backend

    def force_raw(self, raw: Optional[Mapping[str, Any]]) -> None:
        """Test / bench inject. None clears."""
        self._forced = dict(raw) if raw is not None else None

    def _read_raw(self) -> Optional[Dict[str, Any]]:
        if self._forced is not None:
            return dict(self._forced)
        if self._backend is None:
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
            return extract_tier1(
                raw, source=self.name, fsr_threshold=self._fsr_threshold
            )
        except Exception:
            if not self._fail_open:
                raise
            return []
