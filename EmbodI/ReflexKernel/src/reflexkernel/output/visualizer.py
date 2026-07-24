"""
Pygame visualizer — stylized 2D representation of Silent Alice (fox girl in tactical armor).

Based on provided reference imagery (front, side, back profiles).
Supports front / side / back views for proper zone visualization.

Features:
- Reactive fox ears (subtle, human-ear scoped movement)
- Ponytail that moves with orientation and tension
- Armored corset top, pleated skirt, arm guards, knee pads, boots
- Glow highlights on body regions when sensations are directed there
- Tension, arousal, valence, reflexes, and sensation-driven expression

Falls back gracefully if pygame not installed (kernel just logs).
"""

from __future__ import annotations

import math
from typing import List, Optional

from ..config import AvatarConfig
from ..types import AffectiveContext, ReflexAction, ReflexTrace, Stimulus
from ..abstraction.schema import Sensation  # for typing richer sensations


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

        # View support for zone mapping (front | side_left | side_right | back)
        self._view = "front"  # default
        self._ear_twitch = 0.0  # for subtle ear movement
        self._last_render_args = None  # (context, actions, traces, stimuli, sensations) for idle re-renders

    def start(self) -> None:
        try:
            import pygame  # type: ignore

            pygame.init()
            # Use vsync where supported for smoother rendering
            try:
                self._screen = pygame.display.set_mode((self.cfg.width, self.cfg.height), vsync=1)
            except:
                self._screen = pygame.display.set_mode((self.cfg.width, self.cfg.height))
            pygame.display.set_caption("ReflexKernel — Embodied Avatar (Silent Alice)")
            self._clock = pygame.time.Clock()
            self._font = pygame.font.SysFont("consolas", 16) or pygame.font.Font(None, 18)
            self._running = True
            if self.logger:
                self.logger.info("Pygame avatar window opened (Silent Alice mode)")
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

    def prepare_render(self, context, actions, traces, stimuli, sensations=None):
        """Thread-safe update of state for later rendering. Does not draw.
        Used when kernel.step is called from non-main thread (e.g. server API)."""
        self._last_render_args = (context, actions, traces, stimuli, sensations or [])

    def force_render_from_cache(self):
        """Draw using the last prepared state. Must be called from the main thread.
        Used in demo after step(), or in server pump."""
        if not self._running or self._screen is None or not getattr(self, "_last_render_args", None):
            return
        try:
            ctx, acts, trs, stis, sens = self._last_render_args
            self.render(ctx, acts, trs, stis, sensations=sens)
        except Exception as e:
            if self.logger:
                self.logger.debug("force_render error: %s", e)

    def pump_events(self) -> bool:
        """Lightweight event pump + idle re-render from cache.
        Keeps the Pygame window responsive (avoids 'not responding') and shows
        smooth animation/glows even between sporadic steps from the server.
        Must run on the main thread.
        """
        if not self._running or self._screen is None:
            return False
        try:
            import pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    return False

            # Periodically re-draw the last known state so ears twitch, glows etc. animate.
            if getattr(self, "_last_render_args", None):
                if not hasattr(self, "_pump_counter"):
                    self._pump_counter = 0
                self._pump_counter += 1
                if self._pump_counter % 4 == 0:  # effective ~25 Hz if pump at 100Hz
                    self.force_render_from_cache()
                    self._pump_counter = 0

            return True
        except Exception as e:
            if self.logger:
                self.logger.debug("Visualizer pump error: %s", e)
            return False

    def set_view(self, view: str) -> None:
        """Set the current view for the avatar.
        Valid: 'front', 'side_left', 'side_right', 'back'
        This helps visualize zone-specific sensations correctly.
        """
        if view in ("front", "side_left", "side_right", "back"):
            self._view = view
        else:
            self._view = "front"

    # ------------------------------------------------------------------
    # Silent Alice drawing (stylized 2D approximation of reference imagery)
    # ------------------------------------------------------------------

    def _draw_silent_alice(self, screen, cx, cy, w, h, tension, face_t, blink, orient, view, context, sensations):
        import pygame

        # Base colors from reference
        armor_color = (210, 205, 195)
        armor_dark = (160, 155, 148)
        skin = (225, 190, 165)
        hair = (175, 110, 75)
        hair_dark = (130, 75, 50)
        ear_inner = (240, 235, 230)
        accent = (120, 115, 105)

        # View-specific positioning
        head_off_x = 0
        body_scale_x = 1.0
        is_side = "side" in view
        is_back = view == "back"

        if "left" in view:
            head_off_x = -18
            body_scale_x = 0.92
        elif "right" in view:
            head_off_x = 18
            body_scale_x = 0.92

        # === Legs / Boots ===
        boot_y = int(h * 0.72)
        boot_w = 22
        boot_h = 78

        # Left leg
        pygame.draw.rect(screen, armor_dark, (cx - 32, boot_y, boot_w, boot_h), border_radius=6)
        # Right leg
        pygame.draw.rect(screen, armor_dark, (cx + 10, boot_y, boot_w, boot_h), border_radius=6)

        # Knee pads (lighter)
        pygame.draw.ellipse(screen, armor_color, (cx - 30, boot_y + 18, 18, 22))
        pygame.draw.ellipse(screen, armor_color, (cx + 12, boot_y + 18, 18, 22))

        # === Skirt (pleated) ===
        skirt_y = int(h * 0.56)
        skirt_h = 42
        pygame.draw.polygon(
            screen, armor_color,
            [
                (cx - 38, skirt_y),
                (cx + 38, skirt_y),
                (cx + 48, skirt_y + skirt_h),
                (cx - 48, skirt_y + skirt_h),
            ]
        )
        # Pleat lines
        for i in range(-2, 3):
            px = cx + i * 14
            pygame.draw.line(screen, accent, (px, skirt_y + 4), (px + i * 3, skirt_y + skirt_h - 4), 2)

        # === Torso / Corset Armor ===
        torso_y = int(h * 0.42)
        torso_h = 78
        # Main corset
        pygame.draw.rect(
            screen, armor_color,
            (cx - 32, torso_y, 64, torso_h),
            border_radius=8
        )
        # Center seam / zipper detail
        pygame.draw.line(screen, armor_dark, (cx, torso_y + 8), (cx, torso_y + torso_h - 8), 3)
        # Chest armor plates
        pygame.draw.ellipse(screen, armor_dark, (cx - 26, torso_y + 12, 22, 28))
        pygame.draw.ellipse(screen, armor_dark, (cx + 4, torso_y + 12, 22, 28))

        # Shoulder armor
        pygame.draw.rect(screen, armor_dark, (cx - 44, torso_y - 4, 18, 22), border_radius=4)
        pygame.draw.rect(screen, armor_dark, (cx + 26, torso_y - 4, 18, 22), border_radius=4)

        # === Arms with guards ===
        arm_y = torso_y + 8
        # Left arm
        pygame.draw.line(screen, skin, (cx - 32, arm_y + 10), (cx - 52, arm_y + 52), 9)
        pygame.draw.line(screen, skin, (cx + 32, arm_y + 10), (cx + 52, arm_y + 52), 9)
        # Arm guards
        pygame.draw.rect(screen, armor_dark, (cx - 56, arm_y + 22, 12, 28), border_radius=3)
        pygame.draw.rect(screen, armor_dark, (cx + 44, arm_y + 22, 12, 28), border_radius=3)

        # === Head ===
        head_x = cx + head_off_x
        head_r = 46
        pygame.draw.circle(screen, skin, (head_x, cy), head_r)

        # Fox ears (stylized, subtle movement)
        ear_tilt = math.sin(self._ear_twitch) * 4
        # Left ear
        pygame.draw.polygon(screen, armor_color, [
            (head_x - 18, cy - 32),
            (head_x - 36, cy - 68 - ear_tilt),
            (head_x - 2, cy - 38),
        ])
        pygame.draw.polygon(screen, ear_inner, [
            (head_x - 16, cy - 36),
            (head_x - 28, cy - 58 - ear_tilt * 0.6),
            (head_x - 6, cy - 40),
        ])
        # Right ear
        pygame.draw.polygon(screen, armor_color, [
            (head_x + 18, cy - 32),
            (head_x + 36, cy - 68 + ear_tilt),
            (head_x + 2, cy - 38),
        ])
        pygame.draw.polygon(screen, ear_inner, [
            (head_x + 16, cy - 36),
            (head_x + 28, cy - 58 + ear_tilt * 0.6),
            (head_x + 6, cy - 40),
        ])

        # Headphones
        pygame.draw.arc(screen, armor_dark, (head_x - 38, cy - 32, 76, 64), 0.8, 2.3, 6)
        pygame.draw.circle(screen, armor_color, (head_x - 28, cy - 4), 9)
        pygame.draw.circle(screen, armor_color, (head_x + 28, cy - 4), 9)

        # Ponytail (more visible on side/back)
        pony_base_x = head_x + (18 if is_side else 0)
        pony_y = cy + 8
        if is_side or is_back:
            sway = math.sin(context.arousal * 3 + tension * 2) * (12 if is_side else 6)
            pygame.draw.line(screen, hair, (pony_base_x, pony_y), (pony_base_x + sway * 1.6, pony_y + 72), 11)
            pygame.draw.line(screen, hair_dark, (pony_base_x + 3, pony_y + 10), (pony_base_x + sway * 1.4 + 4, pony_y + 68), 5)

        # === Face ===
        eye_y = cy - 6
        eye_open = 1.0 - blink * 0.9

        # Eyes (larger, more anime-inspired to match reference)
        for sign in (-1, 1):
            ex = head_x + sign * 14
            # Eye white
            pygame.draw.ellipse(screen, (250, 248, 245), (ex - 9, eye_y - 7, 18, 14 * eye_open))
            # Iris
            pygame.draw.circle(screen, (60, 70, 95), (ex, eye_y), int(4.5 * eye_open))
            # Pupil
            pygame.draw.circle(screen, (25, 25, 30), (ex + sign * 1, eye_y), int(2 * eye_open))

        # Eyebrows
        brow_y = eye_y - 14
        brow_t = face_t * 3.5
        pygame.draw.line(screen, (80, 55, 45), (head_x - 18, brow_y - brow_t), (head_x - 4, brow_y + brow_t * 0.5), 2)
        pygame.draw.line(screen, (80, 55, 45), (head_x + 4, brow_y + brow_t * 0.5), (head_x + 18, brow_y - brow_t), 2)

        # Mouth
        mouth_y = cy + 20
        if context.valence > 0.2:
            pygame.draw.arc(screen, (70, 45, 40), (head_x - 8, mouth_y - 3, 16, 8), 0.1, 2.9, 2)
        else:
            pygame.draw.line(screen, (70, 45, 40), (head_x - 7, mouth_y), (head_x + 7, mouth_y + int(face_t * 2)), 2)

        # === Sensation Glows (zone highlighting) ===
        if sensations:
            self._draw_sensation_glows(screen, cx, cy, view, sensations, tension)

    def _draw_sensation_glows(self, screen, cx, cy, view, sensations, tension):
        import pygame

        for s in sensations or []:
            zone = (getattr(s, 'zone', '') or '').lower()
            rich = getattr(s, 'arousal_modulated_richness', 0.5)
            intensity = min(1.0, rich * 1.3 + tension * 0.2)

            # Map zone to body region (approximate for Silent Alice silhouette)
            if any(k in zone for k in ['thigh', 'leg', 'inner']):
                # Upper legs / skirt area
                glow_y = cy + 58
                glow_w, glow_h = 38, 26
                glow_x = cx - 18 if 'left' in view or view == 'front' else cx + 8
            elif any(k in zone for k in ['chest', 'breast', 'torso', 'stomach']):
                glow_y = cy + 18
                glow_w, glow_h = 32, 24
                glow_x = cx
            elif 'contact' in zone or 'pressure' in zone:
                glow_y = cy + 36
                glow_w, glow_h = 48, 32
                glow_x = cx
            else:
                # Default torso glow
                glow_y = cy + 28
                glow_w, glow_h = 36, 28
                glow_x = cx

            # Soft glow - reduced layers for performance
            if intensity > 0.1:
                glow_color = (255, 160, 200)
                for i in range(3, 0, -1):
                    alpha_factor = intensity * (0.25 * i)
                    r = max(40, int(glow_color[0] * alpha_factor))
                    g = max(30, int(glow_color[1] * alpha_factor))
                    b = max(60, int(glow_color[2] * alpha_factor))
                    pygame.draw.ellipse(
                        screen,
                        (r, g, b),
                        (glow_x - glow_w // 2 - i * 2, glow_y - glow_h // 2 - i * 1,
                         glow_w + i * 4, glow_h + i * 2),
                        0
                    )

    def render(
        self,
        context: AffectiveContext,
        actions: List[ReflexAction],
        traces: List[ReflexTrace],
        stimuli: List[Stimulus],
        sensations: List[Sensation] | None = None,
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

            # === State calculations ===
            tension = min(1.0, max(0.0, context.arousal * 0.7 + (0.5 - context.valence) * 0.3))
            face_t = min(1.0, tension * 0.85 + 0.1)
            blink = 0.0
            orient = "center"

            # Apply last actions
            for a in actions:
                k = a.kind.value if hasattr(a.kind, "value") else str(a.kind)
                if k == "blink":
                    blink = max(blink, a.intensity)
                if k == "orient":
                    orient = a.params.get("direction", orient)
                if k in ("flinch", "tension", "freeze"):
                    tension = min(1.0, tension + a.intensity * 0.4)
                    face_t = min(1.0, face_t + a.intensity * 0.5)

            # Update ear twitch (subtle, human-scoped reactivity)
            self._ear_twitch = (self._ear_twitch + (context.arousal * 0.08 + tension * 0.04)) % (math.pi * 2)

            # Determine view (allow manual override via set_view)
            view = self._view
            if view == "front" and orient in ("left", "right"):
                view = f"side_{orient}"

            cx, cy = w // 2, int(h * 0.34)  # center reference

            # === Draw Silent Alice based on view ===
            self._draw_silent_alice(screen, cx, cy, w, h, tension, face_t, blink, orient, view, context, sensations)

            # Overlays (kept from original + enhanced sensation display)
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

                # Richer sensations from the Saddle / interface (when available)
                # Glows are drawn on body regions; this text gives details.
                if sensations:
                    y = h - 140
                    screen.blit(self._font.render("sensations (from saddle):", True, (120, 180, 200)), (16, y))
                    for i, s in enumerate(sensations[:2]):
                        desc = s.description[:70] + ("..." if len(s.description) > 70 else "")
                        zone = getattr(s, 'zone', '?')
                        rich = getattr(s, 'arousal_modulated_richness', 0.0)
                        color = (180, 220, 255) if rich > 0.3 else (150, 180, 200)
                        screen.blit(self._font.render(f"• {desc}  [zone={zone} rich={rich:.2f}]", True, color), (16, y + 16 + i * 15))

                # Legend
                legend = "keys: s=loud  m=motion  f=face  c=close  t=touch  q=calm  |  r=reward+  p=reward-  d=demo  e=end"
                screen.blit(self._font.render(legend, True, (90, 90, 100)), (16, h - 18))

            pygame.display.flip()
            if self._clock:
                self._clock.tick(self.cfg.fps)

        except Exception as e:
            if self.logger:
                self.logger.debug("Visualizer render error (non-fatal): %s", e)
