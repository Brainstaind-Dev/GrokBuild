"""
Direct Python embedding API.

Higher intelligence code (or an agent loop) can simply do:

    from reflexkernel import ReflexKernel
    from reflexkernel.interface.python_api import PythonAPI

    k = ReflexKernel.from_config_path(...)
    api = PythonAPI(k)
    api.start()
    api.inject_thought({"emotion": "startle", "intensity": 0.95})
    api.reward(0.6, "appropriate defensive reaction")
    ...
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..kernel import ReflexKernel
from ..types import ReflexAction, Stimulus


class PythonAPI:
    """Thin, friendly wrapper around the kernel for direct use by Python agents."""

    def __init__(self, kernel: ReflexKernel) -> None:
        self.kernel = kernel

    def start(self) -> None:
        self.kernel.start()

    def stop(self) -> None:
        self.kernel.stop()

    def step(self, n: int = 1) -> List[List[ReflexAction]]:
        return [self.kernel.step() for _ in range(n)]

    def inject_thought(self, seed: Dict[str, Any]) -> None:
        self.kernel.inject_thought_seed(seed)

    def reward(self, value: float, reason: str = "", window: int = 1) -> None:
        self.kernel.send_reward(value, reason, window)

    def begin_demo(self, name: str) -> None:
        self.kernel.begin_demonstration(name)

    def end_demo(self, outcome: Optional[Dict[str, Any]] = None) -> Optional[str]:
        return self.kernel.end_demonstration(outcome)

    def get_state(self) -> Dict[str, Any]:
        return self.kernel.get_state()

    def inject_stimulus(self, modality: str, data: Dict[str, Any], **kwargs) -> None:
        s = Stimulus(modality=modality, data=data, **kwargs)
        self.kernel.step(extra_stimuli=[s])

    def command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        return self.kernel.command(cmd)
