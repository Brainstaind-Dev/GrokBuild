"""
Core data types for ReflexKernel.

All public data exchanged between layers uses these (or Pydantic) models.
They are designed to be:
- Easy to serialize (JSON for interface layer)
- Rich enough for fusion, learning, and debugging
- Stable across versions (additive changes preferred)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Modality(str, Enum):
    """Sensory modalities understood by the kernel."""
    VISION = "vision"
    AUDIO = "audio"
    PROPRIO = "proprio"          # internal body state (simulated or real)
    TOUCH = "touch"
    THOUGHT = "thought"          # injected by higher intelligence
    SIM = "sim"                  # pure simulation / scripted events
    OTHER = "other"


class ReflexKind(str, Enum):
    """Canonical reflex / actuation kinds."""
    FLINCH = "flinch"
    BLINK = "blink"
    TENSION = "tension"
    RELAX = "relax"
    ORIENT = "orient"
    FREEZE = "freeze"
    MICRO_EXPRESSION = "micro_expression"
    AUTONOMIC = "autonomic"      # heart_rate, breathing, muscle tone etc.
    CUSTOM = "custom"


@dataclass
class Stimulus:
    """
    A single normalized sensory (or injected) event.

    All sensors and the thought bridge produce these.
    """
    modality: Modality | str
    data: Dict[str, Any]                 # modality-specific payload (keep small)
    ts: float = field(default_factory=time.perf_counter)
    confidence: float = 1.0
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        mod = self.modality.value if isinstance(self.modality, Modality) else str(self.modality)
        return {
            "modality": mod,
            "data": self.data,
            "ts": self.ts,
            "confidence": float(self.confidence),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Stimulus":
        if isinstance(d, cls):
            return d
        if not isinstance(d, dict):
            raise TypeError(f"Stimulus.from_dict expects dict or Stimulus, got {type(d)!r}")
        mod = d.get("modality", "other")
        try:
            modality = Modality(mod)
        except ValueError:
            modality = mod
        return cls(
            modality=modality,
            data=d.get("data", {}) or {},
            ts=float(d.get("ts", time.perf_counter())),
            confidence=float(d.get("confidence", 1.0)),
            source=str(d.get("source", "unknown")),
        )


def normalize_stimuli(items: Optional[List[Any]]) -> List[Stimulus]:
    """
    Accept mixed extra_stimuli from abstraction (dicts), Python API (Stimulus),
    or JSON/Saddle payloads. Silently skips unconvertible items.
    """
    if not items:
        return []
    out: List[Stimulus] = []
    for item in items:
        if isinstance(item, Stimulus):
            out.append(item)
        elif isinstance(item, dict):
            try:
                out.append(Stimulus.from_dict(item))
            except Exception:
                continue
        else:
            # e.g. pydantic model with model_dump / to_dict
            try:
                if hasattr(item, "to_dict") and callable(item.to_dict):
                    out.append(Stimulus.from_dict(item.to_dict()))
                elif hasattr(item, "model_dump") and callable(item.model_dump):
                    out.append(Stimulus.from_dict(item.model_dump()))
            except Exception:
                continue
    return out


@dataclass
class AffectiveContext:
    """
    Unified "felt state" after fusion of real stimuli + thought seeds.

    This is the main context object fed to ReflexCore and Learner.
    Values are typically in [-1, 1] unless otherwise documented.
    """
    valence: float = 0.0          # negative (bad / aversive) ... positive (good / appetitive)
    arousal: float = 0.3          # calm ... highly activated / alert
    dominance: float = 0.0        # controlled / in charge ... overwhelmed / submissive
    urgency: float = 0.0          # 0 = normal, higher = immediate action bias

    salient_stimuli: List[Stimulus] = field(default_factory=list)
    active_patterns: List[str] = field(default_factory=list)   # e.g. ["sudden_loud", "threat_face", "curiosity_seed"]

    ts: float = field(default_factory=time.perf_counter)
    meta: Dict[str, Any] = field(default_factory=dict)

    def clamp(self) -> None:
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.5, self.arousal))
        self.dominance = max(-1.0, min(1.0, self.dominance))
        self.urgency = max(0.0, min(2.0, self.urgency))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
            "dominance": round(self.dominance, 4),
            "urgency": round(self.urgency, 4),
            "active_patterns": list(self.active_patterns),
            "salient_count": len(self.salient_stimuli),
            "ts": self.ts,
        }


@dataclass
class ReflexAction:
    """A single motor / expression / internal command emitted by reflexes or learned policies."""
    kind: ReflexKind | str
    target: str                       # e.g. "face", "neck", "shoulders", "autonomic"
    intensity: float = 0.6            # 0..1+
    duration_ms: int = 180
    params: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.perf_counter)
    source: str = "reflex"            # "reflex", "learned", "override", "higher"

    def to_dict(self) -> Dict[str, Any]:
        kind = self.kind.value if isinstance(self.kind, ReflexKind) else str(self.kind)
        return {
            "kind": kind,
            "target": self.target,
            "intensity": round(float(self.intensity), 3),
            "duration_ms": int(self.duration_ms),
            "params": self.params,
            "ts": self.ts,
            "source": self.source,
        }


@dataclass
class ReflexTrace:
    """Audit / explanation record for why a reflex (or learned behavior) fired."""
    name: str
    trigger: str
    actions: List[ReflexAction]
    latency_ms: float
    affective_snapshot: Dict[str, Any]
    modulated_by: List[str] = field(default_factory=list)
    ts: float = field(default_factory=time.perf_counter)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trigger": self.trigger,
            "actions": [a.to_dict() for a in self.actions],
            "latency_ms": round(self.latency_ms, 2),
            "affective_snapshot": self.affective_snapshot,
            "modulated_by": self.modulated_by,
            "ts": self.ts,
        }


@dataclass
class RewardSignal:
    """Scalar (or lightly shaped) feedback from higher intelligence."""
    value: float
    reason: str = ""
    window_steps: int = 1
    meta: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.perf_counter)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": float(self.value),
            "reason": self.reason,
            "window_steps": int(self.window_steps),
            "meta": self.meta,
            "ts": self.ts,
        }


@dataclass
class DemonstrationStep:
    """One step recorded during an imitation learning session."""
    stimuli: List[Stimulus]
    context: AffectiveContext
    teacher_action: Optional[ReflexAction]
    outcome: Dict[str, Any] = field(default_factory=dict)   # e.g. {"reward": 0.3, "notes": "..."}
    ts: float = field(default_factory=time.perf_counter)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stimuli": [s.to_dict() for s in self.stimuli],
            "context": self.context.to_dict(),
            "teacher_action": self.teacher_action.to_dict() if self.teacher_action else None,
            "outcome": self.outcome,
            "ts": self.ts,
        }


# Convenience type aliases
StimulusBatch = List[Stimulus]
ActionBatch = List[ReflexAction]
TraceBatch = List[ReflexTrace]
