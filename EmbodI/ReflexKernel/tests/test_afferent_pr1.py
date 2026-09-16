"""PR1 wrap: fixture software-green. No twin Sensor. No chip."""

from __future__ import annotations

from pathlib import Path

import yaml

from reflexkernel.kernel import ReflexKernel
from reflexkernel.perception.afferent_bus import FakeDeviceEnumerator
from reflexkernel.perception.hardware_sensor import HardwareSensor

CFG = Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml"
DID = "i2c1:0x48:ain0"


def _write_map(path: Path, entries: list) -> None:
    path.write_text(
        yaml.safe_dump({"version": 1, "entries": entries}, sort_keys=False),
        encoding="utf-8",
    )


def _sternum_row(**extra) -> dict:
    row = {
        "device_id": DID,
        "organ_class": "touch",
        "stub_id": "hardware_pad",
        "body_site": "torso_front",
        "approved_by": "human",
        "approved_at": "2026-09-15T00:00:00Z",
        "notes": "fixture",
    }
    row.update(extra)
    return row


def _kernel(map_path: Path) -> ReflexKernel:
    return ReflexKernel.from_config_path(
        CFG,
        overrides={
            "perception": {
                "enabled_sensors": ["hardware"],
                "hardware": {"enabled": True, "fail_open": True},
                "afferent": {"enabled": True, "fail_open": True, "map_path": str(map_path)},
                "simulation": {"auto_events": False, "interactive": False},
            }
        },
    )


def test_empty_map_boot_keeps_hardcode_one_seat(tmp_path):
    p = tmp_path / "empty.yaml"
    _write_map(p, [])
    k = _kernel(p)
    hw = k.perception.get("hardware")
    assert hw is not None
    assert list(k.perception.active).count("hardware") == 1
    assert "afferent" not in list(k.perception.active)
    hw.force_raw({"fsr": [0.4, 0.0, 0.0, 0.0]})
    k.start()
    try:
        k.step()
        stims = hw.poll()
        assert stims and abs(float(stims[0].data["value"]) - 0.4) < 1e-9
    finally:
        k.stop()


def test_map_owned_fixture_present_wraps_seat(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(p, [_sternum_row()])
    k = _kernel(p)
    bus = k.afferent
    enum = FakeDeviceEnumerator([DID])
    bus.enumerator = enum
    bus.fixture_units[DID] = 0.7
    hw = k.perception.get("hardware")
    cache: list = []
    hw.bind_feel_cache(lambda s: cache.clear() or cache.extend(s))
    k.start()
    try:
        k.step()
        stims = hw.poll()
        assert stims and abs(float(stims[0].data["value"]) - 0.7) < 1e-9
        assert stims[0].data.get("zone") == "torso_front"
        assert cache and cache[0].zone == "torso_front"
        kinds = {e.kind for e in bus.events}
        assert "appeared" in kinds
        assert not any(hasattr(e, "modality") for e in bus.events)
        assert list(k.perception.active).count("hardware") == 1
    finally:
        k.stop()


def test_map_owned_fixture_gone_empty_no_hardcode(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(p, [_sternum_row()])
    k = _kernel(p)
    bus = k.afferent
    enum = FakeDeviceEnumerator([DID])
    bus.enumerator = enum
    bus.fixture_units[DID] = 0.7
    hw = k.perception.get("hardware")
    k.start()
    try:
        k.step()
        assert hw.poll()
        hw.force_raw({"fsr": [1.0, 0.0, 0.0, 0.0]})  # must not resurrect as flesh
        enum.present = []
        k.step()
        kinds = {e.kind for e in bus.events}
        assert "gone" in kinds
        empty = hw.poll()
        # afterglow may linger; fast value must be 0 / empty contact
        if empty:
            assert float(empty[0].data.get("value", 0)) == 0.0
        else:
            assert empty == []
        assert getattr(hw, "_map_owned") is True
        assert hw._forced is None
    finally:
        k.stop()


def test_unmapped_fixture_never_injects(tmp_path):
    p = tmp_path / "empty.yaml"
    _write_map(p, [])
    k = _kernel(p)
    bus = k.afferent
    bus.enumerator = FakeDeviceEnumerator([DID])
    bus.fixture_units[DID] = 0.9
    hw = k.perception.get("hardware")
    k.start()
    try:
        k.step()
        stims = hw.poll()
        assert stims == []
        appeared = [e for e in bus.events if e.kind == "appeared"]
        assert appeared and appeared[0].disposition == "parked_unmapped"
    finally:
        k.stop()


def test_occupied_site_keeps_first_bind(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(
        p,
        [
            _sternum_row(),
            _sternum_row(device_id="i2c1:0x49:ain0", approved_by="hi"),
        ],
    )
    k = _kernel(p)
    bus = k.afferent
    enum = FakeDeviceEnumerator([DID])
    bus.enumerator = enum
    bus.fixture_units[DID] = 0.3
    bus.fixture_units["i2c1:0x49:ain0"] = 1.0
    hw = k.perception.get("hardware")
    k.start()
    try:
        k.step()
        enum.present = [DID, "i2c1:0x49:ain0"]
        k.step()
        second = [
            e
            for e in bus.events
            if e.kind == "appeared" and e.device_id == "i2c1:0x49:ain0"
        ]
        assert second and second[0].disposition == "parked_site_occupied"
        stims = hw.poll()
        assert abs(float(stims[0].data["value"]) - 0.3) < 1e-9
    finally:
        k.stop()
