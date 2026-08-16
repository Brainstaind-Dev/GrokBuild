"""Activation pattern v0 schema + producer."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex import SensoryCortex, load_config
from SensoryCortex.activation_pattern import (
    CORE_ZONES,
    SCHEMA_VERSION,
    build_activation_pattern,
    pattern_to_compact_feel_line,
)
from SensoryCortex.adapters import from_abstraction_dicts


@pytest.fixture
def cortex():
    cfg = load_config()
    d = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
    d["interface"]["min_interval_seconds"] = 0.05
    return SensoryCortex(config=d, mode="embedded")


def test_build_pattern_core_zones_and_clamps():
    coherent = {
        "affective": {"valence": 0.3, "arousal": 0.75, "dominance": 0.5},
        "body_state": {"dominant_zone": "ear_L", "arousal_estimate": 0.75},
        "sensations": [
            {
                "description": "sharp left ear sound",
                "zone": "ear_L",
                "intensity": 0.9,
                "arousal_modulated_richness": 0.85,
            }
        ],
        "reflex_activity": ["orient", "flinch"],
        "active_patterns": ["sudden_loud"],
        "source_path": "sim",
        "tick": 12,
    }
    p = build_activation_pattern(coherent)
    d = p.to_public_dict()
    assert d["schema_version"] == SCHEMA_VERSION
    assert d["source_path"] == "sim"
    assert d["tick"] == 12
    assert "global" in d
    assert 0.0 <= d["global"]["arousal"] <= 1.0
    assert -1.0 <= d["global"]["valence"] <= 1.0
    for z in CORE_ZONES:
        assert z in d["zones"]
    assert d["zones"]["ear_L"] >= 0.85
    assert d["reflexes"]["orient"] > 0
    assert d["reflexes"]["flinch"] > 0
    assert d["salience"]["dominant_zone"] == "ear_L"
    assert "sudden_loud" in d["salience"]["active_pattern_ids"]


def test_nan_and_oob_clamped():
    p = build_activation_pattern(
        {
            "affective": {"valence": 5.0, "arousal": -1.0, "dominance": float("nan")},
            "sensations": [],
        }
    )
    g = p.to_public_dict()["global"]
    assert g["valence"] == 1.0
    assert g["arousal"] == 0.0
    assert g["dominance"] == -1.0 or g["dominance"] == 0.0 or -1.0 <= g["dominance"] <= 1.0


def test_cortex_experience_includes_activation_pattern(cortex):
    coherent = from_abstraction_dicts(
        sensations=[
            {
                "description": "warm pressure chest",
                "zone": "chest",
                "intensity": 0.7,
                "valence": 0.2,
                "arousal_contribution": 0.4,
                "novelty": 0.5,
                "arousal_modulated_richness": 0.6,
            }
        ],
        body_state={"valence_estimate": 0.2, "arousal_estimate": 0.6, "dominant_zone": "chest"},
        reflex_activity=["autonomic"],
        affective={"valence": 0.2, "arousal": 0.6, "dominance": 0.5},
    )
    coherent["source_path"] = "sim"
    update = cortex.process_coherent_input(coherent)
    assert update is not None
    assert update.activation_pattern is not None
    ap = update.activation_pattern
    assert ap["schema_version"] == SCHEMA_VERSION
    assert ap["zones"]["chest"] > 0
    line = pattern_to_compact_feel_line(ap)
    assert line.startswith("feel:")
    assert "arousal=" in line


def test_extended_zone_maps_to_core():
    p = build_activation_pattern(
        {
            "affective": {"valence": 0.1, "arousal": 0.5, "dominance": 0.5},
            "sensations": [
                {"zone": "nipples_areola", "intensity": 0.8, "description": "x"}
            ],
        }
    )
    d = p.to_public_dict()
    assert d["zones"]["chest"] >= 0.8


def test_hi_v01_solar_plexus_and_derived_reflexes():
    """HI feedback pass: solar_plexus core + jaw/shoulder/breath residuals."""
    p = build_activation_pattern(
        {
            "affective": {"valence": -0.1, "arousal": 0.55, "dominance": 0.4, "urgency": 0.2},
            "sensations": [
                {
                    "zone": "solar_plexus",
                    "intensity": 0.7,
                    "description": "mid-torso hold",
                }
            ],
            "reflex_activity": ["tension", "freeze", "autonomic"],
            "body_state": {"dominant_zone": "solar_plexus"},
        }
    )
    d = p.to_public_dict()
    assert "solar_plexus" in d["zones"]
    assert d["zones"]["solar_plexus"] >= 0.7
    assert d["reflexes"]["jaw_clench"] > 0
    assert d["reflexes"]["shoulder_elevation"] > 0
    assert d["reflexes"]["breath_depth"] > 0
    assert d["meta"].get("pattern_rev") == "0.1"
