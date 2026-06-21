#!/usr/bin/env python
"""
Example asynchronous client for the ReflexKernel Remote API.

This is the recommended way for a higher-level intelligence (Grok, LangChain agent,
custom controller, etc.) to connect to a running ReflexKernel server.

Features demonstrated:
- REST calls (thought, reward, demo, state, step, stimulus)
- WebSocket real-time event subscription (reflex traces, state, learner updates)
- Proper async/await + error handling

Requirements (client side):
    pip install httpx websockets

Usage:
    python scripts/remote_client.py --host localhost --port 8000 --api-key reflexkernel-dev
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any, Dict, Optional

import httpx
import websockets


class ReflexKernelRemoteClient:
    """Async client for ReflexKernel remote server."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
        self._client = httpx.AsyncClient(timeout=30.0, headers=self.headers)

    async def close(self):
        await self._client.aclose()

    # ------------------------------------------------------------------
    # REST Methods (mirror PythonAPI / command surface)
    # ------------------------------------------------------------------

    async def inject_thought(self, **kwargs: Any) -> Dict[str, Any]:
        """Send a thought/affective seed."""
        resp = await self._client.post(f"{self.base_url}/api/v1/thought", json=kwargs)
        resp.raise_for_status()
        return resp.json()

    async def send_reward(self, value: float, reason: str = "", window_steps: int = 1) -> Dict[str, Any]:
        payload = {"value": value, "reason": reason, "window_steps": window_steps}
        resp = await self._client.post(f"{self.base_url}/api/v1/reward", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def begin_demo(self, name: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {"name": name, "meta": meta or {}}
        resp = await self._client.post(f"{self.base_url}/api/v1/demo/begin", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def end_demo(self, outcome: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"outcome": outcome or {}}
        resp = await self._client.post(f"{self.base_url}/api/v1/demo/end", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def inject_stimulus(self, modality: str = "sim", data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        payload = {"modality": modality, "data": data or {}, **kwargs}
        resp = await self._client.post(f"{self.base_url}/api/v1/stimulus", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_state(self) -> Dict[str, Any]:
        resp = await self._client.get(f"{self.base_url}/api/v1/state")
        resp.raise_for_status()
        return resp.json()

    async def step(self, n: int = 1, extra_stimuli: Optional[list] = None) -> Dict[str, Any]:
        payload = {"n": n, "extra_stimuli": extra_stimuli or []}
        resp = await self._client.post(f"{self.base_url}/api/v1/step", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def command(self, cmd_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generic passthrough for the classic command dict surface."""
        resp = await self._client.post(f"{self.base_url}/api/v1/command", json=cmd_dict)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # WebSocket real-time events
    # ------------------------------------------------------------------

    async def stream_events(
        self,
        host: str,
        port: int,
        ws_path: str = "/ws/events",
        on_event: Optional[callable] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Connect to the event stream and call on_event for every message.
        This is a long-running coroutine.
        """
        key = api_key or self.api_key
        uri = f"ws://{host}:{port}{ws_path}?api_key={key}"

        print(f"[client] Connecting to event stream: {uri}")

        async with websockets.connect(uri) as ws:
            # Optional: send a ping
            await ws.send(json.dumps({"ping": True}))

            async for message in ws:
                try:
                    event = json.loads(message)
                    if on_event:
                        on_event(event)
                    else:
                        print("[event]", json.dumps(event, indent=2)[:300])
                except Exception as e:
                    print(f"[client] Bad event: {e} - raw: {message}")


async def demo_loop(client: ReflexKernelRemoteClient, host: str, port: int):
    """Example of a remote teaching loop."""
    print("\n=== Remote Teaching Demo Loop ===")

    # 1. Send a strong startle thought
    await client.inject_thought(emotion="startle", intensity=0.9, valence=-0.75, arousal=0.92)
    print("Sent startle thought")

    # 2. Step a few times (the kernel will react)
    for i in range(3):
        result = await client.step(n=1)
        print(f"Step {i+1}: actions={len(result.get('actions', []))}")

    state = await client.get_state()
    print("Current arousal:", state.get("context", {}).get("arousal"))

    # 3. Reward the body
    await client.send_reward(0.65, "good defensive reaction to startle", window_steps=3)
    print("Reward sent")

    # 4. Teach via demonstration
    await client.begin_demo("remote_gentle_greet")
    await client.inject_stimulus(modality="sim", data={"kind": "friendly_wave"})
    await client.step(n=2)
    ended = await client.end_demo({"success": True, "source": "remote_client"})
    print(f"Demo ended: {ended}")

    # 5. Final state
    final = await client.get_state()
    print("Final state tick:", final.get("tick"))


def _print_event(event: Dict[str, Any]):
    """Default event handler for the WS demo."""
    etype = event.get("type")
    if etype in ("reflex_trace", "state", "learner_update"):
        print(f"[{etype}]", event.get("data", {}))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--api-key", default="reflexkernel-dev")
    parser.add_argument("--ws-only", action="store_true", help="Only connect to WS and print events")
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    client = ReflexKernelRemoteClient(base, args.api_key)

    try:
        if args.ws_only:
            print("Running in WS-only mode (will print live events from the kernel)...")
            await client.stream_events(args.host, args.port, on_event=_print_event, api_key=args.api_key)
        else:
            # Run a full remote interaction demo
            await demo_loop(client, args.host, args.port)

            # Then optionally stay connected to see live events
            print("\nNow listening for live events (Ctrl-C to stop)...")
            await client.stream_events(args.host, args.port, on_event=_print_event, api_key=args.api_key)
    except KeyboardInterrupt:
        print("\nClient stopped.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
