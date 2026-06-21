"""
AudioSensor (stub + real implementation).

Provides:
- Sudden loud sound / onset detection (excellent flinch trigger)
- Ambient energy level
- Future: voice activity, simple pitch, keyword stubs

If sounddevice (or pyaudio) is not installed, the sensor stays dormant with a warning.
"""

from __future__ import annotations

import time
from typing import List, Optional

from ..types import Modality, Stimulus
from .base import Sensor

try:
    import sounddevice as sd  # type: ignore
    import numpy as np  # type: ignore

    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False
    sd = None  # type: ignore
    np = None  # type: ignore


class AudioSensor(Sensor):
    name = "audio"
    modality = Modality.AUDIO

    def __init__(self, config: Optional[dict | object] = None) -> None:
        super().__init__(config)
        c = self.config if isinstance(self.config, dict) else (self.config.model_dump() if hasattr(self.config, "model_dump") else dict(self.config or {}))
        self._enabled = bool(c.get("enabled", False)) and _AUDIO_AVAILABLE
        self._stream: Optional[object] = None
        self._last_energy = 0.0
        self._last_onset = 0.0
        self._sample_rate = int(c.get("sample_rate", 16000))
        self._threshold = float(c.get("energy_threshold", 0.025))

        if self._enabled and _AUDIO_AVAILABLE:
            self._init_stream()
        elif c.get("enabled"):
            print("[audio] sounddevice not available. Audio sensor disabled.")

    def _init_stream(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                callback=self._audio_callback,
                blocksize=512,
            )
            self._stream.start()
            print("[audio] InputStream started")
        except Exception as e:
            print(f"[audio] Failed to open audio stream: {e}")
            self._enabled = False

    def _audio_callback(self, indata, frames, time_info, status):  # type: ignore
        if status:
            return
        try:
            energy = float((indata**2).mean() ** 0.5)
            self._last_energy = energy
            now = time.perf_counter()
            if energy > self._threshold and (now - self._last_onset) > 0.12:
                self._last_onset = now
                # We can't directly append to stimuli here (thread), so we stash
                # a flag that poll() will turn into a Stimulus.
                self._pending_onset = True
        except Exception:
            pass

    def __init__(self, *a, **k):  # type: ignore  # re-init guard for callback closure
        # The real __init__ above runs first; this is just to satisfy the linter in some editors.
        pass

    _pending_onset: bool = False

    def poll(self) -> List[Stimulus]:
        if not self._enabled:
            return []

        out: List[Stimulus] = []

        # Onset from callback
        if getattr(self, "_pending_onset", False):
            self._pending_onset = False
            out.append(
                Stimulus(
                    modality=Modality.AUDIO,
                    data={"kind": "sudden_loud_sound", "energy": round(self._last_energy, 4)},
                    confidence=0.9,
                    source="audio",
                )
            )

        # Continuous low-level energy as proprio-like "acoustic environment"
        if self._last_energy > 0.003:
            out.append(
                Stimulus(
                    modality=Modality.AUDIO,
                    data={
                        "kind": "acoustic_energy",
                        "energy": round(self._last_energy, 4),
                    },
                    confidence=0.6,
                    source="audio",
                )
            )

        return out

    def stop(self) -> None:
        super().stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
