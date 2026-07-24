"""Summarizer: package already-coherent RK sensations for the higher intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .schemas import AffectiveCore, SalientSensation, SensoryUpdate


class Summarizer:
    """
    Does **not** re-do ReflexKernel Abstraction + Coherence fusion.

    - Accepts coherent sensations + body state
    - Adds light mood labels, ranking, delta packaging, token estimate
    - Preserves rich Sensation fields for the HI envelope
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        max_s = self.config.get("max_sensations_per_update")
        if max_s is None:
            max_s = self.config.get("max_stimuli_per_update", 3)
        self.max_sensations = int(max_s)
        self.salience_threshold = float(self.config.get("salience_threshold", 0.55))
        self.richness_rank_weight = float(self.config.get("richness_rank_weight", 0.15))
        self.enable_mood = bool(self.config.get("enable_mood_descriptors", True))

    def summarize(self, coherent_input: Dict[str, Any]) -> SensoryUpdate:
        timestamp = coherent_input.get("timestamp", datetime.now())
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)

        affective_core = self._build_affective_core(coherent_input)
        salient = self._extract_salient_sensations(coherent_input)
        reflex_activity = list(coherent_input.get("reflex_activity") or [])
        active_patterns = list(coherent_input.get("active_patterns") or [])

        delta = coherent_input.get("delta_from_last")
        if not delta:
            delta = self._generate_simple_delta(coherent_input)

        trend = coherent_input.get("trend", "")
        detail_level = str(coherent_input.get("detail_level", "normal"))

        token_estimate = self._estimate_tokens(affective_core, salient, delta, trend)

        return SensoryUpdate(
            timestamp=timestamp,
            affective_core=affective_core,
            salient_sensations=salient[: self.max_sensations],
            reflex_activity=reflex_activity,
            active_patterns=active_patterns,
            delta_from_last=delta,
            trend=trend,
            token_estimate=token_estimate,
            detail_level=detail_level,
        )

    def _build_affective_core(self, data: Dict[str, Any]) -> AffectiveCore:
        body = data.get("body_state") or {}
        affective = data.get("affective") or {}

        valence = body.get(
            "valence_estimate",
            affective.get("valence", data.get("valence", 0.0)),
        )
        arousal = body.get(
            "arousal_estimate",
            affective.get("arousal", data.get("arousal", 0.5)),
        )
        dominance = affective.get("dominance", data.get("dominance", 0.5))

        if self.enable_mood:
            mood = self._mood_descriptor(float(valence), float(arousal))
        else:
            mood = "unspecified"

        return AffectiveCore(
            valence=round(float(valence), 2),
            arousal=round(float(arousal), 2),
            dominance=round(float(dominance), 2),
            overall_mood=mood,
        )

    def _mood_descriptor(self, valence: float, arousal: float) -> str:
        if arousal > 0.75 and valence > 0.25:
            return "heightened_interest"
        if arousal > 0.75 and valence < -0.15:
            return "startled_alert"
        if arousal < 0.35:
            return "calm_receptive"
        if valence < -0.3:
            return "wary_attention"
        return "steady_attention"

    def _extract_salient_sensations(self, data: Dict[str, Any]) -> List[SalientSensation]:
        raw_sensations = data.get("sensations") or []
        results: List[SalientSensation] = []

        for s in raw_sensations:
            if hasattr(s, "to_dict"):
                s = s.to_dict()
            elif hasattr(s, "model_dump"):
                s = s.model_dump()
            if not isinstance(s, dict):
                continue

            intensity = float(s.get("intensity", 0.5))
            novelty = float(s.get("novelty", 0.5))
            # Soft floor: keep sub-threshold items if list is small; ranking still applies
            results.append(
                SalientSensation(
                    description=str(s.get("description", "unspecified sensation")),
                    zone=str(s.get("zone", "unknown")),
                    intensity=intensity,
                    valence=float(s.get("valence", 0.0)),
                    arousal_contribution=float(s.get("arousal_contribution", 0.0)),
                    novelty=novelty,
                    category=_enum_str(s.get("category")),
                    temporal_quality=_enum_str(s.get("temporal_quality")),
                    texture_qualities=list(s.get("texture_qualities") or []),
                    movement_quality=s.get("movement_quality"),
                    arousal_modulated_richness=float(
                        s.get("arousal_modulated_richness", 0.0) or 0.0
                    ),
                    zone_character=s.get("zone_character"),
                    confidence=float(s.get("confidence", 0.8) or 0.8),
                    composition_notes=list(s.get("composition_notes") or []),
                )
            )

        w_r = self.richness_rank_weight
        results.sort(
            key=lambda x: (
                x.intensity * 0.55
                + x.novelty * 0.30
                + x.arousal_modulated_richness * w_r
            ),
            reverse=True,
        )
        # Prefer items above salience threshold when enough candidates
        above = [r for r in results if r.intensity >= self.salience_threshold]
        if above:
            return above
        return results

    def _generate_simple_delta(self, data: Dict[str, Any]) -> str:
        changes: List[str] = []
        if data.get("arousal_increased"):
            changes.append("arousal rising")
        if data.get("arousal_decreased"):
            changes.append("arousal falling")
        if data.get("new_contact"):
            changes.append("new contact")
        if data.get("sound_triggered"):
            changes.append("auditory event")
        if data.get("reflex_activity"):
            kinds = data["reflex_activity"]
            if isinstance(kinds, list) and kinds:
                non_auto = [k for k in kinds if str(k).lower() not in ("autonomic",)]
                if non_auto:
                    changes.append("reflex: " + ", ".join(str(k) for k in non_auto[:3]))
        return "; ".join(changes) if changes else "stable"

    def _estimate_tokens(
        self,
        affective: AffectiveCore,
        salient: List[SalientSensation],
        delta: str,
        trend: str,
    ) -> int:
        # Rough heuristic for HI budget tracking
        base = 60
        base += len(salient) * 28
        for s in salient:
            base += min(40, len(s.description) // 4)
            base += len(s.texture_qualities) * 3
        base += len(delta) // 4 + len(trend) // 4
        return int(base)


def _enum_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
