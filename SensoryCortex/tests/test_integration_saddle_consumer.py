"""Unit tests for Saddle consumer / integration helpers (no live server required)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex.integration import (
    experience_to_dict,
    try_create_cortex,
    SaddleEventConsumer,
)
from SensoryCortex.adapters import from_state_payload


def test_try_create_cortex():
    c = try_create_cortex(mode="embedded")
    assert c is not None
    assert c.status()["mode"] == "embedded"


def test_consumer_ingest_payload():
    cortex = try_create_cortex(mode="service")
    consumer = SaddleEventConsumer(
        base_url="http://127.0.0.1:9",  # unused
        cortex=cortex,
        use_websocket=False,
    )
    payload = {
        "tick": 3,
        "context": {"valence": 0.1, "arousal": 0.7, "dominance": 0.5, "active_patterns": []},
        "last_actions": [{"kind": "flinch"}],
        "sensations": [
            {
                "description": "Firm contact",
                "zone": "chest",
                "intensity": 0.8,
                "arousal_modulated_richness": 0.4,
                "temporal_quality": "sudden",
                "texture_qualities": ["firm"],
            }
        ],
        "state_summary": {
            "arousal_estimate": 0.7,
            "valence_estimate": 0.1,
            "contact_state": "firm",
        },
    }
    consumer._ingest_state_payload(payload)
    assert consumer.last_experience is not None
    assert consumer.last_experience["affective_core"]["arousal"] == 0.7
    exp = experience_to_dict(
        cortex.process_coherent_input(from_state_payload(payload), force=True)
    )
    assert exp is not None
    assert exp["salient_sensations"]


def test_from_state_payload_fields():
    c = from_state_payload(
        {
            "tick": 1,
            "context": {"arousal": 0.5, "valence": 0.0},
            "last_actions": [{"kind": "orient"}],
            "sensations": [],
            "state_summary": {"arousal_estimate": 0.5, "valence_estimate": 0.0},
        }
    )
    assert "orient" in c["reflex_activity"]
    assert c["source"] == "saddle"
