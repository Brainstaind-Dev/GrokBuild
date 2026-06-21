"""
Lightweight state machine helpers for reflexes.

For v1 we keep this very small:
- Per-reflex refractory timers
- Simple "active" state for sustained behaviors (tension, freeze)
- Global arousal "mode" that can bias which reflexes are allowed

More sophisticated hierarchical / concurrent state machines can be added later
without changing the primitive function signatures.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ReflexState:
    last_fired_ts: float = 0.0
    active_until: float = 0.0
    count: int = 0


class ReflexStateMachine:
    """
    Manages refractory periods and simple activation windows per reflex name.
    """

    def __init__(self, refractory_ms: Dict[str, int]) -> None:
        self.refractory = {k: v / 1000.0 for k, v in refractory_ms.items()}
        self.default_refractory = self.refractory.get("default", 0.12)
        self.states: Dict[str, ReflexState] = {}

    def _state(self, name: str) -> ReflexState:
        if name not in self.states:
            self.states[name] = ReflexState()
        return self.states[name]

    def can_fire(self, name: str, now: Optional[float] = None) -> bool:
        now = now or time.perf_counter()
        st = self._state(name)
        ref = self.refractory.get(name, self.default_refractory)
        return (now - st.last_fired_ts) >= ref

    def mark_fired(self, name: str, duration_ms: int, now: Optional[float] = None) -> None:
        now = now or time.perf_counter()
        st = self._state(name)
        st.last_fired_ts = now
        st.active_until = now + (duration_ms / 1000.0)
        st.count += 1

    def is_active(self, name: str, now: Optional[float] = None) -> bool:
        now = now or time.perf_counter()
        return now < self._state(name).active_until

    def get_modulators(self, now: Optional[float] = None) -> List[str]:
        """Return names of currently active sustained reflexes (for trace modulation info)."""
        now = now or time.perf_counter()
        return [name for name, st in self.states.items() if now < st.active_until]
