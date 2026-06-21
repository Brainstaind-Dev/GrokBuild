"""Basic type and serialization tests."""

from reflexkernel.types import AffectiveContext, Modality, ReflexAction, ReflexKind, Stimulus


def test_stimulus_roundtrip():
    s = Stimulus(modality=Modality.SIM, data={"kind": "sudden_loud"}, confidence=0.9, source="test")
    d = s.to_dict()
    s2 = Stimulus.from_dict(d)
    assert s2.modality == Modality.SIM
    assert s2.data["kind"] == "sudden_loud"


def test_affective_context_clamp():
    ctx = AffectiveContext(valence=2.0, arousal=-0.3, urgency=10)
    ctx.clamp()
    assert -1.0 <= ctx.valence <= 1.0
    assert ctx.arousal >= 0
    assert ctx.urgency <= 2.0


def test_reflex_action():
    a = ReflexAction(kind=ReflexKind.FLINCH, target="torso", intensity=0.8)
    d = a.to_dict()
    assert d["kind"] == "flinch"
    assert d["target"] == "torso"
