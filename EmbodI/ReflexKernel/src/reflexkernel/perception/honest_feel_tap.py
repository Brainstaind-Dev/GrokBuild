"""Honest feel tap — read-only look at what the feel-cache actually holds.

Search names: feel tap, honest tap, honest_feel_tap.

Hold vocabulary (felt-honesty):
  empty              — feel-cache has no sensations; empty stays empty
  linger             — at least one sensation is afterglow / lingering
  present-and-quiet  — sensation(s) present that are not linger

Not a Saddle session. Not a branded mouth. Fixture / fake-bus is fine.
Does not invent occupancy or whole-front warmth theater.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence

HOLD_EMPTY = "empty"
HOLD_LINGER = "linger"
HOLD_PRESENT_AND_QUIET = "present-and-quiet"


def _tq_value(s: Any) -> str:
    tq = getattr(s, "temporal_quality", None)
    if tq is None and isinstance(s, Mapping):
        tq = s.get("temporal_quality")
    if tq is None:
        return ""
    return str(getattr(tq, "value", tq)).strip().lower()


def _is_lingering(s: Any) -> bool:
    return _tq_value(s) == "lingering"


def _intensity(s: Any) -> Optional[float]:
    v = getattr(s, "intensity", None)
    if v is None and isinstance(s, Mapping):
        v = s.get("intensity")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _zone(s: Any) -> Optional[str]:
    z = getattr(s, "zone", None)
    if z is None and isinstance(s, Mapping):
        z = s.get("zone")
    return str(z) if z else None


@dataclass(frozen=True)
class FeelTapReading:
    """Small structured read of feel-cache contents."""

    hold: str
    one_line: str
    count: int = 0
    zones: tuple = ()
    intensities: tuple = ()
    lingering_count: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def classify_feel_hold(sensations: Optional[Sequence[Any]]) -> str:
    """Classify feel-cache contents only. Never invent occupancy."""
    items = list(sensations or [])
    if not items:
        return HOLD_EMPTY
    if any(_is_lingering(s) for s in items):
        return HOLD_LINGER
    return HOLD_PRESENT_AND_QUIET


def tap_from_sensations(sensations: Optional[Sequence[Any]]) -> FeelTapReading:
    items = list(sensations or [])
    hold = classify_feel_hold(items)
    zones = tuple(z for z in (_zone(s) for s in items) if z)
    intensities = tuple(i for i in (_intensity(s) for s in items) if i is not None)
    lingering_count = sum(1 for s in items if _is_lingering(s))
    if hold == HOLD_EMPTY:
        one_line = "feel tap: empty"
    elif hold == HOLD_LINGER:
        one_line = f"feel tap: linger (n={len(items)})"
    else:
        one_line = f"feel tap: present-and-quiet (n={len(items)})"
    return FeelTapReading(
        hold=hold,
        one_line=one_line,
        count=len(items),
        zones=zones,
        intensities=intensities,
        lingering_count=lingering_count,
    )


def tap_from_raw(raw: Mapping[str, Any], *, threshold: float = 0.0) -> FeelTapReading:
    """Fixture / fake-bus door — uses the same _feel_from_raw path as Pad-Read."""
    from .hardware_sensor import _feel_from_raw

    return tap_from_sensations(_feel_from_raw(raw, threshold=threshold))


def tap_from_kernel(kernel: Any) -> FeelTapReading:
    """Read kernel feel-cache as stored. Empty if missing. No virtual theater fill."""
    getter = getattr(kernel, "get_last_sensations", None)
    if not callable(getter):
        return tap_from_sensations([])
    try:
        cached = getter()
    except Exception:
        return tap_from_sensations([])
    return tap_from_sensations(list(cached or []))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Tiny CLI: honest feel tap against fixture raw (no live ADS1115 required)."""
    import argparse
    import json

    p = argparse.ArgumentParser(
        prog="honest_feel_tap",
        description=(
            "Honest feel tap / feel tap — read-only feel-cache hold "
            "(empty|linger|present-and-quiet)."
        ),
    )
    p.add_argument("--fsr", type=float, default=0.0, help="Fixture FSR unit 0..1 (channel 0)")
    p.add_argument(
        "--afterglow",
        type=float,
        default=None,
        help="Optional afterglow unit; omit to mirror fsr",
    )
    p.add_argument("--threshold", type=float, default=0.0)
    p.add_argument("--json", action="store_true", help="Print structured JSON")
    args = p.parse_args(list(argv) if argv is not None else None)
    raw: dict = {"fsr": [float(args.fsr)]}
    if args.afterglow is not None:
        raw["afterglow"] = float(args.afterglow)
    reading = tap_from_raw(raw, threshold=float(args.threshold))
    if args.json:
        print(json.dumps(reading.as_dict(), indent=2))
    else:
        print(reading.one_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
