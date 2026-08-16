"""HI-facing schemas for Sensory Cortex.

Built on top of ReflexKernel coherent Sensation objects — does not re-fuse
raw sensors. Rich fields from the coherence layer are preserved when present.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .activation_pattern import ActivationPatternV0


class AffectiveCore(BaseModel):
    valence: float = Field(..., ge=-1.0, le=1.0)
    arousal: float = Field(..., ge=0.0, le=1.0)
    dominance: float = Field(0.5, ge=0.0, le=1.0)
    overall_mood: str


class SalientSensation(BaseModel):
    """Wraps a coherent sensation from ReflexKernel's Coherence layer.

    Core fields always present; rich optional fields are preserved when
    supplied by RK so the HI path does not strip June coherence work.
    """

    description: str
    zone: str = "unknown"
    intensity: float = Field(0.5, ge=0.0, le=1.5)
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal_contribution: float = Field(0.0, ge=0.0, le=1.0)
    novelty: float = Field(0.5, ge=0.0, le=1.0)

    # Rich fields from RK Sensation (optional pass-through)
    category: Optional[str] = None
    temporal_quality: Optional[str] = None
    texture_qualities: List[str] = Field(default_factory=list)
    movement_quality: Optional[str] = None
    arousal_modulated_richness: float = Field(0.0, ge=0.0, le=1.0)
    zone_character: Optional[str] = None
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    composition_notes: List[str] = Field(default_factory=list)


class SensoryUpdate(BaseModel):
    """
    The final package sent to the higher intelligence (Grok).
    Built on coherent sensations from ReflexKernel + Cortex temporal context.
    """

    timestamp: datetime
    affective_core: AffectiveCore
    salient_sensations: List[SalientSensation] = Field(default_factory=list)
    reflex_activity: List[str] = Field(default_factory=list)
    active_patterns: List[str] = Field(default_factory=list)
    delta_from_last: str = ""
    trend: str = ""
    token_estimate: int = 0
    source: str = "sensory_cortex"
    detail_level: str = "normal"
    # Body-native feel channel (v0); dual with NL sensations — see activation_pattern.py
    activation_pattern: Optional[Dict[str, Any]] = None


# Backward-compatible alias used briefly in early drafts
SalientStimulus = SalientSensation
