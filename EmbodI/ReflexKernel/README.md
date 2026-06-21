# ReflexKernel

**A trainable low-level embodiment and nervous-system subsystem.**

ReflexKernel gives a higher-level AI (LLM, agent, or symbolic system) the ability to:

- **Feel** grounded, real-world (or simulated) stimuli.
- Exhibit fast, involuntary **reflexes**.
- **Learn and be taught** new reactions, skills, and somatic patterns over time.

It is designed as the **body layer** — fast, modular, persistent, and extensible to real hardware (Raspberry Pi, Arduino, servos, etc.).

---

## Architecture at a Glance

See [PLAN.md](./PLAN.md) for the full layered diagram, data flow, rationale, and roadmap.

Layers (bottom-up):

1. **Perception** — Sensors (sim + real webcam via OpenCV/MediaPipe, mic, future hardware).
2. **Thought/Emotion Bridge** — Ingest "thought seeds" from higher mind + fuse with real stimuli into affective context.
3. **Reflex Core** — State machines + procedural logic for fast involuntary reactions (flinch, tension, micro-expressions, autonomic simulation).
4. **Learner Module** — Imitation learning (record + clone), reinforcement via rewards, parameter updates. Persisted.
5. **Output/Actuation** — Virtual muscles, pygame avatar visualization, structured logs, (future) hardware drivers.
6. **Interface** — Stdio (JSON lines), WebSocket/FastAPI, direct Python embedding. The contract for the "higher intelligence".

---

## Quick Start (Simulation Mode)

```bash
cd I:\GrokBuild\EmbodI\ReflexKernel

# Recommended: create venv
python -m venv .venv
.venv\Scripts\activate

# Core only (no heavy deps)
pip install -e .

# With visualization + optional ML
pip install -e .[viz,ml]

# Run the interactive simulation demo
python -m scripts.demo
# or
python scripts/demo.py
```

In the demo you can:

- Press keys to inject stimuli (e.g. `s` = sudden loud sound → flinch).
- Watch the on-screen avatar react (tension, eyes, posture).
- (Future) pipe JSON "thought seeds" via stdio.

See `configs/sim_only.yaml` for the default simulation profile.

---

## Teaching the Kernel (Higher-Intelligence Integration)

The higher mind interacts via the Interface layer. Example patterns:

### 1. Send a "thought seed" (fast affective priming)

```json
{"type": "thought_seed", "emotion": "startle", "intensity": 0.92, "valence": -0.7, "arousal": 0.95}
```

### 2. Record a demonstration (imitation)

```json
{"type": "begin_demo", "name": "gentle_wave_on_greet"}
# ... interact / stimuli arrive ...
{"type": "end_demo", "name": "gentle_wave_on_greet"}
```

### 3. Reward recent behavior (RL signal)

```json
{"type": "reward", "value": 0.85, "reason": "appropriate_social_tension_reduction", "window_steps": 8}
```

### 4. Subscribe to live reflex traces and current state

(Over WS or by polling `/state` or stdio `get_state`).

The kernel remains fully usable as a library:

```python
from reflexkernel import ReflexKernel
from reflexkernel.config import load_config

kernel = ReflexKernel.from_config("configs/default.yaml")
kernel.start()

# From higher mind / agent loop
kernel.inject_thought_seed({"emotion": "curiosity", "intensity": 0.6})
stim = kernel.perception.get_latest_stimuli()
actions = kernel.step()
```

---

## Remote Intelligence Integration (HTTP + WebSocket)

ReflexKernel can run as a **remote "body service"** that higher-level AIs (Grok, other LLMs, agent frameworks) connect to over the network.

The remote interface is a full FastAPI application with:
- REST endpoints for every major operation
- WebSocket for real-time push of reflex firings, state, learner events, etc.
- Simple API key authentication (`X-API-Key` header)
- Auto-generated OpenAPI docs + interactive Swagger UI at `/docs`
- CORS enabled for browser/local testing

### Running the Server

**Standalone (recommended for remote use):**

```bash
pip install -e .[server]

# Basic (simulation + dev key)
python -m scripts.server

# Production-like
python -m scripts.server \
    --config configs/default.yaml \
    --host 0.0.0.0 \
    --port 8000 \
    --api-key "$REFLEXKERNEL_API_KEY"
```

**Integrated with the interactive demo** (run local Pygame + keyboard while a remote intelligence connects):

```bash
# Edit configs/sim_only.yaml and set:
#   interface:
#     server:
#       enabled: true
#       port: 8000
#       api_key: "reflexkernel-dev"

python -m scripts.demo
```

The server will start in a background thread. You can still use the local keyboard controls and watch the Pygame avatar.

### Key Endpoints

- `POST /api/v1/thought` — inject thought seed
- `POST /api/v1/reward`
- `POST /api/v1/demo/begin` + `POST /api/v1/demo/end`
- `POST /api/v1/stimulus`
- `GET  /api/v1/state`
- `POST /api/v1/step`
- `POST /api/v1/command` — generic fallback (matches old `kernel.command` dicts)
- `WS   /ws/events` — real-time events (reflex_trace, state, learner_update, ...)

Full interactive documentation: `http://localhost:8000/docs`

### curl Examples

```bash
# Inject a strong startle
curl -X POST http://localhost:8000/api/v1/thought \
  -H "X-API-Key: reflexkernel-dev" \
  -H "Content-Type: application/json" \
  -d '{"emotion": "startle", "intensity": 0.95, "valence": -0.8, "arousal": 0.92}'

# Send reward
curl -X POST http://localhost:8000/api/v1/reward \
  -H "X-API-Key: reflexkernel-dev" \
  -d '{"value": 0.7, "reason": "good flinch", "window_steps": 4}'

# Get current body state
curl http://localhost:8000/api/v1/state \
  -H "X-API-Key: reflexkernel-dev"
```

### Python Async Client (httpx + websockets)

See `scripts/remote_client.py` for a complete ready-to-use example.

Basic usage:

```python
import asyncio
from scripts.remote_client import ReflexKernelRemoteClient

async def main():
    client = ReflexKernelRemoteClient("http://localhost:8000", "reflexkernel-dev")
    await client.inject_thought(emotion="curiosity", intensity=0.55)
    await client.send_reward(0.6, "nice orientation")
    state = await client.get_state()
    print(state)
    await client.close()

asyncio.run(main())
```

### Grok / LLM Wrapper Snippet (ready to adapt)

```python
# Example tool / function calling surface you can expose to Grok
async def body_thought(emotion: str, intensity: float = 0.6, valence: float = 0.0, arousal: float = 0.4):
    """Let the body 'feel' an emotion or internal state."""
    await client.inject_thought(emotion=emotion, intensity=intensity, valence=valence, arousal=arousal)
    return {"status": "thought injected"}

async def body_reward(value: float, reason: str):
    """Reinforce or discourage recent behavior."""
    await client.send_reward(value, reason)
    return {"status": "reward sent"}

async def body_observe():
    """Get the current embodied state (what the body is feeling right now)."""
    return await client.get_state()

# In a real agent loop you would also listen on the WebSocket for
# spontaneous reflex firings and feed summaries back into the LLM context.
```

### Authentication & Security Notes

- Default dev key: `reflexkernel-dev` (change it!)
- Set via `--api-key`, `REFLEXKERNEL_API_KEY` env var, or the `interface.server.api_key` config value.
- For anything beyond localhost, put the server behind a reverse proxy (nginx, caddy) with TLS and proper auth, or use a stronger mechanism.

All local functionality (PythonAPI, stdio, demo keyboard/Pygame) continues to work unchanged when the server is disabled (the default).

---

## Configuration

All behavior is driven by YAML + environment overrides (via Pydantic).

See:
- `configs/default.yaml`
- `configs/sim_only.yaml`

Key sections: `perception`, `bridge`, `reflex`, `learner`, `output`, `interface`.

---

## Project Status & Roadmap

This is the initial implementation focused on simulation + core teachable reflexes.

See [PLAN.md](./PLAN.md) for:
- Detailed architecture graph and data flow
- Complete folder structure
- Phased implementation notes
- Hardware and LLM integration strategy

Current priorities (v0.1):
- Solid simulation + keyboard stimuli
- 5–7 believable primitive reflexes
- Basic fusion + pattern detection
- Demonstration recording + simple behavioral cloning
- Reward modulation of reflex strength
- Clean stdio + in-process interface
- Pygame (or rich text) visualization

---

## Dependencies & Optionals

**Core** (always installed):
- pydantic, pyyaml, numpy, rich (pretty logs)

**Optional groups** (install with `pip install -e .[group]`):
- `viz` — pygame (avatar)
- `vision` — opencv-python, mediapipe
- `audio` — sounddevice or pyaudio + webrtcvad (onset detection)
- `ml` — sentence-transformers, scikit-learn (or torch CPU for embeddings + future policies)
- `server` — fastapi, uvicorn, websockets

The code **never hard-crashes** on missing optional deps — features are disabled with clear warnings.

---

## Extensibility Highlights

- New `Sensor` subclass → drop in `perception/`, register in config.
- New primitive reflex → implement in `reflex/primitives.py`, register.
- New learned behavior format → extend `learner/store.py`.
- Hardware driver → implement `Actuator` or `Sensor` interface (see `output/actuation.py` and perception base).
- Custom pattern detectors → subclass in `bridge/`.

Target platforms: desktop sim today, Raspberry Pi 5 + PiCamera2 + servos tomorrow, full humanoid later.

---

## Development

```bash
pip install -e .[dev]
pytest
```

See `tests/` for current coverage targets.

Run type checking (pyright or mypy) and keep docstrings up to date.

---

## License & Attribution

Internal research / embodiment infrastructure for the EmbodI initiative.

---

*ReflexKernel — because even the highest intelligence needs a nervous system.*
