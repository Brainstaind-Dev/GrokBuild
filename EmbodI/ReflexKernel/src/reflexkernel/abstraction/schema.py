"""
Standardized Event + Feature Schema for the Embodied Autonomic System.

This defines the language spoken between the Hardware/Virtual Perception Layer,
the Feature Extraction / Abstraction Layer, and ReflexKernel.

Design goals:
- Clean, serializable (JSON-friendly for remote interfaces)
- Distinguishes discrete **Events** from continuous **Features**
- Provides higher-level **State Summaries** for the Saddle / higher intelligence
- Works for both physical hardware and virtual simulation
- Easy to extend without breaking existing ReflexKernel Stimulus pipeline

All models are Pydantic v2 for validation + serialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SignalCategory(str, Enum):
    """High-level category of the signal."""
    EVENT = "event"           # Discrete, time-bounded occurrence
    FEATURE = "feature"       # Ongoing or computed value
    STATE_SUMMARY = "state_summary"  # Abstracted state for higher intelligence


class SensorSource(str, Enum):
    """Known sources of raw or virtual sensor data."""
    FSR_ARRAY = "fsr_array"
    MPU6050 = "mpu6050"
    MICROPHONE = "microphone"
    DHT22 = "dht22"
    MAX30102 = "max30102"
    GSR = "gsr"
    VIRTUAL = "virtual"
    SIMULATION = "simulation"
    OTHER = "other"


# ------------------------------------------------------------------
# Core Schema Models
# ------------------------------------------------------------------

class BaseSignal(BaseModel):
    """Common fields for all signals produced by the Abstraction Layer."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: str = Field(..., description="Specific signal name, e.g. 'contact_start', 'motion_energy'")
    category: SignalCategory
    value: Any = Field(..., description="Scalar, vector, string, or structured value")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    ts: float = Field(..., description="Monotonic timestamp (perf_counter or similar)")
    source: SensorSource | str = SensorSource.OTHER
    raw_modality: Optional[str] = Field(None, description="Original modality before abstraction (e.g. 'touch', 'proprio')")

    def to_stimulus_dict(self) -> Dict[str, Any]:
        """Convert to a shape compatible with existing ReflexKernel Stimulus."""
        return {
            "modality": self.raw_modality or self.category.value,
            "data": {
                "type": self.type,
                "value": self.value,
                "confidence": self.confidence,
                "source": self.source.value if isinstance(self.source, SensorSource) else self.source,
            },
            "ts": self.ts,
            "confidence": self.confidence,
            "source": str(self.source),
        }


class SensorEvent(BaseSignal):
    """Discrete event detected from sensors."""
    category: SignalCategory = SignalCategory.EVENT
    duration_ms: Optional[float] = Field(None, description="How long the event lasted (if applicable)")


class Feature(BaseSignal):
    """Continuous or computed feature."""
    category: SignalCategory = SignalCategory.FEATURE
    window_ms: Optional[float] = Field(None, description="Time window over which this feature was computed")


class DetailLevel(str, Enum):
    """Granularity of output to the higher intelligence."""
    NORMAL = "normal"          # Clean, high-level coherent sensations (default for HI)
    ENHANCED = "enhanced"      # + texture, temperature nuance, movement quality
    DIAGNOSTIC = "diagnostic"  # Full granular metrics + raw features (debugging only)


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
    """
    A coherent, natural bodily sensation synthesized for the higher intelligence.

    This is the primary output the Saddle / higher intelligence should receive.
    It describes *what it feels like* rather than raw metrics.

    Example: "Firm, warm pressure spreading slowly across my upper inner thigh,
              with a gentle stroking quality that feels increasingly sensitive
              as arousal rises."
    """
    model_config = ConfigDict(extra="allow")

    description: str = Field(..., description="Natural language description of the unified sensation")
    zone: str = Field(..., description="Body zone where the sensation is primarily located (e.g. 'upper_inner_thigh')")
    intensity: float = Field(..., ge=0.0, le=1.5, description="Perceived intensity after sensitivity + arousal modulation")
    valence: float = Field(0.0, ge=-1.0, le=1.0, description="Estimated pleasantness (negative = aversive/uncomfortable)")
    arousal_contribution: float = Field(0.0, ge=0.0, le=1.0, description="How much this sensation is contributing to overall arousal")
    detail_level: DetailLevel = DetailLevel.NORMAL
    source_features: List[str] = Field(default_factory=list, description="Which raw features/events contributed to this sensation")
    ts: float
    confidence: float = 0.8

    # === NEW FIELDS (per DirDoc1.md proposal + CoherenceDir directive) ===
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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BodyStateSummary(BaseModel):
    """
    Higher-level abstracted state intended for the Saddle / higher intelligence.

    This is what a remote LLM or agent should primarily consume to understand
    the current 'felt' condition of the body without drowning in raw data.

    In the new pipeline, this can be derived from coherent sensations rather
    than directly from raw metrics.
    """
    model_config = ConfigDict(extra="allow")

    arousal_estimate: float = Field(0.3, ge=0.0, le=1.5)
    valence_estimate: float = Field(0.0, ge=-1.0, le=1.0)
    posture_stability: float = Field(0.7, ge=0.0, le=1.0)
    contact_state: str = Field("none", description="none | light | firm | multiple")
    dominant_sensation: Optional[str] = None   # Now references a coherent sensation description
    dominant_zone: Optional[str] = None
    environmental_temp: Optional[float] = None

    # New for coherence pipeline
    active_sensations: List[str] = Field(default_factory=list, description="Summary of current coherent sensations")
    detail_level: DetailLevel = DetailLevel.NORMAL

    ts: float
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ------------------------------------------------------------------
# Batch / Envelope Types
# ------------------------------------------------------------------

class AbstractionOutput(BaseModel):
    """Container produced by the Abstraction Layer each cycle.

    Dual-path design:
    - events + features → feed ReflexKernel (for low-level reflexes & learning)
    - sensations + enhanced state_summary → primary output for the Saddle / higher intelligence
    """
    events: List[SensorEvent] = Field(default_factory=list)
    features: List[Feature] = Field(default_factory=list)
    sensations: List[Sensation] = Field(default_factory=list, description="Coherent natural sensations for the higher intelligence")
    state_summary: Optional[BodyStateSummary] = None
    detail_level: DetailLevel = DetailLevel.NORMAL
    ts: float

    def to_stimuli(self) -> List[Dict[str, Any]]:
        """Convert everything into Stimulus-compatible dicts for ReflexKernel (events + features path)."""
        stimuli = []
        for event in self.events:
            stimuli.append(event.to_stimulus_dict())
        for feat in self.features:
            stimuli.append(feat.to_stimulus_dict())
        return stimuli

    def get_coherent_sensations(self) -> List[Sensation]:
        """Primary output for higher intelligence / Saddle."""
        return self.sensations


# ------------------------------------------------------------------
# Convenience Type Aliases
# ------------------------------------------------------------------

EventList = List[SensorEvent]
FeatureList = List[Feature]


# ------------------------------------------------------------------
# Tier 1 Standardized Event & Feature Definitions
# These are the canonical types the system will use for FSR, MPU6050,
# Microphone, and DHT22. Use these strings for consistency.
# ------------------------------------------------------------------

# FSR Array (4 sensors, tactile/contact)
FSR_CONTACT_START = "contact_start"
FSR_CONTACT_END = "contact_end"
FSR_IMPACT = "impact"
FSR_CONTACT_INTENSITY = "contact_intensity"          # per-sensor or aggregate 0-1+
FSR_PRESSURE_GRADIENT = "pressure_gradient"          # difference across sensors

# MPU6050 (motion/orientation)
MPU_SUDDEN_MOVEMENT = "sudden_movement"
MPU_ORIENTATION_CHANGE = "orientation_change"
MPU_MOTION_ENERGY = "motion_energy"                  # combined accel + gyro magnitude
MPU_POSTURE_STABILITY = "posture_stability"          # 0.0 (unstable) to 1.0 (stable)
MPU_TILT_ANGLE = "tilt_angle"                        # degrees from upright

# Microphone (MAX9814 or equivalent)
MIC_SUDDEN_LOUD_SOUND = "sudden_loud_sound"
MIC_SOUND_ONSET = "sound_onset"
MIC_ACOUSTIC_ENERGY = "acoustic_energy"              # RMS or peak energy
MIC_AMPLITUDE_ENVELOPE = "amplitude_envelope"

# DHT22 (temperature/humidity)
DHT_AMBIENT_TEMP = "ambient_temp"
DHT_BODY_TEMP = "body_temp"
DHT_HUMIDITY = "humidity"

# Common state summary fields (for BodyStateSummary)
STATE_AROUSAL_ESTIMATE = "arousal_estimate"
STATE_VALENCE_ESTIMATE = "valence_estimate"
STATE_CONTACT_STATE = "contact_state"                # "none", "light", "firm", "multiple"
STATE_DOMINANT_EVENT = "dominant_event"


def get_all_tier1_event_types() -> list[str]:
    """Return all canonical Tier 1 event type strings."""
    return [
        FSR_CONTACT_START, FSR_CONTACT_END, FSR_IMPACT,
        MPU_SUDDEN_MOVEMENT, MPU_ORIENTATION_CHANGE,
        MIC_SUDDEN_LOUD_SOUND, MIC_SOUND_ONSET,
    ]


def get_all_tier1_feature_types() -> list[str]:
    """Return all canonical Tier 1 feature type strings."""
    return [
        FSR_CONTACT_INTENSITY, FSR_PRESSURE_GRADIENT,
        MPU_MOTION_ENERGY, MPU_POSTURE_STABILITY, MPU_TILT_ANGLE,
        MIC_ACOUSTIC_ENERGY, MIC_AMPLITUDE_ENVELOPE,
        DHT_AMBIENT_TEMP, DHT_BODY_TEMP, DHT_HUMIDITY,
    ]


# ------------------------------------------------------------------
# Sensitivity Mapping (Female Body – from FSM.md)
# ------------------------------------------------------------------

# Base sensitivity multipliers per zone (relative to "medium" = 1.0)
# These will be further modulated by arousal.
FEMALE_SENSITIVITY_MAP: dict[str, float] = {
    # High Sensitivity
    "nipples_areola": 2.8,
    "clitoris_vulva": 3.5,
    "anus": 2.5,               # Strongly arousal-dependent (see multiplier)
    "inner_thighs": 2.2,
    "lower_back_base_spine": 2.0,
    "upper_back": 1.8,
    "neck_throat": 2.4,
    "lips": 2.1,

    # Medium-High
    "breasts_general": 1.7,
    "earlobes": 1.6,
    "inner_wrists": 1.5,
    "lower_stomach": 1.6,
    "upper_buttocks": 1.7,

    # Medium
    "outer_thighs": 1.0,
    "hips": 1.1,
    "shoulders": 1.0,
    "scalp_hair": 1.2,
    "upper_arms": 0.95,

    # Low (intentionally dulled)
    "calves": 0.4,
    "outer_arms": 0.5,
    "feet": 0.2,               # Minimal tactile feedback to avoid tickling
}

# Default zone if unknown
DEFAULT_SENSITIVITY = 1.0

EROGENOUS_ZONES = {
    "clitoris_vulva", "nipples_areola", "anus", "inner_thighs",
    "lower_back_base_spine", "upper_back", "neck_throat", "lips"
}


def get_zone_sensitivity(zone: str, arousal: float = 0.3) -> float:
    """
    Returns the effective sensitivity multiplier for a body zone,
    incorporating base sensitivity and arousal modulation (especially for anus).
    """
    base = FEMALE_SENSITIVITY_MAP.get(zone, DEFAULT_SENSITIVITY)

    # Special arousal-dependent boost for anus (as per FSM.md)
    if zone == "anus":
        # Strong increase as arousal rises (e.g. 1.0 at low arousal → ~2.5+ at high)
        arousal_factor = 1.0 + (arousal * 2.5)
        return base * arousal_factor

    # General mild arousal boost for high-sensitivity zones
    if base > 1.8:
        return base * (1.0 + arousal * 0.6)

    return base
