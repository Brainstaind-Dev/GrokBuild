"""Dispatch xAI tool calls onto the body backend + feed controller."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Optional


def compact_json(obj: Any, max_chars: int = 8000) -> str:
    try:
        s = json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        s = str(obj)
    if len(s) > max_chars:
        return s[: max_chars - 20] + "…[truncated]"
    return s


class ToolRegistry:
    """Maps tool names to handlers; enforces caps and inject cooldown."""

    def __init__(
        self,
        backend: Any,
        config: Any,
        feed_controller: Any = None,
    ):
        self.backend = backend
        self.config = config
        self.feed = feed_controller
        self._last_inject_mono = 0.0
        self.max_step_n = int(getattr(config, "max_step_n", 10))
        self.max_chars = int(getattr(config, "max_tool_result_chars", 8000))
        self.inject_cooldown = float(
            getattr(config, "inject_cooldown_sec", 0.4)
        )

        self._handlers: Dict[str, Callable[..., Dict[str, Any]]] = {
            "feel": self._feel,
            "body_snapshot": self._body_snapshot,
            "recall": self._recall,
            "inject_thought": self._inject_thought,
            "send_reward": self._send_reward,
            "inject_stimulus": self._inject_stimulus,
            "step": self._step,
            "begin_demo": self._begin_demo,
            "end_demo": self._end_demo,
            "get_status": self._get_status,
            "pause_feed": self._pause_feed,
            "resume_feed": self._resume_feed,
        }

    def dispatch(self, name: str, arguments: Dict[str, Any] | str | None) -> str:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                arguments = {}
        args = arguments or {}
        if not isinstance(args, dict):
            args = {}

        handler = self._handlers.get(name)
        if handler is None:
            result = {"ok": False, "error": f"unknown tool: {name}"}
        else:
            try:
                result = handler(**args)
            except TypeError as exc:
                result = {"ok": False, "error": f"bad arguments: {exc}"}
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
        return compact_json(result, self.max_chars)

    def _feel(self, force: bool = False, **_: Any) -> Dict[str, Any]:
        if self.feed is not None and self.feed.is_paused and not force:
            return {
                "ok": True,
                "paused": True,
                "note": "Sensation feed is paused. Call resume_feed when ready, "
                "or feel with force=true for a single voluntary sample.",
                "feed": self.feed.status(),
            }
        return self.backend.feel(force=bool(force))

    def _body_snapshot(self, **_: Any) -> Dict[str, Any]:
        return self.backend.body_snapshot()

    def _recall(self, max_age_minutes: int = 20, **_: Any) -> Dict[str, Any]:
        return self.backend.recall(max_age_minutes=int(max_age_minutes))

    def _check_inject_cooldown(self) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        wait = self.inject_cooldown - (now - self._last_inject_mono)
        if wait > 0:
            return {
                "ok": False,
                "error": f"inject cooldown active; wait {wait:.2f}s",
            }
        self._last_inject_mono = now
        return None

    def _inject_thought(
        self,
        emotion: str = "neutral",
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5,
        text: str = "",
        **_: Any,
    ) -> Dict[str, Any]:
        blocked = self._check_inject_cooldown()
        if blocked:
            return blocked
        return self.backend.inject_thought(
            emotion=emotion,
            intensity=float(intensity),
            valence=float(valence),
            arousal=float(arousal),
            text=text or "",
        )

    def _send_reward(
        self,
        value: float,
        reason: str = "",
        window_steps: int = 6,
        **_: Any,
    ) -> Dict[str, Any]:
        return self.backend.send_reward(
            float(value), reason or "", int(window_steps)
        )

    def _inject_stimulus(
        self,
        kind: str = "sudden_sound",
        intensity: float = 0.7,
        modality: str = "sim",
        **_: Any,
    ) -> Dict[str, Any]:
        blocked = self._check_inject_cooldown()
        if blocked:
            return blocked
        return self.backend.inject_stimulus(
            kind=kind, intensity=float(intensity), modality=modality or "sim"
        )

    def _step(self, n: int = 1, **_: Any) -> Dict[str, Any]:
        n = max(1, min(int(n), self.max_step_n))
        return self.backend.step(n=n)

    def _begin_demo(self, name: str = "demo", **_: Any) -> Dict[str, Any]:
        return self.backend.begin_demo(str(name))

    def _end_demo(self, outcome_note: str = "", **_: Any) -> Dict[str, Any]:
        outcome = {"note": outcome_note} if outcome_note else {}
        return self.backend.end_demo(outcome=outcome)

    def _get_status(self, **_: Any) -> Dict[str, Any]:
        st = self.backend.status()
        if self.feed is not None:
            st["feed"] = self.feed.status()
        return {"ok": True, **st}

    def _pause_feed(self, reason: str = "", **_: Any) -> Dict[str, Any]:
        if self.feed is None:
            return {"ok": False, "error": "feed controller not available"}
        if not getattr(self.config, "allow_hi_pause", True):
            return {"ok": False, "error": "pause disabled by config"}
        return self.feed.pause(reason=reason or "")

    def _resume_feed(self, note: str = "", **_: Any) -> Dict[str, Any]:
        if self.feed is None:
            return {"ok": False, "error": "feed controller not available"}
        return self.feed.resume(note=note or "")
