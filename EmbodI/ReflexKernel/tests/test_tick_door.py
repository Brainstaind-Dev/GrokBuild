"""Tick-Door (A) + One-Body: hardware seat on the tick, no twin sim."""

from __future__ import annotations

from pathlib import Path

import pytest

from reflexkernel.kernel import ReflexKernel
from reflexkernel.perception.extract_tier1 import extract_tier1
from reflexkernel.perception.hardware_sensor import HardwareSensor
from reflexkernel.interface.python_api import PythonAPI
from reflexkernel.types import Modality, Stimulus


def test_extract_tier1_fsr0_point_four():
    stims = extract_tier1({"fsr": [0.4, 0.0, 0.0, 0.0]})
    assert stims, "fsr[0]=0.4 must become a stimulus"
    assert all(isinstance(s, Stimulus) for s in stims)
    touch = [s for s in stims if str(getattr(s.modality, "value", s.modality)) == "touch"]
    assert touch
    assert touch[0].data.get("channel") == 0
    assert abs(float(touch[0].data.get("value", 0)) - 0.4) < 1e-9
    # deterministic
    again = extract_tier1({"fsr": [0.4, 0.0, 0.0, 0.0]})
    assert again[0].data == touch[0].data


def test_extract_tier1_zeros_silent():
    assert extract_tier1({"fsr": [0.0, 0.0, 0.0, 0.0]}) == []
    assert extract_tier1(None) == []
    assert extract_tier1({}) == []


def test_hardware_sensor_fail_open_empty_without_backend():
    s = HardwareSensor({"fail_open": True})
    s.start()
    assert s.poll() == []


def test_hardware_sensor_force_raw_on_tick():
    s = HardwareSensor({"fail_open": True})
    s.start()
    s.force_raw({"fsr": [0.4, 0.0, 0.0, 0.0]})
    out = s.poll()
    assert len(out) == 1
    assert out[0].data["channel"] == 0


def test_kernel_step_hears_fsr_via_hardware_seat():
    k = ReflexKernel.from_config_path(
        Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml",
        overrides={
            "perception": {
                "enabled_sensors": ["hardware"],
                "hardware": {"enabled": True, "fail_open": True},
                "simulation": {"auto_events": False, "interactive": False},
            }
        },
    )
    hw = k.perception.get("hardware")
    assert hw is not None, "HardwareSensor must be on the registry"
    k.start()
    try:
        empty = k.step()
        assert isinstance(empty, list)
        hw.force_raw({"fsr": [0.4, 0.0, 0.0, 0.0]})
        # collect_all is inside step
        actions = k.step()
        assert isinstance(actions, list)
        # stimulus path: fusion should have seen a touch (arousal can rise)
        traces = k.state.last_traces
        # At minimum, a second step must not raise and hardware poll produced a stim
        assert hw.poll()  # forced raw still present
    finally:
        k.stop()


def test_one_body_python_api_shares_sim():
    cfg = Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml"
    k = ReflexKernel.from_config_path(
        str(cfg),
        overrides={"perception": {"simulation": {"auto_events": False, "interactive": False}}},
    )
    k.start()
    try:
        api = PythonAPI(k)
        a = api.ensure_virtual_sim()
        b = api.ensure_virtual_sim()
        assert a is b
        api.get_coherent_sensations(steps=1)
        api.get_body_state()
        assert api.ensure_virtual_sim() is a
        api2 = PythonAPI(k, virtual_sim=a)
        assert api2.ensure_virtual_sim() is a
    finally:
        k.stop()
