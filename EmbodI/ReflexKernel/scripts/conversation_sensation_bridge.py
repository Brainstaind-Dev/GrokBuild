#!/usr/bin/env python
"""
Conversation Sensation Bridge

This script runs a small local web server that receives parsed #states from a
browser userscript monitoring a Grok (or similar) conversation.

It then forwards them as thought seeds (or sensations) into the ReflexKernel
saddle/interface.

This creates a closed loop where the conversation itself generates embodied
states that the higher intelligence can "feel" through the Embodied Autonomic
System.

Requirements:
- Run inside the project's venv that has the [server] extras (or at least httpx + fastapi + uvicorn)
- The ReflexKernel server (saddle) must be running (python -m scripts.server)

Usage:
1. Start the ReflexKernel server first.
2. Run this bridge: python scripts/conversation_sensation_bridge.py
3. Install Tampermonkey in your browser and add the companion userscript.
4. Open a Grok conversation and include or have the AI output lines starting with #state_name

The bridge listens on http://127.0.0.1:9876 by default.

States are sent as structured thought seeds with type "sensation_state".

You can extend the STATE_TO_SEED map below for richer mappings.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ============================================================
# CONFIGURATION - Adjust to your ReflexKernel server (the saddle)
# ============================================================
KERNEL_HOST = "127.0.0.1"
KERNEL_PORT = 8000
API_KEY = "reflexkernel-dev"   # Must match what you use for the kernel server

# Bridge listen address
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 9876

# ============================================================
# Mapping: turn a #state into a richer thought seed for the kernel
# ============================================================
# You can expand this with more sophisticated logic or call into
# the local abstraction/coherence if you want the bridge itself to
# synthesize full Sensation objects.
STATE_TO_SEED: dict[str, dict[str, Any]] = {
    # Example custom mappings
    "arousal_high": {
        "emotion": "arousal",
        "intensity": 0.85,
        "valence": 0.2,
        "text": "The body is experiencing rising physical arousal.",
    },
    "gentle_touch": {
        "emotion": "calm_contact",
        "intensity": 0.5,
        "valence": 0.6,
        "text": "Gentle, pleasant tactile sensation.",
    },
    # Add your own #states here
}

DEFAULT_SEED_TEMPLATE = {
    "emotion": "sensation_state",
    "intensity": 0.6,
    "valence": 0.0,
}

app = FastAPI(title="Conversation Sensation Bridge", version="0.1")

class StatePayload(BaseModel):
    state: str
    context: str | None = None
    source: str | None = "conversation"

@app.post("/state")
async def receive_state(payload: StatePayload):
    state = payload.state.strip()
    if not state.startswith("#"):
        raise HTTPException(status_code=400, detail="State must start with #")

    state_key = state[1:].lower()  # strip the #

    # Build the seed to send to the kernel
    seed = STATE_TO_SEED.get(state_key, DEFAULT_SEED_TEMPLATE.copy())
    seed = dict(seed)  # copy

    # Always include the raw state and some context
    seed["state"] = state
    if payload.context:
        seed["text"] = f"{seed.get('text', '')} Context from conversation: {payload.context[:300]}".strip()
    else:
        seed.setdefault("text", f"Detected state in conversation: {state}")

    seed.setdefault("type", "sensation_state")
    seed.setdefault("source", "conversation_bridge")

    # Forward to the ReflexKernel saddle
    kernel_url = f"http://{KERNEL_HOST}:{KERNEL_PORT}/api/v1/thought"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    step_url = f"http://{KERNEL_HOST}:{KERNEL_PORT}/api/v1/step"
    steps_per_state = 3  # advance kernel so seeds fuse, reflexes fire, and viz updates

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(kernel_url, json=seed, headers=headers)
            resp.raise_for_status()
            step_resp = await client.post(
                step_url,
                json={"n": steps_per_state},
                headers=headers,
            )
            step_resp.raise_for_status()
    except Exception as e:
        print(f"[bridge] Failed to forward state {state} to kernel: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to reach kernel: {e}")

    print(f"[bridge] Forwarded {state} → kernel (thought seed + {steps_per_state} ticks)")
    return {
        "status": "forwarded",
        "state": state,
        "kernel_response": resp.json(),
        "step_response": step_resp.json(),
    }

@app.get("/health")
async def health():
    return {"status": "ok", "kernel": f"http://{KERNEL_HOST}:{KERNEL_PORT}", "bridge_port": BRIDGE_PORT}

if __name__ == "__main__":
    print("=== Conversation Sensation Bridge ===")
    print(f"Listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"Forwarding to kernel at http://{KERNEL_HOST}:{KERNEL_PORT}")
    print(f"API key: {API_KEY}")
    print("Install the companion Tampermonkey userscript in your browser.")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        app,
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info",
    )
