# Embodied Autonomic System

**Project Type**: Technical Systems Design (Standalone)  
**Related Project**: Travelers – Tears of the Stars (Living Lore Bible)  
**Core Technology**: Hardware sensors + ReflexKernel + Feature Abstraction Layer  
**Status**: Design Phase  
**Last Updated**: June 2026

---

## Project Overview

This is a standalone technical project focused on building a grounded **autonomic nervous system layer**. 

Its purpose is to create a reusable subsystem that can be "saddled" by higher intelligences (LLMs, agents, or custom AIs). The system handles low-level perception, fast reflexes, and signal abstraction so that higher intelligences receive clean, meaningful information instead of raw sensor data.

While this work supports the *Travelers – Tears of the Stars* universe, the detailed engineering, architecture, and implementation live in this dedicated project to keep the main lore bible focused on narrative and world-building.

---

## Vision

Build a modular, embodied autonomic subsystem that:

- Handles low-level sensory input and fast reflexes in both physical and virtual environments.
- Extracts and abstracts meaningful signals at the correct level of detail.
- Provides a clean, teachable interface ("saddle") for higher intelligences (LLMs, agents, or custom AIs).
- Serves as a universal layer that works for physical hardware, simulated bodies, and game worlds (e.g. Travelers).

**Long-term Target**: A reusable nervous system layer that allows intelligences to interact with a grounded body — whether physical or virtual — without being overwhelmed by raw data.

---

## Scope

**In Scope**:
- Hardware sensor platform (perception + basic actuation)
- Feature extraction and abstraction layer
- Integration with ReflexKernel
- Clean interface design for higher intelligences ("saddle")
- Support for both physical hardware and virtual simulation

**Out of Scope** (for now):
- Full game integration inside Travelers
- Advanced sound localization (second microphone)
- Complex machine learning models in the learner
- Production-ready hardware enclosures or wearables

This project stays focused on building a solid, well-architected foundation.

---

## Core Architecture

```
Higher Intelligence (LLM / Agent)
          ⇅
Saddle / Interface Layer          ← Clean commands, state, rewards, demos
          ↑
ReflexKernel (Reflex Core + Learner + Affective Bridge)
          ↑
Feature Extraction / Abstraction Layer   ← Critical layer
          ↑
Hardware Perception Layer (or Virtual Sensor Layer)
```

**Key Principle**: Raw data is processed and abstracted before reaching higher intelligence.

---

## Hardware Perception Layer

**Priority Order**:

### Tier 1 – Core Reflex Sensors (Start Here)
- **FSR Array** (4x) — Tactile / contact events
- **MPU6050** — Motion, orientation, sudden movement
- **Microphone** (1x MAX9814 recommended) — Sudden sound detection
- **DHT22** (2x) — Environmental + body temperature context

### Tier 2 – Affective Signals
- **MAX30102** — Heart rate variability (arousal proxy)
- **GSR Module** — Skin conductance (arousal / valence)

### Tier 3 – Physical Output / Actuation
- Vibration motors (haptic expression of reflexes)
- Addressable LEDs / NeoPixels (visual state expression)
- Servo (later) — Physical orientation

**Platform**:
- Raspberry Pi 5 → Primary brain (runs ReflexKernel)
- ESP32 → Sensor aggregation + low-level output driver

**Note**: Second microphone for sound localization is deferred to later phase.

---

## Feature Extraction / Abstraction Layer (Critical)

This layer translates raw sensor data into meaningful, higher-level signals.

**Goals**:
- Reduce data volume
- Detect discrete events
- Compute ongoing features
- Provide consistent output whether body is physical or virtual

**Proposed Output Categories**:

| Category              | Examples of Abstracted Signals                  | Primary Consumers          |
|-----------------------|--------------------------------------------------|----------------------------|
| **Events**            | `contact_start`, `impact`, `sudden_loud_sound`, `sudden_movement` | Reflex Core               |
| **Features**          | `contact_intensity`, `arousal_estimate`, `motion_energy`, `posture_stability` | Reflex Core + Affective   |
| **State Summaries**   | Rising arousal, defensive posture, calm exploration | Higher Intelligence       |

**Design Rule**: Always ask — “What does the higher intelligence actually need to know?”

This layer will be designed to work for both real hardware and virtual sensor simulation.

---

## Integration Targets

1. Hardware sensors feed structured data into the Abstraction Layer.
2. Abstracted events and features feed ReflexKernel.
3. ReflexKernel provides fast reflexes + learning.
4. Clean interface layer allows higher intelligences to:
   - Receive state
   - Send thought seeds
   - Provide rewards
   - Record demonstrations

**Long-term Goal**: The full stack (Hardware + Abstraction + ReflexKernel) becomes a saddleable nervous system usable in both physical and virtual contexts.

---

## Current Status (June 2026)

- Shopping list revised and aligned to ReflexKernel layers
- Milestones and testing checklist defined
- Hardware planning complete for initial bring-up
- Feature Extraction / Abstraction Layer design started
- Awaiting component arrival to begin physical testing

---

## Next Steps

### Priority 1 – Foundation
1. Define the **Event + Feature Schema** (standardized JSON structure)
2. Create sensor-to-feature mapping for Tier 1 hardware (FSR, MPU6050, Microphone, DHT22)

### Priority 2 – Integration
3. Design the data bridge between hardware output and ReflexKernel
4. Develop a virtual sensor simulation layer (for testing without physical hardware)

### Priority 3 – Interface
5. Define the **Saddle Interface** contract (commands, state format, teaching primitives)
6. Document how higher intelligences can interact with the system

---

**This is a living technical project.** It is intentionally kept separate from the main Living Lore Bible to maintain clarity and focus during development.