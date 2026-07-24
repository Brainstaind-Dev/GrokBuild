"""
HIAgent — Higher Intelligence rider for Embodi / ReflexKernel.

Uses the xAI API (Grok) as mind, Sensory Cortex as felt sense,
and ReflexKernel (embedded or remote Saddle) as autonomic body.
"""

from .config import HIAgentConfig, load_config
from .loop.agent import HigherIntelligenceAgent

__version__ = "0.1.0"

__all__ = [
    "HIAgentConfig",
    "load_config",
    "HigherIntelligenceAgent",
]
