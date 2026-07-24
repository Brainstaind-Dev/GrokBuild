"""Embodied memory: temporal continuity over coherent SensoryUpdate packages."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import List, Optional

from .schemas import SensoryUpdate


class EmbodiedMemory:
    """
    Temporal continuity only — no sensory fusion.
    Short-term window, medium history, arousal trend, high-arousal recall.
    """

    def __init__(self, short_term_window: int = 12, max_history: int = 80):
        self.short_term: deque[SensoryUpdate] = deque(maxlen=short_term_window)
        self.history: List[SensoryUpdate] = []
        self.max_history = max_history
        self.last_update: Optional[datetime] = None

    def update(self, update: SensoryUpdate) -> None:
        self.short_term.append(update)
        self.history.append(update)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.last_update = update.timestamp

    def get_current_state(self) -> Optional[SensoryUpdate]:
        return self.short_term[-1] if self.short_term else None

    def get_recent_context(self, count: int = 4) -> List[SensoryUpdate]:
        return list(self.short_term)[-count:]

    def get_trend_summary(self) -> str:
        if len(self.short_term) < 3:
            return "Insufficient history for trend"

        recent_arousal = [u.affective_core.arousal for u in self.short_term]
        delta = recent_arousal[-1] - recent_arousal[0]

        if delta > 0.18:
            return "rising arousal"
        if delta < -0.18:
            return "falling arousal"
        return "relatively stable"

    def last_arousal(self) -> Optional[float]:
        cur = self.get_current_state()
        return cur.affective_core.arousal if cur else None

    def recall_relevant(
        self,
        max_age_minutes: int = 20,
        high_arousal_threshold: float = 0.62,
    ) -> List[SensoryUpdate]:
        if not self.history:
            return []
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        relevant = [
            u
            for u in self.history
            if u.timestamp >= cutoff and u.affective_core.arousal > high_arousal_threshold
        ]
        return relevant[-6:]

    def clear(self) -> None:
        self.short_term.clear()
        self.history.clear()
        self.last_update = None
