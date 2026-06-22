"""
ReflexKernel MCP server — stdio tools for agent-driven embodied interaction.

Exposes simulation-first control of the kernel without parsing JSONL logs manually.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .interface.python_api import PythonAPI
from .kernel import ReflexKernel

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PACKAGE_ROOT / "configs" / "mcp_headless.yaml"

mcp = FastMCP("reflexkernel")


class KernelSession:
    """Thread-safe singleton kernel session for MCP tool calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._api: Optional[PythonAPI] = None
        self._config_path: Optional[Path] = None

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
            return api

    def log_dir(self) -> Path:
        self.ensure_started()
        assert self._api is not None
        return Path(self._api.kernel.cfg.output.log_dir)

    def config_path(self) -> str:
        self.ensure_started()
        return str(self._config_path or self._resolve_config_path())


_SESSION = KernelSession()


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def kernel_status() -> str:
    """Return kernel session status: tick, running state, config path, and last context summary."""
    api = _SESSION.ensure_started()
    state = api.get_state()
    summary = {
        "config": _SESSION.config_path(),
        "tick": state.get("tick"),
        "running": state.get("running"),
        "demo_active": state.get("demo_active"),
        "context": state.get("context"),
        "last_action_count": len(state.get("last_actions") or []),
        "last_trace_count": len(state.get("last_traces") or []),
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
    """Read the current fused affective context and observable kernel state."""
    api = _SESSION.ensure_started()
    return _json(api.get_state())


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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()