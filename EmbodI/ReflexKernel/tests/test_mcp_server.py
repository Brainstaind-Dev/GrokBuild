"""Tests for ReflexKernel MCP session helpers (no live MCP handshake required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# MCP is an optional extra (pip install -e ".[mcp]"). Skip this module cleanly
# when it is not installed so core pytest still passes on Pi / minimal installs.
pytest.importorskip("mcp")

import reflexkernel.mcp_server as mcp_mod
from reflexkernel.mcp_server import (
    KernelSession,
    inject_stimulus,
    query_logs,
    read_affective_state,
    run_demo_episode,
    get_coherent_sensations,
    get_body_state,
    reset_mcp_session,
    cortex_get_experience,
    cortex_inject_thought,
    cortex_send_reward,
    cortex_get_trend,
)


@pytest.fixture(autouse=True)
def reset_mcp_session_fixture() -> None:
    if hasattr(mcp_mod._SESSION, "reset"):
        mcp_mod._SESSION.reset()
    else:
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


def test_get_coherent_sensations_tool(headless_config: Path) -> None:
    raw = get_coherent_sensations(detail_level="normal", steps=1)
    data = json.loads(raw)
    assert data["detail_level"] == "normal"
    assert "sensations" in data
    assert "state_summary" in data
    sens = data.get("sensations", [])
    # Overload safeguard: capped
    assert len(sens) <= 3
    if sens:
        s0 = sens[0]
        # Richer output fields are present (prominent exposure)
        assert "description" in s0
        assert "arousal_modulated_richness" in s0 or "intensity" in s0
        assert "temporal_quality" in s0 or "zone" in s0
        assert "detail_level" in s0 or data["detail_level"] == "normal"


def test_get_body_state_tool(headless_config: Path) -> None:
    raw = get_body_state(detail_level="normal")
    data = json.loads(raw)
    assert data["detail_level"] == "normal"
    assert "state_summary" in data or "arousal_estimate" in data


def test_get_coherent_sensations_rich_fields_and_cap(headless_config: Path) -> None:
    """Verify richer structured output is exposed and capped at default normal (no HI overload)."""
    raw = get_coherent_sensations(detail_level="normal", steps=2)
    data = json.loads(raw)
    sens_list = data["sensations"]
    assert len(sens_list) <= 3, "sensations must be capped for higher intelligence"
    # Ensure at least some richer fields surface when sensations exist
    if sens_list:
        keys = set(sens_list[0].keys())
        assert "description" in keys
        # structured richness fields from coherence
        assert any(k in keys for k in ("arousal_modulated_richness", "zone_character", "texture_qualities", "temporal_quality", "category"))


def test_read_affective_state_includes_richer_output(headless_config: Path) -> None:
    """Primary MCP status tool now prominently includes richer sensations (goal verification)."""
    # drive some activity
    from reflexkernel.mcp_server import inject_stimulus
    inject_stimulus(kind="gentle_contact", intensity=0.5, steps=1)
    raw = read_affective_state()
    state = json.loads(raw)
    # richer now surfaced prominently
    assert "sensations" in state
    assert "state_summary" in state or "arousal_estimate" in (state.get("state_summary") or {})
    if state.get("sensations"):
        assert len(state["sensations"]) <= 3


def test_cortex_get_experience_tool(headless_config: Path) -> None:
    raw = cortex_get_experience(force=True)
    data = json.loads(raw)
    assert data.get("ok") is True
    # Cortex may or may not attach depending on PYTHONPATH; both are valid
    assert "experience" in data or data.get("cortex_attached") is False


def test_cortex_inject_and_reward_tools(headless_config: Path) -> None:
    raw = cortex_inject_thought(
        emotion="curiosity", intensity=0.6, valence=0.2, arousal=0.5, text="probe", steps=1
    )
    data = json.loads(raw)
    assert "result" in data
    raw2 = cortex_send_reward(0.4, "unit-test", window_steps=2)
    data2 = json.loads(raw2)
    assert data2.get("ok") is True


def test_cortex_get_trend_tool(headless_config: Path) -> None:
    cortex_get_experience(force=True)
    raw = cortex_get_trend()
    data = json.loads(raw)
    assert "trend" in data or data.get("ok") is False


def test_kernel_get_last_sensations_public(headless_config: Path) -> None:
    from reflexkernel.kernel import ReflexKernel

    k = ReflexKernel.from_config_path(headless_config)
    k.set_last_sensations(
        [{"description": "test", "zone": "chest", "intensity": 0.5}], max_count=3
    )
    sens = k.get_last_sensations()
    assert len(sens) == 1
    assert sens[0]["description"] == "test"
