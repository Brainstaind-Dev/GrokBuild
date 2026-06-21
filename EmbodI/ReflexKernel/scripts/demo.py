#!/usr/bin/env python
"""
Interactive ReflexKernel demo (simulation mode).

Run:
    python -m scripts.demo
    # or after install:
    reflexkernel-demo

Controls (press keys in the terminal while the avatar window has focus or in the console):
    s   sudden loud sound (strong flinch)
    m   peripheral motion
    f   threatening / approaching face
    c   close approach
    t   touch on shoulder
    h   harsh light / flash
    q   calm / quiet moment
    r   relaxing / pleasant sound
    w   friendly wave / greeting

Additional teaching controls (when avatar is focused or console):
    d   begin demonstration recording (type name in console if prompted)
    e   end demonstration
    +   send positive reward (+0.7)
    -   send negative reward (-0.5)

The pygame window shows the "body" reacting in real time.
Close the window or Ctrl-C to exit.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make src importable when running from repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reflexkernel import ReflexKernel, VirtualSensorSimulator  # noqa: E402
from reflexkernel.abstraction import AbstractionOutput  # noqa: E402
from reflexkernel.config import load_config  # noqa: E402
from reflexkernel.interface.server import create_app, run_server  # noqa: E402
from reflexkernel.interface.stdio_adapter import StdioAdapter  # noqa: E402


def main() -> None:
    print("=== ReflexKernel Interactive Demo ===")
    print("Loading sim_only configuration...")

    cfg_path = ROOT / "configs" / "sim_only.yaml"
    cfg = load_config(cfg_path)

    kernel = ReflexKernel(config=cfg)

    # Optional: start the remote server in a background thread if enabled in config.
    # This lets you use the interactive demo locally (Pygame + keyboard) while a remote
    # intelligence connects via HTTP/WebSocket at the same time.
    server_thread = None
    server_cfg = getattr(cfg.interface, "server", None)
    if server_cfg and getattr(server_cfg, "enabled", False):
        try:
            import threading

            def _run_server_thread():
                # We pass the already-created kernel so local viz/keyboard still work
                app = create_app(kernel=kernel, server_config=server_cfg)
                # Run uvicorn in this thread (it blocks)
                import uvicorn
                uvicorn.run(
                    app,
                    host=server_cfg.host,
                    port=server_cfg.port,
                    log_level="warning",
                    access_log=False,
                )

            server_thread = threading.Thread(target=_run_server_thread, daemon=True, name="reflex-server")
            server_thread.start()
            print(f"\n[REMOTE] Server started in background on http://{server_cfg.host}:{server_cfg.port}/docs")
            print(f"[REMOTE] WebSocket: ws://{server_cfg.host}:{server_cfg.port}{server_cfg.ws_path}")
            print(f"[REMOTE] Use X-API-Key: {server_cfg.api_key}\n")
        except Exception as e:
            print(f"[REMOTE] Failed to start background server: {e}")

    # Simple keyboard teaching loop on top of the kernel
    print("\nKeyboard stimuli (in this console):")
    print("  s m f c t h q r w   |  d=begin_demo  e=end_demo  +=reward  -=punish")
    print("  NEW (abstraction scenarios): i=impact  c=gentle_contact  m=sudden_movement  l=loud_noise")
    print("Pygame avatar will open (if pygame installed). Close it or Ctrl-C to quit.\n")

    # Start kernel (starts sensors + viz)
    kernel.start()

    # --- New: Embodied Autonomic System demo (virtual abstraction layer) ---
    # This shows the new Feature Extraction / Abstraction Layer in action.
    # It generates realistic Tier 1 signals (FSR, MPU, Mic, temp) and turns them
    # into clean Events + Features that feed ReflexKernel.
    virtual_abstraction = VirtualSensorSimulator(seed=123)
    print("\n[NEW] Virtual Abstraction Layer active (Tier 1 sensors).")
    print("      Try pressing keys that trigger scenarios, or just watch the output.\n")

    # Optional: trigger an interesting scenario on startup
    virtual_abstraction.trigger_scenario("gentle_contact", duration=2.0)

    # ------------------------------------------------------------------

    # If user wants pure stdio teaching, they can run with a flag later.
    # For the demo we do a hybrid: we drive the kernel ourselves and also accept typed commands.
    try:
        tick = 0
        while True:
            tick += 1

            # Run the virtual abstraction and feed the results into the kernel
            raw = virtual_abstraction.read_all()
            abstraction_output: AbstractionOutput = virtual_abstraction.process(raw)

            # Convert to stimuli the existing ReflexKernel understands
            stimuli = abstraction_output.to_stimuli()

            # Occasionally show what the abstraction layer is producing
            if tick % 8 == 0 and (abstraction_output.events or abstraction_output.features):
                ev = [e.type for e in abstraction_output.events]
                feat = [f.type for f in abstraction_output.features]
                print(f"[ABSTRACTION] events={ev} features={feat}")

            # New: Show coherent sensations (what the higher intelligence "feels")
            if tick % 12 == 0 and abstraction_output.sensations:
                for sens in abstraction_output.sensations[:2]:
                    print(f"[SENSATION] {sens.description} (zone={sens.zone}, intensity={sens.intensity})")

            actions = kernel.step(extra_stimuli=stimuli if stimuli else None)

            # Very light console status every ~20 ticks
            if tick % 20 == 0:
                st = kernel.get_state()
                ctx = st.get("context") or {}
                print(
                    f"[{tick:04d}] v={ctx.get('valence', 0):+.2f} a={ctx.get('arousal', 0):.2f} "
                    f"actions={len(actions)}"
                )

            # Non-blocking key handling is already done inside SimulationSensor.
            # Here we also support a few meta keys for teaching.
            # We do a best-effort read (same trick as the sensor).
            key = _try_read_key()
            if key:
                _handle_meta_key(key, kernel)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        kernel.stop()
        print("Demo ended. Thanks for playing with the nervous system.")


def _try_read_key() -> str | None:
    try:
        import msvcrt

        if msvcrt.kbhit():
            return msvcrt.getwch().lower()
    except Exception:
        pass
    try:
        import select
        import sys

        if select.select([sys.stdin], [], [], 0.0)[0]:
            return sys.stdin.read(1).lower()
    except Exception:
        pass
    return None


def _handle_meta_key(key: str, kernel: ReflexKernel) -> None:
    if key in ("+", "="):
        kernel.send_reward(0.65, "positive teaching signal from demo")
        print("[demo] + reward sent")
    elif key in ("-", "_"):
        kernel.send_reward(-0.45, "negative teaching signal from demo")
        print("[demo] - reward sent")
    elif key == "d":
        name = input("Demo name (enter for 'demo_session'): ").strip() or "demo_session"
        kernel.begin_demonstration(name)
        print(f"[demo] Recording started: {name}")
    elif key == "e":
        ended = kernel.end_demonstration({"source": "demo"})
        print(f"[demo] Recording ended: {ended}")
    elif key in ("h", "?", "i"):
        print("[demo] state:", kernel.get_state())

    # --- New: Trigger interesting virtual abstraction scenarios ---
    if "virtual_abstraction" in globals() or "virtual_abstraction" in locals():
        va = virtual_abstraction  # type: ignore
        if key == "i":
            va.trigger_scenario("impact", duration=1.2)
            print("[ABSTRACTION] Scenario: impact")
        elif key == "c":
            va.trigger_scenario("gentle_contact", duration=2.5)
            print("[ABSTRACTION] Scenario: gentle_contact")
        elif key == "m":
            va.trigger_scenario("sudden_movement", duration=1.0)
            print("[ABSTRACTION] Scenario: sudden_movement")
        elif key == "l":
            va.trigger_scenario("loud_noise", duration=0.8)
            print("[ABSTRACTION] Scenario: loud_noise")

    # other keys are handled by SimulationSensor automatically


if __name__ == "__main__":
    main()
