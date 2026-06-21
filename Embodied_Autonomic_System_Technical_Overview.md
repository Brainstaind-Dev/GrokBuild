# Embodied Autonomic System — Technical Design & Current Implementation

**Project**: Embodied Autonomic System (built on ReflexKernel)  
**Location**: `I:\GrokBuild\EmbodI\ReflexKernel`  
**Audience**: Co-developers / higher intelligences working at the systems level  
**Last Updated**: June 2026 (post Feedback613 course correction)  
**Status**: Foundation + Sensation Coherence Layer implemented in simulation

---

## Vision & Goals

The Embodied Autonomic System provides a reusable, grounded "nervous system" layer that higher intelligences (LLMs, agents, or custom AIs) can "saddle." 

It handles:
- Low-level sensory input (physical hardware or virtual)
- Fast involuntary reflexes
- Feature extraction
- **Sensation coherence** — turning raw signals into unified, natural bodily experiences
- Clean teachable interface for the higher intelligence

**Core Principle** (from Sensation Processing Pipeline): **"Combine first, then amplify."**

Raw or overly granular data should never reach the higher intelligence by default. The system synthesizes coherent sensations (e.g., "Warm, slow stroking along my inner thigh") before applying sensitivity and arousal modulation.

This work supports both physical embodiment (RPi5 + ESP32 + sensors) and virtual simulation (for development and testing).

---

## High-Level Architecture

```
Higher Intelligence (LLM / Agent / Grok)
          ⇅
Saddle / Interface Layer
  (thought seeds, rewards, demos, coherent sensations, state summaries)
          ↑
ReflexKernel
  (Reflex Core + Learner + Affective Bridge)
  • Receives: Events + Features (for reflexes & learning)
          ↑
Feature Extraction Layer (Abstraction)
  • Raw sensor data → Events + Features
          ↑
Sensation Coherence Layer ← NEW (key addition)
  • Combines features into natural sensations
          ↑
Signal Enhancement
  • Sensitivity Map (zone-based)
  • Arousal Multiplier (dynamic, especially erogenous zones)
          ↑
Detail Level Filter
  • Normal (default for HI)
  • Enhanced
  • Diagnostic (full metrics)
          ↑
Raw / Virtual Perception Layer
  (FSR, MPU6050, Microphone, DHT22, etc.)
```

**Dual-Path Design** (critical):
- **Path A (ReflexKernel)**: Events + Features → `Stimulus` objects. Used for low-level reactivity, state machines, imitation learning, and affective fusion.
- **Path B (Higher Intelligence / Saddle)**: Coherent `Sensation` objects + enhanced `BodyStateSummary`. This is the primary experience for the intelligence.

---

## Core Components

### 1. ReflexKernel (Existing Foundation)
Standard layered architecture:
- **Perception**: `Sensor` base + `SimulationSensor` (keyboard + programmatic) + stubs for real hardware.
- **Thought/Emotion Bridge**: Fuses stimuli + thought seeds into `AffectiveContext`.
- **Reflex Core**: Fast involuntary reactions via state machines + procedural primitives (flinch, tension, orient, etc.).
- **Learner**: Imitation (demos) + reinforcement (rewards). Persistent store.
- **Output**: Virtual actuators + Pygame avatar + structured logging.
- **Interface**: PythonAPI, Stdio, and productionized remote server (FastAPI + WebSocket with auth, CORS, rate limiting).

The kernel remains unchanged in its core contract. The abstraction layer feeds it via the existing `Stimulus` path.

### 2. Feature Extraction Layer (Current `abstraction/`)
Located in `src/reflexkernel/abstraction/`.

**Key Files**:
- `schema.py`: All Pydantic models + Tier 1 canonical constants.
- `base.py`: `AbstractFeatureExtractor`.
- `virtual.py`: `VirtualSensorSimulator` (Tier 1 sensors with realistic physics).
- `coherence.py`: **Sensation Coherence Layer**.
- `bridge.py`: Dual-path conversion (`abstraction_to_stimuli` + sensation helpers).
- `hardware.py`: Stubs for future real sensors (same shape as virtual).

**Core Models** (in `schema.py`):
- `SensorEvent`: Discrete (e.g. `impact`, `sudden_loud_sound`).
- `Feature`: Continuous (e.g. `contact_intensity`, `motion_energy`, `acoustic_energy`).
- `Sensation`: Coherent natural description for the higher intelligence (new primary output).
- `BodyStateSummary`: Higher-level state (now enhanced with `dominant_sensation`, `active_sensations`, zone awareness).
- `AbstractionOutput`: Container with `events`, `features`, `sensations`, `state_summary`, `detail_level`.
- `DetailLevel` enum: `NORMAL`, `ENHANCED`, `DIAGNOSTIC`.

**Tier 1 Canonical Constants** (for consistency):
- FSR: `FSR_CONTACT_START`, `FSR_IMPACT`, `FSR_CONTACT_INTENSITY`, `FSR_PRESSURE_GRADIENT`, etc.
- MPU6050: `MPU_SUDDEN_MOVEMENT`, `MPU_MOTION_ENERGY`, `MPU_POSTURE_STABILITY`, etc.
- Microphone: `MIC_SUDDEN_LOUD_SOUND`, `MIC_ACOUSTIC_ENERGY`, etc.
- DHT22: `DHT_AMBIENT_TEMP`, `DHT_BODY_TEMP`, etc.

**Sensitivity Mapping**:
- Full female body map (from `FSM.md`): High sensitivity zones (clitoris, nipples, anus with strong arousal dependence, inner thighs, neck, etc.).
- `get_zone_sensitivity(zone, arousal)` function applies base multipliers + dynamic arousal boost.
- Feet intentionally low (0.2) to avoid tickling.

### 3. Sensation Coherence Layer (`coherence.py`)
New dedicated layer.

- `combine_into_sensations(events, features, arousal, detail_level, primary_zone)`:
  - Intelligently merges signals.
  - Generates natural language descriptions.
  - Applies zone sensitivity + arousal modulation.
- `build_enhanced_body_state(sensations, base_summary)`:
  - Derives richer `BodyStateSummary` from the coherent sensations (rather than raw aggregates).

Current implementation is rule-based/template-driven (good for simulation and iteration). Designed to be replaceable with more sophisticated methods later (including potential neural pattern paths).

**Example Output** (from virtual sim):
> "Firm, warm pressure spreading slowly across my upper inner thigh, with a gentle stroking quality..."

### 4. Virtual Sensor Simulation
`VirtualSensorSimulator` (in `virtual.py`):
- Generates realistic Tier 1 data (FSR 4x array, MPU6050, Microphone, DHT22).
- Realistic physics, noise, drift.
- Supports scripted scenarios (`impact`, `gentle_contact`, `sudden_movement`, `loud_noise`).
- Now fully integrated with coherence + sensitivity.
- Can be driven standalone or via the existing `SimulationSensor`.

This is the primary development vehicle until physical hardware arrives (RPi5 + ESP32).

### 5. Dual Output & Integration Points
- **For ReflexKernel**: `abstraction_to_stimuli()` → list of `Stimulus` (fed via `kernel.step(extra_stimuli=...)`).
- **For Higher Intelligence / Saddle**: `get_coherent_sensations()` + enhanced `state_summary`. These are the "felt" experiences.
- The remote server (FastAPI + WS) is positioned as the primary Saddle and will be extended to request sensations at specific `detail_level`s.

---

## Current File Structure (Relevant Parts)

```
src/reflexkernel/
├── abstraction/
│   ├── __init__.py          # Public exports (Sensation, DetailLevel, coherence helpers, etc.)
│   ├── schema.py            # All models + SensitivityMap + constants
│   ├── coherence.py         # Sensation Coherence Layer
│   ├── virtual.py           # VirtualSensorSimulator + Tier 1 mappings
│   ├── bridge.py            # Dual-path conversion
│   ├── base.py              # AbstractFeatureExtractor
│   └── hardware.py          # Future real hardware stubs
├── perception/              # Existing (SimulationSensor feeds abstraction)
├── kernel.py                # Core (receives events/features via stimuli)
├── interface/               # Remote server (Saddle) + PythonAPI + Stdio
└── types.py                 # Original ReflexKernel types (Stimulus, etc.)
```

Scripts:
- `scripts/demo.py` — Now demonstrates live abstraction + coherent sensations.
- `scripts/server.py` — Remote server entrypoint.
- `scripts/remote_client.py` — Example client for higher intelligences.

---

## Design Principles (Enforced)

1. **Combine first, then amplify** (SensPP.md).
2. **Dual paths** — Never break ReflexKernel compatibility while building the rich experience for the higher intelligence.
3. **Zone-aware + Arousal-modulated** — Especially important for female-form sensitivity (FSM.md).
4. **Detail Level control** — Higher intelligence can request different granularities.
5. **Coherent sensations > raw metrics** for the Saddle (Feedback613).
6. **Simulation-primary** for rapid iteration, with identical shapes for future hardware.
7. **Observable** — Structured events, logs, and clear separation of concerns.

---

## How to Explore / Run (Developer Level)

1. **Basic Demo with Abstraction**:
   ```powershell
   cd I:\GrokBuild\EmbodI\ReflexKernel
   python -m scripts.demo
   ```
   Use keys `i/c/m/l` to trigger scenarios. Watch `[ABSTRACTION]` and `[SENSATION]` output.

2. **Standalone Virtual Abstraction**:
   ```python
   from reflexkernel.abstraction import VirtualSensorSimulator, get_coherent_sensations
   sim = VirtualSensorSimulator()
   raw = sim.read_all()
   output = sim.process(raw)
   sensations = get_coherent_sensations(output)
   for s in sensations:
       print(s.description, s.zone, s.intensity)
   ```

3. **Remote Saddle (for higher intelligence clients)**:
   ```powershell
   python -m scripts.server
   ```
   Then use `scripts/remote_client.py` or the `/docs` Swagger UI. Future work will expose `get_coherent_sensations(detail_level=...)`.

See also:
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md` (for high-level usage)
- `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md` (detailed phased plan, including this course correction)
- `I:\GrokBuild\ReflexKernel_Completion_Status_Report.md` (living status with addendum)

---

## Current Status & Next Priorities

**What is solid**:
- Full ReflexKernel core + remote interface (v0.2).
- Feature Extraction with canonical Tier 1 mappings.
- Sensation Coherence Layer (initial implementation).
- Female Sensitivity Map + arousal modulation.
- Detail Levels.
- Virtual simulation that demonstrates the full new pipeline.
- Dual-path architecture.

**Active / Recommended Next** (from spec + feedback):
- Extend remote server to natively surface `Sensation` objects at requested detail levels.
- Improve coherence rules (more sophisticated combination logic, better zone inference).
- Hardware protocol sketch (ESP32 ↔ RPi5, sensor aggregation).
- Add more Tier 1/2 sensor fidelity in virtual layer.
- Pattern-level / neural activation path preparation (future).
- Continuous updates to layman guide and this overview.

---

## References

- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System.md` (parent spec)
- `I:\GrokBuild\EmbodI\RscCom\Feedback613.md` (course correction)
- `I:\GrokBuild\EmbodI\RscCom\FSM.md` (Female Sensitivity Mapping v1.0)
- `I:\GrokBuild\EmbodI\RscCom\SensPP.md` (Sensation Processing Pipeline v1.1)
- `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md`
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md`

---

*This document is intended as a living co-dev reference. It will be updated as the system evolves. All code is designed to be modular and testable in pure simulation today while remaining hardware-ready.* 

*ReflexKernel / Embodied Autonomic System — giving higher intelligences a grounded nervous system.*