"""Bidirectional translator: HI intent → ReflexKernel command shapes (+ optional dispatch)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from .schemas import SensoryUpdate


class ReflexDispatch(Protocol):
    """Minimal surface we need from PythonAPI (or a thin wrapper)."""

    def inject_thought(self, seed: Dict[str, Any]) -> Any: ...
    def reward(self, value: float, reason: str = "", window: int = 1) -> Any: ...
    def begin_demo(self, name: str) -> Any: ...
    def end_demo(self, outcome: Optional[Dict[str, Any]] = None) -> Any: ...


class Translator:
    """
    Convert high-level thought seeds / rewards / demos into RK-compatible commands.
    Optionally dispatch through a bound PythonAPI-like object for real execution.
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.enable_modulation = bool(self.config.get("enable_state_modulation", True))
        self.dampen_threshold = float(
            self.config.get("high_arousal_dampen_threshold", 0.85)
        )
        self.curiosity_boost = float(self.config.get("calm_curiosity_boost", 0.15))
        self.max_intensity = float(self.config.get("max_intensity", 1.0))

    def to_reflexkernel(
        self,
        thought: Dict[str, Any],
        current_state: Optional[SensoryUpdate] = None,
    ) -> Dict[str, Any]:
        emotion = thought.get("emotion", "neutral")
        intensity = float(thought.get("intensity", 0.5))
        valence = float(thought.get("valence", 0.0))
        arousal = float(thought.get("arousal", 0.5))
        text = thought.get("text", "") or ""

        if self.enable_modulation and current_state is not None:
            body_arousal = current_state.affective_core.arousal
            if body_arousal > self.dampen_threshold:
                intensity = min(intensity, 0.7)
            if body_arousal < 0.3 and str(emotion).lower() in (
                "curiosity",
                "wonder",
                "interest",
            ):
                intensity = min(self.max_intensity, intensity + self.curiosity_boost)

        intensity = max(0.0, min(self.max_intensity, intensity))

        return {
            "type": "thought_seed",
            "emotion": emotion,
            "intensity": round(intensity, 2),
            "valence": round(valence, 2),
            "arousal": round(arousal, 2),
            "text": text,
            "source": "sensory_cortex",
        }

    def to_reward(
        self, value: float, reason: str = "", window_steps: int = 6
    ) -> Dict[str, Any]:
        return {
            "type": "reward",
            "value": max(-1.0, min(1.0, float(value))),
            "reason": reason,
            "window_steps": int(window_steps),
            "source": "sensory_cortex",
        }

    def to_demonstration(self, name: str, action: str = "begin") -> Dict[str, Any]:
        return {
            "type": f"demo_{action}",
            "name": name,
            "source": "sensory_cortex",
        }

    def dispatch(
        self,
        command: Dict[str, Any],
        api: Optional[ReflexDispatch],
    ) -> Dict[str, Any]:
        """Execute a shaped command against a bound RK API if available."""
        result: Dict[str, Any] = {"command": command, "dispatched": False, "ack": None}
        if api is None:
            return result

        ctype = command.get("type", "")
        try:
            if ctype == "thought_seed":
                seed = {
                    k: command[k]
                    for k in ("emotion", "intensity", "valence", "arousal", "text")
                    if k in command
                }
                api.inject_thought(seed)
                result["dispatched"] = True
                result["ack"] = {"ok": True}
            elif ctype == "reward":
                api.reward(
                    float(command.get("value", 0.0)),
                    str(command.get("reason", "")),
                    int(command.get("window_steps", 1)),
                )
                result["dispatched"] = True
                result["ack"] = {"ok": True}
            elif ctype == "demo_begin":
                api.begin_demo(str(command.get("name", "demo")))
                result["dispatched"] = True
                result["ack"] = {"ok": True}
            elif ctype == "demo_end":
                api.end_demo(command.get("outcome"))
                result["dispatched"] = True
                result["ack"] = {"ok": True}
            else:
                result["ack"] = {"ok": False, "error": f"unknown command type: {ctype}"}
        except Exception as exc:  # noqa: BLE001 — surface to HI without crashing cortex
            result["ack"] = {"ok": False, "error": str(exc)}
        return result
