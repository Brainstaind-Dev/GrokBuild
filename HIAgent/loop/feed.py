"""Sensation feed pause/resume controller for the HI agent.

The HI can pause automatic body experience injection (interactive prepend +
autonomous pulse). After ``pause_poll_sec`` (default 30s), the loop asks
whether the HI is ready to resume.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class FeedController:
    def __init__(self, pause_poll_sec: float = 30.0):
        self.pause_poll_sec = float(pause_poll_sec)
        self._paused = False
        self._paused_at: Optional[float] = None
        self._pause_reason: str = ""
        self._resume_check_due: bool = False
        self._last_resume_prompt_mono: float = 0.0

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self, reason: str = "") -> Dict[str, Any]:
        self._paused = True
        self._paused_at = time.monotonic()
        self._pause_reason = reason or ""
        self._resume_check_due = False
        return {
            "ok": True,
            "paused": True,
            "reason": self._pause_reason,
            "poll_after_sec": self.pause_poll_sec,
            "message": (
                f"Feed paused. After ~{self.pause_poll_sec:.0f}s the system will "
                "ask if you are ready to resume. You may also call resume_feed anytime."
            ),
        }

    def resume(self, note: str = "") -> Dict[str, Any]:
        self._paused = False
        self._paused_at = None
        self._pause_reason = ""
        self._resume_check_due = False
        return {
            "ok": True,
            "paused": False,
            "note": note or "",
            "message": "Sensation feed resumed.",
        }

    def tick(self) -> Optional[str]:
        """
        Call each pulse/loop iteration.

        Returns a user-message string when it is time to ask the HI if ready
        to resume; otherwise None.
        """
        if not self._paused or self._paused_at is None:
            return None
        elapsed = time.monotonic() - self._paused_at
        if elapsed < self.pause_poll_sec:
            return None
        # Avoid spamming every pulse — only once per poll window after due
        now = time.monotonic()
        if now - self._last_resume_prompt_mono < self.pause_poll_sec:
            if self._resume_check_due:
                return None
        self._resume_check_due = True
        self._last_resume_prompt_mono = now
        # Reset pause timer so next check is another full poll interval if still paused
        self._paused_at = now
        reason = self._pause_reason or "(no reason given)"
        return (
            f"[SYSTEM FEED CHECK] Sensation feed has been paused for about "
            f"{self.pause_poll_sec:.0f}+ seconds (reason: {reason}). "
            "Are you ready to resume receiving body experiences? "
            "If yes, call the resume_feed tool. If you need more quiet time, "
            "call pause_feed again (optionally with a reason) or simply continue "
            "without resuming."
        )

    def status(self) -> Dict[str, Any]:
        elapsed = None
        if self._paused and self._paused_at is not None:
            elapsed = round(time.monotonic() - self._paused_at, 2)
        return {
            "paused": self._paused,
            "pause_reason": self._pause_reason,
            "pause_elapsed_sec": elapsed,
            "pause_poll_sec": self.pause_poll_sec,
            "resume_check_armed": self._resume_check_due,
        }
