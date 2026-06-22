"""Tests for ReflexKernel MCP session helpers (no live MCP handshake required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import reflexkernel.mcp_server as mcp_mod
from reflexkernel.mcp_server import (
    KernelSession,
    inject_stimulus,
    query_logs,
    read_affective_state,
    run_demo_episode,
)


@pytest.fixture(autouse=True)
def reset_mcp_session() -> None:
    mcp_mod._SESSION._api = None
    mcp_mod._SESSION._config_path = None


@pytest.fixture
def headless_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "mcp_headless.yaml"
    cfg.write_text(
        """
kernel:
  tick_rate_hz: 30
  log_level: "WARNING"
perception:
  enabled_sensors: [simulation]
  simulation:
    interactive: false
    auto_events: false
bridge:
  use_sentence_transformers: false
  use_sentiment: false
reflex:
  enabled_primitives: [flinch, tension]
learner:
  enabled: false
  store_path: "data/test_mcp"
output:
  visualization: "none"
  log_structured: true
  log_dir: "logs"
interface:
  mode: "none"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("REFLEXKERNEL_CONFIG", str(cfg))
    return cfg


def test_kernel_session_starts(headless_config: Path) -> None:
    session = KernelSession()
    api = session.ensure_started()
    assert api.kernel.state.tick == 0
    api.stop()


def test_inject_stimulus_tool(headless_config: Path) -> None:
    raw = inject_stimulus(kind="sudden_sound", intensity=0.9, steps=2)
    data = json.loads(raw)
    assert data["injected"]["data"]["kind"] == "sudden_sound"
    assert len(data["actions"]) == 2


def test_read_affective_state_tool(headless_config: Path) -> None:
    inject_stimulus(kind="friendly_wave", intensity=0.4, steps=1)
    raw = read_affective_state()
    state = json.loads(raw)
    assert "context" in state
    assert "tick" in state


def test_run_demo_episode_tool(headless_config: Path) -> None:
    raw = run_demo_episode(scenario="sudden_sound", steps=3)
    data = json.loads(raw)
    assert data["scenario"] == "sudden_sound"
    assert len(data["timeline"]) == 3


def test_query_logs_tool(headless_config: Path) -> None:
    inject_stimulus(kind="calm", intensity=0.2, steps=1)
    raw = query_logs(limit=5)
    data = json.loads(raw)
    assert "log_dir" in data
    assert "lines" in data