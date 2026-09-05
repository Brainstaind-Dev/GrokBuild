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
from ..abstraction import VirtualSensorSimulator, get_coherent_sensations, get_capped_coherent_sensations, AbstractionOutput
from ..abstraction.bridge import abstraction_to_stimuli
from ..abstraction.schema import DetailLevel


class PythonAPI:
    """Thin, friendly wrapper around the kernel for direct use by Python agents."""

    def __init__(
        self,
        kernel: ReflexKernel,
        virtual_sim: Optional[VirtualSensorSimulator] = None,
    ) -> None:
        self.kernel = kernel
        self._virtual_sim = virtual_sim

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

    def get_last_sensations(self) -> list:
        """Return cached coherent sensations from the live kernel path (no new sim)."""
        return self.kernel.get_last_sensations()

    def set_last_sensations(self, sensations: list, max_count: int = 3) -> None:
        self.kernel.set_last_sensations(sensations, max_count=max_count)

    def inject_stimulus(self, modality: str, data: Dict[str, Any], **kwargs) -> None:
        s = Stimulus(modality=modality, data=data, **kwargs)
        self.kernel.step(extra_stimuli=[s])

    def command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        return self.kernel.command(cmd)

    def ensure_virtual_sim(self) -> VirtualSensorSimulator:
        """One-Body: one VirtualSensorSimulator per API / live process."""
        if self._virtual_sim is None:
            self._virtual_sim = VirtualSensorSimulator()
        return self._virtual_sim

    def get_coherent_sensations(self, detail_level: str = "normal", steps: int = 1) -> list:
        """Return richer coherent sensations (default NORMAL detail to avoid overload for HI).

        Prominent dedicated method for Saddle/HI path. Returns capped list (MAX_SENSATIONS_FOR_HI) with full rich fields (description, arousal_modulated_richness, etc).
        Drives the *shared* virtual sim (never a new one per poll).
        """
        dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
        sim = self.ensure_virtual_sim()
        last_out = None
        for _ in range(max(1, steps)):
            raw = sim.read_all()
            out: AbstractionOutput = sim.process(raw, detail_level=dl)
            last_out = out
            # Prefer bridge → real Stimulus objects (dicts also accepted by kernel.step).
            self.kernel.step(extra_stimuli=abstraction_to_stimuli(out))
        if last_out is not None:
            self.kernel.set_last_abstraction(last_out)
            if hasattr(self.kernel, "set_last_sensations"):
                self.kernel.set_last_sensations(list(last_out.sensations or []), max_count=3)
        capped = get_capped_coherent_sensations(last_out) if last_out is not None else []
        return [s.to_dict() for s in capped]

    def get_body_state(self, detail_level: str = "normal") -> dict:
        """Return enhanced body state summary (default NORMAL; primary lightweight view to avoid overload).

        Uses the shared sim + last drive when present (One-Body). Does not mint a twin.
        """
        dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
        sim = self.ensure_virtual_sim()
        raw = sim.read_all()
        out: AbstractionOutput = sim.process(raw, detail_level=dl)
        self.kernel.set_last_abstraction(out)
        summary = out.state_summary.to_dict() if out.state_summary else {}
        summary["detail_level"] = dl.value
        return summary
