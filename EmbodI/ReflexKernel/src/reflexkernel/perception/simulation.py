"""
SimulationSensor — the primary sensor for development, demos, and testing.

Features:
- Auto-generated "ambient" events (random-ish motion, breathing, small sounds)
- Interactive keyboard injection (when running in a terminal)
- Explicit programmatic injection for higher-intelligence or test harnesses
- Produces varied, believable stimuli that exercise the whole stack
"""

from __future__ import annotations

import random
import time
from typing import Dict, List, Optional

from ..types import Modality, Stimulus
from .base import Sensor


class SimulationSensor(Sensor):
    name = "simulation"
    modality = Modality.SIM

    # Canonical interactive stimulus map (extend as needed)
    KEY_MAP: Dict[str, Dict[str, any]] = {
        "s": {"kind": "sudden_sound", "intensity": 0.95, "desc": "loud sharp noise"},
        "l": {"kind": "loud_noise", "intensity": 0.75, "desc": "sustained loud sound"},
        "m": {"kind": "motion_periphery", "intensity": 0.6, "desc": "sudden movement at edge of view"},
        "f": {"kind": "threat_face", "intensity": 0.85, "desc": "sudden face-like shape approaching"},
        "c": {"kind": "close_approach", "intensity": 0.7, "desc": "object coming straight at us"},
        "t": {"kind": "touch_shoulder", "intensity": 0.55, "desc": "unexpected touch on shoulder"},
        "h": {"kind": "harsh_light", "intensity": 0.65, "desc": "bright flash / harsh light"},
        "q": {"kind": "calm", "intensity": 0.15, "desc": "quiet calm moment"},
        "r": {"kind": "relaxing_sound", "intensity": 0.25, "desc": "soft pleasant sound"},
        "w": {"kind": "friendly_wave", "intensity": 0.4, "desc": "friendly human wave / greeting"},
    }

    def __init__(self, config: Optional[dict | object] = None) -> None:
        super().__init__(config)
        self._last_auto = time.perf_counter()
        self._pending: List[Stimulus] = []
        c = self.config if isinstance(self.config, dict) else (self.config.model_dump() if hasattr(self.config, "model_dump") else dict(self.config or {}))
        self._interactive = bool(c.get("interactive", True))
        self._auto = bool(c.get("auto_events", True))
        self._interval = float(c.get("auto_event_interval_s", 3.5))
        self._rng = random.Random(42)  # deterministic unless reseeded

    def inject(self, kind: str, intensity: float = 0.7, extra: Optional[Dict] = None) -> Stimulus:
        """Programmatically inject a stimulus (used by demos, interfaces, tests)."""
        data = {
            "kind": kind,
            "intensity": float(intensity),
            "sim": True,
        }
        if extra:
            data.update(extra)
        stim = Stimulus(
            modality=Modality.SIM,
            data=data,
            confidence=0.95,
            source="simulation",
        )
        self._pending.append(stim)
        return stim

    def inject_from_key(self, key: str) -> Optional[Stimulus]:
        key = key.lower().strip()
        if key not in self.KEY_MAP:
            return None
        spec = self.KEY_MAP[key]
        return self.inject(
            kind=spec["kind"],
            intensity=spec["intensity"],
            extra={"desc": spec.get("desc", ""), "via": "keyboard"},
        )

    def poll(self) -> List[Stimulus]:
        out: List[Stimulus] = []
        now = time.perf_counter()

        # Drain any pending programmatic injections first
        if self._pending:
            out.extend(self._pending)
            self._pending.clear()

        # Auto events (ambient life)
        if self._auto and (now - self._last_auto) > self._interval:
            self._last_auto = now
            auto = self._generate_auto_event()
            if auto:
                out.append(auto)

        # Interactive keyboard (best-effort, non-blocking)
        if self._interactive:
            stim = self._try_read_key()
            if stim:
                out.append(stim)

        return out

    # ------------------------------------------------------------------
    # Internal generators
    # ------------------------------------------------------------------

    def _generate_auto_event(self) -> Optional[Stimulus]:
        # Gentle ambient variety
        roll = self._rng.random()
        if roll < 0.25:
            return self.inject("ambient_motion", intensity=0.18 + self._rng.random() * 0.15)
        if roll < 0.45:
            return self.inject("soft_sound", intensity=0.12 + self._rng.random() * 0.18)
        if roll < 0.60:
            return self.inject("breathing", intensity=0.22)
        if roll < 0.75:
            return self.inject("micro_movement", intensity=0.1 + self._rng.random() * 0.1)
        # occasionally nothing — feels more natural
        return None

    def _try_read_key(self) -> Optional[Stimulus]:
        """
        Best-effort non-blocking single key read.

        On Windows we use msvcrt (no echo).
        On Unix we fall back to a very short timeout select (may still block slightly in some envs).
        If nothing is available we return None quickly.
        """
        try:
            import msvcrt  # Windows

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                return self.inject_from_key(ch)
            return None
        except Exception:
            pass

        # POSIX / fallback — try very short select
        try:
            import select
            import sys

            if select.select([sys.stdin], [], [], 0.0)[0]:
                ch = sys.stdin.read(1)
                return self.inject_from_key(ch)
        except Exception:
            pass

        return None
