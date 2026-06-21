"""
ReflexCore — the fast involuntary pathway.

Responsibilities:
- Owns the registry of enabled primitive reflexes
- Runs a tiny state machine for refractory periods
- Modulates reflex strength using current AffectiveContext
- Returns both the actions to execute and rich ReflexTrace objects for logging + learning
- Provides hooks for the Learner to temporarily boost/suppress specific reflexes
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

from ..config import ReflexConfig
from ..types import AffectiveContext, ReflexAction, ReflexTrace, Stimulus
from .primitives import PRIMITIVES
from .state_machines import ReflexStateMachine


class ReflexCore:
    def __init__(self, config: ReflexConfig, logger: object = None) -> None:
        self.cfg = config
        self.logger = logger
        self.state_machine = ReflexStateMachine(config.refractory_period_ms)

        # Which primitives are active this run
        self.enabled: Dict[str, callable] = {}
        for name in config.enabled_primitives:
            if name in PRIMITIVES:
                self.enabled[name] = PRIMITIVES[name]
            else:
                if logger:
                    logger.warning("Unknown reflex primitive requested: %s", name)

        # Learner can inject temporary bias: { "flinch": 0.3, "tension": -0.15, ... }
        self._modulation: Dict[str, float] = {}

    def set_modulation(self, name: str, delta: float) -> None:
        """Called by Learner when it wants to temporarily change sensitivity of a reflex."""
        self._modulation[name] = delta

    def clear_modulation(self, name: str | None = None) -> None:
        if name is None:
            self._modulation.clear()
        else:
            self._modulation.pop(name, None)

    def react(
        self, stimuli: List[Stimulus], context: AffectiveContext
    ) -> Tuple[List[ReflexAction], List[ReflexTrace]]:
        """
        Main entrypoint. Called every kernel tick (or on important stimulus arrival).

        Returns (actions_to_execute, traces_for_logging_and_learning)
        """
        now = time.perf_counter()
        all_actions: List[ReflexAction] = []
        traces: List[ReflexTrace] = []

        modulators = self.state_machine.get_modulators(now)

        for name, func in self.enabled.items():
            if not self.state_machine.can_fire(name, now):
                continue

            # Run the primitive
            actions, trigger = func(stimuli, context)
            if not actions or not trigger:
                continue

            # Apply base sensitivity + affective modulation
            modulated = []
            base_sens = self.cfg.base_sensitivity
            arousal_mult = 1.0 + (context.arousal - 0.35) * 0.8 if self.cfg.arousal_amplifies else 1.0
            valence_mult = 0.7 if (context.valence > 0.2 and self.cfg.valence_dampens_negative) else 1.0

            extra = self._modulation.get(name, 0.0)

            for a in actions:
                a.intensity = min(1.6, a.intensity * base_sens * arousal_mult * valence_mult + extra)
                if a.intensity < 0.12:
                    continue
                modulated.append(a)

            if not modulated:
                continue

            # Record trace
            latency = (now - context.ts) * 1000.0
            trace = ReflexTrace(
                name=name,
                trigger=trigger,
                actions=modulated,
                latency_ms=max(0.0, latency),
                affective_snapshot=context.to_dict(),
                modulated_by=modulators + (["learner"] if extra != 0 else []),
            )
            traces.append(trace)
            all_actions.extend(modulated)

            # Update state machine
            max_dur = max((a.duration_ms for a in modulated), default=150)
            self.state_machine.mark_fired(name, max_dur, now)

        return all_actions, traces
