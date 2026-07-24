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
# Repo root (GrokBuild) for optional SensoryCortex package
_GROK_ROOT = ROOT.parents[1]  # EmbodI/ReflexKernel → GrokBuild
if str(_GROK_ROOT) not in sys.path:
    sys.path.insert(0, str(_GROK_ROOT))

from reflexkernel import ReflexKernel, VirtualSensorSimulator  # noqa: E402
from reflexkernel.abstraction import AbstractionOutput  # noqa: E402
from reflexkernel.config import load_config  # noqa: E402
from reflexkernel.interface.server import create_app, run_server  # noqa: E402
from reflexkernel.interface.stdio_adapter import StdioAdapter  # noqa: E402
from reflexkernel.interface.python_api import PythonAPI  # noqa: E402


def _try_attach_cortex(kernel: ReflexKernel):
    """Optional Sensory Cortex for HI packaging in the demo loop."""
    try:
        from SensoryCortex.integration import try_create_cortex

        cortex = try_create_cortex(mode="embedded", bind_api=PythonAPI(kernel))
        if cortex is not None:
            print("[CORTEX] Sensory Cortex attached (embedded, low-latency path).")
            print("[CORTEX] HI packages print periodically; key 'x' forces an experience dump.\n")
        return cortex
    except Exception as exc:
        print(f"[CORTEX] Not attached ({exc}). Demo continues without Sensory Cortex.")
        return None


def main() -> None:
    print("=== ReflexKernel Interactive Demo ===")
    print("Loading sim_only configuration...")

    cfg_path = ROOT / "configs" / "sim_only.yaml"
    cfg = load_config(cfg_path)

    kernel = ReflexKernel(config=cfg)
    cortex = _try_attach_cortex(kernel)

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
    print("View keys: 1=front, 2=side_left, 3=side_right, 4=back  (for zone testing)")

    # Start kernel (starts sensors + viz)
    kernel.start()
    if "visualizer" in kernel.output:
        viz = kernel.output["visualizer"]
        if getattr(viz, '_running', False):
            print("[demo] Visualization window should now be open (Silent Alice avatar with sensation glows).")
        else:
            print("[demo] WARNING: Visualization failed to start. Is pygame installed in the venv?")

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

            # New: Show coherent sensations (rich structured + descriptive for HI/Saddle)
            if tick % 12 == 0 and abstraction_output.sensations:
                for sens in abstraction_output.sensations[:2]:
                    print(f"[SENSATION] {sens.description} (zone={sens.zone}, cat={sens.category}, temporal={sens.temporal_quality}, textures={sens.texture_qualities}, rich={sens.arousal_modulated_richness})")

            # Attach so the visualizer / Cortex can display the rich sensations
            if hasattr(kernel, "set_last_sensations"):
                kernel.set_last_sensations(list(abstraction_output.sensations)[:3])
            else:
                kernel._last_sensations = list(abstraction_output.sensations)[:3]

            actions = kernel.step(extra_stimuli=stimuli if stimuli else None)

            # Explicit render from main thread (kernel now only prepares to support server+viz)
            if "visualizer" in kernel.output:
                kernel.output["visualizer"].force_render_from_cache()

            # Sensory Cortex HI package (gated; not every tick)
            if cortex is not None and tick % 15 == 0:
                try:
                    from SensoryCortex.adapters import from_kernel

                    body = None
                    if abstraction_output.state_summary is not None:
                        body = abstraction_output.state_summary.to_dict()
                    coherent = from_kernel(
                        kernel,
                        sensations=abstraction_output.sensations[:3],
                        body_state=body,
                    )
                    exp = cortex.process_coherent_input(
                        coherent, respect_gate=True, force=False
                    )
                    if exp is not None:
                        top = (
                            exp.salient_sensations[0].description[:70]
                            if exp.salient_sensations
                            else "(none)"
                        )
                        print(
                            f"[CORTEX] mood={exp.affective_core.overall_mood} "
                            f"a={exp.affective_core.arousal:.2f} "
                            f"delta={exp.delta_from_last!r} "
                            f"tokens~{exp.token_estimate} | {top}"
                        )
                except Exception as exc:
                    if tick % 60 == 0:
                        print(f"[CORTEX] update skipped: {exc}")

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
                _handle_meta_key(key, kernel, cortex=cortex)

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


def _handle_meta_key(key: str, kernel: ReflexKernel, cortex=None) -> None:
    if key in ("+", "="):
        if cortex is not None:
            r = cortex.send_reward(0.65, "positive teaching signal from demo")
            print("[demo] + reward via Cortex", r.get("dispatched"))
        else:
            kernel.send_reward(0.65, "positive teaching signal from demo")
            print("[demo] + reward sent")
    elif key in ("-", "_"):
        if cortex is not None:
            r = cortex.send_reward(-0.45, "negative teaching signal from demo")
            print("[demo] - reward via Cortex", r.get("dispatched"))
        else:
            kernel.send_reward(-0.45, "negative teaching signal from demo")
            print("[demo] - reward sent")
    elif key == "d":
        name = input("Demo name (enter for 'demo_session'): ").strip() or "demo_session"
        if cortex is not None:
            cortex.begin_demonstration(name)
        else:
            kernel.begin_demonstration(name)
        print(f"[demo] Recording started: {name}")
    elif key == "e":
        if cortex is not None:
            cortex.end_demonstration(outcome={"source": "demo"})
            ended = "via_cortex"
        else:
            ended = kernel.end_demonstration({"source": "demo"})
        print(f"[demo] Recording ended: {ended}")
    elif key == "x" and cortex is not None:
        try:
            from SensoryCortex.adapters import from_kernel

            exp = cortex.process_coherent_input(from_kernel(kernel), force=True)
            if exp is not None:
                print("[CORTEX] forced experience:")
                print(
                    f"  mood={exp.affective_core.overall_mood} "
                    f"v={exp.affective_core.valence} a={exp.affective_core.arousal}"
                )
                print(f"  trend={exp.trend} delta={exp.delta_from_last}")
                for s in exp.salient_sensations[:3]:
                    print(
                        f"  - {s.description[:90]} "
                        f"(rich={s.arousal_modulated_richness}, zone={s.zone})"
                    )
        except Exception as exc:
            print(f"[CORTEX] force dump failed: {exc}")
    elif key in ("h", "?"):
        print("[demo] state:", kernel.get_state())
        if cortex is not None:
            print("[CORTEX] status:", cortex.status())

    # View switching for zone visualization testing
    viz = kernel.output.get("visualizer")
    if viz and hasattr(viz, "set_view"):
        if key == "1":
            viz.set_view("front")
            print("[demo] View: front")
        elif key == "2":
            viz.set_view("side_left")
            print("[demo] View: side_left")
        elif key == "3":
            viz.set_view("side_right")
            print("[demo] View: side_right")
        elif key == "4":
            viz.set_view("back")
            print("[demo] View: back")

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
