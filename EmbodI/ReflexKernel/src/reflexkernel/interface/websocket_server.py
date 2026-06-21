"""
WebSocket / FastAPI server skeleton (optional).

To use:
    pip install -e .[server]
    Then import and call run_server(kernel, host, port)

This is intentionally a minimal stub. A production version would add:
- Proper pub/sub of state/actions/traces
- Authentication / rate limiting
- REST endpoints for demos, rewards, config inspection
"""

from __future__ import annotations

from typing import Any, Optional


def run_server(kernel: Any, host: str = "127.0.0.1", port: int = 8765, path: str = "/reflex") -> None:
    """
    Starts a tiny FastAPI + websocket server that forwards commands to the kernel
    and pushes state updates.

    This function only succeeds if the optional 'server' extras are installed.
    """
    try:
        import asyncio  # noqa: F401
        from fastapi import FastAPI, WebSocket  # type: ignore
        import uvicorn  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "WebSocket server requires optional deps. Install with: pip install -e .[server]"
        ) from e

    app = FastAPI(title="ReflexKernel Interface")

    @app.websocket(path)
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        kernel.start()
        try:
            while True:
                data = await websocket.receive_json()
                resp = kernel.command(data)
                await websocket.send_json({"type": "ack", **resp})
                # Push latest state on every roundtrip
                await websocket.send_json({"type": "state", **kernel.get_state()})
        except Exception:
            pass
        finally:
            kernel.stop()

    print(f"[interface] Starting websocket server on ws://{host}:{port}{path}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


# Convenience re-export
__all__ = ["run_server"]
