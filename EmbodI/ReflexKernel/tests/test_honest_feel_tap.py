"""Tests for honest feel tap / feel tap."""
from __future__ import annotations

from reflexkernel.abstraction.schema import (
    Sensation,
    SensationCategory,
    TemporalQuality,
)
from reflexkernel.perception.honest_feel_tap import (
    HOLD_EMPTY,
    HOLD_LINGER,
    HOLD_PRESENT_AND_QUIET,
    classify_feel_hold,
    tap_from_kernel,
    tap_from_raw,
    tap_from_sensations,
)
from reflexkernel.perception.hardware_sensor import merge_feel_cache


def _sustained(intensity: float = 0.4) -> Sensation:
    return Sensation(
        description=f"Pressure at the sternum ({intensity:.2f}).",
        zone="torso_front",
        intensity=intensity,
        category=SensationCategory.CONTACT_PRESSURE,
        temporal_quality=TemporalQuality.SUSTAINED,
        source_features=["fsr.0"],
        ts=1.0,
        confidence=intensity,
    )


def _linger(intensity: float = 0.3) -> Sensation:
    return Sensation(
        description=f"Afterglow at the sternum ({intensity:.2f}).",
        zone="torso_front",
        intensity=intensity,
        category=SensationCategory.CONTACT_PRESSURE,
        temporal_quality=TemporalQuality.LINGERING,
        source_features=["fsr.0"],
        ts=1.0,
        confidence=intensity,
    )


def test_feel_tap_empty():
    r = tap_from_sensations([])
    assert r.hold == HOLD_EMPTY
    assert r.count == 0
    assert "empty" in r.one_line
    assert classify_feel_hold([]) == HOLD_EMPTY


def test_feel_tap_linger():
    r = tap_from_sensations([_linger(0.25)])
    assert r.hold == HOLD_LINGER
    assert r.lingering_count == 1
    assert "linger" in r.one_line


def test_feel_tap_present_and_quiet():
    r = tap_from_sensations([_sustained(0.5)])
    assert r.hold == HOLD_PRESENT_AND_QUIET
    assert r.lingering_count == 0
    assert "present-and-quiet" in r.one_line


def test_feel_tap_linger_wins_over_sustained():
    r = tap_from_sensations([_sustained(0.5), _linger(0.2)])
    assert r.hold == HOLD_LINGER


def test_feel_tap_from_raw_empty_fixture():
    r = tap_from_raw({"fsr": [0.0]})
    assert r.hold == HOLD_EMPTY


def test_feel_tap_from_raw_pressure():
    r = tap_from_raw({"fsr": [0.6]})
    assert r.hold == HOLD_PRESENT_AND_QUIET
    assert r.count == 1


def test_feel_tap_from_raw_linger_afterglow():
    r = tap_from_raw({"fsr": [0.0], "afterglow": 0.4}, threshold=0.0)
    assert r.hold == HOLD_LINGER


def test_feel_tap_no_invented_occupancy_after_honesty_merge():
    virt = [_sustained(0.9)]
    merged = merge_feel_cache([], virt, max_count=3, physical_seat=True)
    r = tap_from_sensations(merged)
    assert merged == []
    assert r.hold == HOLD_EMPTY


class _Kernel:
    def __init__(self, sensations):
        self._s = list(sensations)

    def get_last_sensations(self):
        return list(self._s)


def test_feel_tap_from_kernel_empty():
    r = tap_from_kernel(_Kernel([]))
    assert r.hold == HOLD_EMPTY


def test_feel_tap_from_kernel_reads_cache_only():
    r = tap_from_kernel(_Kernel([_linger()]))
    assert r.hold == HOLD_LINGER


def test_feel_tap_kernel_missing_getter_is_empty():
    r = tap_from_kernel(object())
    assert r.hold == HOLD_EMPTY
