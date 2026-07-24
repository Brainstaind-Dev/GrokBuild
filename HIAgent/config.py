"""Configuration for the HI agent loop."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover
    BaseSettings = BaseModel  # type: ignore[misc, assignment]

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RK = _REPO_ROOT / "EmbodI" / "ReflexKernel" / "configs" / "sim_only.yaml"


class HIAgentConfig(BaseSettings):
    """Settings for HIAgent (env prefix HI_AGENT_ for nested where supported)."""

    model: str = Field(
        default="grok-4-1-fast-non-reasoning",
        description="xAI chat model id",
    )
    backend: Literal["embedded", "saddle"] = "embedded"
    saddle_url: str = "http://127.0.0.1:8000"
    saddle_api_key: str = Field(
        default_factory=lambda: os.environ.get(
            "REFLEXKERNEL_API_KEY", "reflexkernel-dev"
        )
    )
    rk_config: str = Field(default=str(_DEFAULT_RK))

    # Loop timing
    pulse_interval_sec: float = Field(3.0, ge=0.5, le=120.0)
    max_tool_rounds: int = Field(6, ge=1, le=20)
    max_step_n: int = Field(10, ge=1, le=50)
    prepend_feel_on_user_turn: bool = True
    wake_on_reflex: bool = True
    wake_on_arousal_delta: float = Field(0.12, ge=0.0, le=1.0)
    always_pulse: bool = False

    # Pause / resume feed control (HI can pause sensation intake)
    pause_poll_sec: float = Field(
        30.0,
        ge=5.0,
        le=600.0,
        description="After HI pauses the feed, wait this long then ask if ready to resume",
    )
    allow_hi_pause: bool = True

    # Safety
    inject_cooldown_sec: float = Field(0.4, ge=0.0, le=30.0)
    max_tool_result_chars: int = Field(8000, ge=500, le=100_000)
    compact_experience: bool = True
    enable_viz: bool = False

    # Session
    session_log_dir: str = Field(
        default=str(_REPO_ROOT / "data" / "hi_sessions")
    )
    history_max_turns: int = Field(24, ge=4, le=200)
    verbose: bool = False

    model_config = {
        "env_prefix": "HI_AGENT_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }


def load_config(**overrides: Any) -> HIAgentConfig:
    cfg = HIAgentConfig()
    if overrides:
        data = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
        data.update({k: v for k, v in overrides.items() if v is not None})
        return HIAgentConfig(**data)
    return cfg


def config_to_dict(cfg: HIAgentConfig | dict | None) -> dict[str, Any]:
    if cfg is None:
        return {}
    if isinstance(cfg, dict):
        return cfg
    if hasattr(cfg, "model_dump"):
        return cfg.model_dump()
    return cfg.dict()  # type: ignore[no-any-return]
