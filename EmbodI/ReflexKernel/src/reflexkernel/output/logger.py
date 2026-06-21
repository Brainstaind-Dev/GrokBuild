"""
Structured event logger.

Writes machine-readable JSON lines for every important kernel event.
These logs are gold for later analysis, imitation learning datasets, or debugging "why did it flinch?"
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from ..config import OutputConfig
from ..types import AffectiveContext, ReflexAction, ReflexTrace


class StructuredLogger:
    def __init__(self, config: OutputConfig, base_logger: Optional[object] = None) -> None:
        self.cfg = config
        self.base = base_logger
        self.enabled = config.log_structured
        self.log_dir = Path(config.log_dir)
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.path = self.log_dir / f"reflexkernel_{int(time.time())}.jsonl"
        else:
            self.path = None

    def _write(self, record: dict) -> None:
        if not self.enabled or not self.path:
            return
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass

    def log_tick(
        self,
        tick: int,
        context: AffectiveContext,
        actions: List[ReflexAction],
        traces: List[ReflexTrace],
    ) -> None:
        rec = {
            "t": "tick",
            "tick": tick,
            "ts": time.time(),
            "context": context.to_dict(),
            "actions": [a.to_dict() for a in actions],
            "traces": [t.to_dict() for t in traces],
        }
        self._write(rec)

    def log_event(self, event_type: str, payload: dict) -> None:
        self._write({"t": event_type, "ts": time.time(), **payload})
