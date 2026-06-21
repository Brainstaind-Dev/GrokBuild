"""
ReflexKernel
============

Trainable low-level embodiment / nervous-system subsystem.

Public API (stable surface for higher intelligence and demos):

- ReflexKernel: the main orchestrator
- load_config, ReflexKernelConfig
- Core types: Stimulus, AffectiveContext, ReflexAction, RewardSignal, etc.

Example:
    from reflexkernel import ReflexKernel
    from reflexkernel.config import load_config

    kernel = ReflexKernel(config=load_config("configs/sim_only.yaml"))
    kernel.start()
    ...
    kernel.inject_thought_seed({"emotion": "fear", "intensity": 0.9})
    actions = kernel.step()
"""

from __future__ import annotations

__version__ = "0.2.0"  # Interface / remote connectivity focused release

from .config import ReflexKernelConfig, load_config, save_config
from .kernel import ReflexKernel
from .types import (
    AffectiveContext,
    DemonstrationStep,
    Modality,
    ReflexAction,
    ReflexKind,
    ReflexTrace,
    RewardSignal,
    Stimulus,
    StimulusBatch,
)

__all__ = [
    "ReflexKernel",
    "ReflexKernelConfig",
    "load_config",
    "save_config",
    "AffectiveContext",
    "DemonstrationStep",
    "Modality",
    "ReflexAction",
    "ReflexKind",
    "ReflexTrace",
    "RewardSignal",
    "Stimulus",
    "StimulusBatch",
    "__version__",
]

# Embodied Autonomic System extensions (Feature Abstraction Layer + Sensation Coherence)
try:
    from .abstraction import (
        AbstractionOutput,
        BodyStateSummary,
        DetailLevel,
        Feature,
        Sensation,
        SensorEvent,
        VirtualSensorSimulator,
        combine_into_sensations,
        get_coherent_sensations,
    )
    __all__.extend([
        "AbstractionOutput",
        "BodyStateSummary",
        "DetailLevel",
        "Feature",
        "Sensation",
        "SensorEvent",
        "VirtualSensorSimulator",
        "combine_into_sensations",
        "get_coherent_sensations",
    ])
except Exception:
    pass

# Safe remote server exports (only available if [server] extras installed)
try:
    from .interface.server import create_app, run_server  # noqa: F401
    __all__.extend(["create_app", "run_server"])
except Exception:
    pass
