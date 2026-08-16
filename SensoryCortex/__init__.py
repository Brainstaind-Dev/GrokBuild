"""
Sensory Cortex Agent
====================

Interpretive layer between ReflexKernel and the higher intelligence (Grok).

Transforms already-coherent sensations into affectively rich HI packages,
maintains short/medium-term embodied memory, and translates intentions
back into ReflexKernel commands.

Designed for embedded (low-latency, in-process) and service modes.
"""

from .cortex import SensoryCortex
from .schemas import (
    AffectiveCore,
    SalientSensation,
    SalientStimulus,
    SensoryUpdate,
)
from .activation_pattern import (
    ActivationPatternV0,
    build_activation_pattern,
    pattern_to_compact_feel_line,
    SCHEMA_VERSION as ACTIVATION_PATTERN_SCHEMA_VERSION,
)
from .config import (
    InterfaceConfig,
    MemoryConfig,
    SensoryCortexConfig,
    SummarizerConfig,
    TranslatorConfig,
    load_config,
)

__version__ = "0.1.1"

__all__ = [
    "SensoryCortex",
    "SensoryUpdate",
    "AffectiveCore",
    "SalientSensation",
    "SalientStimulus",
    "SensoryCortexConfig",
    "load_config",
    "SummarizerConfig",
    "MemoryConfig",
    "TranslatorConfig",
    "InterfaceConfig",
    "ActivationPatternV0",
    "build_activation_pattern",
    "pattern_to_compact_feel_line",
    "ACTIVATION_PATTERN_SCHEMA_VERSION",
]
