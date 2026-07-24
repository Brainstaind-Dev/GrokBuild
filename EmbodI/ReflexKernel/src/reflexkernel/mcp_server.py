"""
ReflexKernel MCP server — stdio tools for agent-driven embodied interaction.

Exposes simulation-first control + prominently surfaces richer coherent sensations
(Sensation objects) + state summaries for higher intelligence (default normal detail + cap=3 to avoid overload).
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .interface.python_api import PythonAPI
from .kernel import ReflexKernel
from .abstraction import VirtualSensorSimulator, get_coherent_sensations, get_capped_coherent_sensations, AbstractionOutput
from .abstraction.schema import DetailLevel

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PACKAGE_ROOT / "configs" / "mcp_headless.yaml"

mcp = FastMCP("reflexkernel")


class KernelSession:
    """Thread-safe singleton kernel session for MCP tool calls.

    Holds one shared VirtualSensorSimulator + optional Sensory Cortex for
    low-latency HI packaging (no new sim per status poll).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._api: Optional[PythonAPI] = None
        self._config_path: Optional[Path] = None
        self._shared_sim: Optional[VirtualSensorSimulator] = None
        self._cortex: Any = None

    def _resolve_config_path(self) -> Path:
        env_path = os.environ.get("REFLEXKERNEL_CONFIG")
        if env_path:
            return Path(env_path).expanduser().resolve()
        if _DEFAULT_CONFIG.is_file():
            return _DEFAULT_CONFIG
        return Path("configs/mcp_headless.yaml").resolve()

    def ensure_started(self) -> PythonAPI:
        with self._lock:
            if self._api is not None:
                return self._api
            config_path = self._resolve_config_path()
            kernel = ReflexKernel.from_config_path(config_path)
            api = PythonAPI(kernel)
            api.start()
            self._api = api
            self._config_path = config_path
            self._shared_sim = VirtualSensorSimulator()
            self._cortex = self._try_attach_cortex(api)
            return api

    def _try_attach_cortex(self, api: PythonAPI) -> Any:
        try:
            # mcp_server.py → …/GrokBuild (parents: reflexkernel, src, ReflexKernel, EmbodI, GrokBuild)
            grok_root = Path(__file__).resolve().parents[4]
            if str(grok_root) not in sys.path:
                sys.path.insert(0, str(grok_root))
            from SensoryCortex.integration import try_create_cortex

            return try_create_cortex(mode="embedded", bind_api=api)
        except Exception:
            return None

    def shared_sim(self) -> VirtualSensorSimulator:
        self.ensure_started()
        if self._shared_sim is None:
            self._shared_sim = VirtualSensorSimulator()
        return self._shared_sim

    def cortex(self) -> Any:
        self.ensure_started()
        return self._cortex

    def drive_shared(self, steps: int = 1, detail_level: str = "normal") -> AbstractionOutput:
        """Drive the session-shared sim once and feed kernel (preferred HI path)."""
        api = self.ensure_started()
        sim = self.shared_sim()
        dl = (
            DetailLevel(detail_level)
            if detail_level in ("normal", "enhanced", "diagnostic")
            else DetailLevel.NORMAL
        )
        last_out: Optional[AbstractionOutput] = None
        for _ in range(max(1, steps)):
            raw = sim.read_all()
            last_out = sim.process(raw, detail_level=dl)
            stimuli = last_out.to_stimuli() if last_out is not None else []
            for st in stimuli:
                try:
                    from .types import Stimulus

                    s = Stimulus.from_dict(st) if isinstance(st, dict) else st
                    api.kernel.step(extra_stimuli=[s])
                except Exception:
                    pass
        if last_out is not None and hasattr(api.kernel, "set_last_sensations"):
            api.kernel.set_last_sensations(list(last_out.sensations or [])[:3])
        return last_out  # type: ignore[return-value]

    def log_dir(self) -> Path:
        self.ensure_started()
        assert self._api is not None
        return Path(self._api.kernel.cfg.output.log_dir)

    def config_path(self) -> str:
        self.ensure_started()
        return str(self._config_path or self._resolve_config_path())

    def reset(self) -> None:
        with self._lock:
            if self._api is not None:
                try:
                    self._api.stop()
                except Exception:
                    pass
            self._api = None
            self._config_path = None
            self._shared_sim = None
            self._cortex = None


_SESSION = KernelSession()


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def kernel_status() -> str:
    """Return kernel session status + prominently exposed richer sensations/summary for HI.

    Sensations (coherent rich output) and state_summary attached at NORMAL detail by default.
    Uses the session-shared VirtualSensorSimulator (not a new sim per poll).
    """
    api = _SESSION.ensure_started()
    state = api.get_state()
    try:
        out = _SESSION.drive_shared(steps=1, detail_level="normal")
        rich_sens = [s.to_dict() for s in get_capped_coherent_sensations(out)] if out else []
        rich_summary = out.state_summary.to_dict() if out and out.state_summary else {}
    except Exception:
        rich_sens = []
        rich_summary = {}
        # Fall back to cached live sensations if drive fails
        for s in api.get_last_sensations():
            if hasattr(s, "to_dict"):
                rich_sens.append(s.to_dict())
            elif isinstance(s, dict):
                rich_sens.append(s)
    summary = {
        "config": _SESSION.config_path(),
        "tick": state.get("tick"),
        "running": state.get("running"),
        "demo_active": state.get("demo_active"),
        "context": state.get("context"),
        "last_action_count": len(state.get("last_actions") or []),
        "last_trace_count": len(state.get("last_traces") or []),
        "sensations": rich_sens,
        "state_summary": rich_summary,
        "cortex_attached": _SESSION.cortex() is not None,
    }
    return _json(summary)


@mcp.tool()
def inject_stimulus(
    kind: str,
    intensity: float = 0.7,
    modality: str = "sim",
    extra: Optional[Dict[str, Any]] = None,
    steps: int = 1,
) -> str:
    """
    Inject a simulated stimulus and advance the kernel.

    Args:
        kind: Stimulus kind (e.g. sudden_sound, friendly_wave, threat_face)
        intensity: Stimulus intensity 0.0–1.0
        modality: Sensory modality (default: sim)
        extra: Optional extra fields merged into stimulus data
        steps: Kernel ticks to run after injection (default 1)
    """
    api = _SESSION.ensure_started()
    data: Dict[str, Any] = {"kind": kind, "intensity": float(intensity), "sim": True}
    if extra:
        data.update(extra)
    api.inject_stimulus(modality=modality, data=data)
    actions_batches: List[List[Dict[str, Any]]] = []
    for _ in range(max(1, steps)):
        batch = api.kernel.step()
        actions_batches.append([a.to_dict() for a in batch])
    state = api.get_state()
    return _json(
        {
            "injected": {"modality": modality, "data": data},
            "steps": max(1, steps),
            "actions": actions_batches,
            "context": state.get("context"),
            "traces": state.get("last_traces"),
        }
    )


@mcp.tool()
def read_affective_state() -> str:
    """Read the current fused affective context + observable kernel state, with richer sensations and summary prominently included.

    Higher intelligence primary view now surfaces coherent Sensation output (normal detail, capped).
    Uses the session-shared simulator.
    """
    api = _SESSION.ensure_started()
    state = api.get_state()
    try:
        out = _SESSION.drive_shared(steps=1, detail_level="normal")
        if out is not None:
            state["sensations"] = [s.to_dict() for s in get_capped_coherent_sensations(out)]
            state["state_summary"] = (
                out.state_summary.to_dict() if out.state_summary else {}
            )
    except Exception:
        pass
    return _json(state)


@mcp.tool()
def get_reflex_traces(ticks: int = 1) -> str:
    """
    Advance the kernel and return reflex traces from the most recent tick(s).

    Args:
        ticks: Number of kernel ticks to run (default 1)
    """
    api = _SESSION.ensure_started()
    all_traces: List[Dict[str, Any]] = []
    for _ in range(max(1, ticks)):
        api.kernel.step()
        state = api.get_state()
        all_traces.extend(state.get("last_traces") or [])
    return _json({"ticks": max(1, ticks), "traces": all_traces, "context": api.get_state().get("context")})


@mcp.tool()
def inject_thought_seed(
    emotion: str = "neutral",
    intensity: float = 0.5,
    valence: float = 0.0,
    arousal: float = 0.5,
    steps: int = 1,
) -> str:
    """Inject an affective thought seed from higher intelligence, then advance the kernel."""
    api = _SESSION.ensure_started()
    seed = {
        "emotion": emotion,
        "intensity": float(intensity),
        "valence": float(valence),
        "arousal": float(arousal),
    }
    api.inject_thought(seed)
    for _ in range(max(1, steps)):
        api.kernel.step()
    state = api.get_state()
    return _json({"seed": seed, "context": state.get("context"), "traces": state.get("last_traces")})


@mcp.tool()
def run_demo_episode(
    scenario: str = "sudden_sound",
    steps: int = 8,
) -> str:
    """
    Run a named demonstration episode in simulation.

    Scenarios:
        sudden_sound — loud sharp noise (flinch-oriented)
        friendly_greet — friendly wave with calm priming
        threat_approach — threat face with startle priming
        calm_recovery — relaxing stimulus sequence
    """
    api = _SESSION.ensure_started()
    scenarios: Dict[str, List[Dict[str, Any]]] = {
        "sudden_sound": [
            {"type": "stimulus", "kind": "sudden_sound", "intensity": 0.95},
        ],
        "friendly_greet": [
            {"type": "thought", "emotion": "curiosity", "intensity": 0.4, "valence": 0.3, "arousal": 0.35},
            {"type": "stimulus", "kind": "friendly_wave", "intensity": 0.45},
        ],
        "threat_approach": [
            {"type": "thought", "emotion": "startle", "intensity": 0.7, "valence": -0.5, "arousal": 0.8},
            {"type": "stimulus", "kind": "threat_face", "intensity": 0.88},
        ],
        "calm_recovery": [
            {"type": "stimulus", "kind": "relaxing_sound", "intensity": 0.3},
            {"type": "stimulus", "kind": "calm", "intensity": 0.2},
        ],
    }
    script = scenarios.get(scenario)
    if script is None:
        return _json({"error": f"unknown scenario: {scenario}", "available": sorted(scenarios)})

    trace_log: List[Dict[str, Any]] = []
    for entry in script:
        if entry["type"] == "thought":
            api.inject_thought(
                {
                    "emotion": entry.get("emotion", "neutral"),
                    "intensity": entry.get("intensity", 0.5),
                    "valence": entry.get("valence", 0.0),
                    "arousal": entry.get("arousal", 0.5),
                }
            )
        elif entry["type"] == "stimulus":
            api.inject_stimulus(
                modality="sim",
                data={
                    "kind": entry["kind"],
                    "intensity": float(entry.get("intensity", 0.7)),
                    "sim": True,
                },
            )

    for _ in range(max(1, steps)):
        api.kernel.step()
        state = api.get_state()
        trace_log.append(
            {
                "tick": state.get("tick"),
                "context": state.get("context"),
                "traces": state.get("last_traces"),
                "actions": state.get("last_actions"),
            }
        )

    final = api.get_state()
    return _json(
        {
            "scenario": scenario,
            "steps": max(1, steps),
            "timeline": trace_log,
            "final_context": final.get("context"),
            "final_traces": final.get("last_traces"),
        }
    )


@mcp.tool()
def query_logs(
    limit: int = 20,
    event_type: Optional[str] = None,
    contains: Optional[str] = None,
) -> str:
    """
    Query recent structured JSONL logs from the kernel log directory.

    Args:
        limit: Maximum log lines to return (default 20, max 200)
        event_type: Filter by record field 't' (e.g. tick, stimulus, reflex)
        contains: Substring filter applied to the JSON line
    """
    log_dir = _SESSION.log_dir()
    if not log_dir.is_dir():
        return _json({"log_dir": str(log_dir), "lines": [], "note": "log directory not found"})

    max_limit = max(1, min(int(limit), 200))
    files = sorted(log_dir.glob("reflexkernel_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    lines: List[Dict[str, Any]] = []

    for path in files:
        try:
            content = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw in reversed(content):
            if contains and contains not in raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event_type and rec.get("t") != event_type:
                continue
            lines.append({"file": path.name, "record": rec})
            if len(lines) >= max_limit:
                break
        if len(lines) >= max_limit:
            break

    return _json({"log_dir": str(log_dir), "count": len(lines), "lines": lines})


@mcp.tool()
def send_reward(value: float, reason: str = "", window: int = 1) -> str:
    """Send a reinforcement-learning reward signal for recent kernel behavior."""
    api = _SESSION.ensure_started()
    api.reward(float(value), reason, window)
    return _json({"ok": True, "value": float(value), "reason": reason, "window": window})


@mcp.tool()
def get_coherent_sensations(detail_level: str = "normal", steps: int = 1) -> str:
    """
    Drive virtual abstraction path and return richer coherent sensations (with structured + NL fields).

    DEFAULT NORMAL for higher intelligence (prominent but non-overloading). Sensations capped.
    Uses the session-shared VirtualSensorSimulator.
    """
    dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
    last_out = _SESSION.drive_shared(steps=max(1, steps), detail_level=dl.value)
    capped = get_capped_coherent_sensations(last_out) if last_out is not None else []
    summary = last_out.state_summary.to_dict() if last_out is not None and last_out.state_summary else {}
    return _json({
        "detail_level": dl.value,
        "sensations": [s.to_dict() for s in capped],
        "state_summary": summary,
        "ticks": max(1, steps)
    })


@mcp.tool()
def get_body_state(detail_level: str = "normal") -> str:
    """Return enhanced body state summary (default NORMAL; lightweight primary view for HI).

    Richer sensations available via dedicated get_coherent_sensations (prominently exposed).
    """
    dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
    out = _SESSION.drive_shared(steps=1, detail_level=dl.value)
    summary = out.state_summary.to_dict() if out and out.state_summary else {}
    summary["detail_level"] = dl.value
    return _json({
        "detail_level": dl.value,
        "state_summary": summary
    })


# ------------------------------------------------------------------
# Sensory Cortex MCP tools (HI packaging layer)
# ------------------------------------------------------------------


@mcp.tool()
def cortex_get_experience(force: bool = False) -> str:
    """
    Get Sensory Cortex HI package: mood, salient sensations (rich fields), delta, trend.

    Prefer this for long agent sessions (token-minded envelope on top of RK sensations).
    force=True bypasses rate/salience gating.
    """
    api = _SESSION.ensure_started()
    cortex = _SESSION.cortex()
    try:
        out = _SESSION.drive_shared(steps=1, detail_level="normal")
    except Exception:
        out = None
    if cortex is None:
        # Fallback envelope without Cortex package
        sens = []
        if out is not None:
            sens = [s.to_dict() for s in get_capped_coherent_sensations(out)]
        return _json({
            "ok": True,
            "cortex_attached": False,
            "experience": {
                "sensations": sens,
                "context": api.get_state().get("context"),
                "source": "fallback_no_cortex",
            },
        })
    try:
        from SensoryCortex.adapters import from_kernel
        from SensoryCortex.integration import experience_to_dict

        body = None
        sens = None
        if out is not None:
            sens = list(out.sensations or [])[:3]
            if out.state_summary is not None:
                body = out.state_summary.to_dict()
        coherent = from_kernel(api.kernel, sensations=sens, body_state=body)
        update = cortex.process_coherent_input(
            coherent, respect_gate=not force, force=force
        )
        return _json({
            "ok": True,
            "cortex_attached": True,
            "experience": experience_to_dict(update),
            "gated": update is None,
        })
    except Exception as exc:
        return _json({"ok": False, "error": str(exc), "cortex_attached": True})


@mcp.tool()
def cortex_inject_thought(
    emotion: str = "neutral",
    intensity: float = 0.5,
    valence: float = 0.0,
    arousal: float = 0.5,
    text: str = "",
    steps: int = 1,
) -> str:
    """Shape (and dispatch) a thought seed via Sensory Cortex into ReflexKernel, then step."""
    api = _SESSION.ensure_started()
    cortex = _SESSION.cortex()
    if cortex is not None:
        result = cortex.inject_thought(
            emotion=emotion,
            intensity=float(intensity),
            valence=float(valence),
            arousal=float(arousal),
            text=text or "",
        )
    else:
        seed = {
            "emotion": emotion,
            "intensity": float(intensity),
            "valence": float(valence),
            "arousal": float(arousal),
            "text": text or "",
        }
        api.inject_thought(seed)
        result = {"command": seed, "dispatched": True, "ack": {"ok": True}, "via": "python_api"}
    for _ in range(max(1, steps)):
        api.kernel.step()
    return _json({"result": result, "context": api.get_state().get("context")})


@mcp.tool()
def cortex_send_reward(value: float, reason: str = "", window_steps: int = 6) -> str:
    """Send a reward through Sensory Cortex (or PythonAPI fallback)."""
    api = _SESSION.ensure_started()
    cortex = _SESSION.cortex()
    if cortex is not None:
        result = cortex.send_reward(float(value), reason, int(window_steps))
    else:
        api.reward(float(value), reason, int(window_steps))
        result = {"dispatched": True, "via": "python_api"}
    return _json({"ok": True, "result": result})


@mcp.tool()
def cortex_get_trend() -> str:
    """Return Sensory Cortex temporal trend summary over recent experiences."""
    cortex = _SESSION.cortex()
    if cortex is None:
        _SESSION.ensure_started()
        cortex = _SESSION.cortex()
    if cortex is None:
        return _json({"ok": False, "trend": None, "cortex_attached": False})
    return _json({"ok": True, "trend": cortex.get_trend(), "status": cortex.status()})


@mcp.tool()
def cortex_recall(max_age_minutes: int = 20) -> str:
    """Recall recent high-arousal Sensory Cortex experiences from embodied memory."""
    cortex = _SESSION.cortex()
    if cortex is None:
        _SESSION.ensure_started()
        cortex = _SESSION.cortex()
    if cortex is None:
        return _json({"ok": False, "items": [], "cortex_attached": False})
    items = cortex.recall(max_age_minutes=int(max_age_minutes))
    from SensoryCortex.integration import experience_to_dict

    return _json({
        "ok": True,
        "count": len(items),
        "items": [experience_to_dict(u) for u in items],
    })


@mcp.tool()
def reset_mcp_session() -> str:
    """Reset the MCP kernel session for clean state (used in tests and repeated runs)."""
    _SESSION.reset()
    return _json({"reset": True})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()