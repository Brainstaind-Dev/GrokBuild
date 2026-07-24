"""
Service runner — lightweight FastAPI façade over Sensory Cortex.

For isolation/debug. Prefer embedded mode for lowest latency.
Does not re-implement fusion; expects coherent-input payloads.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from SensoryCortex import SensoryCortex, SensoryUpdate, load_config

cortex: Optional[SensoryCortex] = None


class CoherentInput(BaseModel):
    """Coherent input matching the adapter contract (not raw FSR fusion)."""

    data: Dict[str, Any] = Field(default_factory=dict)


class ThoughtSeed(BaseModel):
    emotion: str
    intensity: float = 0.5
    valence: float = 0.0
    arousal: float = 0.5
    text: str = ""


class RewardSignal(BaseModel):
    value: float
    reason: str = ""
    window_steps: int = 6


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cortex
    config = load_config()
    cfg = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    cfg.setdefault("interface", {})["mode"] = "service"
    cortex = SensoryCortex(config=cfg, mode="service")
    print("Sensory Cortex Service started")
    yield
    cortex = None
    print("Sensory Cortex Service stopped")


app = FastAPI(
    title="Sensory Cortex Service",
    description=(
        "HI packaging layer over ReflexKernel coherent sensations. "
        "POST coherent inputs (from Saddle/adapter), not raw sensors."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.status()


@app.post("/coherent", response_model=Optional[SensoryUpdate])
async def process_coherent(payload: CoherentInput):
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.process_coherent_input(payload.data)


@app.post("/stimulus", response_model=Optional[SensoryUpdate])
async def process_stimulus_compat(payload: CoherentInput):
    """Backward-compatible alias for /coherent."""
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.process_coherent_input(payload.data)


@app.get("/experience", response_model=Optional[SensoryUpdate])
async def get_current_experience():
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.get_current_experience()


@app.post("/thought")
async def inject_thought(seed: ThoughtSeed):
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.inject_thought(
        emotion=seed.emotion,
        intensity=seed.intensity,
        valence=seed.valence,
        arousal=seed.arousal,
        text=seed.text,
    )


@app.post("/reward")
async def send_reward(signal: RewardSignal):
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return cortex.send_reward(
        value=signal.value,
        reason=signal.reason,
        window_steps=signal.window_steps,
    )


@app.get("/trend")
async def get_trend():
    if cortex is None:
        raise HTTPException(status_code=503, detail="Cortex not initialized")
    return {"trend": cortex.get_trend()}


def run_service(host: str = "127.0.0.1", port: int = 8100):
    import uvicorn

    print(f"Starting Sensory Cortex Service on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_saddle_consumer(
    saddle_url: str = "http://127.0.0.1:8765",
    api_key: str = "reflexkernel-dev",
    poll_interval: float = 0.5,
    duration: float = 0.0,
):
    """
    Service-mode: poll/listen to Saddle and feed Sensory Cortex.

    duration=0 runs until Ctrl-C.
    """
    from SensoryCortex.integration import SaddleEventConsumer, try_create_cortex

    cortex = try_create_cortex(mode="service")
    if cortex is None:
        print("Failed to create Sensory Cortex")
        return

    def _on_exp(exp):
        mood = (exp.get("affective_core") or {}).get("overall_mood")
        delta = exp.get("delta_from_last")
        print(f"[consumer] mood={mood} delta={delta!r} tokens~{exp.get('token_estimate')}")

    consumer = SaddleEventConsumer(
        base_url=saddle_url,
        api_key=api_key,
        cortex=cortex,
        poll_interval=poll_interval,
        use_websocket=False,  # robust default on Windows; enable WS if websockets installed
        on_experience=_on_exp,
    )
    print(f"Saddle consumer → {saddle_url} (poll {poll_interval}s)")
    consumer.start()
    try:
        if duration and duration > 0:
            import time

            time.sleep(duration)
        else:
            while True:
                import time

                time.sleep(1.0)
    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        consumer.stop()
        print("Last experience:", consumer.last_experience)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Sensory Cortex service / Saddle consumer")
    p.add_argument("--mode", choices=("api", "consumer"), default="api")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8100)
    p.add_argument("--saddle", default="http://127.0.0.1:8765")
    p.add_argument("--api-key", default="reflexkernel-dev")
    p.add_argument("--duration", type=float, default=0.0)
    args = p.parse_args()
    if args.mode == "consumer":
        run_saddle_consumer(
            saddle_url=args.saddle,
            api_key=args.api_key,
            duration=args.duration,
        )
    else:
        run_service(host=args.host, port=args.port)
