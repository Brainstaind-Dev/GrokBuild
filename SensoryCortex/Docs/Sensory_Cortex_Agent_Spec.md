# Sensory Cortex Agent Specification

**Project**: GrokBuild / Embodi  
**Component**: Sensory Cortex Agent  
**Version**: 0.1.1 (Aligned with ReflexKernel coherence + Saddle)  
**Date**: 2026-07-15 (updated 2026-07-24)  
**Goal**: Interpretive layer that packages ReflexKernel’s coherent sensations into meaningful, token-efficient experiences for the higher intelligence (Grok), with bidirectional command shaping.

## 1. Purpose & Vision

The Sensory Cortex sits **between** ReflexKernel (body/nervous system) and the higher intelligence.

It does **not** re-fuse sensors or re-run the Sensation Coherence layer. It:

1. Accepts already-coherent `Sensation` objects + body state from RK  
2. Adds temporal continuity (memory, deltas, trends)  
3. Packages a clean HI envelope (`SensoryUpdate`)  
4. Shapes HI intent into RK thought seeds / rewards / demos (and dispatches when bound)

```
Higher Intelligence (Grok / agent tools)
        ↑↓  SensoryUpdate + shaped commands
[ Sensory Cortex ]   ← this package
        ↑↓  coherent sensations / inject APIs
ReflexKernel Interface (PythonAPI / Saddle / MCP)
        ↑↓
ReflexKernel Core + Abstraction + Coherence
```

## 2. Key Goals

- Deliver **meaningful felt experience** to Grok (not raw data).
- **Preserve** rich RK fields (temporal, texture, zone_character, arousal_modulated_richness).
- Maintain strict **token efficiency** for long sessions.
- Preserve **modularity** — do not bloat ReflexKernel.
- Support bidirectional flow (body → Grok and Grok → body).
- **Embedded-first** low latency; service mode secondary.
- Produce consistent, inspectable, debuggable output.

## 3. Layer ownership

| Concern | Owner |
|--------|--------|
| Sensor fusion, zone sensitivity, arousal-modulated richness, NL synthesis | ReflexKernel Coherence |
| Caps for HI overload (`MAX_SENSATIONS_FOR_HI`, DetailLevel) | ReflexKernel Interface |
| Temporal continuity, deltas/trends, mood packaging | Sensory Cortex |
| Command shaping (dampen/boost from embodied state) | Sensory Cortex Translator |
| Actually stepping kernel / firing seeds / rewards | ReflexKernel via PythonAPI or Saddle |

## 4. Core Data Schema (SensoryUpdate)

```json
{
  "timestamp": "ISO8601",
  "affective_core": {
    "valence": -1.0,
    "arousal": 0.0,
    "dominance": 0.5,
    "overall_mood": "steady_attention"
  },
  "salient_sensations": [
    {
      "description": "…",
      "zone": "upper_inner_thigh",
      "intensity": 0.8,
      "valence": 0.3,
      "arousal_contribution": 0.4,
      "novelty": 0.7,
      "category": "combined_touch",
      "temporal_quality": "sustained",
      "texture_qualities": ["warm", "smooth"],
      "movement_quality": "gentle stroking",
      "arousal_modulated_richness": 0.72,
      "zone_character": "high-sensitivity erogenous zone",
      "confidence": 0.9
    }
  ],
  "reflex_activity": ["flinch", "orient"],
  "active_patterns": ["startle_response"],
  "delta_from_last": "arousal rising; new contact",
  "trend": "rising arousal",
  "token_estimate": 120,
  "source": "sensory_cortex",
  "detail_level": "normal"
}
```

Canonical field name: **`salient_sensations`** (not `salient_stimuli`).

## 5. Public API

```python
from SensoryCortex import SensoryCortex, load_config
from SensoryCortex.adapters import from_kernel, drive_shared_sim

cortex = SensoryCortex(config=load_config().model_dump(), mode="embedded")
cortex.bind_reflex(python_api)  # optional, enables real dispatch

update = cortex.process_coherent_input(coherent_dict)
# or gated:
if cortex.should_emit(coherent_dict):
    update = cortex.process_coherent_input(coherent_dict, respect_gate=True, force=False)

cortex.inject_thought(emotion, intensity, valence=…, arousal=…, text=…)
cortex.send_reward(value, reason=…)
cortex.begin_demonstration(name) / end_demonstration(name)
cortex.get_current_experience() / get_trend() / recall()
```

### Tool interface roadmap (for Grok function-calling)

| Tool | Status |
|------|--------|
| cortex process / get experience | Implemented (Python + service REST) |
| cortex_inject_thought | Implemented (dispatch when bound) |
| cortex_send_reward | Implemented |
| cortex_record_demonstration | Implemented (begin/end) |
| cortex_recall_memory | Implemented (`recall`) |
| cortex_adjust_sensitivity | Not yet (would map to RK config / future) |
| MCP tool wrappers | Planned |

## 6. Coupling (latency)

See `LatencyStrag.md`. Summary:

- **Embedded primary**: same process, object passing, shared `VirtualSensorSimulator`
- **Push path**: after `kernel.step` / Saddle drive → `from_kernel` / `drive_shared_sim` → `process_coherent_input`
- **Do not** create a new VirtualSensorSimulator on every status poll when live pipeline already ran
- Salience + `min_interval_seconds` gates HI emission rate

## 7. Location

```
I:\GrokBuild\SensoryCortex\     # repo-root package (Embodi-adjacent)
```

Import: add repo root to `PYTHONPATH` or `sys.path`. Optional future: move under `EmbodI/SensoryCortex/`.

## 8. Success criteria

- Grok receives coherent, affectively rich updates that preserve RK richness fields.
- Token usage efficient (typical update ≪ 400 tokens).
- Bidirectional loop works when `bind_reflex(PythonAPI)` is used.
- RK dual path unchanged (stimuli for reflexes; sensations for HI).
- Unit tests pass without requiring hardware.

## 9. Implementation status (2026-07-24)

| Phase | Status |
|-------|--------|
| MVP summarizer + memory + translator | Done |
| Schema preserves rich Sensation fields | Done |
| RK adapter (`adapters/reflex_kernel.py`) | Done |
| Embedded bind + should_emit | Done |
| Service REST (coherent input) | Done |
| `kernel.get_last_sensations()` public API | Done |
| Demo loop wiring (`scripts.demo`) | Done |
| Saddle `/api/v1/experience` + cortex status | Done |
| MCP tools (`cortex_*`) + shared sim session | Done |
| Saddle poll/WS consumer (`runners.service_runner --mode consumer`) | Done |

### MCP tools (ReflexKernel MCP server)

- `cortex_get_experience(force=False)`
- `cortex_inject_thought(...)`
- `cortex_send_reward(...)`
- `cortex_get_trend()`
- `cortex_recall(max_age_minutes=20)`

### Saddle endpoints

- `GET /api/v1/experience?force=false`
- `GET /api/v1/cortex/status`
- `GET /api/v1/cortex/trend`

### Saddle consumer

```powershell
python -m SensoryCortex.runners.service_runner --mode consumer --saddle http://127.0.0.1:8765
```
