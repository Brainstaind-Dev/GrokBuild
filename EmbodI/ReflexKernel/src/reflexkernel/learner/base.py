"""
Learner Module — imitation + reinforcement for ReflexKernel.

Current implementation (v0.1, deliberately simple & inspectable):

Imitation:
- Record full DemonstrationStep sequences.
- On "teach", extract (stimulus_signature, preferred_action) exemplars.
- At runtime, compute cheap similarity (kind match + intensity + simple embedding of kind strings)
  and if above threshold, emit the teacher action (behavioral cloning lite).

Reinforcement:
- Higher intelligence sends RewardSignal.
- We maintain per-reflex bias values (positive or negative) that ReflexCore reads.
- Simple exponential moving update.

Future upgrades (easy to add without breaking API):
- Store actual numpy feature vectors per exemplar.
- Train tiny decision tree or 1-layer net (numpy or sklearn).
- Multi-behavior library with retrieval.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np  # always available (core dep)

from ..config import LearnerConfig
from ..types import AffectiveContext, DemonstrationStep, ReflexAction, ReflexTrace, RewardSignal, Stimulus
from .store import LearnerStore


def _stim_signature(stim: Stimulus) -> str:
    kind = str((stim.data or {}).get("kind", stim.modality)).lower()[:24]
    return f"{stim.modality}:{kind}"


def _demo_to_exemplar(step: DemonstrationStep) -> Optional[Dict[str, Any]]:
    if not step.teacher_action:
        return None
    sigs = [_stim_signature(s) for s in step.stimuli]
    # Very cheap "feature": bag of stimulus kinds + arousal bucket
    arousal_bucket = int(step.context.arousal * 5)
    return {
        "sigs": sigs,
        "arousal_b": arousal_bucket,
        "action": step.teacher_action.to_dict(),
        "ts": step.ts,
    }


class Learner:
    def __init__(self, config: LearnerConfig, logger: Optional[object] = None) -> None:
        self.cfg = config
        self.logger = logger
        self.store = LearnerStore(config.store_path)

        # In-memory exemplars for fast lookup (loaded + new)
        self.exemplars: Dict[str, List[Dict[str, Any]]] = {}  # behavior_name -> list
        self._load_existing_demos()

        # Current reflex biases (synced with store)
        self.reflex_biases: Dict[str, float] = self.store.all_biases()

        self._attached_reflex_core: Optional[Any] = None

    def _load_existing_demos(self) -> None:
        for meta in self.store.list_demonstrations():
            # For v0 we don't auto-replay full history into memory on every start.
            # We only keep behaviors that were explicitly "taught" (see put_behavior).
            pass

    def attach_reflex_core(self, core: Any) -> None:
        """Give learner a handle so it can push bias updates directly."""
        self._attached_reflex_core = core
        # Push any persisted biases at attach time
        if core and hasattr(core, "set_modulation"):
            for name, bias in self.reflex_biases.items():
                core.set_modulation(name, bias)

    # ------------------------------------------------------------------
    # Imitation learning
    # ------------------------------------------------------------------

    def ingest_demonstration(
        self, name: str, steps: List[DemonstrationStep], outcome: Dict[str, Any]
    ) -> None:
        if not self.cfg.imitation.enabled or not steps:
            return

        path = self.store.save_demonstration(name, steps, outcome)
        if self.logger:
            self.logger.info("[learner] saved demo '%s' → %s (%d steps)", name, path, len(steps))

        # Extract exemplars
        exs: List[Dict[str, Any]] = []
        for step in steps:
            ex = _demo_to_exemplar(step)
            if ex:
                exs.append(ex)

        if exs:
            self.exemplars[name] = exs
            # Also record as a "behavior" the system can retrieve later
            self.store.put_behavior(
                name,
                {
                    "type": "imitation_exemplars",
                    "num_exemplars": len(exs),
                    "similarity_threshold": self.cfg.imitation.similarity_threshold,
                },
            )
            if self.logger:
                self.logger.info("[learner] behavior '%s' registered with %d exemplars", name, len(exs))

    def _similarity(self, current_sigs: List[str], arousal_b: int, ex: Dict[str, Any]) -> float:
        # Jaccard on kind signatures + small arousal match bonus
        set_cur = set(current_sigs)
        set_ex = set(ex["sigs"])
        if not set_cur or not set_ex:
            return 0.0
        inter = len(set_cur & set_ex)
        uni = len(set_cur | set_ex)
        jacc = inter / max(1, uni)
        a_match = 1.0 - (abs(arousal_b - ex.get("arousal_b", arousal_b)) / 6.0)
        return 0.6 * jacc + 0.4 * max(0.0, a_match)

    def maybe_clone_action(
        self, stimuli: List[Stimulus], context: AffectiveContext
    ) -> Optional[ReflexAction]:
        """If the current situation is similar enough to a taught demonstration, return the taught action."""
        if not self.cfg.imitation.enabled or not self.exemplars:
            return None

        sigs = [_stim_signature(s) for s in stimuli]
        a_b = int(context.arousal * 5)
        thresh = self.cfg.imitation.similarity_threshold

        best_score = 0.0
        best_action = None
        best_name = None

        for name, ex_list in self.exemplars.items():
            for ex in ex_list[-self.cfg.imitation.max_exemplars_per_behavior :]:
                sc = self._similarity(sigs, a_b, ex)
                if sc > best_score and sc >= thresh:
                    best_score = sc
                    best_action = ReflexAction(**ex["action"])  # reconstruct
                    best_name = name

        if best_action:
            best_action.source = "learned"
            if self.logger:
                self.logger.info("[learner] cloned action from '%s' (sim=%.2f)", best_name, best_score)
            return best_action
        return None

    # ------------------------------------------------------------------
    # Reinforcement learning (bias modulation)
    # ------------------------------------------------------------------

    def receive_reward(self, reward: RewardSignal) -> None:
        if not self.cfg.reinforcement.enabled:
            return

        self.store.append_reward(reward)

        # Very simple credit assignment: if recent traces involved certain reflexes,
        # nudge their bias in the direction of the reward.
        # In a real system we would look at the actual ReflexTraces from the last N ticks.
        # Here we do a cheap global update to any reflex that has a non-zero bias or was recently active.
        lr = self.cfg.reinforcement.learning_rate
        delta = reward.value * lr * (1.0 if reward.value > 0 else 0.6)

        # Update all known biases a little (very naive but works for demo)
        for name in list(self.reflex_biases.keys()) or ["flinch", "tension", "blink"]:
            new_bias = self.store.update_reflex_bias(name, delta, lr=0.6)
            self.reflex_biases[name] = new_bias
            if self._attached_reflex_core and hasattr(self._attached_reflex_core, "set_modulation"):
                self._attached_reflex_core.set_modulation(name, new_bias)

        if self.logger:
            self.logger.info("[learner] reward %.3f applied (biases updated)", reward.value)

    # ------------------------------------------------------------------
    # Observation hook (called by kernel every tick)
    # ------------------------------------------------------------------

    def observe(
        self,
        stimuli: List[Stimulus],
        context: AffectiveContext,
        actions: List[ReflexAction],
        traces: List[ReflexTrace],
    ) -> None:
        """
        The kernel calls this every step so the learner can:
        - Record for future imitation (if demo active — handled in kernel)
        - Potentially override or inject learned actions (done in kernel after this call)
        - Update internal statistics
        """
        # We currently do most work via explicit ingest_demonstration + receive_reward.
        # This hook is here for future online learning or eligibility traces.
        pass

    # ------------------------------------------------------------------
    # Public query surface
    # ------------------------------------------------------------------

    def get_biases(self) -> Dict[str, float]:
        return dict(self.reflex_biases)

    def get_behaviors(self) -> Dict[str, Any]:
        return {k: self.store.get_behavior(k) for k in self.store._params.get("behaviors", {})}
