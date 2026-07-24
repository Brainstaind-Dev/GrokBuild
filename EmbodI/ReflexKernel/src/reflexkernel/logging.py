"""
Structured logging for ReflexKernel.

Uses rich for beautiful console output when available and falls back gracefully.
All important events (stimuli, fusions, reflex fires, rewards, learned updates)
should go through the helpers here so they are consistently formatted.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.traceback import install as rich_traceback_install

    RICH_AVAILABLE = True
    rich_traceback_install(show_locals=False)
except ImportError:
    RICH_AVAILABLE = False

from .types import AffectiveContext, ReflexAction, ReflexTrace, RewardSignal, Stimulus


_console: Optional[Console] = None


def get_logger(name: str = "reflexkernel", level: str = "INFO") -> logging.Logger:
    """Get (or configure) the root ReflexKernel logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured
        logger.setLevel(level)
        return logger

    logger.setLevel(level)

    if RICH_AVAILABLE:
        handler = RichHandler(rich_tracebacks=True, markup=True, show_path=False)
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console()
    return _console


def log_stimulus(logger: logging.Logger, stim: Stimulus | dict, level: int = logging.DEBUG) -> None:
    if isinstance(stim, dict):
        mod = stim.get("modality", "unknown")
        src = stim.get("source", "unknown")
        conf = stim.get("confidence", 1.0)
        data = stim.get("data", {})
    else:
        mod = stim.modality.value if hasattr(stim.modality, "value") else stim.modality
        src = stim.source
        conf = stim.confidence
        data = stim.data
    logger.log(level, f"[stim] {mod:8s} src={src} conf={conf:.2f} data={data}")


def log_fusion(
    logger: logging.Logger,
    context: AffectiveContext,
    num_stimuli: int,
    num_patterns: int,
    level: int = logging.DEBUG,
) -> None:
    logger.log(
        level,
        f"[fusion] v={context.valence:+.2f} a={context.arousal:.2f} dom={context.dominance:+.2f} "
        f"urg={context.urgency:.2f} | stimuli={num_stimuli} patterns={num_patterns}",
    )


def log_reflex_fire(logger: logging.Logger, trace: ReflexTrace, level: int = logging.INFO) -> None:
    acts = ", ".join(f"{a.kind}:{a.target}@{a.intensity:.1f}" for a in trace.actions)
    mod = f" mod={trace.modulated_by}" if trace.modulated_by else ""
    logger.log(
        level,
        f"[reflex] {trace.name} ← {trace.trigger} → [{acts}] {trace.latency_ms:.1f}ms{mod}",
    )


def log_reward(logger: logging.Logger, reward: RewardSignal, level: int = logging.INFO) -> None:
    logger.log(
        level,
        f"[reward] {reward.value:+.3f} (window={reward.window_steps}) reason='{reward.reason}'",
    )


def log_learner_update(
    logger: logging.Logger,
    kind: str,
    behavior: str,
    detail: str = "",
    level: int = logging.INFO,
) -> None:
    logger.log(level, f"[learner] {kind} '{behavior}' {detail}")


def log_kernel_tick(
    logger: logging.Logger,
    tick: int,
    actions: int,
    context: Optional[AffectiveContext] = None,
    level: int = logging.DEBUG,
) -> None:
    if context:
        logger.log(
            level,
            f"[tick {tick:05d}] actions={actions} | v={context.valence:+.2f} a={context.arousal:.2f}",
        )
    else:
        logger.log(level, f"[tick {tick:05d}] actions={actions}")
