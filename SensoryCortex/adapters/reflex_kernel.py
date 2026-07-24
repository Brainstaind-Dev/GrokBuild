"""
ReflexKernel adapter — low-latency coherent-input builders.

Design rules:
- Prefer **already-produced** sensations on the live kernel (push path).
- Prefer a **shared** VirtualSensorSimulator on the host (Saddle pattern).
- Do **not** spawn a new VirtualSensorSimulator on every status poll when
  a live pipeline already ran (avoids duplicate work + desync from viz).
- Cortex never re-fuses sensors; this adapter only packages RK outputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence


def _sensations_to_dicts(sensations: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in sensations or []:
        if hasattr(s, "to_dict"):
            out.append(s.to_dict())
        elif hasattr(s, "model_dump"):
            out.append(s.model_dump())
        elif isinstance(s, dict):
            out.append(s)
    return out


def _reflex_kinds(state: Dict[str, Any]) -> List[str]:
    kinds: List[str] = []
    for a in state.get("last_actions") or []:
        if isinstance(a, dict):
            k = a.get("kind") or a.get("type") or a.get("name")
            if k:
                kinds.append(str(k))
        else:
            kinds.append(str(a))
    # unique, preserve order
    seen = set()
    ordered: List[str] = []
    for k in kinds:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def from_kernel(
    kernel: Any,
    *,
    sensations: Optional[Sequence[Any]] = None,
    body_state: Optional[Dict[str, Any]] = None,
    detail_level: str = "normal",
    prev_arousal: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build coherent-input from a live ReflexKernel instance.

    Sensation priority:
    1. Explicit ``sensations`` argument (host already has them)
    2. ``kernel._last_sensations`` / ``get_last_sensations()`` if present
    3. Empty list (affective/reflex still useful)
    """
    state = kernel.get_state() if hasattr(kernel, "get_state") else {}
    if not isinstance(state, dict):
        state = {}

    if sensations is None:
        # Prefer public API; fall back to private cache for older kernels
        if hasattr(kernel, "get_last_sensations"):
            try:
                sensations = kernel.get_last_sensations()
            except Exception:
                sensations = None
        if not sensations:
            sensations = getattr(kernel, "_last_sensations", None) or []

    sens_dicts = _sensations_to_dicts(sensations)

    context = state.get("context") or {}
    if not isinstance(context, dict):
        context = {}

    body = body_state or {}
    if not body and sens_dicts:
        # Lightweight summary from sensations when no body_state attached
        arousals = [float(s.get("arousal_contribution", 0.0) or 0.0) for s in sens_dicts]
        vals = [float(s.get("valence", 0.0) or 0.0) for s in sens_dicts]
        body = {
            "arousal_estimate": max(
                float(context.get("arousal", 0.0) or 0.0),
                max(arousals) if arousals else 0.0,
            ),
            "valence_estimate": float(context.get("valence", 0.0) or 0.0)
            if "valence" in context
            else (sum(vals) / len(vals) if vals else 0.0),
            "active_sensations": [s.get("description", "") for s in sens_dicts[:3]],
            "dominant_zone": sens_dicts[0].get("zone") if sens_dicts else None,
        }
    elif not body:
        body = {
            "arousal_estimate": float(context.get("arousal", 0.0) or 0.0),
            "valence_estimate": float(context.get("valence", 0.0) or 0.0),
        }

    arousal = float(body.get("arousal_estimate", context.get("arousal", 0.0)) or 0.0)
    arousal_increased = (
        prev_arousal is not None and (arousal - prev_arousal) >= 0.08
    )
    arousal_decreased = (
        prev_arousal is not None and (prev_arousal - arousal) >= 0.08
    )

    patterns = list(context.get("active_patterns") or [])
    reflex = _reflex_kinds(state)

    contact = str(body.get("contact_state", "none")).lower()
    new_contact = contact not in ("", "none", "null")

    return {
        "timestamp": datetime.now(),
        "sensations": sens_dicts,
        "body_state": body,
        "affective": {
            "valence": float(context.get("valence", body.get("valence_estimate", 0.0)) or 0.0),
            "arousal": float(context.get("arousal", body.get("arousal_estimate", 0.5)) or 0.5),
            "dominance": float(context.get("dominance", 0.5) or 0.5),
        },
        "reflex_activity": reflex,
        "active_patterns": [str(p) for p in patterns],
        "arousal_increased": arousal_increased,
        "arousal_decreased": arousal_decreased,
        "new_contact": new_contact,
        "detail_level": detail_level,
        "source": "kernel",
        "tick": state.get("tick"),
    }


def from_state_payload(
    state: Dict[str, Any],
    *,
    prev_arousal: Optional[float] = None,
    detail_level: str = "normal",
) -> Dict[str, Any]:
    """
    Build coherent-input from a Saddle-shaped state payload:

    ``{ tick, context, last_actions, sensations, state_summary, ... }``
    """
    sensations = state.get("sensations") or []
    body = state.get("state_summary") or state.get("body_state") or {}
    context = state.get("context") or {}
    if not isinstance(context, dict):
        context = {}
    if not isinstance(body, dict):
        body = {}

    arousal = float(
        body.get("arousal_estimate", context.get("arousal", 0.0)) or 0.0
    )
    return {
        "timestamp": datetime.now(),
        "sensations": _sensations_to_dicts(sensations),
        "body_state": body,
        "affective": {
            "valence": float(
                context.get("valence", body.get("valence_estimate", 0.0)) or 0.0
            ),
            "arousal": arousal,
            "dominance": float(context.get("dominance", 0.5) or 0.5),
        },
        "reflex_activity": _reflex_kinds(state),
        "active_patterns": list(context.get("active_patterns") or []),
        "arousal_increased": prev_arousal is not None
        and (arousal - prev_arousal) >= 0.08,
        "arousal_decreased": prev_arousal is not None
        and (prev_arousal - arousal) >= 0.08,
        "new_contact": str(body.get("contact_state", "none")).lower()
        not in ("", "none", "null"),
        "detail_level": state.get("detail_level", detail_level),
        "source": "saddle",
        "tick": state.get("tick"),
    }


def from_abstraction_dicts(
    sensations: Sequence[Any],
    body_state: Optional[Dict[str, Any]] = None,
    *,
    reflex_activity: Optional[List[str]] = None,
    active_patterns: Optional[List[str]] = None,
    affective: Optional[Dict[str, Any]] = None,
    detail_level: str = "normal",
) -> Dict[str, Any]:
    """Package explicit abstraction/coherence outputs without a kernel handle."""
    sens = _sensations_to_dicts(sensations)
    body = body_state or {}
    aff = affective or {
        "valence": float(body.get("valence_estimate", 0.0) or 0.0),
        "arousal": float(body.get("arousal_estimate", 0.5) or 0.5),
        "dominance": 0.5,
    }
    return {
        "timestamp": datetime.now(),
        "sensations": sens,
        "body_state": body,
        "affective": aff,
        "reflex_activity": list(reflex_activity or []),
        "active_patterns": list(active_patterns or []),
        "detail_level": detail_level,
        "source": "abstraction",
    }


def drive_shared_sim(
    kernel: Any,
    virtual_sim: Any,
    *,
    detail_level: str = "normal",
    steps: int = 1,
    feed_kernel: bool = True,
    max_sensations: int = 3,
) -> Dict[str, Any]:
    """
    One low-latency drive of a **shared** VirtualSensorSimulator (Saddle pattern).

    - Produces rich sensations + body_state
    - Optionally feeds stimuli into the live kernel
    - Caches sensations on ``kernel._last_sensations`` for later from_kernel calls
    - Returns a coherent-input dict ready for ``process_coherent_input``

    Hosts should keep one ``virtual_sim`` for the process lifetime.
    """
    try:
        from reflexkernel.abstraction.schema import DetailLevel
        from reflexkernel.types import Stimulus
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "drive_shared_sim requires ReflexKernel on PYTHONPATH"
        ) from exc

    dl = (
        DetailLevel(detail_level)
        if detail_level in ("normal", "enhanced", "diagnostic")
        else DetailLevel.NORMAL
    )

    last_out = None
    for _ in range(max(1, int(steps))):
        raw = virtual_sim.read_all()
        if hasattr(virtual_sim, "process"):
            last_out = virtual_sim.process(raw, detail_level=dl)
        else:
            last_out = None
            break

        if feed_kernel and last_out is not None and hasattr(kernel, "step"):
            stim_dicts = (
                last_out.to_stimuli() if hasattr(last_out, "to_stimuli") else []
            )
            extras = []
            for d in stim_dicts:
                try:
                    extras.append(
                        Stimulus.from_dict(d) if isinstance(d, dict) else d
                    )
                except Exception:
                    pass
            if extras:
                kernel.step(extra_stimuli=extras)

    if last_out is None:
        return from_kernel(kernel, detail_level=detail_level)

    sens = list(getattr(last_out, "sensations", None) or [])[:max_sensations]
    try:
        kernel._last_sensations = list(sens)
    except Exception:
        pass

    body = {}
    if getattr(last_out, "state_summary", None) is not None:
        summary = last_out.state_summary
        body = summary.to_dict() if hasattr(summary, "to_dict") else dict(summary)

    state = kernel.get_state() if hasattr(kernel, "get_state") else {}
    return from_kernel(
        kernel,
        sensations=sens,
        body_state=body,
        detail_level=detail_level,
    )
