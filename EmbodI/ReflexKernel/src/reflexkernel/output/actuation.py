"""
Actuation hub.

In v1 this is purely virtual:
- Collects ReflexActions
- Maintains a very simple "virtual muscle / expression" state that the visualizer can read
- Later: real hardware drivers will subclass or be plugged in here.

The kernel and higher intelligence can also query current "body state".
"""

from __future__ import annotations

from typing import Dict, List

from ..config import OutputConfig
from ..types import ReflexAction, ReflexKind


class VirtualBody:
    """Extremely simplified simulated physiology + expression parameters."""

    def __init__(self) -> None:
        self.heart_rate = 0.38
        self.muscle_tone = 0.28
        self.breath_rate = 0.42
        self.tension = 0.0          # shoulders / torso
        self.face_tension = 0.0
        self.blink = 0.0
        self.head_orient = "center"
        self.last_update = 0.0

    def apply(self, action: ReflexAction) -> None:
        p = action.params or {}
        kind = action.kind.value if hasattr(action.kind, "value") else str(action.kind)
        i = float(action.intensity)

        if kind == "autonomic":
            self.heart_rate = 0.3 * self.heart_rate + 0.7 * p.get("heart_rate", self.heart_rate)
            self.muscle_tone = 0.4 * self.muscle_tone + 0.6 * p.get("muscle_tone", self.muscle_tone)
            self.breath_rate = 0.5 * self.breath_rate + 0.5 * p.get("breath_depth", self.breath_rate)
        elif kind == "tension":
            self.tension = max(self.tension, i * 0.9)
            self.face_tension = max(self.face_tension, i * 0.6)
        elif kind == "flinch":
            self.tension = min(1.0, self.tension + i * 0.7)
            self.face_tension = min(1.0, self.face_tension + i * 0.85)
        elif kind == "blink":
            self.blink = min(1.0, i)
        elif kind == "orient":
            self.head_orient = p.get("direction", "center")
        elif kind == "freeze":
            self.tension = max(self.tension, i * 0.6)
            self.muscle_tone = min(0.95, self.muscle_tone + i * 0.3)

        # Natural relaxation toward baseline over time is done by decay() below

    def decay(self, dt: float) -> None:
        # Homeostatic return to calm
        self.tension = max(0.0, self.tension - dt * 1.8)
        self.face_tension = max(0.0, self.face_tension - dt * 2.2)
        self.blink = max(0.0, self.blink - dt * 6.0)
        self.heart_rate = 0.92 * self.heart_rate + 0.08 * 0.38
        self.muscle_tone = 0.95 * self.muscle_tone + 0.05 * 0.28
        self.breath_rate = 0.93 * self.breath_rate + 0.07 * 0.42


class ActuationHub:
    def __init__(self, config: OutputConfig) -> None:
        self.cfg = config
        self.body = VirtualBody()
        self._last_decay = 0.0

    def apply(self, actions: List[ReflexAction]) -> None:
        now = 0.0
        try:
            import time

            now = time.perf_counter()
        except Exception:
            pass

        for a in actions:
            self.body.apply(a)

        # Decay between calls
        if self._last_decay:
            self.body.decay(max(0.01, now - self._last_decay))
        self._last_decay = now

    def get_body_state(self) -> Dict[str, float | str]:
        return {
            "heart_rate": round(self.body.heart_rate, 3),
            "muscle_tone": round(self.body.muscle_tone, 3),
            "breath_rate": round(self.body.breath_rate, 3),
            "tension": round(self.body.tension, 3),
            "face_tension": round(self.body.face_tension, 3),
            "blink": round(self.body.blink, 3),
            "head_orient": self.body.head_orient,
        }
