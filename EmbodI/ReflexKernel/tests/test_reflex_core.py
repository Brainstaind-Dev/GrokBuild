"""Reflex core + primitives tests."""

from reflexkernel.config import load_config
from reflexkernel.reflex.core import ReflexCore
from reflexkernel.types import AffectiveContext, Modality, Stimulus


def test_flinch_on_sudden_loud():
    cfg = load_config("configs/sim_only.yaml").reflex
    core = ReflexCore(cfg)

    stimuli = [Stimulus(modality=Modality.SIM, data={"kind": "sudden_loud"})]
    ctx = AffectiveContext(arousal=0.6, valence=-0.3)

    actions, traces = core.react(stimuli, ctx)
    assert len(actions) >= 1
    assert len(traces) >= 1
    assert any("flinch" in str(t.name) for t in traces)


def test_tension_requires_arousal():
    cfg = load_config("configs/sim_only.yaml").reflex
    core = ReflexCore(cfg)

    stimuli = []
    ctx = AffectiveContext(arousal=0.2, valence=0.1)  # low arousal

    actions, traces = core.react(stimuli, ctx)
    # tension should not fire at low arousal
    assert not any("tension" in str(t.name) for t in traces)
