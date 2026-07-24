# Proposed Sensation Model Extension

**File**: `src/reflexkernel/abstraction/schema.py`  
**Purpose**: Extend the `Sensation` model to support richer structured representation for coherent bodily experience.

## Current State
The existing `Sensation` model captures basic intensity, valence, and arousal contribution, but lacks the structured fields needed for temporal awareness, texture, sensation category, and richer arousal/zone interaction.

## Proposed Additions

Add the following fields to the `Sensation` class:

```python
from enum import Enum

class SensationCategory(str, Enum):
    """High-level category of the synthesized sensation."""
    CONTACT_PRESSURE = "contact_pressure"
    STROKING_MOVEMENT = "stroking_movement"
    TEMPERATURE = "temperature"
    COMBINED_TOUCH = "combined_touch"      # Pressure + movement + temperature blended
    INTERNAL = "internal"
    HAIR_SCALP = "hair_scalp"
    PROPRIOCEPTIVE = "proprioceptive"
    AMBIENT = "ambient"
    OTHER = "other"

class TemporalQuality(str, Enum):
    """Temporal character of the sensation."""
    SUDDEN = "sudden"
    SUSTAINED = "sustained"
    BUILDING = "building"
    FADING = "fading"
    RHYTHMIC = "rhythmic"
    PULSING = "pulsing"
    LINGERING = "lingering"
    INTERMITTENT = "intermittent"
    UNKNOWN = "unknown"

class Sensation(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Existing fields (keep)
    description: str
    zone: str
    intensity: float
    valence: float
    arousal_contribution: float
    detail_level: DetailLevel
    source_features: List[str]
    ts: float
    confidence: float

    # === NEW FIELDS ===

    category: SensationCategory = SensationCategory.COMBINED_TOUCH
    """High-level category of this sensation."""

    temporal_quality: TemporalQuality = TemporalQuality.UNKNOWN
    """Temporal character (sudden, sustained, building, fading, rhythmic, etc.)."""

    texture_qualities: List[str] = Field(default_factory=list)
    """List of texture/quality descriptors (e.g. ["warm", "smooth", "firm", "silky"])."""

    movement_quality: Optional[str] = None
    """Description of movement component (e.g. "gentle stroking upward", "slow circling")."""

    arousal_modulated_richness: float = Field(0.0, ge=0.0, le=1.0)
    """How much arousal has increased the richness/detail of this sensation (separate from raw intensity)."""

    zone_character: Optional[str] = None
    """Optional short descriptor of zone-specific sensory character (e.g. "highly sensitive erogenous", "intentionally dulled")."""

    composition_notes: List[str] = Field(default_factory=list)
    """Internal notes about how multiple features were blended (useful for debugging and future pattern mapping)."""