"""
Sensation Coherence Layer

This module sits on top of Feature Extraction.
Its job is to intelligently combine multiple events + features into
unified, natural, coherent bodily sensations (the primary experience
for the higher intelligence).

Core Principle (from SensPP.md): "Combine first, then amplify."

It then applies:
- Zone sensitivity (from Female Sensitivity Map)
- Arousal-based dynamic modulation
- Detail Level filtering

This produces the "Sensation" objects that the Saddle / higher intelligence
should primarily receive.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .schema import (
    BodyStateSummary,
    DetailLevel,
    Feature,
    Sensation,
    SensorEvent,
    get_zone_sensitivity,
)


def _describe_contact(features: List[Feature], events: List[SensorEvent]) -> str:
    """Helper to generate natural language for contact sensations."""
    intensity_feat = next((f for f in features if f.type == "contact_intensity"), None)
    pressure_grad = next((f for f in features if f.type == "pressure_gradient"), None)

    intensity = intensity_feat.value if intensity_feat else 0.0
    has_impact = any(e.type == "impact" for e in events)

    if has_impact:
        return "strong, sudden impact pressure"
    if intensity > 0.6:
        return "firm, deep pressure"
    if intensity > 0.25:
        return "steady, noticeable pressure"
    return "light, subtle contact"


def _describe_movement(features: List[Feature]) -> str:
    """Helper for motion-related qualities."""
    motion = next((f for f in features if f.type == "motion_energy"), None)
    if not motion:
        return ""

    val = motion.value
    if val > 3.0:
        return " with rapid, energetic movement"
    if val > 1.5:
        return " with clear, deliberate movement"
    if val > 0.6:
        return " with gentle, slow movement"
    return ""


def _describe_temperature(features: List[Feature]) -> str:
    temp_feat = next((f for f in features if f.type == "ambient_temp"), None)
    if not temp_feat:
        return ""

    t = temp_feat.value
    if t > 30:
        return " warm"
    if t < 18:
        return " cool"
    return " neutral-temperature"


def combine_into_sensations(
    events: List[SensorEvent],
    features: List[Feature],
    arousal: float = 0.3,
    detail_level: DetailLevel = DetailLevel.NORMAL,
    primary_zone: str = "unknown",
) -> List[Sensation]:
    """
    Core of the Sensation Coherence Layer.

    Takes raw events + features and synthesizes them into one or more
    natural, coherent sensations.

    Applies sensitivity mapping and arousal modulation.
    """
    sensations: List[Sensation] = []
    now = max((e.ts for e in events), default=0.0) or max((f.ts for f in features), default=0.0)

    # --- Primary Contact Sensation (most common case) ---
    contact_events = [e for e in events if "contact" in e.type or e.type == "impact"]
    contact_features = [f for f in features if "contact" in f.type or f.type == "pressure_gradient"]

    if contact_events or contact_features:
        base_desc = _describe_contact(contact_features, contact_events)
        movement_desc = _describe_movement(features)
        temp_desc = _describe_temperature(features)

        # Build natural description
        description = f"{base_desc}{movement_desc}{temp_desc}"

        if detail_level in (DetailLevel.ENHANCED, DetailLevel.DIAGNOSTIC):
            # Add more texture/quality
            if any("slow" in f.type or "gentle" in str(f.value).lower() for f in features):
                description += ", with a smooth, lingering quality"
            if detail_level == DetailLevel.DIAGNOSTIC:
                intensity_val = next((f.value for f in contact_features if f.type == "contact_intensity"), 0)
                description += f" (raw intensity ≈ {intensity_val:.2f})"

        # Apply sensitivity + arousal modulation
        effective_intensity = get_zone_sensitivity(primary_zone, arousal)
        # Scale the base intensity
        base_intensity = 0.4
        if contact_features:
            base_intensity = max(f.value for f in contact_features if isinstance(f.value, (int, float))) or 0.4

        modulated_intensity = min(1.4, base_intensity * effective_intensity)

        # Valence proxy (can be refined later)
        valence = 0.2
        if "impact" in [e.type for e in events]:
            valence = -0.4

        sens = Sensation(
            description=description.strip().capitalize(),
            zone=primary_zone,
            intensity=round(modulated_intensity, 3),
            valence=round(valence, 2),
            arousal_contribution=round(min(0.9, modulated_intensity * 0.7), 2),
            detail_level=detail_level,
            source_features=[f.type for f in features[:3]],
            ts=now,
            confidence=0.78,
        )
        sensations.append(sens)

    # --- Secondary / Ambient Sensation (e.g. temperature + general proprio) ---
    temp_feat = next((f for f in features if f.type in ("ambient_temp", "body_temp")), None)
    if temp_feat and not any("contact" in e.type for e in events):
        temp_val = temp_feat.value
        temp_desc = "pleasantly warm" if temp_val > 28 else ("cool and crisp" if temp_val < 18 else "comfortably neutral")
        desc = f"Overall body awareness of {temp_desc} air against the skin"

        if detail_level == DetailLevel.ENHANCED:
            desc += f", with a steady temperature around {temp_val}°C"

        sens = Sensation(
            description=desc,
            zone="whole_body",
            intensity=round(0.25 + (arousal * 0.15), 2),
            valence=0.15,
            arousal_contribution=round(arousal * 0.2, 2),
            detail_level=detail_level,
            source_features=[temp_feat.type],
            ts=now,
            confidence=0.85,
        )
        sensations.append(sens)

    return sensations


def build_enhanced_body_state(
    sensations: List[Sensation],
    base_summary: BodyStateSummary | None = None,
) -> BodyStateSummary:
    """
    Creates or augments a BodyStateSummary using coherent sensations
    rather than (or in addition to) raw metrics.
    """
    if not sensations:
        if base_summary:
            return base_summary
        return BodyStateSummary(
            arousal_estimate=0.3,
            valence_estimate=0.0,
            posture_stability=0.7,
            contact_state="none",
            ts=0.0,
        )

    # Derive from sensations
    avg_arousal = sum(s.arousal_contribution for s in sensations) / len(sensations)
    avg_valence = sum(s.valence for s in sensations) / len(sensations)
    dominant = max(sensations, key=lambda s: s.intensity)

    contact = "multiple" if len(sensations) > 1 else "light"
    if any("firm" in s.description.lower() or "impact" in s.description.lower() for s in sensations):
        contact = "firm"

    if base_summary:
        base_summary.arousal_estimate = round(max(base_summary.arousal_estimate, avg_arousal), 3)
        base_summary.valence_estimate = round(avg_valence, 2)
        base_summary.contact_state = contact
        base_summary.dominant_sensation = dominant.description
        base_summary.dominant_zone = dominant.zone
        base_summary.active_sensations = [s.description for s in sensations[:3]]
        base_summary.detail_level = dominant.detail_level
        return base_summary

    return BodyStateSummary(
        arousal_estimate=round(avg_arousal, 3),
        valence_estimate=round(avg_valence, 2),
        posture_stability=0.7,
        contact_state=contact,
        dominant_sensation=dominant.description,
        dominant_zone=dominant.zone,
        active_sensations=[s.description for s in sensations[:3]],
        detail_level=dominant.detail_level,
        ts=dominant.ts,
        confidence=0.8,
    )
