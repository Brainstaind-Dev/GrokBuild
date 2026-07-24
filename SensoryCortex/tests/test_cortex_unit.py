"""Unit tests for Sensory Cortex (no ReflexKernel required)."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex import SensoryCortex, load_config, SalientSensation
from SensoryCortex.adapters import from_abstraction_dicts, from_state_payload


@pytest.fixture
def cortex():
    cfg = load_config()
    d = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
    d["interface"]["min_interval_seconds"] = 0.05
    return SensoryCortex(config=d, mode="embedded")


def _rich_sensation(**overrides):
    base = {
        "description": "Sustained warm pressure on upper inner thigh",
        "zone": "upper_inner_thigh",
        "intensity": 0.8,
        "valence": 0.3,
        "arousal_contribution": 0.4,
        "novelty": 0.7,
        "category": "combined_touch",
        "temporal_quality": "sustained",
        "texture_qualities": ["warm", "smooth", "tingling"],
        "movement_quality": "gentle stroking",
        "arousal_modulated_richness": 0.72,
        "zone_character": "high-sensitivity erogenous zone",
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def test_package_import():
    from SensoryCortex import SensoryCortex, SalientSensation, SensoryUpdate

    assert SensoryCortex is not None
    assert SalientSensation is not None
    assert SensoryUpdate is not None


def test_rich_fields_preserved(cortex):
    coherent = from_abstraction_dicts(
        sensations=[_rich_sensation()],
        body_state={"valence_estimate": 0.3, "arousal_estimate": 0.75},
        reflex_activity=["orient"],
        affective={"valence": 0.3, "arousal": 0.75, "dominance": 0.5},
    )
    update = cortex.process_coherent_input(coherent)
    assert update is not None
    assert len(update.salient_sensations) >= 1
    s = update.salient_sensations[0]
    assert isinstance(s, SalientSensation)
    assert "warm pressure" in s.description
    assert s.arousal_modulated_richness == pytest.approx(0.72)
    assert s.temporal_quality == "sustained"
    assert "tingling" in s.texture_qualities
    assert s.zone_character and "erogenous" in s.zone_character
    assert s.movement_quality == "gentle stroking"
    assert update.token_estimate < 400
    assert update.token_estimate > 0


def test_cap_max_sensations(cortex):
    sensations = [
        _rich_sensation(description=f"s{i}", intensity=0.9 - i * 0.05, novelty=0.5)
        for i in range(8)
    ]
    coherent = from_abstraction_dicts(
        sensations=sensations,
        body_state={"arousal_estimate": 0.6, "valence_estimate": 0.1},
    )
    update = cortex.process_coherent_input(coherent)
    assert update is not None
    assert len(update.salient_sensations) <= 3


def test_from_state_payload_saddle_shape(cortex):
    payload = {
        "tick": 12,
        "context": {"valence": 0.1, "arousal": 0.55, "dominance": 0.4, "active_patterns": ["x"]},
        "last_actions": [{"kind": "flinch"}, {"kind": "autonomic"}],
        "sensations": [_rich_sensation()],
        "state_summary": {
            "arousal_estimate": 0.55,
            "valence_estimate": 0.1,
            "contact_state": "firm",
        },
    }
    coherent = from_state_payload(payload)
    assert "flinch" in coherent["reflex_activity"]
    update = cortex.process_coherent_input(coherent)
    assert update is not None
    assert update.affective_core.arousal == pytest.approx(0.55)


def test_should_emit_rate_gate(cortex):
    coherent = from_abstraction_dicts(
        sensations=[_rich_sensation(intensity=0.4, novelty=0.2)],
        body_state={"arousal_estimate": 0.4, "valence_estimate": 0.0},
        reflex_activity=["autonomic"],
        affective={"arousal": 0.4, "valence": 0.0, "dominance": 0.5},
    )
    # First emit allowed after process sets clock
    u1 = cortex.process_coherent_input(coherent, respect_gate=True, force=False)
    assert u1 is not None
    # Immediate second with only autonomic should throttle
    u2 = cortex.process_coherent_input(coherent, respect_gate=True, force=False)
    assert u2 is None
    # Non-autonomic reflex forces emit
    coherent2 = dict(coherent)
    coherent2["reflex_activity"] = ["flinch"]
    assert cortex.should_emit(coherent2) is True


def test_translator_shapes_without_dispatch(cortex):
    r = cortex.inject_thought("curiosity", 0.7, 0.4, 0.5, "hi", dispatch=False)
    assert r["dispatched"] is False
    assert r["command"]["type"] == "thought_seed"
    assert r["command"]["emotion"] == "curiosity"


class _FakeAPI:
    def __init__(self):
        self.thoughts = []
        self.rewards = []

    def inject_thought(self, seed):
        self.thoughts.append(seed)

    def reward(self, value, reason="", window=1):
        self.rewards.append((value, reason, window))

    def begin_demo(self, name):
        pass

    def end_demo(self, outcome=None):
        pass


def test_bind_and_dispatch(cortex):
    api = _FakeAPI()
    cortex.bind_reflex(api)
    r = cortex.inject_thought("startle", 0.9, -0.5, 0.9, "bang")
    assert r["dispatched"] is True
    assert api.thoughts and api.thoughts[0]["emotion"] == "startle"
    r2 = cortex.send_reward(0.5, "good")
    assert r2["dispatched"] is True
    assert api.rewards


def test_memory_trend(cortex):
    for i, a in enumerate([0.3, 0.4, 0.55, 0.7]):
        coherent = from_abstraction_dicts(
            sensations=[_rich_sensation(intensity=a)],
            body_state={"arousal_estimate": a, "valence_estimate": 0.1},
            affective={"arousal": a, "valence": 0.1, "dominance": 0.5},
        )
        cortex.process_coherent_input(coherent)
    assert "rising" in cortex.get_trend().lower() or "stable" in cortex.get_trend().lower()
