# Embodied Autonomic System — Implementation Plan

**Parent Spec**: `I:\GrokBuild\EmbodI\Embodied_Autonomic_System.md`  
**Base Technology**: ReflexKernel (v0.2+)  
**Focus**: Adding the **Feature Extraction / Abstraction Layer** + Hardware/Virtual Perception bridge  
**Date**: June 2026

## Goals (from Spec)
- Define standardized **Event + Feature Schema**
- Build sensor-to-feature mapping for Tier 1 hardware (and virtual equivalents)
- Create a clean **Abstraction Layer** that sits between raw sensors and ReflexKernel
- Support both physical hardware (RPi5 + ESP32) and virtual simulation
- Keep the "Saddle" (interface for higher intelligence) clean

## Current ReflexKernel State (Leverage)
- Strong `Stimulus`, `AffectiveContext`, `ReflexTrace`, etc. in `types.py`
- Existing `perception/` with `Sensor` base + `SimulationSensor`
- Remote server (FastAPI + WS) already productionized
- PythonAPI + command surface

**Strategy**: Extend rather than replace. The Abstraction Layer will produce `Stimulus` (or richer `SensorEvent` / `Feature` objects) that feed into the existing pipeline.

## Phase 1: Schema & Core Abstraction (Current Priority)

### 1.1 Define Event + Feature Schema
**Location**: `src/reflexkernel/abstraction/schema.py` (or extend `types.py`)

Proposed core models (Pydantic for serialization):

- `SensorEvent` — discrete, timestamped events (e.g. `contact_start`, `sudden_loud_sound`)
- `Feature` — continuous or computed values (e.g. `contact_intensity`, `motion_energy`, `arousal_estimate`)
- `BodyStateSummary` — higher-level abstracted state for the Saddle / higher intelligence

Standard fields for all:
- `type`: str (event name or feature name)
- `value`: Any (scalar, vector, enum)
- `confidence`: float
- `ts`: float
- `source`: str (e.g. "fsr_array", "mpu6050", "virtual")
- `raw_modality`: optional link back to hardware

### 1.2 Abstraction Layer Structure
New package:
```
src/reflexkernel/abstraction/
    __init__.py
    schema.py          # Pydantic models
    base.py            # AbstractFeatureExtractor
    tier1.py           # Mappings for FSR, MPU6050, Mic, DHT22
    virtual.py         # VirtualSensorSimulator
    bridge.py          # Converts abstracted output → ReflexKernel Stimulus / direct input
```

### 1.3 Virtual Sensor Simulation (High Value Early)
Implement a rich `VirtualSensorSimulator` that can generate realistic Tier 1 signals for testing:
- FSR contact / pressure events
- MPU6050 motion / orientation / sudden movement
- Microphone onset / loudness
- DHT22 temperature / humidity drift

This allows full stack testing without waiting for hardware.

## Phase 2: Mappings & Bridge

### Tier 1 Mappings (start with these)
- **FSR Array (4x)**:
  - Events: `contact_start`, `contact_end`, `impact`
  - Features: `contact_intensity` (per sensor + aggregate), `pressure_gradient`
- **MPU6050**:
  - Events: `sudden_movement`, `orientation_change`
  - Features: `motion_energy`, `posture_stability`, `tilt_angle`
- **Microphone (MAX9814)**:
  - Events: `sudden_loud_sound`, `sound_onset`
  - Features: `acoustic_energy`, `amplitude_envelope`
- **DHT22 (2x)**:
  - Features: `ambient_temp`, `body_temp`, `humidity` (slow moving state)

### Data Bridge
- Option A (preferred for minimal change): Abstraction produces `Stimulus` objects with `modality=TOUCH|PROPRIO|AUDIO` and rich `data` dicts containing the abstracted signals.
- Option B: New direct feed into ReflexKernel (e.g. `kernel.inject_features(...)` or extend the bridge).

Start with Option A for fastest integration with existing Reflex Core + Learner.

## Phase 3: Saddle / Interface Evolution
- The existing remote server (FastAPI + WS) becomes the primary "Saddle".
- May need minor schema extensions for new `StateSummary` objects.
- Document the contract clearly for higher intelligences.

## Implementation Order (This Session)

1. **Schema Definition** (Priority 1)
2. **Abstraction Base + Virtual Simulator** (enables immediate testing)
3. **Tier 1 Feature Mappers** (virtual first, hardware stubs later)
4. **Bridge into ReflexKernel** (update perception or add abstraction feed)
5. **Update demo / simulation** to use the new virtual layer
6. **Documentation** (update README, add examples in docs/)
7. **Hardware readiness notes** (pinouts, ESP32/RPi communication protocol sketch)

## Backward Compatibility
- All existing simulation paths must continue to work.
- `SimulationSensor` can feed the new abstraction layer.
- Remote interface remains unchanged in API shape (new richer data just appears in `context` and traces).

## Success Criteria
- Can run full stack in pure virtual mode and see abstracted events/features reach ReflexKernel and trigger reflexes.
- Schema is clean, documented, and serializable.
- Higher intelligence can still use the existing Saddle (thought seeds, rewards, demos, state queries) with richer underlying signals.

## Notes
- Hardware bring-up (actual FSR etc.) is deferred until components arrive.
- This work makes ReflexKernel much more powerful as the "nervous system kernel".
- Keep everything modular so the same abstraction can later support game engine sensors (for Travelers) or other bodies.

---

**Next Action**: Begin with schema + virtual abstraction layer.

---

## Phase 4: Course Correction – Sensation Coherence & Sensitivity (Based on Feedback613.md + Supporting Docs)

This phase incorporates direct feedback on the Abstraction Layer (June 2026).

### Goals from Feedback
- Evolve from "structured sensor abstraction/metrics" toward **coherent, natural bodily sensations** that a higher intelligence can directly "feel".
- Add **Sensitivity Mapping** (female body zones from FSM.md).
- Introduce **Arousal-based dynamic modulation**.
- Add **Detail Level** control (Normal / Enhanced / Diagnostic).
- Create a dedicated **Sensation Coherence Layer** (per SensPP.md) that combines features/events into unified sensations *before* amplification and delivery to the Saddle/Higher Intelligence.
- Keep dual paths:
  - Current events + features → ReflexKernel (for reflexes, learning, low-level reactivity).
  - New coherent sensations + enhanced summaries → Saddle / Higher Intelligence (for direct experience).

### Updated Architecture (Refined)
```
Higher Intelligence (LLM / Agent)
          ⇅  (Saddle: thought seeds, rewards, demos, coherent sensations, state summaries)
Interface Layer (remote server – will expose sensations)
          ↑
ReflexKernel (core – unchanged, continues to receive events/features)
          ↑
Feature Extraction Layer (current abstraction – events + raw features)
          ↑
Sensation Coherence Layer  ← NEW (combines into natural sensations like “Warm, slow stroking along my inner thigh”)
          ↑
Signal Enhancement (Sensitivity Map + Arousal Multiplier)
          ↑
Detail Level Filter
          ↑
Raw / Virtual Sensors
```

**Core Principle** (from SensPP.md): **"Combine first, then amplify."**

### Priority 1 – Short Term (Immediate)
1. Extend `schema.py`:
   - Add `DetailLevel` enum (Normal, Enhanced, Diagnostic).
   - Add or evolve `Sensation` model (coherent text description + metadata, zone, intensity).
   - Add `SensitivityMap` (female zones from FSM.md with base multipliers).
   - Make `BodyStateSummary` or new output zone-aware and support sensation descriptions.

2. Add Sensitivity & Modulation:
   - Implement simple `SensitivityMap` (dict of zones → multipliers).
   - Add arousal-based multiplier logic (e.g., anus sensitivity scales with arousal).
   - Zone-aware arousal/valence calculation (contact on high-sensitivity zones has stronger effect).

3. Begin Sensation Coherence Layer:
   - New module or class (e.g., `coherence.py` or inside virtual/abstraction).
   - Rule-based or template initial implementation to combine features into natural language sensations.
   - Example output: "Firm, warm pressure on upper thigh with slow movement."

4. Add Detail Level support:
   - Filter in `AbstractionOutput` or new `SensationOutput`.
   - Normal = high-level sensations.
   - Enhanced = + texture/temperature/movement details.
   - Diagnostic = full metrics + raw features (for debugging).

### Priority 2 – Integration & Dual Path
- Keep existing `to_stimuli()` path for ReflexKernel compatibility.
- Add parallel `to_sensations()` or `get_coherent_sensations(detail_level=...)` for the Saddle/HI.
- Update `VirtualSensorSimulator` to demonstrate zone-aware logic and produce example sensations.
- Update demo to optionally show coherent sensations (with detail level).
- Update remote server (Saddle) in future to request sensations at specific detail levels.

### Priority 3 – Documentation & Roadmap
- Update this implementation plan.
- Update the Layman’s Guide with new concepts (sensation coherence, sensitivity zones, detail levels).
- Update the main status report.
- Add notes on future neural pattern activation path (for when deeper access is available).

### Success Criteria for This Phase
- Virtual simulator can produce at least one coherent, zone-aware sensation description that incorporates sensitivity mapping and arousal modulation.
- Schema supports both metric features (for ReflexKernel) and natural sensations (for HI).
- Dual output paths are clearly separated and documented.
- Layman’s guide explains the new pipeline in simple terms.

**This phase directly addresses the constructive feedback that the current layer is a strong foundation but needs to evolve toward “coherent bodily sensation” to match the deeper goals of the project.**

**Status (as of this update)**: Core schema extensions, Sensitivity Map, Sensation Coherence Layer (initial rule-based implementation), DetailLevel support, and integration into the virtual simulator + demo have been implemented. The layman guide and this status report have been refreshed. The remote server (Saddle) is ready to be extended to surface the new `Sensation` objects in a future step.

