"""Adapters from external systems into Sensory Cortex coherent-input dicts."""

from .reflex_kernel import (
    from_kernel,
    from_state_payload,
    from_abstraction_dicts,
    drive_shared_sim,
)

__all__ = [
    "from_kernel",
    "from_state_payload",
    "from_abstraction_dicts",
    "drive_shared_sim",
]
