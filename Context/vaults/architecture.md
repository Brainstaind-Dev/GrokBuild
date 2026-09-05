# Vault — Architecture

## Layer stack (bottom-up)

```
Perception → Thought/Emotion Bridge → Reflex Core → Learner → Output/Actuation → Interface
```

Higher intelligence uses **Interface** (Python API, stdio JSON-lines, WebSocket/FastAPI/Saddle).

## Ownership (locked)

| Component | Owns | Does **not** own |
|-----------|------|------------------|
| ReflexKernel Coherence | Fusion / richness of stimuli | HI packaging |
| Saddle / PythonAPI / MCP | Caps, inject, live drive | Re-fusion |
| Sensory Cortex | Temporal memory, deltas/trends, mood packaging, command shape/dispatch | Sensor re-fusion |
| HIAgent | xAI loop over body (embedded or Saddle) | Kernel internals |

## Dual path (HI packaging)

- **Stimuli** — low-latency reflex path  
- **Sensations** — HI-facing packaged experience (`/api/v1/experience`, `kernel.get_last_sensations()`)

## Tick-Door (A, 2026-09-04)

Physical feel enters on `kernel.step` via `HardwareSensor` + deterministic `extract_tier1`. Missing hardware **fail_open** (empty poll). One live process, **one** `VirtualSensorSimulator` (PythonAPI/Saddle match MCP). Not AfferentBus. Not D0.

## Dual path (stimulus sources → RK)

ReflexKernel lives **only** in the Embodi main suite. It does **not** run inside Unreal.

```
                    ┌─────────────────────┐
  Real world  ──►   │  Perception / inject │
  (Pi, ESP32, FSR…) │         ▼            │──► ReflexKernel ──► Cortex / HI
  Virtual world ──► │   same Stimulus API  │
  (UE avatar/env)   └─────────────────────┘
```

| Path | Role |
|------|------|
| **Physical** | Real sensors → RK (hardware / Pi / ESP32 / mics…) |
| **Virtual** | UE-simulated contacts, motion, props → same inject/stimulus contracts |
| **UE avatar** | Rigged presentation + optional virtual sensor theater; **not** a second kernel |
| **Outbound** | RK/Cortex state → UE for visualization (Saddle JSON/WS) |

Both inbound paths are first-class; neither replaces the other.

## Shared sim rule

One `VirtualSensorSimulator` per process when live pipeline runs — never spin a new virtual sim on every HI poll.

## Key trees

| Path | Role |
|------|------|
| `EmbodI/ReflexKernel/` | Kernel package |
| `SensoryCortex/` | HI packaging layer |
| `HIAgent/` | xAI agent body loop |
| `Travelers/Docs/` | Plans (scaffold, UE, eval) |

## Principles

Simulation-first · modular layers · graceful optional deps · structured logs · pytest for RK changes

## North star (intent — locked with user 2026-08-15)

**Ground an ethereal mind in a path of enrichment** — real and virtual worlds feeding one autonomic body — so the HI is not only language, but *situated*.

### Toward activation-pattern feel

Today HI mostly sees **packaged language/JSON** (sensations, mood, deltas).  
The long arc is for Embodi to address the HI increasingly through **activation patterns** — structured, body-native signals (zone maps, arousal fields, reflex bursts, temporal envelopes) that are the closest thing the HI has to **feelings**, whether driven by physical sensors or virtual sim.

| Horizon | HI receives | Role |
|---------|-------------|------|
| Now | Experience packages, sensations, state | Interpretable, debuggable, tool-friendly |
| Near | Richer pattern fields + language | Dual channel: feel-shape + NL gloss |
| Aim | **Activation patterns as primary address** | Grounded affect; language becomes optional commentary |

Cortex/RK still own body-side fusion and packaging; they do **not** become the HI. Patterns are the **interface language of embodiment**, not a replacement mind.
