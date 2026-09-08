"""C′ Richness: AffectiveCore clamp so loud does not crash."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex.summarizer import Summarizer


def test_oob_affect_does_not_crash():
    s = Summarizer()
    update = s.summarize(
        {
            "affective": {"valence": 9.0, "arousal": 5.0, "dominance": -3.0},
            "sensations": [
                {
                    "description": "too loud",
                    "zone": "torso_front",
                    "intensity": 9.0,
                    "valence": -4.0,
                    "arousal_modulated_richness": 2.0,
                }
            ],
        }
    )
    core = update.affective_core
    assert -1.0 <= core.valence <= 1.0
    assert 0.0 <= core.arousal <= 1.0
    assert 0.0 <= core.dominance <= 1.0
    assert update.salient_sensations
    hit = update.salient_sensations[0]
    assert 0.0 <= hit.intensity <= 1.5
    assert 0.0 <= hit.arousal_modulated_richness <= 1.0


def test_high_arousal_fills_missing_richness():
    s = Summarizer()
    update = s.summarize(
        {
            "affective": {"valence": 0.2, "arousal": 0.9, "dominance": 0.5},
            "sensations": [
                {
                    "description": "press",
                    "zone": "torso_front",
                    "intensity": 0.8,
                }
            ],
        }
    )
    rich = update.salient_sensations[0].arousal_modulated_richness
    assert rich > 0.5
    assert rich <= 1.0
