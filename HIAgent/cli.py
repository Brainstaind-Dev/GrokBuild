"""CLI entry: python -m HIAgent.cli …"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root on path
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_RK = _REPO / "EmbodI" / "ReflexKernel" / "src"
if str(_RK) not in sys.path:
    sys.path.insert(0, str(_RK))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="HIAgent — Grok (xAI API) riding ReflexKernel / Sensory Cortex"
    )
    p.add_argument(
        "--backend",
        choices=["embedded", "saddle"],
        default="embedded",
        help="Body connection mode",
    )
    p.add_argument("--model", default=None, help="xAI model id override")
    p.add_argument(
        "--saddle-url",
        default=None,
        help="Saddle base URL (backend=saddle)",
    )
    p.add_argument("--saddle-api-key", default=None)
    p.add_argument("--rk-config", default=None, help="Path to RK yaml (embedded)")
    p.add_argument("--viz", action="store_true", help="Enable pygame viz (embedded)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--pause-poll",
        type=float,
        default=None,
        help="Seconds after pause before asking HI to resume (default 30)",
    )

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("interactive", help="Human ↔ Grok with body tools")

    pulse = sub.add_parser("pulse", help="Autonomous feel→act loop")
    pulse.add_argument("--interval", type=float, default=None)
    pulse.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Stop after N pulses (default: run until Ctrl+C)",
    )

    once = sub.add_parser("once", help="Single user message then exit")
    once.add_argument("message", help="User message to send")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    from HIAgent.config import load_config
    from HIAgent.loop.agent import HigherIntelligenceAgent

    overrides = {
        "backend": args.backend,
        "verbose": args.verbose,
        "enable_viz": bool(args.viz),
    }
    if args.model:
        overrides["model"] = args.model
    if args.saddle_url:
        overrides["saddle_url"] = args.saddle_url
    if args.saddle_api_key:
        overrides["saddle_api_key"] = args.saddle_api_key
    if args.rk_config:
        overrides["rk_config"] = args.rk_config
    if args.pause_poll is not None:
        overrides["pause_poll_sec"] = args.pause_poll

    cfg = load_config(**overrides)
    agent = HigherIntelligenceAgent(cfg)

    print("=== HIAgent ===")
    print(f"backend={cfg.backend} model={cfg.model}")
    print(f"pause_poll_sec={cfg.pause_poll_sec}")
    print("Starting body…")
    try:
        agent.start()
    except Exception as exc:
        print(f"Failed to start: {exc}", file=sys.stderr)
        return 1
    print("Body ready.", agent.backend.status())
    if agent.session:
        print(f"Session log: {agent.session.path}")

    try:
        if args.command == "interactive":
            print(
                "\nInteractive mode. Type messages; empty line or Ctrl+C to quit.\n"
                "Grok can call tools: feel, inject_thought, pause_feed, resume_feed, …\n"
            )
            while True:
                try:
                    line = input("You> ").strip()
                except EOFError:
                    break
                if not line:
                    break
                reply = agent.turn(line)
                print(f"\nGrok> {reply}\n")

        elif args.command == "pulse":
            agent.pulse_loop(
                interval=args.interval,
                max_cycles=args.max_cycles,
            )

        elif args.command == "once":
            reply = agent.turn(args.message)
            print(reply)

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        agent.stop()
        print("Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
