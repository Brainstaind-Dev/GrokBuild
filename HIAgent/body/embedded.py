"""Embedded body: same process as ReflexKernel + Sensory Cortex."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_REPO = Path(__file__).resolve().parents[2]
_RK_SRC = _REPO / "EmbodI" / "ReflexKernel" / "src"


def _ensure_paths() -> None:
    for p in (str(_REPO), str(_RK_SRC)):
        if p not in sys.path:
            sys.path.insert(0, p)


class EmbeddedBodyBackend:
    """Low-latency in-process body via PythonAPI + shared VirtualSensorSimulator."""

    name = "embedded"

    def __init__(self, config: Any):
        _ensure_paths()
        self.config = config
        self._api = None
        self._kernel = None
        self._sim = None
        self._cortex = None
        self._started = False
        self._last_error: Optional[str] = None

    def start(self) -> None:
        if self._started:
            return
        from reflexkernel.kernel import ReflexKernel
        from reflexkernel.interface.python_api import PythonAPI
        from reflexkernel.abstraction.virtual import VirtualSensorSimulator
        from SensoryCortex.integration import try_create_cortex

        rk_path = getattr(self.config, "rk_config", None) or str(
            _REPO / "EmbodI" / "ReflexKernel" / "configs" / "sim_only.yaml"
        )
        # Prefer headless for agent unless viz explicitly enabled (set before init)
        enable_viz = bool(getattr(self.config, "enable_viz", False))
        overrides = None
        if not enable_viz:
            overrides = {"output": {"visualization": "none"}}
        kernel = ReflexKernel.from_config_path(str(rk_path), overrides=overrides)

        api = PythonAPI(kernel)
        api.start()
        self._kernel = kernel
        self._api = api
        self._sim = VirtualSensorSimulator()
        self._cortex = try_create_cortex(mode="embedded", bind_api=api)
        self._started = True
        # Warm body once
        try:
            self.feel(force=True)
        except Exception as exc:
            self._last_error = str(exc)

    def stop(self) -> None:
        if self._api is not None:
            try:
                self._api.stop()
            except Exception:
                pass
        self._api = None
        self._kernel = None
        self._sim = None
        self._cortex = None
        self._started = False

    def _require(self) -> None:
        if not self._started or self._api is None:
            raise RuntimeError("Embedded body not started")

    def feel(self, force: bool = False) -> Dict[str, Any]:
        self._require()
        from SensoryCortex.adapters import drive_shared_sim, from_kernel
        from SensoryCortex.integration import experience_to_dict

        out_dict: Dict[str, Any] = {"ok": True, "force": force}
        try:
            coherent = drive_shared_sim(
                self._kernel,
                self._sim,
                steps=1,
                feed_kernel=True,
            )
            if self._cortex is not None:
                update = self._cortex.process_coherent_input(
                    coherent, respect_gate=not force, force=force
                )
                if update is None and not force:
                    # Gated — still return light status
                    cur = self._cortex.get_current_experience()
                    out_dict["gated"] = True
                    out_dict["experience"] = experience_to_dict(cur)
                    out_dict["note"] = "Cortex gate skipped new package; returning last if any"
                    return out_dict
                out_dict["gated"] = False
                out_dict["experience"] = experience_to_dict(update)
            else:
                # Fallback without cortex
                from_k = from_kernel(self._kernel)
                out_dict["experience"] = {
                    "affective_core": from_k.get("affective"),
                    "salient_sensations": from_k.get("sensations", [])[:3],
                    "reflex_activity": from_k.get("reflex_activity"),
                    "delta_from_last": from_k.get("delta_from_last", ""),
                    "source": "fallback_no_cortex",
                }
                out_dict["cortex_attached"] = False
            out_dict["cortex_attached"] = self._cortex is not None
            out_dict["tick"] = (self._api.get_state() or {}).get("tick")
            return out_dict
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def body_snapshot(self) -> Dict[str, Any]:
        self._require()
        state = self._api.get_state()
        sens = []
        for s in self._api.get_last_sensations():
            if hasattr(s, "to_dict"):
                sens.append(s.to_dict())
            elif isinstance(s, dict):
                sens.append(s)
        return {
            "ok": True,
            "state": state,
            "sensations": sens[:3],
            "cortex": self._cortex.status() if self._cortex else None,
        }

    def inject_thought(
        self,
        emotion: str = "neutral",
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5,
        text: str = "",
    ) -> Dict[str, Any]:
        self._require()
        if self._cortex is not None:
            return self._cortex.inject_thought(
                emotion=emotion,
                intensity=float(intensity),
                valence=float(valence),
                arousal=float(arousal),
                text=text or "",
            )
        seed = {
            "emotion": emotion,
            "intensity": float(intensity),
            "valence": float(valence),
            "arousal": float(arousal),
            "text": text or "",
        }
        self._api.inject_thought(seed)
        return {"command": seed, "dispatched": True, "ack": {"ok": True}}

    def send_reward(
        self, value: float, reason: str = "", window_steps: int = 6
    ) -> Dict[str, Any]:
        self._require()
        if self._cortex is not None:
            return self._cortex.send_reward(
                float(value), reason, int(window_steps)
            )
        self._api.reward(float(value), reason, int(window_steps))
        return {"dispatched": True, "ack": {"ok": True}}

    def inject_stimulus(
        self,
        kind: str = "sudden_sound",
        intensity: float = 0.7,
        modality: str = "sim",
    ) -> Dict[str, Any]:
        self._require()
        data = {"kind": kind, "intensity": float(intensity), "sim": True}
        self._api.inject_stimulus(modality=modality, data=data)
        return {"ok": True, "injected": data}

    def step(self, n: int = 1) -> Dict[str, Any]:
        self._require()
        n = max(1, int(n))
        batches = self._api.step(n)
        return {
            "ok": True,
            "steps": n,
            "action_counts": [len(b) for b in batches],
            "tick": self._api.get_state().get("tick"),
        }

    def begin_demo(self, name: str) -> Dict[str, Any]:
        self._require()
        if self._cortex is not None:
            return self._cortex.begin_demonstration(name)
        self._api.begin_demo(name)
        return {"ok": True, "name": name, "dispatched": True}

    def end_demo(self, outcome: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._require()
        if self._cortex is not None:
            return self._cortex.end_demonstration(outcome=outcome or {})
        ended = self._api.end_demo(outcome)
        return {"ok": True, "ended": ended}

    def recall(self, max_age_minutes: int = 20) -> Dict[str, Any]:
        self._require()
        if self._cortex is None:
            return {"ok": False, "items": [], "error": "cortex not attached"}
        from SensoryCortex.integration import experience_to_dict

        items = self._cortex.recall(max_age_minutes=int(max_age_minutes))
        return {
            "ok": True,
            "count": len(items),
            "items": [experience_to_dict(u) for u in items],
        }

    def status(self) -> Dict[str, Any]:
        st: Dict[str, Any] = {
            "backend": self.name,
            "started": self._started,
            "cortex_attached": self._cortex is not None,
            "last_error": self._last_error,
        }
        if self._api is not None:
            try:
                ks = self._api.get_state()
                st["tick"] = ks.get("tick")
                st["running"] = ks.get("running")
                st["context"] = ks.get("context")
            except Exception as exc:
                st["state_error"] = str(exc)
        if self._cortex is not None:
            try:
                st["cortex"] = self._cortex.status()
            except Exception:
                pass
        return st
