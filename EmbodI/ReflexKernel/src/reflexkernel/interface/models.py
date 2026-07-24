"""
Pydantic models for the remote server API.

These are designed to be:
- Compatible with the shapes accepted by kernel.command() and PythonAPI.
- Rich enough for excellent OpenAPI / Swagger documentation.
- Lenient where the original command surface was lenient (extra fields allowed for thought seeds etc.).

All models use Pydantic v2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..abstraction.schema import Sensation, BodyStateSummary, DetailLevel


class BaseRequest(BaseModel):
    """Base for all incoming requests. Allows extra fields for forward compat."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ------------------------------------------------------------------
# Request Models
# ------------------------------------------------------------------

class ThoughtSeedRequest(BaseRequest):
    """Body for POST /api/v1/thought (maps to inject_thought_seed).

    Supports both structured fields and free-form (extra) for full flexibility.
    """
    emotion: Optional[str] = None
    intensity: float = Field(0.6, ge=0.0, le=2.0)
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.3, ge=0.0, le=1.5)
    dominance: float = Field(0.0, ge=-1.0, le=1.0)
    urgency: float = Field(0.0, ge=0.0, le=2.0)
    patterns: Optional[List[str]] = None
    text: Optional[str] = None
    trigger: Optional[str] = None

    # Common aliases used in command surface
    type: Optional[str] = None   # "thought_seed"
    cmd: Optional[str] = None


class RewardRequest(BaseRequest):
    """Body for POST /api/v1/reward."""
    value: float = Field(..., ge=-2.0, le=2.0)
    reason: str = ""
    window_steps: int = Field(1, ge=1, le=100)
    meta: Dict[str, Any] = Field(default_factory=dict)


class BeginDemoRequest(BaseRequest):
    """Body for POST /api/v1/demo/begin."""
    name: str = Field(..., min_length=1, max_length=128)
    # Optional metadata
    meta: Dict[str, Any] = Field(default_factory=dict)


class EndDemoRequest(BaseRequest):
    """Body for POST /api/v1/demo/end."""
    outcome: Dict[str, Any] = Field(default_factory=dict)


class InjectStimulusRequest(BaseRequest):
    """Body for POST /api/v1/stimulus.

    Accepts the same shape as Stimulus or a simplified form.
    """
    modality: str = "sim"
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    source: str = "remote"


class StepRequest(BaseRequest):
    """Body for POST /api/v1/step."""
    n: int = Field(1, ge=1, le=100)
    # Optional extra stimuli in one go
    extra_stimuli: List[Dict[str, Any]] = Field(default_factory=list)


class CommandRequest(BaseRequest):
    """Generic fallback for the old command surface (for maximum compatibility)."""
    cmd: Optional[str] = None
    type: Optional[str] = None
    # All other fields are allowed via extra=allow on base


# ------------------------------------------------------------------
# Response Models
# ------------------------------------------------------------------

class AckResponse(BaseModel):
    """Standard acknowledgment."""
    ok: bool = True
    error: Optional[str] = None
    demo: Optional[str] = None
    ended: Optional[str] = None


class StateResponse(BaseModel):
    """Current kernel state snapshot.

    Prominently includes richer coherent sensations (Sensation objects with full structured fields
    + natural NL) + state_summary for the Saddle / higher intelligence. Default detail=normal keeps
    output HI-friendly and non-overloading.
    """
    tick: int
    running: bool
    context: Optional[Dict[str, Any]] = None
    last_actions: List[Dict[str, Any]] = Field(default_factory=list)
    last_traces: List[Dict[str, Any]] = Field(default_factory=list)
    demo_active: bool = False
    demo_name: Optional[str] = None
    # Richer outputs exposed prominently (capped list at normal detail)
    sensations: List[Dict[str, Any]] = Field(default_factory=list, description="Coherent richer sensations (top N, detail normal by default)")
    state_summary: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="allow")


class StepResponse(BaseModel):
    """Result of a step call."""
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    tick: Optional[int] = None


class SensationsResponse(BaseModel):
    """Dedicated response for richer coherent sensations + summary (primary Saddle/HI path).

    Use this (or /state) to receive the synthesized 'felt' body experiences instead of raw metrics.
    Sensations capped; default normal detail ensures no overload for higher intelligence.
    """
    detail_level: str = "normal"
    sensations: List[Dict[str, Any]] = Field(default_factory=list, description="Rich structured sensations (capped)")
    state_summary: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="allow")


class EventMessage(BaseModel):
    """Generic event pushed over WebSocket."""
    type: str   # "state", "reflex_trace", "learner_update", "log", "error", etc.
    data: Dict[str, Any] = Field(default_factory=dict)
    ts: Optional[float] = None
    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------------
# Convenience type aliases for server code
# ------------------------------------------------------------------

ThoughtSeed = ThoughtSeedRequest
Reward = RewardRequest
BeginDemo = BeginDemoRequest
EndDemo = EndDemoRequest
InjectStimulus = InjectStimulusRequest
Step = StepRequest
Command = CommandRequest
