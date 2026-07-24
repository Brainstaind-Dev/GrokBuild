#!/usr/bin/env python
"""
Standalone ReflexKernel Remote Server.

This script starts a production-style FastAPI + WebSocket server that exposes
the full ReflexKernel control surface to remote higher-level intelligences
(Grok, other agents, etc.).

Usage examples:
    # Basic (uses sim_only.yaml and dev api key)
    python -m scripts.server

    # Custom everything
    python -m scripts.server \
        --config configs/default.yaml \
        --host 0.0.0.0 \
        --port 8000 \
        --api-key "my-secret-key-for-grok"

    # With a specific API key from environment (recommended)
    REFLEXKERNEL_API_KEY=prod-key python -m scripts.server --config my_body.yaml

After starting, visit:
    http://localhost:8000/docs          # Swagger UI (interactive)
    http://localhost:8000/health
    ws://localhost:8000/ws/events?api_key=...

The server drives its own kernel loop (or you can integrate it with an existing kernel).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the package importable when running as a script from repo root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reflexkernel import ReflexKernel  # noqa: E402
from reflexkernel.config import load_config  # noqa: E402
from reflexkernel.interface.server import create_app, run_server  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ReflexKernel Remote Server (FastAPI + WebSocket)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default=str(ROOT / "configs" / "sim_only.yaml"),
        help="Path to ReflexKernel YAML config",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind (overrides config)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Port to bind (overrides config)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for X-API-Key header (overrides config; env REFLEXKERNEL_API_KEY also works)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level",
    )
    parser.add_argument(
        "--no-kernel-start",
        action="store_true",
        help="Do not auto-start the kernel (advanced)",
    )

    args = parser.parse_args()

    print("=== ReflexKernel Remote Server ===")
    print(f"Loading config from: {args.config}")

    cfg = load_config(args.config)

    # Apply CLI / env overrides to server section
    server_cfg = cfg.interface.server

    if args.host:
        server_cfg.host = args.host
    if args.port is not None:
        server_cfg.port = args.port

    # Priority: CLI > env var > config file
    api_key = args.api_key or os.environ.get("REFLEXKERNEL_API_KEY") or server_cfg.api_key
    server_cfg.api_key = api_key

    # Force enable the server for this run
    server_cfg.enabled = True

    print(f"Server will listen on http://{server_cfg.host}:{server_cfg.port}")
    print(f"API key in use: {server_cfg.api_key}  (change this for anything beyond local dev!)")
    print(f"Swagger UI: http://{server_cfg.host}:{server_cfg.port}/docs")
    print(f"WebSocket:  ws://{server_cfg.host}:{server_cfg.port}{server_cfg.ws_path}?api_key=...")
    print()

    # Create the kernel
    kernel = ReflexKernel(config=cfg)

    if not args.no_kernel_start:
        kernel.start()

    viz = kernel.output.get("visualizer") if hasattr(kernel, "output") else None
    has_viz = viz and getattr(viz, "_running", False)

    if has_viz:
        print("\n[INFO] Visualization enabled. Running server in background thread to keep Pygame window responsive.")
        print("       The main thread will pump Pygame events + idle re-renders (using last step state).")
        print("       Updates will appear when the bridge sends #states or you call /step etc.")
        print("       Use Ctrl-C to stop.\n")
        import threading
        import time

        def _run_server_thread():
            try:
                run_server(
                    kernel=kernel,
                    server_config=server_cfg,
                    host=server_cfg.host,
                    port=server_cfg.port,
                    log_level=args.log_level,
                )
            except Exception as e:
                print(f"[SERVER THREAD ERROR] {e}")

        server_thread = threading.Thread(target=_run_server_thread, daemon=True, name="reflex-server")
        server_thread.start()

        # Main thread: keep pumping viz events so the window stays responsive
        try:
            while viz and viz.pump_events():
                # Light sleep to not burn CPU; render updates come from API-driven steps
                # If you want continuous driving even without external input, consider a ticker here.
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nServer stopped by user (via viz loop).")
        finally:
            if kernel._running:
                kernel.stop()
            print("ReflexKernel server shutdown complete.")
    else:
        # No viz: normal blocking server
        try:
            run_server(
                kernel=kernel,
                server_config=server_cfg,
                host=server_cfg.host,
                port=server_cfg.port,
                log_level=args.log_level,
            )
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
        finally:
            if kernel._running:
                kernel.stop()
            print("ReflexKernel server shutdown complete.")


if __name__ == "__main__":
    main()
