"""Sensory Cortex facade — HI packaging + temporal memory + RK command shaping."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .config import config_to_dict
from .memory import EmbodiedMemory
from .schemas import SensoryUpdate
from .summarizer import Summarizer
from .translator import Translator


class SensoryCortex:
    """
    Complementary layer above ReflexKernel Abstraction + Coherence.

    - Accept already-coherent sensations / body state
    - Add temporal continuity (memory, trends, deltas)
    - Package experience for higher intelligence
    - Shape and optionally dispatch thought seeds / rewards / demos to RK
    """

    def __init__(
        self,
        config: Dict[str, Any] | Any | None = None,
        mode: str = "embedded",
    ):
        cfg = config_to_dict(config)
        self.mode = mode or str(
            (cfg.get("interface") or {}).get("mode", "embedded")
        )
        self.config = cfg

        summ_cfg = dict(cfg.get("summarizer") or {})
        # Resolve alias
        if summ_cfg.get("max_sensations_per_update") is None and summ_cfg.get(
            "max_stimuli_per_update"
        ):
            summ_cfg["max_sensations_per_update"] = summ_cfg["max_stimuli_per_update"]

        mem_cfg = cfg.get("memory") or {}
        self.summarizer = Summarizer(summ_cfg)
        self.memory = EmbodiedMemory(
            short_term_window=int(mem_cfg.get("short_term_window", 12)),
            max_history=int(mem_cfg.get("max_history", 80)),
        )
        self.translator = Translator(cfg.get("translator") or {})

        iface = cfg.get("interface") or {}
        self.min_interval = float(iface.get("min_interval_seconds", 0.4))
        self.force_on_reflex = bool(iface.get("force_on_reflex", True))
        self.force_arousal_delta = float(iface.get("force_arousal_delta", 0.12))
        self.auto_dispatch = bool(
            (cfg.get("translator") or {}).get("auto_dispatch", True)
        )

        self._reflex_api: Any = None
        self._last_emit_mono: float = 0.0
        self._prev_arousal: Optional[float] = None

    # ------------------------------------------------------------------
    # Binding (embedded low-latency path)
    # ------------------------------------------------------------------

    def bind_reflex(self, api: Any) -> "SensoryCortex":
        """
        Bind a PythonAPI-like object (inject_thought, reward, begin_demo, end_demo).

        Embedded hosts should call this once; translator will dispatch when
        auto_dispatch is enabled.
        """
        self._reflex_api = api
        return self

    @property
    def reflex_api(self) -> Any:
        return self._reflex_api

    # ------------------------------------------------------------------
    # Emission gating (token + latency hygiene)
    # ------------------------------------------------------------------

    def should_emit(self, coherent_data: Dict[str, Any], *, force: bool = False) -> bool:
        """
        Salience / rate gate for HI updates.

        Always True when force=True. Otherwise:
        - force on non-autonomic reflex activity
        - force on large arousal jump vs last stored experience
        - else require min_interval since last emit
        """
        if force:
            return True

        now = time.monotonic()
        reflexes = [
            str(r).lower()
            for r in (coherent_data.get("reflex_activity") or [])
        ]
        non_auto = [r for r in reflexes if r and r != "autonomic"]
        if self.force_on_reflex and non_auto:
            return True

        aff = coherent_data.get("affective") or {}
        body = coherent_data.get("body_state") or {}
        arousal = float(
            aff.get("arousal", body.get("arousal_estimate", 0.0)) or 0.0
        )
        if self._prev_arousal is not None:
            if abs(arousal - self._prev_arousal) >= self.force_arousal_delta:
                return True
        if coherent_data.get("arousal_increased") or coherent_data.get(
            "new_contact"
        ):
            # Soft force for meaningful deltas
            if now - self._last_emit_mono >= min(0.15, self.min_interval):
                return True

        if now - self._last_emit_mono < self.min_interval:
            return False
        return True

    # ------------------------------------------------------------------
    # Incoming coherent data from ReflexKernel
    # ------------------------------------------------------------------

    def process_coherent_input(
        self,
        coherent_data: Dict[str, Any],
        *,
        force: bool = True,
        respect_gate: bool = False,
    ) -> Optional[SensoryUpdate]:
        """
        Main entry: already-coherent RK sensations + body state → SensoryUpdate.

        By default always processes (force=True). Set respect_gate=True to honor
        should_emit (returns None when throttled).
        """
        if respect_gate and not self.should_emit(coherent_data, force=force):
            return None

        # Enrich delta helpers from memory if missing
        data = dict(coherent_data)
        if self._prev_arousal is not None and "arousal_increased" not in data:
            body = data.get("body_state") or {}
            aff = data.get("affective") or {}
            arousal = float(
                aff.get("arousal", body.get("arousal_estimate", 0.0)) or 0.0
            )
            data["arousal_increased"] = (arousal - self._prev_arousal) >= 0.08
            data["arousal_decreased"] = (self._prev_arousal - arousal) >= 0.08

        update = self.summarizer.summarize(data)
        # Trend includes history before this store, then we store (current becomes part of next)
        # Include a post-store trend on the object for HI convenience:
        self.memory.update(update)
        update.trend = self.memory.get_trend_summary()

        self._last_emit_mono = time.monotonic()
        self._prev_arousal = update.affective_core.arousal
        return update

    # Backward-compatible alias for early travel drafts / service stubs
    def process_stimulus(self, data: Dict[str, Any]) -> Optional[SensoryUpdate]:
        """Deprecated name — routes to process_coherent_input."""
        return self.process_coherent_input(data)

    def get_current_experience(self) -> Optional[SensoryUpdate]:
        return self.memory.get_current_state()

    def get_recent_context(self, count: int = 4) -> List[SensoryUpdate]:
        return self.memory.get_recent_context(count)

    def get_trend(self) -> str:
        return self.memory.get_trend_summary()

    # ------------------------------------------------------------------
    # Higher intelligence → Body
    # ------------------------------------------------------------------

    def inject_thought(
        self,
        emotion: str,
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5,
        text: str = "",
        *,
        dispatch: Optional[bool] = None,
    ) -> Dict[str, Any]:
        thought = {
            "emotion": emotion,
            "intensity": intensity,
            "valence": valence,
            "arousal": arousal,
            "text": text,
        }
        current_state = self.memory.get_current_state()
        command = self.translator.to_reflexkernel(thought, current_state)
        do_dispatch = self.auto_dispatch if dispatch is None else dispatch
        if do_dispatch and self._reflex_api is not None:
            return self.translator.dispatch(command, self._reflex_api)
        return {"command": command, "dispatched": False, "ack": None}

    def send_reward(
        self,
        value: float,
        reason: str = "",
        window_steps: int = 6,
        *,
        dispatch: Optional[bool] = None,
    ) -> Dict[str, Any]:
        command = self.translator.to_reward(value, reason, window_steps)
        do_dispatch = self.auto_dispatch if dispatch is None else dispatch
        if do_dispatch and self._reflex_api is not None:
            return self.translator.dispatch(command, self._reflex_api)
        return {"command": command, "dispatched": False, "ack": None}

    def begin_demonstration(
        self, name: str, *, dispatch: Optional[bool] = None
    ) -> Dict[str, Any]:
        command = self.translator.to_demonstration(name, action="begin")
        do_dispatch = self.auto_dispatch if dispatch is None else dispatch
        if do_dispatch and self._reflex_api is not None:
            return self.translator.dispatch(command, self._reflex_api)
        return {"command": command, "dispatched": False, "ack": None}

    def end_demonstration(
        self,
        name: str = "",
        outcome: Optional[Dict[str, Any]] = None,
        *,
        dispatch: Optional[bool] = None,
    ) -> Dict[str, Any]:
        command = self.translator.to_demonstration(name or "demo", action="end")
        if outcome is not None:
            command["outcome"] = outcome
        do_dispatch = self.auto_dispatch if dispatch is None else dispatch
        if do_dispatch and self._reflex_api is not None:
            return self.translator.dispatch(command, self._reflex_api)
        return {"command": command, "dispatched": False, "ack": None}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def recall(self, max_age_minutes: int = 20) -> List[SensoryUpdate]:
        thr = float(
            (self.config.get("memory") or {}).get("high_arousal_threshold", 0.62)
        )
        return self.memory.recall_relevant(
            max_age_minutes=max_age_minutes, high_arousal_threshold=thr
        )

    def status(self) -> Dict[str, Any]:
        current = self.memory.get_current_state()
        return {
            "mode": self.mode,
            "bound": self._reflex_api is not None,
            "memory_size": len(self.memory.short_term),
            "last_update": current.timestamp.isoformat() if current else None,
            "current_mood": current.affective_core.overall_mood if current else None,
            "trend": self.get_trend(),
        }
