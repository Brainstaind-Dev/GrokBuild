"""
Virtual Sensor Simulator for the Embodied Autonomic System.

This provides realistic synthetic sensor data for Tier 1 (and eventually Tier 2)
sensors. It is the primary way to develop and test the full stack while waiting
for physical hardware (FSR, MPU6050, MAX9814, DHT22, etc.).

Key features:
- Generates both raw readings and the abstracted events/features
- Supports scripted "scenarios" (e.g. "sudden impact", "gentle contact", "walking")
- Time-based drift and noise for realism
- Can be driven by the existing SimulationSensor or used standalone

Usage example:
    from reflexkernel.abstraction import VirtualSensorSimulator

    sim = VirtualSensorSimulator()
    raw = sim.read_all()
    output = sim.process(raw)   # or use the extractor
    stimuli = output.to_stimuli()
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, List, Optional

from .base import AbstractFeatureExtractor
from .schema import (
    AbstractionOutput,
    BodyStateSummary,
    DetailLevel,
    Feature,
    SensorEvent,
    SensorSource,
    Sensation,
    FSR_IMPACT,
    FSR_CONTACT_START,
    FSR_CONTACT_INTENSITY,
    FSR_PRESSURE_GRADIENT,
    MPU_SUDDEN_MOVEMENT,
    MPU_MOTION_ENERGY,
    MPU_POSTURE_STABILITY,
    MIC_SUDDEN_LOUD_SOUND,
    MIC_ACOUSTIC_ENERGY,
    DHT_AMBIENT_TEMP,
    DHT_BODY_TEMP,
)
from .coherence import combine_into_sensations, build_enhanced_body_state


class VirtualSensorSimulator(AbstractFeatureExtractor):
    """
    Generates synthetic Tier 1 sensor data + performs feature extraction.

    This is both a sensor simulator *and* a feature extractor for virtual mode.
    """

    name = "virtual_tier1"

    def __init__(self, config: Optional[Dict[str, Any]] = None, *, seed: Optional[int] = None):
        super().__init__(config)
        if seed is not None:
            effective_seed = seed
        else:
            effective_seed = config.get("seed", 42) if config else 42
        self.rng = random.Random(effective_seed)
        self._last_read_ts = time.perf_counter()

        # Internal state for realism
        self._fsr_values = [0.0] * 4
        self._mpu_accel = [0.0, 0.0, 1.0]  # x, y, z (gravity baseline)
        self._mpu_gyro = [0.0, 0.0, 0.0]
        self._mic_energy = 0.02
        self._temp_ambient = 22.5
        self._temp_body = 32.0

        # Scenario state
        self._current_scenario: Optional[str] = None
        self._scenario_end_ts = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_all(self) -> Dict[str, Any]:
        """Return current raw virtual sensor readings (what real hardware would produce)."""
        now = time.perf_counter()
        dt = now - self._last_read_ts
        self._last_read_ts = now

        self._update_internal_state(dt)

        return {
            "fsr": self._fsr_values.copy(),                    # 4 values, 0.0 - 1.0+
            "mpu": {
                "accel": self._mpu_accel.copy(),               # m/s² or g
                "gyro": self._mpu_gyro.copy(),                 # deg/s
            },
            "microphone": {
                "energy": self._mic_energy,
                "onset": self._mic_energy > 0.15,              # simple flag
            },
            "dht22": {
                "ambient_temp": self._temp_ambient,
                "body_temp": self._temp_body,
            },
            "ts": now,
        }

    def process(self, raw_data: Optional[Dict[str, Any]] = None, detail_level: DetailLevel = DetailLevel.NORMAL) -> AbstractionOutput:
        """
        Run the full virtual perception + abstraction pipeline using explicit
        Tier 1 sensor-to-feature mappings.

        This is the heart of the virtual "body" for development and testing.
        detail_level controls sensation richness passed to Saddle/HI (NORMAL default avoids overload).
        """
        if raw_data is None:
            raw_data = self.read_all()

        now = raw_data.get("ts", time.perf_counter())
        events: List[SensorEvent] = []
        features: List[Feature] = []

        # ============================================================
        # FSR Array (4x) - Tactile / contact events
        # ============================================================
        fsr = raw_data.get("fsr", [0.0] * 4)
        max_fsr = max(fsr) if fsr else 0.0
        active_contacts = sum(1 for v in fsr if v > 0.08)
        avg_fsr = sum(fsr) / len(fsr) if fsr else 0.0

        # Discrete events
        if max_fsr > 0.65 and self.rng.random() < 0.6:
            events.append(SensorEvent(
                type=FSR_IMPACT,
                value={"max_pressure": round(max_fsr, 3), "contacts": active_contacts},
                confidence=0.85,
                ts=now,
                source=SensorSource.FSR_ARRAY,
                raw_modality="touch",
            ))
        elif max_fsr > 0.12:
            event_type = FSR_CONTACT_START if max_fsr > 0.25 else "light_contact"
            events.append(SensorEvent(
                type=event_type,
                value={"pressure": round(max_fsr, 3), "sensor_count": active_contacts},
                confidence=0.75,
                ts=now,
                source=SensorSource.FSR_ARRAY,
                raw_modality="touch",
            ))

        # Continuous features
        features.append(Feature(
            type=FSR_CONTACT_INTENSITY,
            value=round(max_fsr, 3),
            confidence=0.9,
            ts=now,
            source=SensorSource.FSR_ARRAY,
            raw_modality="touch",
        ))

        # Simple pressure gradient (left-right difference as example)
        if len(fsr) >= 4:
            left = (fsr[0] + fsr[1]) / 2
            right = (fsr[2] + fsr[3]) / 2
            gradient = abs(left - right)
            features.append(Feature(
                type=FSR_PRESSURE_GRADIENT,
                value=round(gradient, 3),
                confidence=0.8,
                ts=now,
                source=SensorSource.FSR_ARRAY,
                raw_modality="touch",
            ))

        # ============================================================
        # MPU6050 - Motion, orientation, sudden movement
        # ============================================================
        mpu = raw_data.get("mpu", {})
        accel = mpu.get("accel", [0, 0, 1])
        gyro = mpu.get("gyro", [0, 0, 0])

        motion_energy = math.sqrt(sum(a * a for a in accel)) + (math.sqrt(sum(g * g for g in gyro)) * 0.1)

        if motion_energy > 2.8:
            events.append(SensorEvent(
                type=MPU_SUDDEN_MOVEMENT,
                value={"energy": round(motion_energy, 2)},
                confidence=0.8,
                ts=now,
                source=SensorSource.MPU6050,
                raw_modality="proprio",
            ))

        features.append(Feature(
            type=MPU_MOTION_ENERGY,
            value=round(motion_energy, 3),
            confidence=0.85,
            ts=now,
            source=SensorSource.MPU6050,
            raw_modality="proprio",
        ))

        # Posture stability (inverse of gyro activity)
        gyro_magnitude = abs(gyro[0]) + abs(gyro[1]) + abs(gyro[2])
        posture = max(0.0, 1.0 - (gyro_magnitude * 0.08))
        features.append(Feature(
            type=MPU_POSTURE_STABILITY,
            value=round(posture, 3),
            confidence=0.7,
            ts=now,
            source=SensorSource.MPU6050,
            raw_modality="proprio",
        ))

        # ============================================================
        # Microphone - Sudden sound detection
        # ============================================================
        mic = raw_data.get("microphone", {})
        mic_energy = mic.get("energy", 0.02)

        if mic.get("onset") or mic_energy > 0.18:
            events.append(SensorEvent(
                type=MIC_SUDDEN_LOUD_SOUND,
                value={"energy": round(mic_energy, 3)},
                confidence=0.82,
                ts=now,
                source=SensorSource.MICROPHONE,
                raw_modality="audio",
            ))

        features.append(Feature(
            type=MIC_ACOUSTIC_ENERGY,
            value=round(mic_energy, 3),
            confidence=0.88,
            ts=now,
            source=SensorSource.MICROPHONE,
            raw_modality="audio",
        ))

        # ============================================================
        # DHT22 - Environmental + body temperature
        # ============================================================
        dht = raw_data.get("dht22", {})
        features.append(Feature(
            type=DHT_AMBIENT_TEMP,
            value=round(dht.get("ambient_temp", 22.0), 1),
            confidence=0.95,
            ts=now,
            source=SensorSource.DHT22,
            raw_modality="proprio",
            window_ms=5000,
        ))
        features.append(Feature(
            type=DHT_BODY_TEMP,
            value=round(dht.get("body_temp", 32.0), 1),
            confidence=0.9,
            ts=now,
            source=SensorSource.DHT22,
            raw_modality="proprio",
            window_ms=8000,
        ))

        # ============================================================
        # Body State Summary + Coherent Sensations for Higher Intelligence / Saddle
        # ============================================================
        arousal = min(1.4, 0.25 + (max_fsr * 0.7) + (motion_energy * 0.12) + (mic_energy * 0.9))
        contact_state = "multiple" if active_contacts > 1 else (
            "firm" if max_fsr > 0.5 else ("light" if max_fsr > 0.12 else "none")
        )

        # Determine primary contact zone for sensitivity (simple heuristic for demo / virtual)
        primary_zone = "upper_inner_thigh" if max_fsr > 0.3 else "whole_body"

        # Generate coherent sensations (new primary output path for higher intelligence)
        sensations: List[Sensation] = combine_into_sensations(
            events=events,
            features=features,
            arousal=arousal,
            detail_level=detail_level,
            primary_zone=primary_zone,
        )

        base_state = BodyStateSummary(
            arousal_estimate=round(arousal, 3),
            valence_estimate=round(0.1 - (max_fsr * 0.3), 3),
            posture_stability=round(posture, 3),
            contact_state=contact_state,
            dominant_event=events[0].type if events else None,
            environmental_temp=dht.get("ambient_temp"),
            ts=now,
            confidence=0.75,
        )

        enhanced_state = build_enhanced_body_state(sensations, base_state)

        return AbstractionOutput(
            events=events,
            features=features,
            sensations=sensations,
            state_summary=enhanced_state,
            detail_level=detail_level,
            ts=now,
        )

    # ------------------------------------------------------------------
    # Scenario Control (great for demos and testing)
    # ------------------------------------------------------------------

    def trigger_scenario(self, name: str, duration: float = 1.5):
        """Force a particular interesting behavior for a short time."""
        self._current_scenario = name.lower()
        self._scenario_end_ts = time.perf_counter() + duration

    def _update_internal_state(self, dt: float):
        """Advance the virtual sensors with physics-like behavior."""
        now = time.perf_counter()

        # Decay previous contacts
        for i in range(4):
            self._fsr_values[i] = max(0.0, self._fsr_values[i] - dt * 1.8)

        # Apply current scenario or natural variation
        scenario = self._current_scenario
        if scenario and now > self._scenario_end_ts:
            self._current_scenario = None
            scenario = None

        if scenario == "impact":
            self._fsr_values[0] = 0.95
            self._fsr_values[1] = 0.7
            self._mpu_gyro = [45, 20, 10]
            self._mic_energy = 0.45
        elif scenario == "gentle_contact":
            self._fsr_values[2] = 0.35
            self._mpu_accel = [0.1, 0.05, 0.98]
        elif scenario == "sudden_movement":
            self._mpu_gyro = [self.rng.uniform(-80, 80) for _ in range(3)]
            self._mic_energy = 0.12
        elif scenario == "loud_noise":
            self._mic_energy = 0.55
        else:
            # Natural idle variation
            for i in range(4):
                self._fsr_values[i] = max(0.0, self._fsr_values[i] + self.rng.uniform(-0.03, 0.06))

            # Small motion
            self._mpu_gyro = [self.rng.gauss(0, 3) for _ in range(3)]
            self._mpu_accel = [
                self.rng.gauss(0, 0.08),
                self.rng.gauss(0, 0.08),
                1.0 + self.rng.gauss(0, 0.04),
            ]

            # Ambient sound
            self._mic_energy = max(0.015, self._mic_energy * 0.6 + self.rng.uniform(0, 0.04))

        # Slow environmental drift
        self._temp_ambient += self.rng.gauss(0, 0.002) * dt
        self._temp_body += self.rng.gauss(0, 0.001) * dt

        # Clamp values
        self._fsr_values = [max(0.0, min(1.8, v)) for v in self._fsr_values]
        self._mic_energy = max(0.01, min(1.0, self._mic_energy))
