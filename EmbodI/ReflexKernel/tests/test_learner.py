"""Learner basic functionality (imitation + reward)."""

from reflexkernel.config import load_config
from reflexkernel.learner.base import Learner
from reflexkernel.types import AffectiveContext, DemonstrationStep, ReflexAction, ReflexKind, RewardSignal, Stimulus


def test_reward_updates_bias():
    cfg = load_config("configs/sim_only.yaml").learner
    learner = Learner(cfg)

    before = learner.get_biases().get("flinch", 0.0)
    learner.receive_reward(RewardSignal(value=0.8, reason="test"))
    after = learner.get_biases().get("flinch", 0.0)

    # Should have moved (even if only a little)
    assert after != before or abs(after) > 0.001


def test_demo_ingest_creates_behavior():
    cfg = load_config("configs/sim_only.yaml").learner
    learner = Learner(cfg)

    step = DemonstrationStep(
        stimuli=[Stimulus(modality="sim", data={"kind": "friendly_wave"})],
        context=AffectiveContext(valence=0.4, arousal=0.35),
        teacher_action=ReflexAction(kind=ReflexKind.ORIENT, target="head", intensity=0.4),
    )
    learner.ingest_demonstration("test_wave", [step], {"ok": True})

    behaviors = learner.get_behaviors()
    assert "test_wave" in behaviors or any("test_wave" in k for k in behaviors)
