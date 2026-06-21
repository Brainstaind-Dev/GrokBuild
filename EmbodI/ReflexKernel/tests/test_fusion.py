"""Thought bridge / fusion tests."""

from reflexkernel.bridge.thought_bridge import ThoughtBridge
from reflexkernel.config import load_config
from reflexkernel.types import Modality, Stimulus


def test_structured_seed_and_fusion():
    cfg = load_config("configs/sim_only.yaml").bridge
    bridge = ThoughtBridge(cfg)

    # Inject a strong negative seed
    bridge.inject_seed({"emotion": "fear", "intensity": 0.9, "valence": -0.8, "arousal": 0.95})

    stimuli = [Stimulus(modality=Modality.SIM, data={"kind": "sudden_loud"})]
    ctx = bridge.fuse(stimuli)

    assert ctx.arousal > 0.6
    assert ctx.valence < -0.2
    assert any("fear" in p or "sudden" in p for p in ctx.active_patterns)
