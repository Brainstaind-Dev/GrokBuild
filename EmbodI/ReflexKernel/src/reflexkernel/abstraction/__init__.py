"""
Feature Extraction / Abstraction Layer for the Embodied Autonomic System.

This layer sits between raw (or virtual) sensors and ReflexKernel.
It reduces raw data volume, detects meaningful events, computes features,
and produces clean signals that higher intelligences can actually use.

Public surface:
    from reflexkernel.abstraction import (
        AbstractionOutput,
        SensorEvent,
        Feature,
        BodyStateSummary,
        VirtualSensorSimulator,
    )
"""

from .base import AbstractFeatureExtractor
from .bridge import (
    abstraction_to_stimuli,
    get_capped_coherent_sensations,
    get_coherent_sensations,
    get_state_summary,
    MAX_SENSATIONS_FOR_HI,
)
from .coherence import build_enhanced_body_state, combine_into_sensations
from .schema import (
    AbstractionOutput,
    BaseSignal,
    BodyStateSummary,
    DetailLevel,
    Feature,
    Sensation,
    SensorEvent,
    SensorSource,
    SignalCategory,
    get_all_tier1_event_types,
    get_all_tier1_feature_types,
    get_zone_sensitivity,
    FEMALE_SENSITIVITY_MAP,
)
from .virtual import VirtualSensorSimulator

__all__ = [
    "AbstractFeatureExtractor",
    "AbstractionOutput",
    "BaseSignal",
    "BodyStateSummary",
    "DetailLevel",
    "Feature",
    "Sensation",
    "SensorEvent",
    "SensorSource",
    "SignalCategory",
    "VirtualSensorSimulator",
    # Schema helpers
    "get_all_tier1_event_types",
    "get_all_tier1_feature_types",
    "get_zone_sensitivity",
    "FEMALE_SENSITIVITY_MAP",
    # Bridge & Coherence helpers
    "abstraction_to_stimuli",
    "get_coherent_sensations",
    "get_capped_coherent_sensations",
    "get_state_summary",
    "MAX_SENSATIONS_FOR_HI",
    "combine_into_sensations",
    "build_enhanced_body_state",
]
