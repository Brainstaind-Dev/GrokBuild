"""
Deterministic tier-1 extract: raw hardware-shaped dict → Stimulus list.

No RNG. A given press always becomes the same stimuli.
Theater noise stays in VirtualSensorSimulator.read_all, not here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ..types import Modality, Stimulus


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def extract_tier1(
    raw: Mapping[str, Any] | None,
    *,
    source: str = "hardware",
    fsr_threshold: float = 0.0,
) -> List[Stimulus]:
    """
    Turn a Virtual-shaped raw packet into kernel stimuli.

    `fsr[0] = 0.4` always yields a touch stimulus (threshold default 0).
    Empty / missing / all-zero FSR yields [].
    """
    if not raw:
        return []
    out: List[Stimulus] = []
    fsr = raw.get("fsr") or []
    if not isinstance(fsr, (list, tuple)):
        fsr = []
    for i, val in enumerate(fsr):
        v = _f(val)
        if v is None:
            continue
        if v > fsr_threshold:
            out.append(
                Stimulus(
                    modality=Modality.TOUCH,
                    data={
                        "type": "fsr",
                        "channel": i,
                        "value": v,
                        "kind": "pressure",
                        "source_path": "physical",
                    },
                    confidence=min(1.0, max(0.0, v)),
                    source=source,
                )
            )
    return out
