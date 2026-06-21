"""
Perception package.

Public surface:
    from reflexkernel.perception import SimulationSensor, SensorRegistry
"""

from .base import Sensor, SensorRegistry
from .simulation import SimulationSensor

__all__ = ["Sensor", "SensorRegistry", "SimulationSensor"]

# Optional re-exports (will succeed only when deps present)
try:
    from .vision import VisionSensor  # noqa: F401
    __all__.append("VisionSensor")
except Exception:
    pass

try:
    from .audio import AudioSensor  # noqa: F401
    __all__.append("AudioSensor")
except Exception:
    pass
