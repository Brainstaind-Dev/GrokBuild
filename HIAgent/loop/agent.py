"""HigherIntelligenceAgent — main orchestration."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from ..body import create_backend
from ..config import HIAgentConfig, load_config
from ..llm.prompts import SYSTEM_PROMPT, format_body_update, pulse_user_message
from ..llm.xai_chat import XAIChatSession
from ..tools.registry import ToolRegistry
from ..tools.schemas import build_xai_tools
from .feed import FeedController
from .session import SessionLog


class HigherIntelligenceAgent:
    """
    Grok-via-xAI riding ReflexKernel through Sensory Cortex tools.

    Supports interactive turns and autonomous pulse, with HI-controlled
    pause/resume of the sensation feed.
    """

    def __init__(self, config: Optional[HIAgentConfig] = None):
        # Load ~/.config/embodi/env before config defaults read env vars
        try:
            from HIAgent.env_bootstrap import load_embodi_env

            load_embodi_env()
        except Exception:
            pass
        self.config = config or load_config()
        self.backend = create_backend(self.config)
        self.feed = FeedController(
            pause_poll_sec=float(self.config.pause_poll_sec)
        )
        self.registry = ToolRegistry(
            self.backend, self.config, feed_controller=self.feed
        )
        self.session: Optional[SessionLog] = None
        self._llm: Optional[XAIChatSession] = None
        self._started = False
        self._prev_arousal: Optional[float] = None

    def start(self, *, open_session: bool = True) -> None:
        self.backend.start()
        if open_session:
            self.session = SessionLog(self.config.session_log_dir)
            self.session.write(
                "session_start",
                backend=self.config.backend,
                model=self.config.model,
            )
        tools = build_xai_tools()
        self._llm = XAIChatSession(
            model=self.config.model,
            tools=tools,
            tool_dispatch=self.registry.dispatch,
            max_tool_rounds=int(self.config.max_tool_rounds),
            system_prompt=SYSTEM_PROMPT,
        )
        self._started = True

    def stop(self) -> None:
        if self.session:
            self.session.write("session_end")
            self.session.close()
            self.session = None
        try:
            self.backend.stop()
        except Exception:
            pass
        self._started = False

    def _log(self, event: str, **payload: Any) -> None:
        if self.session:
            self.session.write(event, **payload)

    def _on_llm_event(self, event: str, data: Dict[str, Any]) -> None:
        self._log(event, **data)
        if self.config.verbose:
            if event == "tool_call":
                print(f"  → tool {data.get('name')} {data.get('args')}")
            elif event == "tool_result":
                print(f"  ← {data.get('name')}: {data.get('result_preview', '')[:120]}")
            elif event == "assistant" and data.get("content"):
                print(f"  Grok: {data['content'][:300]}")

    def _maybe_auto_feel(self) -> Optional[str]:
        if self.feed.is_paused:
            return None
        if not self.config.prepend_feel_on_user_turn:
            return None
        result = self.backend.feel(force=False)
        self._log("feel", result_ok=result.get("ok"), gated=result.get("gated"))
        self._track_arousal(result)
        return format_body_update(
            result, compact=self.config.compact_experience
        )

    def _track_arousal(self, feel_result: Dict[str, Any]) -> None:
        exp = feel_result.get("experience") or {}
        core = exp.get("affective_core") if isinstance(exp, dict) else None
        if isinstance(core, dict) and core.get("arousal") is not None:
            self._prev_arousal = float(core["arousal"])

    def turn(self, user_text: str) -> str:
        """One interactive (or synthetic) user turn with optional body prepend."""
        if not self._started or self._llm is None:
            raise RuntimeError("Agent not started")

        # Pause-resume poll may inject a system check as part of this turn
        resume_prompt = self.feed.tick()
        parts = []
        if resume_prompt:
            parts.append(resume_prompt)
            self._log("feed_resume_prompt", text=resume_prompt)

        body = self._maybe_auto_feel()
        if body:
            parts.append(body)

        parts.append(user_text.strip())
        combined = "\n\n".join(parts)

        self._log("turn_start", mode="interactive", user=user_text[:2000])
        content, rounds = self._llm.run_turn(
            combined, on_event=self._on_llm_event
        )
        self._log("turn_end", tool_rounds=rounds, assistant=content[:4000])
        return content

    def should_wake(self, feel_result: Dict[str, Any]) -> bool:
        if self.config.always_pulse:
            return True
        if feel_result.get("paused"):
            return False
        exp = feel_result.get("experience") or {}
        if not isinstance(exp, dict):
            return bool(feel_result.get("ok"))

        reflexes = [str(r).lower() for r in (exp.get("reflex_activity") or [])]
        non_auto = [r for r in reflexes if r and r != "autonomic"]
        if self.config.wake_on_reflex and non_auto:
            return True

        core = exp.get("affective_core") or {}
        arousal = core.get("arousal")
        if arousal is not None and self._prev_arousal is not None:
            if abs(float(arousal) - self._prev_arousal) >= self.config.wake_on_arousal_delta:
                return True

        delta = str(exp.get("delta_from_last") or "").lower()
        if any(
            k in delta
            for k in ("new contact", "arousal rising", "reflex:", "auditory")
        ):
            return True

        # First pulse with any experience
        if self._prev_arousal is None and core.get("arousal") is not None:
            return True
        return False

    def pulse_once(self) -> Optional[str]:
        """
        One autonomous cycle. Returns assistant text if a turn ran, else None.
        Respects feed pause; may still run a resume-check turn.
        """
        if not self._started or self._llm is None:
            raise RuntimeError("Agent not started")

        resume_prompt = self.feed.tick()
        if resume_prompt:
            self._log("feed_resume_prompt", text=resume_prompt)
            content, rounds = self._llm.run_turn(
                resume_prompt, on_event=self._on_llm_event
            )
            self._log("turn_end", mode="resume_check", tool_rounds=rounds)
            return content

        if self.feed.is_paused:
            self._log("pulse_skip", reason="feed_paused")
            return None

        feel_result = self.backend.feel(force=False)
        self._log("pulse_feel", ok=feel_result.get("ok"), gated=feel_result.get("gated"))
        wake = self.should_wake(feel_result)
        self._track_arousal(feel_result)

        if not wake:
            self._log("pulse_skip", reason="no_wake")
            return None

        body_text = format_body_update(
            feel_result, compact=self.config.compact_experience
        )
        user_msg = pulse_user_message(body_text)
        self._log("turn_start", mode="pulse")
        content, rounds = self._llm.run_turn(
            user_msg, on_event=self._on_llm_event
        )
        self._log("turn_end", mode="pulse", tool_rounds=rounds)
        return content

    def pulse_loop(
        self,
        *,
        interval: Optional[float] = None,
        max_cycles: Optional[int] = None,
        on_response: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Block until KeyboardInterrupt or max_cycles."""
        interval = float(interval or self.config.pulse_interval_sec)
        cycles = 0
        print(
            f"[HIAgent] pulse loop interval={interval}s "
            f"(Ctrl+C to stop; pause_feed available to HI)"
        )
        try:
            while True:
                if max_cycles is not None and cycles >= max_cycles:
                    break
                cycles += 1
                try:
                    text = self.pulse_once()
                    if text and on_response:
                        on_response(text)
                    elif text:
                        print(f"\n[pulse {cycles}] {text}\n")
                except Exception as exc:
                    self._log("pulse_error", error=str(exc))
                    print(f"[pulse error] {exc}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[HIAgent] pulse stopped.")
