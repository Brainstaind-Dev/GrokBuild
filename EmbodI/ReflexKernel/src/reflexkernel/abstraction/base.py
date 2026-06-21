"""
Base classes for the Feature Extraction / Abstraction Layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .schema import AbstractionOutput, Feature, SensorEvent


class AbstractFeatureExtractor(ABC):
    """
    Abstract base for any feature extractor / abstraction processor.

    Implementations can be:
    - Virtual (for simulation and testing)
    - Hardware-backed (reading from ESP32 / direct GPIO / I2C)
    - Hybrid
    """

    name: str = "abstract_extractor"

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def process(self, raw_data: Dict[str, Any]) -> AbstractionOutput:
        """
        Take raw sensor readings (or virtual readings) and return abstracted output.

        The `raw_data` dict is intentionally flexible so different sources
        (virtual simulator, ESP32 serial, direct I2C, etc.) can feed it.
        """
        ...

    def process_batch(self, raw_batches: List[Dict[str, Any]]) -> List[AbstractionOutput]:
        """Convenience for processing multiple readings."""
        return [self.process(data) for data in raw_batches]

    def to_stimuli(self, output: AbstractionOutput) -> List[Dict[str, Any]]:
        """Helper: convert abstraction output into ReflexKernel-compatible Stimulus dicts."""
        return output.to_stimuli()
