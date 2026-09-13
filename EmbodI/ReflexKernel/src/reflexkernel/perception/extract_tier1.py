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


def fsr_to_unit(x: Any) -> float | None:
    """Pad-Read / Tick-Door touch unit. Continuous [0, 1]. Never boolean. Never raw ADC/volts."""
    v = _f(x)
    if v is None:
        return None
    return max(0.0, min(1.0, v))


def extract_tier1(
    raw: Mapping[str, Any] | None,
    *,
    source: str = "hardware",
    fsr_threshold: float = 0.0,
) -> List[Stimulus]:
    """
    Turn a Virtual-shaped raw packet into kernel stimuli.

    `fsr[0] = 0.4` always yields a touch stimulus (threshold default 0).
    Empty / missing / all-zero FSR yields [] unless channel-0 `afterglow` remains.
    Values are the continuous unit [0, 1] (soft vs hard are different numbers).
    Fast `value` + slow `afterglow` share that unit on the same Stimulus (no second Sensor).
    Out-of-range saturates; never a contact bit, never a raw volts/ADC leak.
    """
    if not raw:
        return []
    out: List[Stimulus] = []
    fsr = raw.get("fsr") or []
    if not isinstance(fsr, (list, tuple)):
        fsr = []
    glow0 = fsr_to_unit(raw.get("afterglow"))
    for i, val in enumerate(fsr):
        v = fsr_to_unit(val)
        if v is None:
            continue
        glow = glow0 if i == 0 and glow0 is not None else 0.0
        if v > fsr_threshold or glow > fsr_threshold:
            data: Dict[str, Any] = {
                "type": "fsr",
                "channel": i,
                "value": v,
                "kind": "pressure",
                "source_path": "physical",
                **({"zone": "torso_front"} if i == 0 else {}),
            }
            if i == 0:
                data["afterglow"] = glow if glow0 is not None else v
            out.append(
                Stimulus(
                    modality=Modality.TOUCH,
                    data=data,
                    confidence=max(v, glow),
                    source=source,
                )
            )
    return out
