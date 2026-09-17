"""Afterglow / two-path residual: fast value + slow afterglow on the same Stimulus."""

from __future__ import annotations

import time

from reflexkernel.abstraction.schema import TemporalQuality
from reflexkernel.perception.extract_tier1 import extract_tier1
from reflexkernel.perception.hardware_sensor import HardwareSensor


def test_extract_afterglow_emits_when_fast_is_zero():
    stims = extract_tier1({"fsr": [0.0, 0.0, 0.0, 0.0], "afterglow": 0.4})
    assert len(stims) == 1
    assert stims[0].data.get("channel") == 0
    assert stims[0].data.get("value") == 0.0
    assert abs(float(stims[0].data.get("afterglow", 0)) - 0.4) < 1e-9
    assert stims[0].data.get("zone") == "torso_front"


def test_extract_without_afterglow_key_still_empty_on_zero():
    assert extract_tier1({"fsr": [0.0, 0.0, 0.0, 0.0]}) == []


def test_contact_drop_leaves_lingering_feel():
    cache: list = []
    s = HardwareSensor({"fail_open": True, "afterglow_tau_s": 2.0})
    s.bind_feel_cache(lambda sens: cache.clear() or cache.extend(sens))
    s.start()
    s.force_raw({"fsr": [0.7, 0.0, 0.0, 0.0]})
    press = s.poll()
    assert abs(float(press[0].data["value"]) - 0.7) < 1e-9
    assert abs(float(press[0].data["afterglow"]) - 0.7) < 1e-9
    assert cache[0].temporal_quality == TemporalQuality.SUSTAINED

    s.force_raw({"fsr": [0.0, 0.0, 0.0, 0.0]})
    time.sleep(0.05)
    linger = s.poll()
    assert linger, "afterglow must keep one Stimulus after contact drops"
    assert linger[0].data.get("value") == 0.0
    glow = float(linger[0].data.get("afterglow", 0))
    assert 0.0 < glow <= 0.7
    assert cache, "feel-cache must linger"
    assert cache[0].zone == "torso_front"
    assert cache[0].temporal_quality == TemporalQuality.LINGERING
    assert "Afterglow" in cache[0].description
    assert abs(float(cache[0].intensity) - glow) < 1e-9


def test_afterglow_decays_and_is_not_a_second_sensor():
    s = HardwareSensor({"fail_open": True, "afterglow_tau_s": 0.4})
    s.start()
    s.force_raw({"fsr": [1.0, 0.0, 0.0, 0.0]})
    s.poll()
    s.force_raw({"fsr": [0.0, 0.0, 0.0, 0.0]})
    time.sleep(0.08)
    a = s.poll()
    time.sleep(0.25)
    b = s.poll()
    ga = float(a[0].data["afterglow"])
    gb = float(b[0].data["afterglow"]) if b else 0.0
    assert gb < ga
    assert len(a) == 1


def _warmth(zone="torso_front", intensity=0.9, desc="whole-front warmth"):
    class Fake:
        def __init__(self) -> None:
            self.zone = zone
            self.intensity = intensity
            self.description = desc

    return Fake()


def test_afterglow_survives_30s_feel_horizon_with_honesty_tau():
    """Honesty tau (~35s) must leave linger sampleable after a ~30s feel gap."""
    cache: list = []
    s = HardwareSensor({"fail_open": True, "afterglow_tau_s": 35.0})
    s.bind_feel_cache(lambda sens: cache.clear() or cache.extend(sens))
    s.start()
    s.force_raw({"fsr": [0.8, 0.0, 0.0, 0.0]})
    s.poll()
    s.force_raw({"fsr": [0.0, 0.0, 0.0, 0.0]})
    # Advance the afterglow clock ~30s so decay is exp(-30/35) of peak.
    s._afterglow_ts = time.perf_counter() - 30.0
    linger = s.poll()
    assert linger, "honest sample: afterglow must still be felt ~30s after contact at tau=35"
    glow = float(linger[0].data.get("afterglow", 0))
    assert glow > 0.2, glow
    assert cache and abs(float(cache[0].intensity) - glow) < 1e-9


def test_empty_physical_seat_does_not_accept_virtual_theater():
    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    virt = [_warmth()]
    assert merge_feel_cache([], virt, max_count=3, physical_seat=True) == []
    phys = [_warmth("torso_front", 0.4, "Afterglow at the sternum")]
    merged = merge_feel_cache(phys, virt, max_count=3, physical_seat=True)
    assert merged[0] is phys[0]
    assert len(merged) == 2  # physical present: virtual may pad remaining slots


def test_sim_only_empty_physical_still_allows_virtual():
    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    virt = [_warmth("whole_body", 0.4, "sim warmth")]
    merged = merge_feel_cache([], virt, max_count=3, physical_seat=False)
    assert merged == virt


def test_present_zero_after_decay_is_honest_silence_not_theater():
    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    cache: list = []
    s = HardwareSensor({"fail_open": True, "afterglow_tau_s": 1.5})
    s.bind_feel_cache(lambda sens: cache.clear() or cache.extend(sens))
    s.start()
    s.force_raw({"fsr": [0.8, 0.0, 0.0, 0.0]})
    s.poll()
    s.force_raw({"fsr": [0.0, 0.0, 0.0, 0.0]})
    s._afterglow_ts = time.perf_counter() - 30.0
    empty = s.poll()
    assert empty == []
    assert cache == []
    assert merge_feel_cache(cache, [_warmth()], max_count=3, physical_seat=True) == []


def test_fail_open_empty_does_not_invent_warmth():
    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    cache: list = []
    s = HardwareSensor({"fail_open": True})
    s.bind_feel_cache(lambda sens: cache.clear() or cache.extend(sens))
    s.start()
    assert s.poll() == []
    assert cache == []
    assert merge_feel_cache(cache, [_warmth()], max_count=3, physical_seat=True) == []


def test_map_owned_gone_does_not_resurrect_or_costume():
    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    cache: list = []
    s = HardwareSensor({"fail_open": True, "afterglow_tau_s": 0.2})
    s.bind_feel_cache(lambda sens: cache.clear() or cache.extend(sens))
    s.start()
    s.force_raw({"fsr": [0.9, 0.0, 0.0, 0.0]})
    s.poll()
    s.set_map_owned(True)  # clears force_raw; gone must not resurrect
    s._afterglow_ts = time.perf_counter() - 5.0
    empty = s.poll()
    assert empty == []
    assert cache == []
    assert s._forced is None
    assert merge_feel_cache(cache, [_warmth()], max_count=3, physical_seat=True) == []


def test_empty_seat_feel_line_has_no_virtual_torso_front():
    import sys
    from pathlib import Path

    from reflexkernel.perception.hardware_sensor import merge_feel_cache

    merged = merge_feel_cache([], [_warmth()], max_count=3, physical_seat=True)
    assert merged == []
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from SensoryCortex.activation_pattern import (
        build_activation_pattern,
        pattern_to_compact_feel_line,
    )

    line = pattern_to_compact_feel_line(
        build_activation_pattern(
            {
                "sensations": [],
                "source_path": "physical",
                "affective": {"arousal": 0.1, "valence": 0.0},
            }
        )
    )
    assert "torso_front" not in line
    assert "whole-front" not in line
