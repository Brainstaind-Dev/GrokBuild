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
    get_coherent_sensations,
    get_state_summary,
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
    # Bridge & Coherence helpers
    "abstraction_to_stimuli",
    "get_coherent_sensations",
    "get_state_summary",
    "combine_into_sensations",
    "build_enhanced_body_state",
]
