"""Integration smoke: embedded body feel + inject (no xAI)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_RK = _ROOT / "EmbodI" / "ReflexKernel" / "src"
for p in (str(_ROOT), str(_RK)):
    if p not in sys.path:
        sys.path.insert(0, p)

pytest.importorskip("reflexkernel")
pytest.importorskip("SensoryCortex")


def test_embedded_feel_and_thought():
    from HIAgent.config import load_config
    from HIAgent.body.embedded import EmbeddedBodyBackend

    cfg = load_config(
        backend="embedded",
        enable_viz=False,
        rk_config=str(_ROOT / "EmbodI" / "ReflexKernel" / "configs" / "sim_only.yaml"),
    )
    body = EmbeddedBodyBackend(cfg)
    body.start()
    try:
        st = body.status()
        assert st["started"] is True
        felt = body.feel(force=True)
        assert felt.get("ok") is True
        assert "experience" in felt
        r = body.inject_thought(
            emotion="curiosity", intensity=0.5, valence=0.2, arousal=0.4, text="test"
        )
        assert r.get("dispatched") is True or r.get("ack", {}).get("ok")
        body.step(n=1)
    finally:
        body.stop()
