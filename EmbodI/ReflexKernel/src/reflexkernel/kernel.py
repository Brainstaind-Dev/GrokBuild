"""
ReflexKernel — main orchestrator.

Responsibilities:
- Owns the tick loop (synchronous, deterministic for v1)
- Coordinates Perception → Bridge → ReflexCore → Learner → Output
- Provides the public surface used by Interface adapters and higher intelligence:
    inject_thought_seed, reward, begin_demo / end_demo, step, get_state, etc.
- Gracefully degrades when optional components are missing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import ReflexKernelConfig, load_config
from .logging import (
    get_logger,
    log_fusion,
    log_kernel_tick,
    log_reflex_fire,
    log_reward,
    log_stimulus,
)
from .types import (
    AffectiveContext,
    DemonstrationStep,
    Modality,
    ReflexAction,
    ReflexTrace,
    RewardSignal,
    Stimulus,
    StimulusBatch,
)


@dataclass
class KernelState:
    """Lightweight observable snapshot for interfaces."""
    tick: int = 0
    last_context: Optional[Dict[str, Any]] = None
    last_actions: List[Dict[str, Any]] = field(default_factory=list)
    last_traces: List[Dict[str, Any]] = field(default_factory=list)
    demo_active: bool = False
    demo_name: Optional[str] = None


class ReflexKernel:
    """
    The central ReflexKernel instance.

    Usage (programmatic):
        kernel = ReflexKernel.from_config_path("configs/sim_only.yaml")
        kernel.start()
        for _ in range(120):
            actions = kernel.step()
            ...
        kernel.stop()
    """

    def __init__(self, config: Optional[ReflexKernelConfig] = None) -> None:
        self.cfg = config or load_config()
        self.logger = get_logger("reflexkernel", level=self.cfg.kernel.log_level)

        self.state = KernelState()
        self._running = False
        self._last_tick_time = 0.0
        self._last_sensations: List[Any] = []  # set by interface when driving abstraction from Saddle inputs

        # Layers (populated in _init_layers)
        self.perception: Any = None
        self.bridge: Any = None
        self.reflex_core: Any = None
        self.learner: Any = None
        self.output: Any = None

        # Demo recording
        self._current_demo: List[DemonstrationStep] = []
        self._demo_name: Optional[str] = None

        # Lightweight event system for remote interfaces (WebSocket, etc.)
        # Callbacks receive (event_type: str, payload: dict)
        self._event_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

        self._init_layers()
        self.logger.info("ReflexKernel initialized (tick_rate=%d Hz)", self.cfg.kernel.tick_rate_hz)

    @classmethod
    def from_config_path(cls, path: str | Path, overrides: Optional[Dict[str, Any]] = None) -> "ReflexKernel":
        cfg = load_config(path, overrides=overrides)
        return cls(config=cfg)

    def _init_layers(self) -> None:
        """Wire all layers. Import lazily so missing optionals do not break core."""
        # --- Perception ---
        from .perception.base import SensorRegistry
        from .perception.simulation import SimulationSensor

        registry = SensorRegistry()
        sim_sensor = SimulationSensor(self.cfg.perception.simulation)
        registry.register("simulation", sim_sensor)

        # Vision / Audio will be registered only if enabled and importable (see perception/__init__ later)
        try:
            if "vision" in self.cfg.perception.enabled_sensors:
                from .perception.vision import VisionSensor  # type: ignore

                registry.register("vision", VisionSensor(self.cfg.perception.vision))
                self.logger.info("Vision sensor registered")
        except Exception as e:
            self.logger.warning("Vision sensor unavailable: %s", e)

        try:
            if "audio" in self.cfg.perception.enabled_sensors:
                from .perception.audio import AudioSensor  # type: ignore

                registry.register("audio", AudioSensor(self.cfg.perception.audio))
                self.logger.info("Audio sensor registered")
        except Exception as e:
            self.logger.warning("Audio sensor unavailable: %s", e)

        self.perception = registry

        # --- Bridge ---
        from .bridge.thought_bridge import ThoughtBridge

        self.bridge = ThoughtBridge(self.cfg.bridge, logger=self.logger)

        # --- Reflex Core ---
        from .reflex.core import ReflexCore

        self.reflex_core = ReflexCore(self.cfg.reflex, logger=self.logger)

        # --- Learner ---
        from .learner.base import Learner

        self.learner = Learner(self.cfg.learner, logger=self.logger)

        # --- Output / Actuation ---
        from .output.actuation import ActuationHub
        from .output.logger import StructuredLogger

        self.output = {
            "actuation": ActuationHub(self.cfg.output),
            "structured_log": StructuredLogger(self.cfg.output, self.logger),
        }

        # Visualization (optional)
        if self.cfg.output.visualization == "pygame":
            try:
                from .output.visualizer import PygameVisualizer  # type: ignore

                self.output["visualizer"] = PygameVisualizer(self.cfg.output.avatar, self.logger)
                self.logger.info("Pygame visualizer enabled")
            except Exception as e:
                self.logger.warning("Pygame visualizer unavailable (%s). Falling back to text logs.", e)
                self.output["visualizer"] = None
        elif self.cfg.output.visualization == "text":
            self.output["visualizer"] = None  # text is handled via logger

        # Give learner access to reflex registry for modulation (future)
        self.learner.attach_reflex_core(self.reflex_core)

    # ------------------------------------------------------------------
    # Public control surface (used by higher intelligence & interfaces)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start background elements (sensors that need threads, viz, etc.)."""
        self._running = True
        self.perception.start_all()
        if viz := self.output.get("visualizer"):
            viz.start()
        self.logger.info("ReflexKernel started")

    def stop(self) -> None:
        self._running = False
        self.perception.stop_all()
        if viz := self.output.get("visualizer"):
            viz.stop()
        self.logger.info("ReflexKernel stopped")

    def step(self, extra_stimuli: Optional[StimulusBatch] = None) -> List[ReflexAction]:
        """
        Single tick of the kernel.

        Returns the batch of ReflexActions that were commanded this tick.
        """
        tick_start = time.perf_counter()
        self.state.tick += 1

        # 1. Collect real + injected stimuli
        stimuli: StimulusBatch = self.perception.collect_all()

        # Normalize extra_stimuli.
        # The abstraction layer's to_stimuli() returns List[dict], while
        # perception and internal paths return List[Stimulus].
        # We accept both for flexibility when driving from virtual abstraction or Saddle.
        if extra_stimuli:
            for item in extra_stimuli:
                if isinstance(item, dict):
                    stimuli.append(Stimulus.from_dict(item))
                elif isinstance(item, Stimulus):
                    stimuli.append(item)
                else:
                    try:
                        stimuli.append(Stimulus.from_dict(item))
                    except Exception:
                        pass

        for s in stimuli:
            log_stimulus(self.logger, s)

        # 2. Bridge: thought seeds (injected earlier) + stimuli → AffectiveContext
        context = self.bridge.fuse(stimuli)
        log_fusion(self.logger, context, len(stimuli), len(context.active_patterns))

        # 3. Reflex core (fast path)
        actions, traces = self.reflex_core.react(stimuli, context)
        for t in traces:
            log_reflex_fire(self.logger, t)
            self._emit("reflex_trace", t.to_dict())

        # 4. Learner observes everything (for future imitation / RL)
        self.learner.observe(stimuli, context, actions, traces)

        # If a demo is active, record the step
        if self._current_demo is not None and self.state.demo_active:
            step = DemonstrationStep(
                stimuli=stimuli,
                context=context,
                teacher_action=actions[0] if actions else None,
                outcome={},
            )
            self._current_demo.append(step)

        # 5. Apply to actuators + visualization
        self.output["actuation"].apply(actions)
        if viz := self.output.get("visualizer"):
            # Prepare data for the visualizer (thread-safe update of cache).
            # Actual drawing happens on the main thread (either inside this step for demo,
            # or via the pump_events loop when server is in bg thread).
            sens = getattr(self, "_last_sensations", None) or []
            if hasattr(viz, "prepare_render"):
                viz.prepare_render(context, actions, traces, stimuli, sens)
            else:
                # Fallback for older visualizers
                viz.render(context, actions, traces, stimuli, sensations=sens)

        self.output["structured_log"].log_tick(self.state.tick, context, actions, traces)

        # Update observable state
        self.state.last_context = context.to_dict()
        self.state.last_actions = [a.to_dict() for a in actions]
        self.state.last_traces = [t.to_dict() for t in traces]

        self._emit("state", self.get_state())

        log_kernel_tick(self.logger, self.state.tick, len(actions), context)

        # Simple rate limiting
        target_dt = 1.0 / max(1, self.cfg.kernel.tick_rate_hz)
        elapsed = time.perf_counter() - tick_start
        if elapsed < target_dt:
            time.sleep(target_dt - elapsed)

        return actions

    # -----------------------------
    # Higher-intelligence API
    # -----------------------------

    def inject_thought_seed(self, seed: Dict[str, Any]) -> None:
        """
        Inject an affective "thought" from the higher intelligence.

        Accepted keys (best effort):
            emotion, intensity, valence, arousal, dominance, patterns, text, ...
        """
        self.bridge.inject_seed(seed)
        self.logger.debug("Thought seed injected: %s", seed)

    def send_reward(self, value: float, reason: str = "", window_steps: int = 1) -> None:
        reward = RewardSignal(value=value, reason=reason, window_steps=window_steps)
        log_reward(self.logger, reward)
        self.learner.receive_reward(reward)
        self._emit("reward", reward.to_dict())

    def begin_demonstration(self, name: str) -> None:
        if self.state.demo_active:
            self.end_demonstration()
        self.state.demo_active = True
        self.state.demo_name = name
        self._demo_name = name
        self._current_demo = []
        self.logger.info("Demonstration recording started: '%s'", name)
        self._emit("learner_update", {"event": "demo_begin", "name": name})

    def end_demonstration(self, outcome: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not self.state.demo_active:
            return None
        name = self._demo_name or "unnamed"
        steps = self._current_demo
        self.learner.ingest_demonstration(name, steps, outcome or {})
        self.state.demo_active = False
        self.state.demo_name = None
        self._current_demo = []
        self._demo_name = None
        self.logger.info("Demonstration '%s' ended (%d steps). Learner ingested.", name, len(steps))
        self._emit("learner_update", {"event": "demo_end", "name": name, "steps": len(steps)})
        return name

    def get_state(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot suitable for interfaces."""
        return {
            "tick": self.state.tick,
            "running": self._running,
            "context": self.state.last_context,
            "last_actions": self.state.last_actions,
            "last_traces": self.state.last_traces,
            "demo_active": self.state.demo_active,
            "demo_name": self.state.demo_name,
        }

    def get_last_sensations(self) -> List[Any]:
        """Public accessor for the most recent coherent sensations (HI/Saddle path).

        Populated by the Saddle drive loop, demo abstraction path, or
        ``set_last_sensations``. Prefer this over reading ``_last_sensations``.
        """
        return list(getattr(self, "_last_sensations", None) or [])

    def set_last_sensations(self, sensations: List[Any], max_count: int = 3) -> None:
        """Cache coherent sensations for viz / Sensory Cortex / HI consumers."""
        try:
            max_n = max(0, int(max_count))
        except (TypeError, ValueError):
            max_n = 3
        self._last_sensations = list(sensations or [])[:max_n]

    # ------------------------------------------------------------------
    # Lightweight event emission for remote interfaces (WebSocket etc.)
    # These are intentionally private-ish and non-breaking.
    # ------------------------------------------------------------------

    def add_event_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a callback for internal events (used by the server layer)."""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event to all registered callbacks. Never raises."""
        for cb in list(self._event_callbacks):
            try:
                cb(event_type, dict(payload))  # copy to be safe
            except Exception:
                # Events must never break the kernel
                pass

    def command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic command entrypoint (used by stdio / WS adapters).

        Supported commands (extensible):
            {"cmd": "reward", "value": 0.7, "reason": "..."}
            {"cmd": "thought_seed", ...}
            {"cmd": "begin_demo", "name": "foo"}
            {"cmd": "end_demo"}
            {"cmd": "get_state"}
            {"cmd": "inject_stimulus", "stimulus": {...}}
        """
        c = cmd.get("cmd") or cmd.get("type")
        if c in ("thought_seed", "inject_seed"):
            self.inject_thought_seed(cmd)
            return {"ok": True}
        if c == "reward":
            self.send_reward(
                float(cmd.get("value", 0.0)),
                cmd.get("reason", ""),
                int(cmd.get("window_steps", 1)),
            )
            return {"ok": True}
        if c == "begin_demo":
            name = cmd.get("name") or cmd.get("behavior") or "demo"
            self.begin_demonstration(str(name))
            return {"ok": True, "demo": name}
        if c == "end_demo":
            name = self.end_demonstration(cmd.get("outcome"))
            return {"ok": True, "ended": name}
        if c == "get_state":
            return self.get_state()
        if c == "inject_stimulus":
            stim = Stimulus.from_dict(cmd.get("stimulus", {}))
            self.step(extra_stimuli=[stim])
            return {"ok": True}
        if c == "stop":
            self.stop()
            return {"ok": True}
        return {"ok": False, "error": f"unknown command: {c}"}

    # Convenience for demos / tests
    def run_for_ticks(self, n: int, inject: Optional[List[Dict[str, Any]]] = None) -> List[List[ReflexAction]]:
        """Run N ticks, optionally injecting thought seeds each tick."""
        results: List[List[ReflexAction]] = []
        inject = inject or []
        for i in range(n):
            seed = inject[i] if i < len(inject) else None
            if seed:
                self.inject_thought_seed(seed)
            actions = self.step()
            results.append(actions)
        return results
