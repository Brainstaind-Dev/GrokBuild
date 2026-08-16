"""Regression: AbstractionOutput → Stimulus → kernel.step (dict and object paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

from reflexkernel.abstraction import VirtualSensorSimulator
from reflexkernel.abstraction.bridge import abstraction_to_stimuli
from reflexkernel.kernel import ReflexKernel
from reflexkernel.types import Stimulus, normalize_stimuli


@pytest.fixture
def sim_kernel(tmp_path):
    cfg = Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml"
    if not cfg.exists():
        pytest.skip("sim_only.yaml missing")
    k = ReflexKernel.from_config_path(str(cfg))
    # Avoid opening pygame window in CI/headless if possible
    k.start()
    yield k
    k.stop()


def test_to_stimuli_dicts_normalize_to_stimulus():
    sim = VirtualSensorSimulator()
    out = sim.process(sim.read_all())
    dicts = out.to_stimuli()
    assert dicts, "expected abstraction events/features"
    assert all(isinstance(d, dict) for d in dicts)
    # source should be plain strings (not "SensorSource.X")
    for d in dicts:
        assert "SensorSource." not in str(d.get("source", ""))
        assert isinstance(d.get("data"), dict)
    norms = normalize_stimuli(dicts)
    assert len(norms) == len(dicts)
    assert all(isinstance(s, Stimulus) for s in norms)


def test_abstraction_to_stimuli_returns_stimulus_objects():
    sim = VirtualSensorSimulator()
    out = sim.process(sim.read_all())
    stimuli = abstraction_to_stimuli(out)
    assert stimuli
    assert all(isinstance(s, Stimulus) for s in stimuli)
    # includes body_state_summary proprio
    assert any(
        s.modality in ("proprio", getattr(s.modality, "value", None) == "proprio")
        or (isinstance(s.modality, str) and s.modality == "proprio")
        or str(getattr(s.modality, "value", s.modality)) == "proprio"
        for s in stimuli
    )


def test_kernel_step_accepts_dicts_and_stimuli(sim_kernel):
    sim = VirtualSensorSimulator()
    out = sim.process(sim.read_all())
    dicts = out.to_stimuli()
    objs = abstraction_to_stimuli(out)

    # Must not raise (historical dict-vs-Stimulus break)
    a1 = sim_kernel.step(extra_stimuli=dicts)
    a2 = sim_kernel.step(extra_stimuli=objs)
    a3 = sim_kernel.step(extra_stimuli=dicts + objs)
    assert isinstance(a1, list)
    assert isinstance(a2, list)
    assert isinstance(a3, list)


def test_normalize_stimuli_mixed_and_bad():
    good = Stimulus(modality="touch", data={"type": "x"}, source="test")
    out = normalize_stimuli(
        [
            good,
            {"modality": "audio", "data": {"type": "y"}, "confidence": 0.5},
            "not-a-stimulus",
            None,
            {"modality": "vision", "data": {}},
        ]
    )
    assert len(out) == 3
    assert out[0] is good
    assert out[1].modality.value == "audio" or out[1].modality == "audio"
