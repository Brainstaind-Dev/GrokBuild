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
