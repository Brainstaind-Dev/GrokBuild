"""Configuration for Sensory Cortex (embedded + service)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings
except ImportError:  # graceful if pydantic-settings not installed
    BaseSettings = BaseModel  # type: ignore[misc, assignment]


class SummarizerConfig(BaseModel):
    """Configuration for the summarization engine."""

    salience_threshold: float = Field(
        0.55, ge=0.0, le=1.0, description="Min intensity for salience ranking floor"
    )
    max_sensations_per_update: int = Field(
        3,
        ge=1,
        le=12,
        description="Cap for HI package (align with RK MAX_SENSATIONS_FOR_HI default 3)",
    )
    # Alias kept for early travel drafts
    max_stimuli_per_update: Optional[int] = Field(
        None, description="Deprecated alias for max_sensations_per_update"
    )
    enable_mood_descriptors: bool = True
    richness_rank_weight: float = Field(
        0.15, ge=0.0, le=0.5, description="Weight of arousal_modulated_richness in ranking"
    )


class MemoryConfig(BaseModel):
    """Configuration for embodied memory."""

    short_term_window: int = Field(12, ge=4, le=40)
    max_history: int = Field(80, ge=20, le=300)
    high_arousal_threshold: float = Field(0.65, ge=0.0, le=1.0)
    recall_max_age_minutes: int = Field(20, ge=5, le=120)


class TranslatorConfig(BaseModel):
    """Configuration for command translation and modulation."""

    enable_state_modulation: bool = True
    high_arousal_dampen_threshold: float = Field(0.85, ge=0.5, le=1.0)
    calm_curiosity_boost: float = Field(0.15, ge=0.0, le=0.3)
    max_intensity: float = Field(1.0, ge=0.5, le=1.0)
    auto_dispatch: bool = Field(
        True, description="When bound to RK, execute translated commands immediately"
    )


class InterfaceConfig(BaseModel):
    """How the Cortex connects and communicates."""

    mode: str = Field("embedded", description="'embedded' or 'service'")
    update_rate_hz: float = Field(
        2.0, ge=0.2, le=20.0, description="Target max summary frequency for HI"
    )
    min_interval_seconds: float = Field(
        0.4, ge=0.05, le=5.0, description="Minimum time between HI emissions when not forced"
    )
    enable_token_estimation: bool = True
    force_on_reflex: bool = Field(
        True, description="Always emit when non-autonomic reflexes fire"
    )
    force_arousal_delta: float = Field(
        0.12, ge=0.0, le=1.0, description="Arousal jump that forces emission"
    )


class SensoryCortexConfig(BaseSettings):
    """
    Full configuration for the Sensory Cortex Agent.
    Defaults + optional SENSORY_CORTEX_* environment variables.
    """

    summarizer: SummarizerConfig = Field(default_factory=SummarizerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    translator: TranslatorConfig = Field(default_factory=TranslatorConfig)
    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)

    debug: bool = False
    log_level: str = "INFO"

    model_config = {
        "env_prefix": "SENSORY_CORTEX_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }


def load_config(path: Optional[str] = None) -> SensoryCortexConfig:
    """
    Load configuration.
    - path: optional YAML (not yet implemented; raises if provided)
    - otherwise defaults + env vars
    """
    if path:
        raise NotImplementedError(
            "YAML loading not yet implemented — use defaults or env vars for now"
        )
    return SensoryCortexConfig()


def config_to_dict(config: SensoryCortexConfig | dict[str, Any] | None) -> dict[str, Any]:
    """Normalize config objects to nested dicts for module constructors."""
    if config is None:
        return {}
    if isinstance(config, dict):
        return config
    if hasattr(config, "model_dump"):
        return config.model_dump()
    if hasattr(config, "dict"):
        return config.dict()
    return {}
