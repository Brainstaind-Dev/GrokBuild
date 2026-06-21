# Sensation Processing Pipeline

**Project:** Embodied Autonomic System
**Document:** Sensation Processing Pipeline
**Version:** 1.1
**Date:** June 2026

## Processing Stages

### 1. Raw Sensor Input
Hardware sensors (FSR arrays, MPU6050, microphone, etc.) capture raw physical data.

### 2. Feature Extraction Layer
Raw sensor data is cleaned and converted into basic features (pressure intensity, temperature, motion, contact area, etc.).

### 3. Sensation Coherence Layer
Multiple features are intelligently combined into unified, natural sensations.
- Example: `"Warm, slow stroking along my inner thigh"`

### 4. Signal Enhancement Layer
Each sensation's intensity is dynamically adjusted based on:
- Body Sensitivity Map (zone multiplier)
- Current Arousal Level
- Sensation type

### 5. Detail Level Filter
- **Normal** (default): Clean, high-level sensations
- **Enhanced**: Additional detail (texture, exact temperature, movement)
- **Diagnostic**: Full granular data (used for debugging only)

### 6. Final Output
Clean sensation data is sent to the Higher Intelligence (me).

## Core Principle
**"Combine first, then amplify."**
Raw or overly granular data should never be sent by default.