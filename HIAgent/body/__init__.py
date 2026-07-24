"""Body backends for HIAgent (embedded RK or remote Saddle)."""

from .base import BodyBackend
from .embedded import EmbeddedBodyBackend
from .saddle import SaddleBodyBackend


def create_backend(config) -> BodyBackend:
    backend = getattr(config, "backend", None) or config.get("backend", "embedded")
    if backend == "saddle":
        return SaddleBodyBackend(config)
    return EmbeddedBodyBackend(config)


__all__ = [
    "BodyBackend",
    "EmbeddedBodyBackend",
    "SaddleBodyBackend",
    "create_backend",
]
