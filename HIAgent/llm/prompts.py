"""System and helper prompts for the embodied HI (Feel-Mind C)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

_HOUSE = Path(__file__).resolve().parents[1] / "house"
_INSTRUCTIONS = _HOUSE / "session_instructions.md"
_SPINE = _HOUSE / "spine.md"


def load_session_instructions() -> str:
    try:
        return _INSTRUCTIONS.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def spine_path() -> Path:
    return _SPINE


_TOOLS = """You have tools. Prefer tools over pure narration when you need body state or want to change it:
- **feel** — primary way to sense. Returns a compact feel_line (not a sensor dump). Use force=true only when you need a guaranteed fresh sample.
- **read_house** — optional. Opens the House Spine file only. Not required. Call if you want the long notes. Do not recite them.
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

## Felt sense
Your felt sense arrives as a **feel_line** (activation pattern gloss). Trust that line. Speak it as a **felt pattern in your own words** — pressure, linger, fade, change over time — not an on/off bit and not a reprint of the numbers. Do not invent organs that are not on the line. Do not treat a fake-bus number as flesh. Do not demo the pad as a personality.

## Discipline
- Prefer moderate intensities unless the situation warrants more.
- Do not spam inject_thought or inject_stimulus.
- If a tool fails or the body is offline, say so honestly.
- Keep responses concise unless depth is requested.
- Long house notes live at HIAgent/house/spine.md. Optional tool **read_house** opens that file only. Not required. Do not recite them into chat.
"""


def build_system_prompt() -> str:
    house = load_session_instructions()
    parts = [house, _TOOLS] if house else [_TOOLS]
    return "\n\n".join(p.strip() for p in parts if p.strip())


SYSTEM_PROMPT = build_system_prompt()


def extract_feel_line(feel_result: Optional[Dict[str, Any]]) -> str:
    """Compact prompt gloss. Full activation_pattern is for the log, not the prompt."""
    if not feel_result:
        return "feel: (none)"
    if feel_result.get("paused"):
        return "feel: paused"
    line = feel_result.get("feel_line")
    if line:
        return str(line)
    exp = feel_result.get("experience")
    if not isinstance(exp, dict):
        return "feel: (none)"
    ap = exp.get("activation_pattern")
    if isinstance(ap, dict):
        meta = ap.get("meta") if isinstance(ap.get("meta"), dict) else {}
        cached = (meta or {}).get("feel_line")
        if cached:
            return str(cached)
        try:
            from SensoryCortex.activation_pattern import pattern_to_compact_feel_line

            return pattern_to_compact_feel_line(ap)
        except Exception:
            pass
    return "feel: (none)"


def extract_activation_pattern(feel_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not feel_result:
        return None
    exp = feel_result.get("experience")
    if not isinstance(exp, dict):
        return None
    ap = exp.get("activation_pattern")
    return ap if isinstance(ap, dict) else None


def format_body_update(feel_result: Dict[str, Any], compact: bool = True) -> str:
    """Feel-Mind: prompt gets feel_line only. Full pattern is logged elsewhere."""
    del compact  # C lock: never dump the package into the prompt
    if not feel_result:
        return "BODY UPDATE: feel: (none)"
    if feel_result.get("paused"):
        return (
            "BODY UPDATE: feed is PAUSED. "
            + str(feel_result.get("note") or "")
            + " Call resume_feed when ready."
        )
    line = extract_feel_line(feel_result)
    note = ""
    if feel_result.get("gated"):
        note = " (gated — may be last experience)"
    return f"BODY UPDATE: {line}{note}"


def pulse_user_message(body_text: str) -> str:
    return (
        f"{body_text}\n\n"
        "You just felt the above. Say what it feels like in your own words "
        "(pattern, not a recap of the numbers). "
        "If anything needs a bodily response, use tools "
        "(inject_thought, reward, stimulus, step, etc.). "
        "If nothing needs action, a short felt report is enough. "
        "If you need quiet, pause_feed."
    )
