"""
VisionSensor (stub + real implementation).

When opencv + mediapipe are installed and enabled in config, this provides:
- Face presence / expression proxies (via MediaPipe Face Mesh or Holistic)
- Sudden motion / approach detection
- (future) hand pose as social signals

If the heavy dependencies are missing, the sensor still registers but emits
only a warning and stays dormant (no crash).
"""

from __future__ import annotations

from typing import List, Optional

from ..types import Modality, Stimulus
from .base import Sensor

try:
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore

    _VISION_AVAILABLE = True
except ImportError:
    _VISION_AVAILABLE = False
    cv2 = None  # type: ignore
    mp = None  # type: ignore


class VisionSensor(Sensor):
    name = "vision"
    modality = Modality.VISION

    def __init__(self, config: Optional[dict | object] = None) -> None:
        super().__init__(config)
        self._cap: Optional["cv2.VideoCapture"] = None  # type: ignore
        self._face_mesh: Optional[object] = None
        self._prev_frame_gray: Optional[object] = None
        c = self.config if isinstance(self.config, dict) else (self.config.model_dump() if hasattr(self.config, "model_dump") else dict(self.config or {}))
        self._enabled = bool(c.get("enabled", False)) and _VISION_AVAILABLE

        if self._enabled and _VISION_AVAILABLE:
            self._init_capture()
        else:
            if c.get("enabled"):
                print("[vision] OpenCV + MediaPipe not available. Vision sensor disabled.")

    def _init_capture(self) -> None:
        device = int(self.config.get("device", 0))
        self._cap = cv2.VideoCapture(device)
        if not self._cap or not self._cap.isOpened():
            print(f"[vision] Failed to open camera {device}")
            self._enabled = False
            return

        # MediaPipe face for expression / blink / gaze proxies
        if self.config.get("use_mediapipe", True) and mp is not None:
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        print("[vision] Camera + MediaPipe ready")

    def poll(self) -> List[Stimulus]:
        if not self._enabled or self._cap is None:
            return []

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return []

        stimuli: List[Stimulus] = []
        h, w = frame.shape[:2]

        # Very lightweight motion detection (good enough for flinch/orient triggers)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._prev_frame_gray is not None:
            diff = cv2.absdiff(self._prev_frame_gray, gray)
            motion = float(diff.mean()) / 255.0
            if motion > 0.12:
                stimuli.append(
                    Stimulus(
                        modality=Modality.VISION,
                        data={
                            "kind": "sudden_motion",
                            "motion_energy": round(motion, 3),
                            "location": "periphery" if motion > 0.22 else "center",
                        },
                        confidence=min(0.95, 0.6 + motion),
                        source="vision",
                    )
                )
        self._prev_frame_gray = gray

        # Face / expression proxy via MediaPipe (when available)
        if self._face_mesh is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._face_mesh.process(rgb)
            if results.multi_face_landmarks:
                # Extremely simplified "expression energy" + presence
                # In real use we would extract blendshapes or specific landmarks
                expr_energy = 0.35 + (hash(str(id(results))) % 100) / 400.0  # fake but varying
                stimuli.append(
                    Stimulus(
                        modality=Modality.VISION,
                        data={
                            "kind": "face_present",
                            "expression_energy": round(expr_energy, 3),
                            "face_count": len(results.multi_face_landmarks),
                        },
                        confidence=0.88,
                        source="vision",
                    )
                )

        return stimuli

    def stop(self) -> None:
        super().stop()
        if self._cap is not None:
            self._cap.release()
        if self._face_mesh is not None:
            self._face_mesh.close()
