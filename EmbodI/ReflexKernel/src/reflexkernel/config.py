"""
Configuration system for ReflexKernel.

Uses Pydantic v2 models for validation, environment overrides,
and clean YAML loading.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class KernelConfig(BaseModel):
    tick_rate_hz: int = 30
    log_level: str = "INFO"
    seed: int = 42


class SimulationConfig(BaseModel):
    interactive: bool = True
    auto_events: bool = True
    auto_event_interval_s: float = 4.0


class VisionConfig(BaseModel):
    enabled: bool = False
    device: int = 0
    use_mediapipe: bool = True
    face: bool = True
    hands: bool = False
    pose: bool = False
    motion_detection: bool = True


class AudioConfig(BaseModel):
    enabled: bool = False
    sample_rate: int = 16000
    vad_enabled: bool = True
    energy_threshold: float = 0.02


class PerceptionConfig(BaseModel):
    enabled_sensors: List[str] = Field(default_factory=lambda: ["simulation"])
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)


class FusionConfig(BaseModel):
    arousal_decay_per_tick: float = 0.03
    valence_decay_per_tick: float = 0.01
    stimulus_weight: float = 0.65
    thought_weight: float = 0.55
    max_salient_stimuli: int = 5


class BridgeConfig(BaseModel):
    structured_seeds: bool = True
    keyword_rules: bool = True
    use_sentence_transformers: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    use_sentiment: bool = True
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    fusion: FusionConfig = Field(default_factory=FusionConfig)


class ReflexConfig(BaseModel):
    enabled_primitives: List[str] = Field(
        default_factory=lambda: ["flinch", "blink", "tension", "orient", "freeze", "autonomic"]
    )
    base_sensitivity: float = 0.8
    refractory_period_ms: Dict[str, int] = Field(
        default_factory=lambda: {"flinch": 180, "blink": 80, "default": 120}
    )
    arousal_amplifies: bool = True
    valence_dampens_negative: bool = True


class ImitationConfig(BaseModel):
    enabled: bool = True
    similarity_threshold: float = 0.72
    max_exemplars_per_behavior: int = 200


class ReinforcementConfig(BaseModel):
    enabled: bool = True
    learning_rate: float = 0.08
    reward_window: int = 12


class LearnerConfig(BaseModel):
    enabled: bool = True
    store_path: str = "data/learned"
    persistence_format: str = "jsonl"
    imitation: ImitationConfig = Field(default_factory=ImitationConfig)
    reinforcement: ReinforcementConfig = Field(default_factory=ReinforcementConfig)
    allow_dynamic_registration: bool = False


class AvatarConfig(BaseModel):
    width: int = 640
    height: int = 480
    fps: int = 30
    show_stimuli_overlay: bool = True
    show_reflex_traces: bool = True


class OutputConfig(BaseModel):
    visualization: Literal["pygame", "text", "none"] = "pygame"
    log_structured: bool = True
    log_dir: str = "logs"
    avatar: AvatarConfig = Field(default_factory=AvatarConfig)


class StdioConfig(BaseModel):
    enabled: bool = True
    pretty: bool = False


class WebsocketConfig(BaseModel):
    """Legacy websocket config (kept for backward compat; prefer server for new remote use)."""
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765
    path: str = "/reflex"


class ServerConfig(BaseModel):
    """Production remote server settings (FastAPI + WebSocket).

    Enabled by default is False for full backward compatibility with local-only use.
    """
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    api_key: str = "reflexkernel-dev"   # Change in production! Dev default only.
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    enable_rate_limit: bool = True
    rate_limit_per_minute: int = 120
    # WebSocket specific
    ws_path: str = "/ws/events"
    # Future: enable_tls, etc.


class InterfaceConfig(BaseModel):
    mode: Literal["stdio", "websocket", "both", "none"] = "stdio"
    stdio: StdioConfig = Field(default_factory=StdioConfig)
    websocket: WebsocketConfig = Field(default_factory=WebsocketConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    python_api: Dict[str, bool] = Field(default_factory=lambda: {"enabled": True})


class ReflexKernelConfig(BaseModel):
    """Root configuration object."""
    kernel: KernelConfig = Field(default_factory=KernelConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    reflex: ReflexConfig = Field(default_factory=ReflexConfig)
    learner: LearnerConfig = Field(default_factory=LearnerConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)

    @model_validator(mode="after")
    def _validate_paths(self) -> "ReflexKernelConfig":
        # Ensure learner store and logs are resolvable
        Path(self.learner.store_path).mkdir(parents=True, exist_ok=True)
        if self.output.log_structured:
            Path(self.output.log_dir).mkdir(parents=True, exist_ok=True)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


def load_config(path: Optional[str | Path] = None, overrides: Optional[Dict[str, Any]] = None) -> ReflexKernelConfig:
    """
    Load configuration from YAML (or use defaults) and apply optional dict overrides + env.

    Environment variables with prefix REFLEXKERNEL_ are applied last (highest precedence).
    Example: REFLEXKERNEL_KERNEL__LOG_LEVEL=DEBUG
    """
    cfg_dict: Dict[str, Any] = {}

    if path:
        p = Path(path)
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                cfg_dict.update(loaded)
        else:
            print(f"[config] WARNING: config file not found at {p}, using defaults + overrides")

    if overrides:
        # Deep-merge simple overrides
        def deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in over.items():
                if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                    base[k] = deep_merge(base[k], v)
                else:
                    base[k] = v
            return base
        cfg_dict = deep_merge(cfg_dict, overrides)

    # Very light env support (top-level sections only for simplicity)
    env_prefix = "REFLEXKERNEL_"
    for key, val in os.environ.items():
        if key.startswith(env_prefix):
            # e.g. REFLEXKERNEL_KERNEL__TICK_RATE_HZ=15
            rest = key[len(env_prefix):].lower()
            if "__" in rest:
                section, field = rest.split("__", 1)
                if section not in cfg_dict:
                    cfg_dict[section] = {}
                cfg_dict[section][field] = _maybe_coerce(val)
            else:
                # flat kernel keys etc.
                cfg_dict[rest] = _maybe_coerce(val)

    return ReflexKernelConfig(**cfg_dict)


def _maybe_coerce(val: str) -> Any:
    val = val.strip()
    if val.lower() in ("true", "yes", "on"):
        return True
    if val.lower() in ("false", "no", "off"):
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def save_config(cfg: ReflexKernelConfig, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg.to_dict(), f, sort_keys=False, default_flow_style=False)
