"""
Perception package.

Public surface:
    from reflexkernel.perception import SimulationSensor, SensorRegistry
"""

from .base import Sensor, SensorRegistry
from .extract_tier1 import extract_tier1
from .hardware_sensor import HardwareSensor
from .simulation import SimulationSensor

__all__ = ["Sensor", "SensorRegistry", "SimulationSensor", "HardwareSensor", "extract_tier1"]

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
