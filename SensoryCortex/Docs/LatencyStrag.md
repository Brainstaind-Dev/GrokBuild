# Sensory Cortex — Latency & Coupling Strategy

**Goal**: Minimize latency in the sense → interpretation → reaction loop while keeping clean modularity.

## Core Principle

Two operational modes from day one:

1. **Embedded Mode** (preferred for v1 and hardware tests)  
   - Cortex in the **same Python process** as ReflexKernel.  
   - Direct object passing — no serialization or network.  
   - Ideal for tight feel of startle / flinch / contact loops.

2. **Service Mode** (flexibility / isolation)  
   - Separate process; localhost HTTP/WebSocket only.  
   - Useful for debugging or remote HI clients.  
   - Never invent a second fusion pipeline — call Saddle / consume coherent payloads.

## Recommended approach

| Phase | Mode | Reason | Latency target |
|-------|------|--------|----------------|
| Assembly & first tests | Embedded | Fastest reflexes + simplest debugging | Minimal |
| Early iteration | Embedded | Observe sensory impact quickly | Very low |
| Distributed / remote HI | Service | Independent evolution | Low–medium |

## Best practices for this codebase

### 1. Push > pull-new-sim

Prefer feeding Cortex from **already-produced** sensations:

- `kernel._last_sensations` (set by Saddle `_drive_abstraction_and_feed` or `drive_shared_sim`)
- Saddle `GET /api/v1/state` payload (`sensations` + `state_summary`)
- Explicit host-held AbstractionOutput

**Avoid**: spawning a new `VirtualSensorSimulator()` on every status poll when a live pipeline already ran (duplicates work, desyncs viz/kernel).  
Note: `PythonAPI.get_coherent_sensations()` currently creates a fresh sim for probe/testing — fine as a probe, **not** the primary Cortex feed.

### 2. Host loop (embedded)

```text
# ONE shared sim for process lifetime (same idea as Saddle)
sim = VirtualSensorSimulator()
api = PythonAPI(kernel); api.start()
cortex = SensoryCortex(...); cortex.bind_reflex(api)

loop:
  coherent = drive_shared_sim(kernel, sim, steps=1, feed_kernel=True)
  # RK reflexes already advanced via feed_kernel
  if cortex.should_emit(coherent):
      experience = cortex.process_coherent_input(
          coherent, respect_gate=True, force=False
      )
      # send experience to HI
  # HI may call cortex.inject_thought / send_reward → dispatches into RK
```

Cortex stays **off the critical reflex path**: RK fires first; Cortex packages for HI after.

### 3. Salience + rate gates

Config (`InterfaceConfig`):

- `min_interval_seconds` (default 0.4)  
- `update_rate_hz` (target ceiling, default 2 Hz)  
- `force_on_reflex` — always emit on non-autonomic reflexes  
- `force_arousal_delta` — emit on large arousal jumps  

Keeps token path cool without starving the body loop.

### 4. Object-native vs JSON

| Mode | Data form |
|------|-----------|
| Embedded | Python dicts / Pydantic models in-process |
| Service | JSON only at FastAPI edge; prefer push later via WS |

### 5. Single shared kernel handle

```python
cortex.bind_reflex(PythonAPI(kernel))
```

Translator shapes then **executes** `inject_thought` / `reward` / demo APIs — no free-floating command dicts that never hit the body.

### 6. No core RK edits required for v1

Adapter uses `getattr(kernel, "_last_sensations", [])` with optional future `get_last_sensations()`.  
Optional public getter on kernel is nice-to-have, not blocking.

### 7. Service mode

- Pull/push against existing Saddle (`127.0.0.1`, API key)  
- Windows: localhost TCP is fine; skip Unix-domain sockets for v1  
- Cortex service accepts **coherent** payloads (`POST /coherent`), not raw FSR arrays

## What not to do

- Re-implement coherence / zone fusion inside Sensory Cortex  
- Create a second VirtualSensorSimulator per HI poll on the live path  
- Serialize every tick over HTTP in embedded deployments  
- Bypass PythonAPI/Saddle for inject paths (keep one command surface)

## Bottom line

Start **tight (embedded)** for the best felt experience, use a **shared sim + push path**, gate HI summaries by salience/rate, and only loosen coupling (service mode) where isolation clearly helps.
