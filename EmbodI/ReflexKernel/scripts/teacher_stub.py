#!/usr/bin/env python
"""
Example "Higher Intelligence" that talks to ReflexKernel over stdio (JSON lines).

This simulates what an LLM agent wrapper or symbolic controller would do:

1. Start the kernel in a subprocess (or import directly).
2. Send thought seeds based on its own "goals".
3. Occasionally reward good or bad behavior.
4. Record demonstrations when it wants the body to learn a new micro-skill.
5. Listen to state / traces to build grounded world model.

Run together with the kernel in stdio mode, or use the PythonAPI directly (easier for pure Python agents).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    kernel_script = ROOT / "scripts" / "demo.py"
    print("=== Teacher Stub (higher intelligence example) ===")
    print("Spawning ReflexKernel demo in stdio-teaching mode (simplified)...\n")

    # In real life the "kernel" would be started with a special flag that only does the stdio adapter.
    # For this stub we just show the messages you would send.

    print("If you were piping JSON to a ReflexKernel process, you would send lines like:\n")
    examples = [
        {"cmd": "thought_seed", "emotion": "startle", "intensity": 0.92, "valence": -0.75, "arousal": 0.9},
        {"cmd": "reward", "value": 0.8, "reason": "good defensive reaction to real threat", "window_steps": 5},
        {"cmd": "begin_demo", "name": "gentle_social_wave"},
        # ... interact with world or wait for stimuli ...
        {"cmd": "end_demo"},
        {"cmd": "get_state"},
    ]
    for ex in examples:
        print("   ", json.dumps(ex))
    print()

    print("Direct Python usage (recommended for agent code):")
    print("""
    from reflexkernel import ReflexKernel
    from reflexkernel.interface.python_api import PythonAPI
    from reflexkernel.config import load_config

    k = ReflexKernel.from_config_path("configs/sim_only.yaml")
    api = PythonAPI(k)
    api.start()

    api.inject_thought({"emotion": "curiosity", "intensity": 0.55})
    api.step(8)
    api.reward(0.4, "curious but not tense orientation toward person")
    api.begin_demo("soft_greet")
    ... # let the body experience stimuli while you guide it
    api.end_demo({"success": True, "notes": "gentle wave learned"})
    """)

    print("\nTeacher stub complete. See scripts/demo.py and the PythonAPI for the real loop.")


if __name__ == "__main__":
    main()
