"""
Embedded runner — lowest-latency path: Cortex in-process with ReflexKernel.

Recommended host loop:
  kernel.step → (optional drive_shared_sim) → cortex.process_coherent_input
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Repo root on path for `import SensoryCortex`
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from SensoryCortex import SensoryCortex, load_config
from SensoryCortex.adapters import from_abstraction_dicts, from_kernel


def run_embedded(
    config_path: Optional[str] = None,
    demo: bool = False,
    duration_seconds: float = 20.0,
    with_reflexkernel: bool = False,
):
    """
    Start Sensory Cortex in embedded mode.

    Args:
        demo: simulated coherent inputs (no RK required)
        with_reflexkernel: if True and demo, use shared VirtualSensorSimulator + RK
    """
    config = load_config(config_path)
    # BaseSettings may not have nested mutability in all versions — rebuild
    cfg_dict = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    cfg_dict.setdefault("interface", {})["mode"] = "embedded"

    cortex = SensoryCortex(config=cfg_dict, mode="embedded")

    print("=" * 60)
    print("Sensory Cortex — Embedded Mode")
    print("=" * 60)
    print(cortex.status())
    print()

    if not demo:
        print("Cortex ready. Call cortex.process_coherent_input(...) from the host loop.")
        print("Prefer adapters.from_kernel / drive_shared_sim — not a new sim per poll.")
        return cortex

    if with_reflexkernel:
        return _demo_with_rk(cortex, duration_seconds)

    return _demo_synthetic(cortex, duration_seconds)


def _demo_synthetic(cortex: SensoryCortex, duration_seconds: float):
    print(f"Running synthetic coherent demo for {duration_seconds}s...\n")
    start = time.time()
    step = 0
    while time.time() - start < duration_seconds:
        step += 1
        intensity = 0.4 + (0.4 * abs((step % 10) - 5) / 5)
        is_event = step % 7 == 0
        coherent = from_abstraction_dicts(
            sensations=[
                {
                    "description": (
                        "Sudden firm contact on the left forearm with a sharp edge"
                        if is_event
                        else "Light ambient awareness across the skin"
                    ),
                    "zone": "left_forearm" if is_event else "chest",
                    "intensity": intensity if is_event else 0.25,
                    "valence": -0.1 if is_event else 0.1,
                    "arousal_contribution": intensity * 0.5,
                    "novelty": 0.85 if is_event else 0.3,
                    "category": "contact_pressure",
                    "temporal_quality": "sudden" if is_event else "sustained",
                    "texture_qualities": ["firm", "warm"] if is_event else ["soft"],
                    "arousal_modulated_richness": 0.4 if is_event else 0.1,
                    "zone_character": "tactile surface",
                }
            ],
            body_state={
                "valence_estimate": -0.1 if is_event else 0.1,
                "arousal_estimate": intensity,
                "contact_state": "firm" if is_event else "light",
            },
            reflex_activity=["flinch", "orient"] if is_event else ["autonomic"],
            active_patterns=["startle_response"] if is_event else [],
            affective={
                "valence": -0.1 if is_event else 0.1,
                "arousal": intensity,
                "dominance": 0.55,
            },
        )
        experience = cortex.process_coherent_input(coherent)
        if experience:
            print(
                f"[{step:03d}] Mood: {experience.affective_core.overall_mood:20} "
                f"| Arousal: {experience.affective_core.arousal:.2f} "
                f"| Sensations: {len(experience.salient_sensations)} "
                f"| Delta: {experience.delta_from_last} "
                f"| tokens~{experience.token_estimate}"
            )
        time.sleep(0.5)

    print("\nDemo finished.")
    print("Final status:", cortex.status())
    return cortex


def _demo_with_rk(cortex: SensoryCortex, duration_seconds: float):
    """Live RK + shared sim drive (requires ReflexKernel installed)."""
    rk_root = _REPO_ROOT / "EmbodI" / "ReflexKernel"
    src = rk_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from reflexkernel.kernel import ReflexKernel
    from reflexkernel.interface.python_api import PythonAPI
    from reflexkernel.abstraction.virtual import VirtualSensorSimulator
    from SensoryCortex.adapters import drive_shared_sim

    cfg_path = rk_root / "configs" / "sim_only.yaml"
    kernel = ReflexKernel.from_config_path(str(cfg_path))
    # Avoid viz lockups in headless demo if possible
    try:
        if hasattr(kernel.cfg, "output") and hasattr(kernel.cfg.output, "enable_visualizer"):
            kernel.cfg.output.enable_visualizer = False
    except Exception:
        pass

    api = PythonAPI(kernel)
    api.start()
    cortex.bind_reflex(api)
    sim = VirtualSensorSimulator()  # ONE shared sim for the session

    print(f"Running RK-coupled demo for {duration_seconds}s (shared sim)...\n")
    start = time.time()
    step = 0
    while time.time() - start < duration_seconds:
        step += 1
        coherent = drive_shared_sim(kernel, sim, steps=1, feed_kernel=True)
        experience = cortex.process_coherent_input(
            coherent, respect_gate=True, force=False
        )
        if experience is None:
            # still step wall clock
            time.sleep(0.15)
            continue
        print(
            f"[{step:03d}] tick={coherent.get('tick')} "
            f"mood={experience.affective_core.overall_mood} "
            f"arousal={experience.affective_core.arousal:.2f} "
            f"n_sens={len(experience.salient_sensations)} "
            f"delta={experience.delta_from_last!r} "
            f"tokens~{experience.token_estimate}"
        )
        if step == 3:
            r = cortex.inject_thought(
                emotion="curiosity",
                intensity=0.65,
                valence=0.3,
                arousal=0.55,
                text="Noticing contact patterns",
            )
            print("  inject_thought:", r.get("dispatched"), r.get("command", {}).get("emotion"))
        time.sleep(0.35)

    api.stop()
    print("\nRK-coupled demo finished.")
    print("Final status:", cortex.status())
    return cortex


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Sensory Cortex embedded runner")
    p.add_argument("--demo", action="store_true", default=True)
    p.add_argument("--rk", action="store_true", help="Couple to ReflexKernel sim")
    p.add_argument("--duration", type=float, default=12.0)
    args = p.parse_args()
    run_embedded(demo=True, duration_seconds=args.duration, with_reflexkernel=args.rk)
