"""
Stdio adapter — the simplest and most reliable way for a higher intelligence
(or a wrapper script) to talk to ReflexKernel.

Protocol (JSON lines, one message per line):

Higher → Kernel:
    {"cmd": "thought_seed", "emotion": "fear", "intensity": 0.9, "valence": -0.7}
    {"cmd": "reward", "value": 0.8, "reason": "good flinch on real threat"}
    {"cmd": "begin_demo", "name": "social_gentle_wave"}
    {"cmd": "end_demo"}
    {"cmd": "get_state"}
    {"cmd": "inject_stimulus", "stimulus": {"modality": "sim", "data": {"kind": "friendly_wave"}}}

Kernel → Higher (responses + spontaneous events):
    {"type": "state", "tick": 123, "context": {...}, ...}
    {"type": "actions", "actions": [...]}
    {"type": "trace", "trace": {...}}
    {"type": "ack", "ok": true, ...}

When pretty=True (debug), the adapter also prints human lines.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from ..kernel import ReflexKernel


class StdioAdapter:
    def __init__(self, kernel: ReflexKernel, pretty: bool = False) -> None:
        self.kernel = kernel
        self.pretty = pretty
        self._in = sys.stdin
        self._out = sys.stdout

    def send(self, obj: Dict[str, Any]) -> None:
        line = json.dumps(obj, default=str)
        self._out.write(line + "\n")
        self._out.flush()
        if self.pretty:
            print(">>>", line, file=sys.stderr)

    def run(self) -> None:
        """Blocking read-eval-print loop. Call from main demo or dedicated process."""
        self.kernel.start()
        self.send({"type": "hello", "version": "0.1.0", "msg": "ReflexKernel stdio ready"})

        try:
            for line in self._in:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    self.send({"type": "error", "error": "invalid_json"})
                    continue

                # Handle command
                try:
                    resp = self.kernel.command(msg)
                    self.send({"type": "ack", **resp})
                except Exception as e:
                    self.send({"type": "error", "error": str(e)})

                # Also push current state on every command (cheap for teaching loops)
                try:
                    st = self.kernel.get_state()
                    self.send({"type": "state", **st})
                except Exception:
                    pass

        except KeyboardInterrupt:
            pass
        finally:
            self.kernel.stop()
            self.send({"type": "goodbye"})
