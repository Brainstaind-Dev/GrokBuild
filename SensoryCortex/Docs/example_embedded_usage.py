# example_embedded_usage.py
"""Minimal embedded usage — coherent input path (aligned with ReflexKernel)."""

from datetime import datetime
import sys
from pathlib import Path

# Repo root
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from SensoryCortex.cortex import SensoryCortex
from SensoryCortex.config import load_config
from SensoryCortex.adapters import from_abstraction_dicts


def main():
    config = load_config()
    cfg = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    cortex = SensoryCortex(config=cfg, mode="embedded")

    print("Sensory Cortex started in embedded mode")
    print(cortex.status())

    # Coherent input as produced by RK Coherence / Saddle (not raw FSR fusion)
    coherent = from_abstraction_dicts(
        sensations=[
            {
                "description": (
                    "Sustained warm pressure with a gentle stroking quality "
                    "across my left forearm"
                ),
                "zone": "left_forearm",
                "intensity": 0.82,
                "valence": 0.25,
                "arousal_contribution": 0.35,
                "novelty": 0.9,
                "category": "combined_touch",
                "temporal_quality": "sustained",
                "texture_qualities": ["warm", "smooth"],
                "movement_quality": "gentle stroking",
                "arousal_modulated_richness": 0.55,
                "zone_character": "tactile surface",
            },
            {
                "description": "Light contact on the chest",
                "zone": "chest",
                "intensity": 0.31,
                "valence": 0.1,
                "novelty": 0.2,
                "temporal_quality": "sustained",
                "texture_qualities": ["soft"],
                "arousal_modulated_richness": 0.1,
            },
        ],
        body_state={
            "valence_estimate": 0.25,
            "arousal_estimate": 0.68,
            "contact_state": "firm",
            "dominant_zone": "left_forearm",
        },
        reflex_activity=["flinch", "orient"],
        active_patterns=["startle_response"],
        affective={"valence": 0.25, "arousal": 0.68, "dominance": 0.55},
    )
    coherent["timestamp"] = datetime.now()
    coherent["arousal_increased"] = True
    coherent["new_contact"] = True
    coherent["sound_triggered"] = True

    experience = cortex.process_coherent_input(coherent)
    assert experience is not None

    print("\n--- Current Experience ---")
    print(f"Mood: {experience.affective_core.overall_mood}")
    print(
        f"Valence: {experience.affective_core.valence} | "
        f"Arousal: {experience.affective_core.arousal}"
    )
    print(
        f"Salient sensations: {[s.description for s in experience.salient_sensations]}"
    )
    if experience.salient_sensations:
        top = experience.salient_sensations[0]
        print(
            f"Top richness={top.arousal_modulated_richness} "
            f"temporal={top.temporal_quality} textures={top.texture_qualities}"
        )
    print(f"Delta: {experience.delta_from_last}")
    print(f"Estimated tokens: {experience.token_estimate}")

    # Without bind_reflex, commands are shaped but not dispatched
    thought = cortex.inject_thought(
        emotion="curiosity",
        intensity=0.7,
        valence=0.4,
        arousal=0.65,
        text="Interesting contact pattern. Exploring the source.",
    )
    print("\n--- Thought seed (shaped) ---")
    print(thought)

    reward = cortex.send_reward(
        value=0.6,
        reason="Appropriate startle followed by orientation",
        window_steps=5,
    )
    print("\n--- Reward (shaped) ---")
    print(reward)

    print("\n--- Memory ---")
    print(cortex.get_trend())
    print(f"Recent context length: {len(cortex.get_recent_context())}")


if __name__ == "__main__":
    main()
