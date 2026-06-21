"""
Allow: python -m reflexkernel

Currently just prints version and basic info.
Real entrypoints are the demo script and direct ReflexKernel usage.
"""

from . import __version__
from .config import load_config

print(f"ReflexKernel {__version__}")
print("Use: python -m scripts.demo   or   from reflexkernel import ReflexKernel")
print("Default config loaded for sanity check:")
cfg = load_config()
print("  tick_rate_hz =", cfg.kernel.tick_rate_hz)
print("  enabled primitives:", cfg.reflex.enabled_primitives)
