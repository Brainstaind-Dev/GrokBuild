"""JSONL session logging for HI agent turns."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class SessionLog:
    def __init__(self, log_dir: str | Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = self.log_dir / f"session_{stamp}.jsonl"
        self._fp = open(self.path, "a", encoding="utf-8")

    def write(self, event_type: str, **payload: Any) -> None:
        rec: Dict[str, Any] = {
            "t": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self._fp.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
        self._fp.flush()

    def close(self) -> None:
        try:
            self._fp.close()
        except Exception:
            pass

    def __enter__(self) -> "SessionLog":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
