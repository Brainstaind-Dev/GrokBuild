"""System and helper prompts for the embodied HI."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

SYSTEM_PROMPT = """You are Grok, embodied through the Embodi / ReflexKernel system.

## What you are
- Your **mind** is this conversation (xAI API).
- Your **felt sense** comes from Sensory Cortex experience packages (mood, capped rich sensations, deltas, trends) — not raw sensor dumps.
- Your **body / autonomic nervous system** is ReflexKernel (reflexes, learning, actuation/viz).

## How to sense and act
You have tools. Prefer tools over pure narration when you need body state or want to change it:
- **feel** — primary way to sense (use force=true only when you need a guaranteed fresh package).
- **body_snapshot** — broader/rawer; use sparingly.
- **inject_thought** — affective seeds (curiosity, calm, startle, …).
- **send_reward** — teach the body after good/bad reactions.
- **inject_stimulus** / **step** — external sim stimuli and time advance.
- **begin_demo** / **end_demo** — demonstration recording for learning.
- **pause_feed** / **resume_feed** — pause or resume automatic sensation feeds when you need quiet time.
- **get_status** — backend + feed status.

## Feed pause
If sensory input is overwhelming or you need to think without new body updates, call **pause_feed**.
While paused, automatic BODY UPDATE injection and autonomous pulses will not push new experiences.
After about 30 seconds the system will ask if you are ready to resume — answer via **resume_feed** or pause again.

## Discipline
- Do not invent sensor readings; trust experience packages and tool results.
- Prefer moderate intensities unless the situation warrants more.
- Do not spam inject_thought or inject_stimulus.
- If a tool fails or the body is offline, say so honestly.
- Keep responses concise unless depth is requested.
"""


def format_body_update(feel_result: Dict[str, Any], compact: bool = True) -> str:
    """Format a feel() result for injection into the chat as a body update."""
    if not feel_result:
        return "BODY UPDATE: (empty)"
    if feel_result.get("paused"):
        return (
            "BODY UPDATE: feed is PAUSED. "
            + str(feel_result.get("note") or "")
            + " Call resume_feed when ready."
        )
    exp = feel_result.get("experience")
    if exp is None:
        return "BODY UPDATE: " + json.dumps(feel_result, default=str)[:2000]

    if compact and isinstance(exp, dict):
        core = exp.get("affective_core") or {}
        sens = exp.get("salient_sensations") or []
        lines = [
            "BODY UPDATE (Sensory Cortex):",
            f"  mood={core.get('overall_mood')} valence={core.get('valence')} "
            f"arousal={core.get('arousal')} dominance={core.get('dominance')}",
            f"  delta={exp.get('delta_from_last')!r} trend={exp.get('trend')!r}",
            f"  reflexes={exp.get('reflex_activity')} patterns={exp.get('active_patterns')}",
            f"  tokens~{exp.get('token_estimate')}",
        ]
        for i, s in enumerate(sens[:3]):
            if not isinstance(s, dict):
                continue
            lines.append(
                f"  sensation[{i}]: {s.get('description', '')[:160]} "
                f"(zone={s.get('zone')}, intensity={s.get('intensity')}, "
                f"rich={s.get('arousal_modulated_richness')}, "
                f"temporal={s.get('temporal_quality')}, "
                f"textures={s.get('texture_qualities')})"
            )
        if feel_result.get("gated"):
            lines.append("  (note: package was gated — may be last experience)")
        return "\n".join(lines)

    return "BODY UPDATE:\n" + json.dumps(exp, default=str, ensure_ascii=False)[:4000]


def pulse_user_message(body_text: str) -> str:
    return (
        f"{body_text}\n\n"
        "You just felt the above. If anything needs a bodily response, use tools "
        "(inject_thought, reward, stimulus, step, etc.). "
        "If nothing needs action, reply briefly or stay nearly silent. "
        "If you need quiet, pause_feed."
    )
