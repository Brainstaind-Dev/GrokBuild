"""
Pygame visualizer — simple but expressive avatar.

Shows:
- Head + face (eyes, mouth, brow) whose tension / expression reflects virtual body state
- Shoulders / torso posture (tension, flinch, freeze)
- Head orientation
- Overlay of recent stimuli kinds and active reflex names (very helpful for teaching/debug)

Falls back gracefully if pygame not installed (kernel just logs).
"""

from __future__ import annotations

import math
from typing import List, Optional

from ..config import AvatarConfig
from ..types import AffectiveContext, ReflexAction, ReflexTrace, Stimulus


class PygameVisualizer:
    def __init__(self, config: AvatarConfig, logger: Optional[object] = None) -> None:
        self.cfg = config
        self.logger = logger
        self._screen = None
        self._clock = None
        self._font = None
        self._running = False
        self._last_body: dict = {}
        self._recent_stim_text: List[str] = []
        self._recent_reflex_text: List[str] = []

    def start(self) -> None:
        try:
            import pygame  # type: ignore

            pygame.init()
            self._screen = pygame.display.set_mode((self.cfg.width, self.cfg.height))
            pygame.display.set_caption("ReflexKernel — Embodied Avatar")
            self._clock = pygame.time.Clock()
            self._font = pygame.font.SysFont("consolas", 16) or pygame.font.Font(None, 18)
            self._running = True
            if self.logger:
                self.logger.info("Pygame avatar window opened")
        except Exception as e:
            if self.logger:
                self.logger.warning("Could not start pygame visualizer: %s", e)
            self._running = False

    def stop(self) -> None:
        try:
            import pygame  # type: ignore

            pygame.quit()
        except Exception:
            pass
        self._running = False

    def render(
        self,
        context: AffectiveContext,
        actions: List[ReflexAction],
        traces: List[ReflexTrace],
        stimuli: List[Stimulus],
    ) -> None:
        if not self._running or self._screen is None:
            return

        try:
            import pygame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    return

            # Update recent overlays
            for s in stimuli:
                k = str((s.data or {}).get("kind", s.modality))
                txt = f"{k}"
                if txt not in self._recent_stim_text:
                    self._recent_stim_text.append(txt)
            self._recent_stim_text = self._recent_stim_text[-6:]

            for t in traces:
                if t.name not in self._recent_reflex_text:
                    self._recent_reflex_text.append(t.name)
            self._recent_reflex_text = self._recent_reflex_text[-5:]

            w, h = self.cfg.width, self.cfg.height
            screen = self._screen
            screen.fill((18, 18, 24))

            # Simple body state (we read from last known or synthesize from context + actions)
            tension = min(1.0, max(0.0, context.arousal * 0.7 + (0.5 - context.valence) * 0.3))
            face_t = min(1.0, tension * 0.85 + 0.1)
            blink = 0.0
            orient = "center"

            # Apply last actions for snappier viz
            for a in actions:
                k = a.kind.value if hasattr(a.kind, "value") else str(a.kind)
                if k == "blink":
                    blink = max(blink, a.intensity)
                if k == "orient":
                    orient = a.params.get("direction", orient)
                if k in ("flinch", "tension", "freeze"):
                    tension = min(1.0, tension + a.intensity * 0.4)
                    face_t = min(1.0, face_t + a.intensity * 0.5)

            # Draw torso / shoulders
            shoulder_y = int(h * 0.58)
            shoulder_t = tension * 18
            pygame.draw.rect(
                screen,
                (70, 70, 85),
                (w // 2 - 70, shoulder_y, 140, 110),
                border_radius=12,
            )
            # Shoulders raised with tension
            pygame.draw.line(
                screen,
                (95, 95, 110),
                (w // 2 - 55, shoulder_y + 10),
                (w // 2 - 55 - shoulder_t * 0.6, shoulder_y - 18),
                9,
            )
            pygame.draw.line(
                screen,
                (95, 95, 110),
                (w // 2 + 55, shoulder_y + 10),
                (w // 2 + 55 + shoulder_t * 0.6, shoulder_y - 18),
                9,
            )

            # Head
            cx, cy = w // 2, int(h * 0.34)
            head_r = 58
            head_off_x = -12 if orient == "left" else (12 if orient == "right" else 0)
            pygame.draw.circle(screen, (125, 115, 108), (cx + head_off_x, cy), head_r)

            # Eyes
            eye_y = cy - 8
            eye_open = 1.0 - blink * 0.92
            for ex in (-22, 22):
                ex += head_off_x
                # eye white
                pygame.draw.ellipse(screen, (235, 235, 240), (cx + ex - 11, eye_y - 9, 22, 18 * eye_open))
                # iris
                iris_off = head_off_x * 0.25
                pygame.draw.circle(
                    screen, (45, 55, 75), (cx + ex + int(iris_off), eye_y), int(5.5 * eye_open)
                )
                # lid tension
                if face_t > 0.3:
                    lid = int(3 + face_t * 5)
                    pygame.draw.line(
                        screen,
                        (70, 55, 50),
                        (cx + ex - 11, eye_y - 9 + lid),
                        (cx + ex + 11, eye_y - 9 + lid),
                        2,
                    )

            # Eyebrows (tension / negative valence raises inner brow)
            brow_y = eye_y - 18
            brow_t = face_t * 4
            pygame.draw.line(
                screen,
                (55, 45, 40),
                (cx - 28 + head_off_x, brow_y - brow_t),
                (cx - 8 + head_off_x, brow_y + brow_t * 0.6),
                3,
            )
            pygame.draw.line(
                screen,
                (55, 45, 40),
                (cx + 8 + head_off_x, brow_y + brow_t * 0.6),
                (cx + 28 + head_off_x, brow_y - brow_t),
                3,
            )

            # Mouth (valence + tension)
            mouth_y = cy + 26
            mouth_w = 18 + int(tension * 6)
            mouth_h = 3 + int(max(0, -context.valence) * 7)
            if context.valence > 0.15:
                # slight smile
                pygame.draw.arc(
                    screen,
                    (55, 35, 35),
                    (cx - mouth_w, mouth_y - 4, mouth_w * 2, 14),
                    0.2,
                    2.9,
                    2,
                )
            else:
                pygame.draw.line(
                    screen,
                    (55, 35, 35),
                    (cx - mouth_w, mouth_y),
                    (cx + mouth_w, mouth_y + mouth_h),
                    3,
                )

            # Neck line (flinch / tension)
            neck_t = tension * 6
            pygame.draw.line(
                screen,
                (85, 75, 70),
                (cx + head_off_x, cy + head_r - 6),
                (cx, shoulder_y + 4),
                max(3, int(5 + neck_t)),
            )

            # Overlays
            if self._font:
                # Affective state
                info = (
                    f"v={context.valence:+.2f}  a={context.arousal:.2f}  u={context.urgency:.2f}  "
                    f"pat={','.join(context.active_patterns[:3]) or '-'}"
                )
                txt = self._font.render(info, True, (170, 170, 180))
                screen.blit(txt, (16, 12))

                # Body vitals
                body = f"tone={tension:.2f}  face={face_t:.2f}  orient={orient}"
                txt2 = self._font.render(body, True, (150, 150, 160))
                screen.blit(txt2, (16, 30))

                # Recent stimuli
                if self.cfg.show_stimuli_overlay and self._recent_stim_text:
                    y = h - 92
                    screen.blit(self._font.render("stimuli:", True, (120, 140, 120)), (16, y))
                    for i, s in enumerate(self._recent_stim_text):
                        screen.blit(self._font.render(f"• {s}", True, (130, 160, 130)), (16, y + 16 + i * 15))

                # Recent reflexes
                if self.cfg.show_reflex_traces and self._recent_reflex_text:
                    y = h - 92
                    rx = w - 220
                    screen.blit(self._font.render("reflexes:", True, (180, 130, 110)), (rx, y))
                    for i, r in enumerate(self._recent_reflex_text):
                        screen.blit(self._font.render(f"• {r}", True, (200, 140, 120)), (rx, y + 16 + i * 15))

                # Legend
                legend = "keys: s=loud  m=motion  f=face  c=close  t=touch  q=calm  |  r=reward+  p=reward-  d=demo  e=end"
                screen.blit(self._font.render(legend, True, (90, 90, 100)), (16, h - 18))

            pygame.display.flip()
            if self._clock:
                self._clock.tick(self.cfg.fps)

        except Exception as e:
            if self.logger:
                self.logger.debug("Visualizer render error (non-fatal): %s", e)
