"""
Primitive reflex implementations.

These are the fast, involuntary building blocks.

Each primitive is a pure function (or small class) that, given current stimuli + affective context,
returns zero or more ReflexActions + a short explanation string used for traces.

They are intentionally simple and interpretable at first.
State machines and timers live in state_machines.py or inside ReflexCore.
"""

from __future__ import annotations

import time
from typing import List, Tuple

from ..types import AffectiveContext, ReflexAction, ReflexKind, Stimulus


def _has_kind(stimuli: List[Stimulus], *kinds: str) -> bool:
    for s in stimuli:
        k = str((s.data or {}).get("kind", "")).lower()
        if any(needle in k for needle in kinds):
            return True
    return False


def _intensity_from_context(ctx: AffectiveContext, base: float, arousal_boost: float = 0.6) -> float:
    return min(1.4, base + (ctx.arousal - 0.3) * arousal_boost)


# ----------------------------------------------------------------------
# The actual primitives
# ----------------------------------------------------------------------

def flinch(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """
    Classic defensive flinch.
    Triggered by sudden loud, sudden motion, close approach, or high-urgency threat seeds.
    """
    trigger = None
    if _has_kind(stimuli, "sudden_loud", "loud_noise", "sudden_sound"):
        trigger = "sudden_loud"
    elif _has_kind(stimuli, "sudden_motion", "motion_periphery"):
        trigger = "sudden_motion"
    elif _has_kind(stimuli, "close_approach", "threat"):
        trigger = "close_approach"
    elif "sudden_loud" in ctx.active_patterns or "threat" in ctx.active_patterns:
        trigger = "affective_threat"

    if not trigger:
        return [], ""

    intensity = _intensity_from_context(ctx, 0.75, 0.7)
    actions = [
        ReflexAction(
            kind=ReflexKind.FLINCH,
            target="torso_neck",
            intensity=intensity,
            duration_ms=160,
            params={"direction": "backward", "sharp": True},
            source="reflex",
        ),
        ReflexAction(
            kind=ReflexKind.BLINK,
            target="face",
            intensity=min(1.0, intensity + 0.1),
            duration_ms=90,
            params={"both": True},
            source="reflex",
        ),
    ]
    return actions, f"flinch({trigger})"


def blink(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """Protective or expressive blink. Lower threshold than full flinch."""
    if not _has_kind(stimuli, "sudden", "harsh_light", "motion", "face_present"):
        if ctx.urgency > 0.6 or "threat" in ctx.active_patterns:
            pass
        else:
            return [], ""

    intensity = 0.55 + ctx.arousal * 0.3
    return [
        ReflexAction(
            kind=ReflexKind.BLINK,
            target="face",
            intensity=min(1.0, intensity),
            duration_ms=70,
            params={"soft": ctx.valence > 0.1},
            source="reflex",
        )
    ], "blink"


def tension(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """
    General muscle tone increase.
    Triggered by sustained high arousal + negative valence or specific threat patterns.
    """
    if ctx.arousal < 0.55 or (ctx.valence > 0.15 and "threat" not in ctx.active_patterns):
        return [], ""

    intensity = _intensity_from_context(ctx, 0.45, 0.55)
    actions = [
        ReflexAction(
            kind=ReflexKind.TENSION,
            target="shoulders",
            intensity=intensity,
            duration_ms=420,
            params={"hold": True},
            source="reflex",
        ),
        ReflexAction(
            kind=ReflexKind.AUTONOMIC,
            target="physiology",
            intensity=0.35,
            duration_ms=600,
            params={"heart_rate": 0.2 + intensity * 0.3, "breath_rate": 0.15},
            source="reflex",
        ),
    ]
    return actions, "tension(arousal)"


def orient(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """Orienting response toward salient novel stimuli (motion, sound, social)."""
    trigger = None
    direction = "center"
    if _has_kind(stimuli, "motion_periphery", "peripheral_motion"):
        trigger = "peripheral_motion"
        direction = "left" if "left" in str(stimuli) else "right"  # simplistic
    elif _has_kind(stimuli, "friendly_wave", "social_greeting"):
        trigger = "social"
        direction = "center"
    elif _has_kind(stimuli, "sudden_motion"):
        trigger = "sudden_motion"

    if not trigger and ctx.urgency > 0.45:
        trigger = "affective_orient"

    if not trigger:
        return [], ""

    intensity = 0.35 + ctx.arousal * 0.25
    return [
        ReflexAction(
            kind=ReflexKind.ORIENT,
            target="head",
            intensity=intensity,
            duration_ms=280,
            params={"direction": direction, "speed": "medium"},
            source="reflex",
        )
    ], f"orient({trigger})"


def freeze(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """
    Freeze / still response.
    High arousal + negative valence + no clear escape → momentary freeze.
    """
    if ctx.arousal < 0.65 or ctx.valence > -0.15:
        return [], ""
    if not any(p in ctx.active_patterns for p in ("threat", "sudden_loud", "close_approach")):
        return [], ""

    intensity = min(0.9, 0.55 + ctx.arousal * 0.3)
    return [
        ReflexAction(
            kind=ReflexKind.FREEZE,
            target="whole_body",
            intensity=intensity,
            duration_ms=380,
            params={"breath_hold": ctx.arousal > 0.8},
            source="reflex",
        )
    ], "freeze(threat)"


def autonomic(stimuli: List[Stimulus], ctx: AffectiveContext) -> Tuple[List[ReflexAction], str]:
    """
    Background simulated physiology (always lightly active).
    This is the "internal body" that higher cognition can also learn to read.
    """
    base_hr = 0.35 + (ctx.arousal - 0.2) * 0.4
    base_tone = 0.25 + max(0, -ctx.valence) * 0.25

    return [
        ReflexAction(
            kind=ReflexKind.AUTONOMIC,
            target="physiology",
            intensity=0.3,
            duration_ms=1200,
            params={
                "heart_rate": round(base_hr, 3),
                "muscle_tone": round(base_tone, 3),
                "breath_depth": round(0.4 + ctx.arousal * 0.2, 3),
            },
            source="reflex",
        )
    ], "autonomic"


# Mapping used by ReflexCore
PRIMITIVES = {
    "flinch": flinch,
    "blink": blink,
    "tension": tension,
    "orient": orient,
    "freeze": freeze,
    "autonomic": autonomic,
}
