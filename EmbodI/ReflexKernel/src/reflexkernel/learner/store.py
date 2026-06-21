"""
Persistence layer for the Learner.

Design goals:
- Everything is human-readable / git-friendly where possible (JSONL)
- Demonstration recordings are full-fidelity for later replay or cloning
- Learned parameters / policies are versioned snapshots
- Very tolerant of missing files / partial data
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..types import DemonstrationStep, RewardSignal


class LearnerStore:
    def __init__(self, base_path: str | Path) -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)
        self.demos_dir = self.base / "demos"
        self.demos_dir.mkdir(exist_ok=True)
        self.rewards_path = self.base / "rewards.jsonl"
        self.params_path = self.base / "learned_params.json"
        self._params: Dict[str, Any] = self._load_params()

    # --------------------------- Demos ---------------------------

    def save_demonstration(
        self, name: str, steps: List[DemonstrationStep], outcome: Dict[str, Any]
    ) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        ts = int(time.time())
        path = self.demos_dir / f"{safe}_{ts}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for step in steps:
                f.write(json.dumps(step.to_dict(), default=str) + "\n")
            meta = {"name": name, "steps": len(steps), "outcome": outcome, "ts": ts}
            f.write(json.dumps({"__meta__": meta}) + "\n")
        return path

    def list_demonstrations(self) -> List[Dict[str, Any]]:
        out = []
        for p in sorted(self.demos_dir.glob("*.jsonl")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    last = None
                    for line in f:
                        last = line
                    if last and "__meta__" in last:
                        meta = json.loads(last)["__meta__"]
                        meta["path"] = str(p)
                        out.append(meta)
            except Exception:
                continue
        return out

    # --------------------------- Rewards ---------------------------

    def append_reward(self, reward: RewardSignal) -> None:
        with self.rewards_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reward.to_dict(), default=str) + "\n")

    def recent_rewards(self, n: int = 50) -> List[Dict[str, Any]]:
        if not self.rewards_path.exists():
            return []
        lines = self.rewards_path.read_text(encoding="utf-8").strip().splitlines()[-n:]
        return [json.loads(l) for l in lines if l.strip()]

    # --------------------------- Parameters / Policies ---------------------------

    def _load_params(self) -> Dict[str, Any]:
        if self.params_path.exists():
            try:
                return json.loads(self.params_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"version": 1, "behaviors": {}, "reflex_biases": {}}

    def save_params(self) -> None:
        self.params_path.write_text(
            json.dumps(self._params, indent=2, default=str), encoding="utf-8"
        )

    def get_behavior(self, name: str) -> Optional[Dict[str, Any]]:
        return self._params.get("behaviors", {}).get(name)

    def put_behavior(self, name: str, spec: Dict[str, Any]) -> None:
        self._params.setdefault("behaviors", {})[name] = {
            **spec,
            "updated_ts": time.time(),
        }
        self.save_params()

    def get_reflex_bias(self, name: str) -> float:
        return float(self._params.get("reflex_biases", {}).get(name, 0.0))

    def update_reflex_bias(self, name: str, delta: float, lr: float = 0.1) -> float:
        current = self.get_reflex_bias(name)
        new = current + delta * lr
        self._params.setdefault("reflex_biases", {})[name] = round(new, 4)
        self.save_params()
        return new

    def all_biases(self) -> Dict[str, float]:
        return {k: float(v) for k, v in self._params.get("reflex_biases", {}).items()}
