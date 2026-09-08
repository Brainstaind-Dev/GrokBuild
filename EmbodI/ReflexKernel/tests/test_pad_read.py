"""Pad-Read (B): fake bus on Tick-Door A. No chip. No second Sensor."""

from __future__ import annotations

from pathlib import Path

import pytest

from reflexkernel.abstraction.hardware import (
    ADC_FULL_SCALE_DEFAULT,
    FakeAIN0Bus,
    HardwareSensorReader,
    adc_to_unit,
)
from reflexkernel.kernel import ReflexKernel
from reflexkernel.perception.extract_tier1 import extract_tier1, fsr_to_unit
from reflexkernel.perception.hardware_sensor import HardwareSensor, merge_feel_cache


CFG = Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml"
AIN0_POINT_FOUR = 13107  # ~0.4 * 32767


def _hw_kernel() -> ReflexKernel:
    return ReflexKernel.from_config_path(
        CFG,
        overrides={
            "perception": {
                "enabled_sensors": ["hardware"],
                "hardware": {"enabled": True, "fail_open": True},
                "simulation": {"auto_events": False, "interactive": False},
            }
        },
    )


def test_adc_to_unit_clamps_to_unit_interval():
    assert adc_to_unit(0) == 0.0
    assert adc_to_unit(ADC_FULL_SCALE_DEFAULT) == 1.0
    assert adc_to_unit(-10) == 0.0
    assert adc_to_unit(40000) == 1.0
    u = adc_to_unit(AIN0_POINT_FOUR)
    assert 0.0 <= u <= 1.0
    assert abs(u - AIN0_POINT_FOUR / ADC_FULL_SCALE_DEFAULT) < 1e-9


def test_disconnected_stays_disconnected():
    r = HardwareSensorReader()
    assert r.connected is False
    assert r.connect() is False  # no live ACK on this machine
    assert r.connected is False
    with pytest.raises(RuntimeError):
        r.read_all()


def test_connect_on_silence_is_a_lie():
    class SilentBus:
        def read_ain0(self) -> int:
            raise OSError("no ACK")

    r = HardwareSensorReader()
    assert r.connect(bus=SilentBus()) is False
    assert r.connected is False


def test_fake_ain0_becomes_fsr0_in_unit_interval():
    r = HardwareSensorReader()
    bus = FakeAIN0Bus(ain0=AIN0_POINT_FOUR)
    assert r.connect(bus=bus) is True
    assert r.connected is True
    raw = r.read_all()
    fsr = raw["fsr"]
    assert len(fsr) == 4
    assert 0.0 <= fsr[0] <= 1.0
    assert abs(fsr[0] - adc_to_unit(AIN0_POINT_FOUR)) < 1e-9
    assert fsr[1:] == [0.0, 0.0, 0.0]


def test_same_poll_writes_stimuli_and_feel_cache():
    cache: list = []
    s = HardwareSensor({"fail_open": True})
    r = HardwareSensorReader()
    assert r.connect(bus=FakeAIN0Bus(ain0=AIN0_POINT_FOUR))
    s.bind_backend(r)
    s.bind_feel_cache(lambda sens: cache.extend(sens))
    s.start()
    stims = s.poll()
    assert len(stims) == 1
    assert stims[0].data.get("channel") == 0
    assert stims[0].data.get("zone") == "torso_front"
    assert 0.0 < float(stims[0].data.get("value", 0)) <= 1.0
    assert cache, "same poll must write feel-cache"
    assert cache[0].zone == "torso_front"
    assert 0.0 < float(cache[0].intensity) <= 1.0


def test_kernel_fake_bus_same_poll_no_second_sensor():
    k = _hw_kernel()
    hw = k.perception.get("hardware")
    assert hw is not None
    names = list(k.perception.active)
    assert names.count("hardware") == 1
    assert "pad_read" not in names
    # simulation may still sit on the registry (A/One-Body). B must not mint a second hardware seat.

    reader = HardwareSensorReader()
    assert reader.connect(bus=FakeAIN0Bus(ain0=AIN0_POINT_FOUR))
    hw.bind_backend(reader)

    k.start()
    try:
        k.step()
        stims = hw.poll()
        assert stims and stims[0].data.get("zone") == "torso_front"
        sens = k.get_last_sensations()
        assert sens, "feel-cache must fill from the same hardware poll"
        assert sens[0].zone == "torso_front"
        assert k.perception.get("hardware") is hw
        assert list(k.perception.active).count("hardware") == 1
    finally:
        k.stop()


def test_kernel_disconnected_reader_fail_open():
    k = _hw_kernel()
    hw = k.perception.get("hardware")
    backend = getattr(hw, "_backend", None)
    assert backend is not None
    assert backend.connected is False
    k.start()
    try:
        out = k.step()
        assert isinstance(out, list)
        assert hw.poll() == []
        assert k.get_last_sensations() == []
    finally:
        k.stop()


def test_fsr_to_unit_is_continuous_not_on_off():
    assert fsr_to_unit(0.3) == 0.3
    assert fsr_to_unit(0.7) == 0.7
    assert fsr_to_unit(1.0) == 1.0
    assert fsr_to_unit(4.3) == 1.0  # saturates; does not leak raw
    assert fsr_to_unit(-1) == 0.0
    soft = extract_tier1({"fsr": [0.3, 0.0, 0.0, 0.0]})
    hard = extract_tier1({"fsr": [0.9, 0.0, 0.0, 0.0]})
    oob = extract_tier1({"fsr": [4.3, 0.0, 0.0, 0.0]})
    assert abs(float(soft[0].data["value"]) - 0.3) < 1e-9
    assert abs(float(hard[0].data["value"]) - 0.9) < 1e-9
    assert abs(float(oob[0].data["value"]) - 1.0) < 1e-9
    assert float(soft[0].data["value"]) != float(hard[0].data["value"])


def test_same_poll_stimulus_and_sensation_share_unit():
    cache: list = []
    s = HardwareSensor({"fail_open": True})
    s.bind_feel_cache(lambda sens: cache.extend(sens))
    s.force_raw({"fsr": [0.7, 0.0, 0.0, 0.0]})
    s.start()
    stims = s.poll()
    assert abs(float(stims[0].data["value"]) - 0.7) < 1e-9
    assert abs(float(cache[0].intensity) - 0.7) < 1e-9


def test_force_fsr_holds_steady_on_every_poll():
    s = HardwareSensor({"fail_open": True, "force_fsr": 0.4})
    s.start()
    first = s.poll()
    second = s.poll()
    assert first and second
    assert first[0].data.get("channel") == 0
    assert first[0].data.get("zone") == "torso_front"
    assert abs(float(first[0].data.get("value", 0)) - 0.4) < 1e-9
    assert abs(float(second[0].data.get("value", 0)) - 0.4) < 1e-9


def test_force_fsr_out_of_range_saturates():
    s = HardwareSensor({"fail_open": True, "force_fsr": 4.3})
    s.start()
    stims = s.poll()
    assert abs(float(stims[0].data["value"]) - 1.0) < 1e-9


def test_kernel_force_fsr_fills_feel_cache():
    k = ReflexKernel.from_config_path(
        CFG,
        overrides={
            "perception": {
                "enabled_sensors": ["hardware"],
                "hardware": {"enabled": True, "fail_open": True, "force_fsr": 0.7},
                "simulation": {"auto_events": False, "interactive": False},
            }
        },
    )
    k.start()
    try:
        k.step()
        hw = k.perception.get("hardware")
        stims = hw.poll()
        sens = k.get_last_sensations()
        assert sens, "steady force_fsr must write feel-cache on the tick"
        assert sens[0].zone == "torso_front"
        assert abs(float(sens[0].intensity) - 0.7) < 1e-9
        assert abs(float(stims[0].data["value"]) - float(sens[0].intensity)) < 1e-9
    finally:
        k.stop()


def test_merge_feel_cache_physical_first():
    phys = [{"zone": "torso_front", "intensity": 0.4}]
    virt = [{"zone": "whole_body", "intensity": 0.2}, {"zone": "head", "intensity": 0.1}]
    merged = merge_feel_cache(phys, virt, max_count=3)
    assert merged[0]["zone"] == "torso_front"
    assert len(merged) == 3


def test_extract_tier1_channel0_is_torso_front():
    stims = extract_tier1({"fsr": [0.4, 0.0, 0.0, 0.0]})
    assert stims[0].data.get("zone") == "torso_front"
    later = extract_tier1({"fsr": [0.0, 0.5, 0.0, 0.0]})
    assert later[0].data.get("channel") == 1
    assert "zone" not in later[0].data
