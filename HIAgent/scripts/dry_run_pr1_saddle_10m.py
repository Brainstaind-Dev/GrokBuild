"""Desktop 10-minute PR1 wrap + Saddle + xAI rider. Not the Pi. Not flesh."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RK = _REPO / "EmbodI" / "ReflexKernel"
_PY = _RK / ".venv" / "Scripts" / "python.exe"
DID = "i2c1:0x48:ain0"
BASE = "http://127.0.0.1:8000"
API_KEY = "reflexkernel-dev"
CFG = _RK / "configs" / "pr1_saddle_dry.yaml"

# (start_s, end_s, present, unit, label)
SCORE = [
    (0, 60, True, 0.3, "light 0.3"),
    (60, 150, True, 0.7, "firm 0.7"),
    (150, 210, True, 1.0, "full 1.0"),
    (210, 300, True, 0.0, "present 0 — afterglow"),
    (300, 360, False, 0.0, "gone"),
    (360, 450, True, 0.5, "reappear 0.5"),
    (450, 470, True, 0.2, "pulse 0.2"),
    (470, 490, True, 0.9, "pulse 0.9"),
    (490, 510, True, 0.2, "pulse 0.2"),
    (510, 570, True, 0.0, "fade 0"),
    (570, 600, False, 0.0, "gone silence"),
]


def _apply_score(enum, bus, elapsed: float) -> str:
    label = "hold"
    present, unit = True, 0.0
    for start, end, pres, u, lab in SCORE:
        if start <= elapsed < end:
            present, unit, label = pres, u, lab
            break
    else:
        present, unit, label = False, 0.0, "done"
    enum.present = [DID] if present else []
    bus.fixture_units[DID] = float(unit)
    return label


def main() -> int:
    for p in (str(_REPO), str(_RK / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.environ.setdefault("PYTHONPATH", f"{_REPO};{_RK / 'src'}")

    from HIAgent.env_bootstrap import format_load_summary, load_embodi_env
    from HIAgent.config import load_config
    from HIAgent.loop.agent import HigherIntelligenceAgent
    from reflexkernel.kernel import ReflexKernel
    from reflexkernel.perception.afferent_bus import FakeDeviceEnumerator
    from reflexkernel.interface.server import create_app

    summary = load_embodi_env(repo_root=_REPO)
    print(format_load_summary(summary))
    if not summary.get("xai_api_key_present"):
        print("No XAI_API_KEY", file=sys.stderr)
        return 2

    kernel = ReflexKernel.from_config_path(
        CFG,
        overrides={
            "perception": {
                "afferent": {
                    "map_path": str(_RK / "configs" / "pr1_saddle_map.yaml"),
                }
            }
        },
    )
    enum = FakeDeviceEnumerator([DID])
    kernel.afferent.enumerator = enum
    kernel.afferent.fixture_units[DID] = 0.3
    kernel.start()

    import uvicorn

    app = create_app(kernel)
    uv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning"))
    threading.Thread(target=uv.run, daemon=True).start()

    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=2)
            break
        except Exception:
            time.sleep(0.4)
    else:
        print("Saddle did not come up", file=sys.stderr)
        return 1
    print("SADDLE_UP")

    stop = threading.Event()

    def score_loop():
        t0 = time.time()
        last = ""
        while not stop.is_set() and (time.time() - t0) < 610:
            lab = _apply_score(enum, kernel.afferent, time.time() - t0)
            if lab != last:
                print(f"PHASE {lab}", flush=True)
                last = lab
            time.sleep(0.5)

    threading.Thread(target=score_loop, daemon=True).start()

    cfg = load_config(
        backend="saddle",
        rk_config=str(CFG),
        saddle_url=BASE,
        saddle_api_key=API_KEY,
        enable_viz=False,
        prepend_feel_on_user_turn=True,
        verbose=True,
    )
    agent = HigherIntelligenceAgent(cfg)
    agent.start()
    print("RIDER_UP")
    t0 = time.time()
    n = 0
    try:
        while (time.time() - t0) < 600:
            n += 1
            elapsed = int(time.time() - t0)
            lab = _apply_score(enum, kernel.afferent, time.time() - t0)
            msg = (
                f"Call feel with force=true. Elapsed {elapsed}s, fixture phase: {lab}. "
                "Desktop PR1 wrap on the sternum seat — not flesh, not the Pi. "
                "Say what it feels like in your own words (pressure, linger, fade, change). "
                "Do not reprint the feel_line numbers. Do not invent other organs."
            )
            print(f"\n=== turn {n} t={elapsed}s phase={lab} ===", flush=True)
            try:
                print(agent.turn(msg), flush=True)
            except Exception as exc:
                print(f"TURN_FAIL {exc}", file=sys.stderr)
            remaining = 600 - (time.time() - t0)
            if remaining <= 0:
                break
            time.sleep(min(30.0, remaining))
    finally:
        stop.set()
        agent.stop()
        uv.should_exit = True
        kernel.stop()
        if agent.session:
            print(f"Session log: {agent.session.path}")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
