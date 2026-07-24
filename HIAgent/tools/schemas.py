"""xAI client-side tool schemas for the HI agent."""

from __future__ import annotations

from typing import Any, List


def build_xai_tools() -> List[Any]:
    """Return list of xai_sdk.chat.tool definitions."""
    from xai_sdk.chat import tool

    return [
        tool(
            name="feel",
            description=(
                "Sense the body via Sensory Cortex experience package "
                "(mood, salient sensations with rich fields, delta, trend). "
                "Prefer this over body_snapshot. Set force=true to bypass "
                "rate/salience gating."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Bypass cortex gate and force a fresh package",
                        "default": False,
                    }
                },
                "required": [],
            },
        ),
        tool(
            name="body_snapshot",
            description=(
                "Broader kernel state snapshot (tick, context, actions, "
                "sensations). Use sparingly — prefer feel for day-to-day sensing."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
        ),
        tool(
            name="recall",
            description="Recall recent high-arousal embodied experiences from Cortex memory.",
            parameters={
                "type": "object",
                "properties": {
                    "max_age_minutes": {
                        "type": "integer",
                        "description": "How far back to search",
                        "default": 20,
                    }
                },
                "required": [],
            },
        ),
        tool(
            name="inject_thought",
            description=(
                "Inject an affective thought seed into the body "
                "(emotion, intensity, valence, arousal, optional text). "
                "This influences affective state and reflexes."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "emotion": {"type": "string", "description": "e.g. curiosity, calm, startle"},
                    "intensity": {"type": "number", "minimum": 0, "maximum": 1.5},
                    "valence": {"type": "number", "minimum": -1, "maximum": 1},
                    "arousal": {"type": "number", "minimum": 0, "maximum": 1.5},
                    "text": {"type": "string", "description": "Optional natural language seed"},
                },
                "required": ["emotion"],
            },
        ),
        tool(
            name="send_reward",
            description="Send a teaching reward (-1..1) for recent body behavior.",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "minimum": -1, "maximum": 1},
                    "reason": {"type": "string"},
                    "window_steps": {"type": "integer", "default": 6},
                },
                "required": ["value"],
            },
        ),
        tool(
            name="inject_stimulus",
            description=(
                "Inject a simulated external stimulus (e.g. sudden_sound, "
                "friendly_wave, threat_face, gentle_contact, calm)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "intensity": {"type": "number", "minimum": 0, "maximum": 1},
                    "modality": {"type": "string", "default": "sim"},
                },
                "required": ["kind"],
            },
        ),
        tool(
            name="step",
            description="Advance the body kernel by n ticks (capped by agent config).",
            parameters={
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "minimum": 1, "maximum": 50, "default": 1}
                },
                "required": [],
            },
        ),
        tool(
            name="begin_demo",
            description="Begin recording a demonstration for the learner.",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        ),
        tool(
            name="end_demo",
            description="End the current demonstration recording.",
            parameters={
                "type": "object",
                "properties": {
                    "outcome_note": {
                        "type": "string",
                        "description": "Optional outcome note stored with the demo",
                    }
                },
                "required": [],
            },
        ),
        tool(
            name="get_status",
            description="Get body backend + agent feed status (tick, cortex, pause state).",
            parameters={"type": "object", "properties": {}, "required": []},
        ),
        tool(
            name="pause_feed",
            description=(
                "Pause automatic body experience feeds into your context "
                "(interactive prepend and autonomous pulse). Use when you need "
                "quiet time to think. The system will check after ~30s whether "
                "you are ready to resume."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why you want the feed paused",
                    }
                },
                "required": [],
            },
        ),
        tool(
            name="resume_feed",
            description=(
                "Resume automatic body experience feeds after a pause. "
                "Call this when ready to feel again."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "note": {"type": "string", "description": "Optional note"}
                },
                "required": [],
            },
        ),
    ]
