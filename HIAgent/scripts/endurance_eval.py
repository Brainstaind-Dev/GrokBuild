#!/usr/bin/env python
"""
10-minute Embodi + xAI API endurance evaluation.

Injects varied virtual stimuli on a schedule, asks Grok (xAI) to feel/respond,
logs full session JSONL + a human-readable transcript for post analysis.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RK_SRC = _REPO / "EmbodI" / "ReflexKernel" / "src"
for p in (str(_REPO), str(_RK_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Scenario schedule: (elapsed_sec_min, elapsed_sec_max bucket label, action)
# Actions are executed when wall time reaches each step once.

DURATION_SEC = 600  # 10 minutes
MODEL_DEFAULT = "grok-4-1-fast-non-reasoning"

STIMULUS_PLAN = [
    # (at_second, kind, intensity, human_prompt_for_grok)
    (
        15,
        None,
        None,
        "Baseline. Call feel (force true). Describe what you sense in 2-3 sentences. "
        "Comment on clarity, richness, and whether anything feels missing for embodiment.",
    ),
    (
        45,
        "sudden_sound",
        0.92,
        "A sudden loud sound was just injected into the body. Call feel (force true). "
        "Describe the change vs baseline. Did startle/arousal land? What would improve it?",
    ),
    (
        90,
        "gentle_contact",
        0.55,
        "Gentle contact was injected. Feel again (force true). Describe zone, texture, "
        "temporal quality if present. Is contact distinguishable from ambient?",
    ),
    (
        130,
        None,
        None,
        "No new stimulus. Feel (force false is ok). Report delta/trend if any. "
        "Does the body feel continuous over time or static between events?",
    ),
    (
        170,
        "threat_face",
        0.85,
        "Threat-oriented stimulus injected. Feel (force true). Describe affective and "
        "reflexive change. Critique usefulness of the package for deciding an action.",
    ),
    (
        210,
        "friendly_wave",
        0.45,
        "Friendly/social stimulus injected. Feel (force true). Contrast with the threat moment. "
        "Are valence and social calm readable enough?",
    ),
    (
        250,
        "impact",
        0.88,
        "Impact-like stimulus path (if kind unsupported, still feel). Feel force true. "
        "Describe intensity and any flinch/tension. What structured fields helped most?",
    ),
    (
        300,
        None,
        None,
        "Mid-session reflection (5 min mark). Summarize what embodiment has felt like so far. "
        "List 3 concrete improvements for the sensation/cortex stack. Use tools if helpful.",
    ),
    (
        340,
        "relaxing_sound",
        0.35,
        "Calming stimulus injected. Feel force true. Does recovery/calm read clearly after prior high arousal?",
    ),
    (
        380,
        "calm",
        0.25,
        "Additional calm. Feel. Comment on whether reward/teaching would make sense here; "
        "optionally send a small positive reward if the recovery felt appropriate.",
    ),
    (
        420,
        "sudden_sound",
        0.7,
        "Second startle at moderate intensity. Feel force true. Compare to first startle. "
        "Is intensity scaling meaningful?",
    ),
    (
        470,
        None,
        None,
        "Explore freely for one turn: inject_thought with curiosity or calm, step a few ticks, "
        "feel again. Report whether thought seeds change felt state as expected.",
    ),
    (
        520,
        "gentle_contact",
        0.75,
        "Stronger gentle contact. Feel force true. Critique zone specificity and richness fields "
        "(arousal_modulated_richness, textures, temporal_quality).",
    ),
    (
        560,
        None,
        None,
        "Final debrief before session end. Give structured feedback: "
        "(A) strengths of current virtual embodiment, "
        "(B) weaknesses/pain points, "
        "(C) top 5 prioritized improvements, "
        "(D) readiness for an HI to 'live' in this body for longer sessions. "
        "Be specific and technical where useful.",
    ),
]


def main() -> int:
    from HIAgent.config import load_config
    from HIAgent.loop.agent import HigherIntelligenceAgent

    out_dir = _REPO / "data" / "hi_eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    transcript_path = out_dir / f"eval_transcript_{stamp}.md"
    events_path = out_dir / f"eval_events_{stamp}.jsonl"

    cfg = load_config(
        backend="embedded",
        enable_viz=False,
        verbose=True,
        prepend_feel_on_user_turn=True,
        model=MODEL_DEFAULT,
        max_tool_rounds=8,
        inject_cooldown_sec=0.2,
        session_log_dir=str(out_dir / "sessions"),
    )

    agent = HigherIntelligenceAgent(cfg)
    events: list[dict] = []
    t0 = time.monotonic()

    def log_event(event: str, **payload):
        rec = {
            "t": event,
            "ts": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": round(time.monotonic() - t0, 2),
            **payload,
        }
        events.append(rec)
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
        preview = {k: v for k, v in payload.items() if k != "reply"}
        if "reply" in payload:
            preview["reply"] = str(payload["reply"])[:200]
        print(f"[{rec['elapsed_sec']:7.1f}s] {event}: {preview}", flush=True)

    print("=== Embodi xAI endurance eval ===", flush=True)
    print(f"duration={DURATION_SEC}s model={cfg.model}", flush=True)
    print(f"transcript={transcript_path}", flush=True)
    print(f"events={events_path}", flush=True)

    if not __import__("os").environ.get("XAI_API_KEY"):
        print("FAIL: XAI_API_KEY not set in this process", flush=True)
        return 1

    try:
        agent.start()
    except Exception as exc:
        print("START FAILED:", exc, flush=True)
        traceback.print_exc()
        return 1

    log_event("session_start", backend=agent.backend.status())
    t0 = time.monotonic()  # reset clock after body warm-up
    plan_idx = 0
    transcript_lines = [
        f"# Embodi xAI Endurance Eval — {stamp}",
        "",
        f"- Model: `{cfg.model}`",
        f"- Backend: embedded (viz off)",
        f"- Duration target: {DURATION_SEC}s",
        "",
        "---",
        "",
    ]

    try:
        while True:
            elapsed = time.monotonic() - t0
            if elapsed >= DURATION_SEC:
                break

            # Fire due plan steps
            while plan_idx < len(STIMULUS_PLAN) and elapsed >= STIMULUS_PLAN[plan_idx][0]:
                at, kind, intensity, prompt = STIMULUS_PLAN[plan_idx]
                plan_idx += 1
                step_elapsed = time.monotonic() - t0

                if kind:
                    try:
                        result = agent.backend.inject_stimulus(
                            kind=kind, intensity=float(intensity or 0.7)
                        )
                        log_event(
                            "stimulus_injected",
                            kind=kind,
                            intensity=intensity,
                            result=result,
                        )
                        agent.backend.step(n=3)
                        try:
                            sim = getattr(agent.backend, "_sim", None)
                            if sim is not None and hasattr(sim, "trigger_scenario"):
                                scenario_map = {
                                    "impact": "impact",
                                    "gentle_contact": "gentle_contact",
                                    "sudden_sound": "loud_noise",
                                    "sudden_movement": "sudden_movement",
                                }
                                sc = scenario_map.get(kind)
                                if sc:
                                    sim.trigger_scenario(sc, duration=1.5)
                                    log_event("scenario_triggered", scenario=sc)
                                    agent.backend.step(n=2)
                        except Exception as se:
                            log_event("scenario_skip", error=str(se))
                    except Exception as e:
                        log_event("stimulus_error", kind=kind, error=str(e))

                turn_prompt = (
                    f"[EVAL turn @ {step_elapsed:.0f}s / plan@{at}s]\n{prompt}"
                )
                log_event("turn_request", prompt=turn_prompt[:500], plan_at=at)
                try:
                    reply = agent.turn(turn_prompt)
                    log_event("turn_reply", reply=reply, plan_at=at)
                    transcript_lines.extend(
                        [
                            f"## t≈{step_elapsed:.0f}s — plan step {plan_idx} (scheduled {at}s)",
                            "",
                            f"**Stimulus:** `{kind}` intensity={intensity}",
                            "",
                            "### Prompt to Grok",
                            "",
                            prompt,
                            "",
                            "### Grok (xAI) response",
                            "",
                            reply or "_(empty)_",
                            "",
                            "---",
                            "",
                        ]
                    )
                    transcript_path.write_text(
                        "\n".join(transcript_lines), encoding="utf-8"
                    )
                except Exception as e:
                    err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                    log_event("turn_error", error=str(e))
                    transcript_lines.extend(
                        [
                            f"## t≈{step_elapsed:.0f}s — ERROR",
                            "",
                            f"```\n{err}\n```",
                            "",
                            "---",
                            "",
                        ]
                    )
                    transcript_path.write_text(
                        "\n".join(transcript_lines), encoding="utf-8"
                    )

                elapsed = time.monotonic() - t0

            # Keep body ticking between LLM turns
            try:
                agent.backend.step(n=1)
            except Exception:
                pass
            time.sleep(1.5)

            if plan_idx >= len(STIMULUS_PLAN):
                try:
                    agent.backend.feel(force=False)
                    agent.backend.step(n=1)
                except Exception:
                    pass
                time.sleep(2.0)

        if plan_idx < len(STIMULUS_PLAN):
            log_event(
                "warning",
                msg="not all plan steps executed before timeout",
                plan_idx=plan_idx,
                remaining=len(STIMULUS_PLAN) - plan_idx,
            )

        log_event("session_complete", wall_sec=round(time.monotonic() - t0, 1))
    except KeyboardInterrupt:
        log_event("interrupted")
    except Exception as e:
        log_event("fatal", error=str(e), tb=traceback.format_exc())
    finally:
        try:
            agent.stop()
        except Exception:
            pass

    wall = time.monotonic() - t0
    transcript_lines.extend(
        [
            "",
            f"*Session wall time: {wall:.1f}s*",
            f"*Events file: `{events_path.name}`*",
            f"*Agent session dir: `{cfg.session_log_dir}`*",
            f"*Plan steps completed: {plan_idx}/{len(STIMULUS_PLAN)}*",
        ]
    )
    transcript_path.write_text("\n".join(transcript_lines), encoding="utf-8")
    # marker for analysis
    (out_dir / f"eval_latest.txt").write_text(
        f"{transcript_path}\n{events_path}\n", encoding="utf-8"
    )
    print("DONE", transcript_path, flush=True)
    print("elapsed", round(wall, 1), "s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
