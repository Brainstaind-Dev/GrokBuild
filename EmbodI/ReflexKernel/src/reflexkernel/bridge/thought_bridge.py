"""
Thought / Emotion Bridge.

This is the "interface between mind and body".

It:
- Accepts explicit thought/affective seeds from the higher intelligence (inject_seed)
- Runs pattern detectors over both seeds and raw stimuli
- Maintains a slowly decaying affective state
- Produces the canonical AffectiveContext consumed by ReflexCore + Learner
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..config import BridgeConfig
from ..types import AffectiveContext, Modality, Stimulus
from .pattern_detector import (
    PatternMatch,
    detect_from_stimuli,
    detect_sentiment,
    detect_with_embeddings,
    parse_structured_seed,
)


class ThoughtBridge:
    def __init__(self, config: BridgeConfig, logger: Optional[object] = None) -> None:
        self.cfg = config
        self.logger = logger
        self._pending_seeds: List[Dict[str, Any]] = []
        self._current_context = AffectiveContext(arousal=0.25)
        self._last_fusion_ts = time.perf_counter()

    def inject_seed(self, seed: Dict[str, Any]) -> None:
        """Called by kernel when higher intelligence sends a thought / emotion command."""
        self._pending_seeds.append(seed)

    def fuse(self, stimuli: List[Stimulus]) -> AffectiveContext:
        """
        Main entry point every kernel tick.

        Returns a (possibly updated) AffectiveContext.
        """
        now = time.perf_counter()
        ctx = self._current_context

        # 1. Natural decay (homeostasis)
        dt = max(0.001, now - self._last_fusion_ts)
        decay_a = self.cfg.fusion.arousal_decay_per_tick * dt * 20
        decay_v = self.cfg.fusion.valence_decay_per_tick * dt * 20
        ctx.arousal = max(0.05, ctx.arousal - decay_a)
        ctx.valence = ctx.valence * (1.0 - decay_v * 0.6)
        ctx.urgency = max(0.0, ctx.urgency * 0.7 - 0.03)

        # 2. Process any pending thought seeds (highest priority)
        seed_matches: List[PatternMatch] = []
        for seed in self._pending_seeds:
            seed_matches.extend(parse_structured_seed(seed))
            # Also allow raw text in seeds to go through optional ML
            if self.cfg.use_sentence_transformers and "text" in seed:
                seed_matches.extend(
                    detect_with_embeddings(str(seed["text"]), self.cfg.embedding_model)
                )
            if self.cfg.use_sentiment and "text" in seed:
                seed_matches.extend(detect_sentiment(str(seed["text"])))
        self._pending_seeds.clear()

        # 3. Fast detectors from real-world stimuli
        stim_matches = detect_from_stimuli(stimuli)

        # 4. Optional heavy embedding pass on any "thought" modality stimuli
        ml_matches: List[PatternMatch] = []
        if self.cfg.use_sentence_transformers:
            for s in stimuli:
                if s.modality in (Modality.THOUGHT, "thought") and "text" in (s.data or {}):
                    ml_matches.extend(detect_with_embeddings(str(s.data["text"]), self.cfg.embedding_model))

        all_matches = seed_matches + stim_matches + ml_matches

        # 5. Apply matches into context (weighted fusion)
        w_stim = self.cfg.fusion.stimulus_weight
        w_thought = self.cfg.fusion.thought_weight

        for m in all_matches:
            weight = w_thought if m.name.startswith("seed_") or m.name.startswith("embed_") else w_stim
            ctx.valence += m.valence_delta * weight * m.confidence * 0.6
            ctx.arousal += m.arousal_delta * weight * m.confidence * 0.55
            ctx.urgency += m.urgency * m.confidence * 0.4
            if m.name not in ctx.active_patterns:
                ctx.active_patterns.append(m.name)

        # Trim active patterns
        if len(ctx.active_patterns) > 8:
            ctx.active_patterns = ctx.active_patterns[-8:]

        # 6. Bring in salient raw stimuli (for reflexes + learning to inspect)
        ctx.salient_stimuli = (ctx.salient_stimuli + stimuli)[-self.cfg.fusion.max_salient_stimuli :]

        ctx.clamp()
        ctx.ts = now
        self._current_context = ctx
        self._last_fusion_ts = now

        return ctx

    @property
    def current_context(self) -> AffectiveContext:
        return self._current_context
