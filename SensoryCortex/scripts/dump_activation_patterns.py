#!/usr/bin/env python3
"""Dump activation_pattern_v0 samples from sim / fixture scenarios for inspection + HI feedback."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex import SensoryCortex, load_config, pattern_to_compact_feel_line
from SensoryCortex.adapters import from_abstraction_dicts

OUT_DIR = _ROOT / "data" / "activation_pattern_samples"


SCENARIOS = [
    {
        "name": "quiet_baseline",
        "sensations": [
            {
                "description": "soft ambient body tone",
                "zone": "whole_body",
                "intensity": 0.15,
                "valence": 0.1,
                "arousal_contribution": 0.1,
                "novelty": 0.2,
                "arousal_modulated_richness": 0.12,
            }
        ],
        "body_state": {"arousal_estimate": 0.28, "valence_estimate": 0.1, "dominant_zone": "whole_body"},
        "affective": {"valence": 0.1, "arousal": 0.28, "dominance": 0.55},
        "reflex_activity": ["autonomic"],
        "active_patterns": [],
    },
    {
        "name": "loud_left_ear_startle",
        "sensations": [
            {
                "description": "sudden sharp sound at left ear",
                "zone": "ear_L",
                "intensity": 0.92,
                "valence": -0.35,
                "arousal_contribution": 0.8,
                "novelty": 0.95,
                "arousal_modulated_richness": 0.88,
            }
        ],
        "body_state": {"arousal_estimate": 0.82, "valence_estimate": -0.3, "dominant_zone": "ear_L"},
        "affective": {"valence": -0.3, "arousal": 0.82, "dominance": 0.28},
        "reflex_activity": ["orient", "flinch", "tension"],
        "active_patterns": ["sudden_loud"],
    },
    {
        "name": "chest_warm_contact",
        "sensations": [
            {
                "description": "sustained warm pressure on chest",
                "zone": "chest",
                "intensity": 0.7,
                "valence": 0.35,
                "arousal_contribution": 0.45,
                "novelty": 0.4,
                "arousal_modulated_richness": 0.62,
            }
        ],
        "body_state": {"arousal_estimate": 0.55, "valence_estimate": 0.35, "dominant_zone": "chest"},
        "affective": {"valence": 0.35, "arousal": 0.55, "dominance": 0.5},
        "reflex_activity": ["autonomic", "relax"],
        "active_patterns": ["gentle_contact"],
    },
    {
        "name": "solar_plexus_guard",
        "sensations": [
            {
                "description": "held tightness under the sternum",
                "zone": "solar_plexus",
                "intensity": 0.72,
                "valence": -0.1,
                "arousal_contribution": 0.5,
                "novelty": 0.5,
                "arousal_modulated_richness": 0.55,
            }
        ],
        "body_state": {
            "arousal_estimate": 0.58,
            "valence_estimate": -0.1,
            "dominant_zone": "solar_plexus",
        },
        "affective": {"valence": -0.1, "arousal": 0.58, "dominance": 0.42, "urgency": 0.25},
        "reflex_activity": ["tension", "autonomic"],
        "active_patterns": ["guarding"],
    },
    {
        "name": "neck_tension",
        "sensations": [
            {
                "description": "tight band at neck",
                "zone": "neck_throat",
                "intensity": 0.65,
                "valence": -0.15,
                "arousal_contribution": 0.5,
                "novelty": 0.55,
                "arousal_modulated_richness": 0.5,
            }
        ],
        "body_state": {"arousal_estimate": 0.6, "valence_estimate": -0.15, "dominant_zone": "neck_throat"},
        "affective": {"valence": -0.15, "arousal": 0.6, "dominance": 0.4},
        "reflex_activity": ["tension", "freeze"],
        "active_patterns": ["guarding"],
    },
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    d = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
    cortex = SensoryCortex(config=d, mode="embedded")

    index = []
    for i, sc in enumerate(SCENARIOS):
        coherent = from_abstraction_dicts(
            sensations=sc["sensations"],
            body_state=sc["body_state"],
            reflex_activity=sc["reflex_activity"],
            affective=sc["affective"],
        )
        coherent["active_patterns"] = sc.get("active_patterns") or []
        coherent["source_path"] = "sim"
        coherent["tick"] = 100 + i
        update = cortex.process_coherent_input(coherent, force=True)
        assert update is not None and update.activation_pattern
        ap = update.activation_pattern
        feel = pattern_to_compact_feel_line(ap)
        payload = {
            "scenario": sc["name"],
            "dumped_at": datetime.now(timezone.utc).isoformat(),
            "feel_line": feel,
            "mood": update.affective_core.overall_mood,
            "delta_from_last": update.delta_from_last,
            "activation_pattern": ap,
            "salient_sensations": [s.model_dump() for s in update.salient_sensations],
        }
        path = OUT_DIR / f"{sc['name']}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        index.append({"scenario": sc["name"], "file": path.name, "feel_line": feel})
        print(f"wrote {path}")
        print(f"  {feel}")

    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"index -> {OUT_DIR / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
