"""D0/PR0 AfferentBus: topology only. No Stimulus. No second Sensor."""

from __future__ import annotations

from pathlib import Path

import yaml

from reflexkernel.kernel import ReflexKernel
from reflexkernel.perception.afferent_bus import AfferentBus, FakeDeviceEnumerator
from reflexkernel.perception.hardware_sensor import HardwareSensor

CFG = Path(__file__).resolve().parents[1] / "configs" / "sim_only.yaml"
DEFAULT_MAP = Path(__file__).resolve().parents[1] / "configs" / "afferent_map.yaml"


def _write_map(path: Path, entries: list) -> None:
    path.write_text(
        yaml.safe_dump({"version": 1, "entries": entries}, sort_keys=False),
        encoding="utf-8",
    )


def test_default_map_file_is_empty():
    data = yaml.safe_load(DEFAULT_MAP.read_text(encoding="utf-8"))
    assert data.get("version") == 1
    assert data.get("entries") == []


def test_empty_map_parks_unmapped():
    enum = FakeDeviceEnumerator(["i2c1:0x48:ain0"])
    bus = AfferentBus(map_path=DEFAULT_MAP, enumerator=enum)
    evs = bus.poll()
    appeared = [e for e in evs if e.kind == "appeared"]
    assert len(appeared) == 1
    assert appeared[0].disposition == "parked_unmapped"
    assert appeared[0].device_id == "i2c1:0x48:ain0"


def test_mapped_free_site_reserves_without_stimulus(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(
        p,
        [
            {
                "device_id": "i2c1:0x48:ain0",
                "organ_class": "touch",
                "stub_id": "hardware_pad",
                "body_site": "torso_front",
                "approved_by": "human",
                "approved_at": "2026-09-10T00:00:00Z",
                "notes": "fixture",
            }
        ],
    )
    enum = FakeDeviceEnumerator(["i2c1:0x48:ain0"])
    bus = AfferentBus(map_path=p, enumerator=enum)
    evs = bus.poll()
    appeared = [e for e in evs if e.kind == "appeared"]
    assert appeared[0].disposition == "reserved"
    assert appeared[0].body_site == "torso_front"
    assert not hasattr(bus.poll, "stimuli")
    assert all(not hasattr(e, "modality") for e in evs)


def test_occupied_site_parks_second_device(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(
        p,
        [
            {
                "device_id": "i2c1:0x48:ain0",
                "organ_class": "touch",
                "stub_id": "hardware_pad",
                "body_site": "torso_front",
                "approved_by": "human",
            },
            {
                "device_id": "i2c1:0x49:ain0",
                "organ_class": "touch",
                "stub_id": "hardware_pad",
                "body_site": "torso_front",
                "approved_by": "hi",
            },
        ],
    )
    enum = FakeDeviceEnumerator(["i2c1:0x48:ain0"])
    bus = AfferentBus(map_path=p, enumerator=enum)
    bus.poll()
    enum.present = ["i2c1:0x48:ain0", "i2c1:0x49:ain0"]
    evs = bus.poll()
    second = [e for e in evs if e.kind == "appeared" and e.device_id == "i2c1:0x49:ain0"]
    assert second and second[0].disposition == "parked_site_occupied"


def test_gone_and_heartbeat(tmp_path):
    p = tmp_path / "map.yaml"
    _write_map(
        p,
        [
            {
                "device_id": "usb:widget:ch0",
                "organ_class": "touch",
                "stub_id": "hardware_pad",
                "body_site": "torso_front",
                "approved_by": "hi",
            }
        ],
    )
    enum = FakeDeviceEnumerator(["usb:widget:ch0"])
    bus = AfferentBus(map_path=p, enumerator=enum)
    bus.poll()
    beat = bus.poll()
    assert any(e.kind == "heartbeat_ok" and e.device_id == "usb:widget:ch0" for e in beat)
    enum.present = []
    gone = bus.poll()
    kinds = {e.kind for e in gone if e.device_id == "usb:widget:ch0"}
    assert "gone" in kinds
    assert "heartbeat_lost" in kinds


def test_missing_map_fail_open(tmp_path):
    missing = tmp_path / "nope.yaml"
    enum = FakeDeviceEnumerator(["i2c1:0x48:ain0"])
    bus = AfferentBus(map_path=missing, enumerator=enum, fail_open=True)
    evs = bus.poll()
    assert evs[0].kind == "appeared"
    assert evs[0].disposition == "parked_unmapped"


def test_kernel_afferent_is_not_a_sensor():
    k = ReflexKernel.from_config_path(
        CFG,
        overrides={
            "perception": {
                "enabled_sensors": ["hardware"],
                "hardware": {"enabled": True, "fail_open": True},
                "simulation": {"auto_events": False, "interactive": False},
            }
        },
    )
    assert k.afferent is not None
    names = list(k.perception.active)
    assert "afferent" not in names
    assert names.count("hardware") == 1
    k.start()
    try:
        k.step()
        assert k.perception.get("hardware") is not None
        assert isinstance(k.perception.get("hardware"), HardwareSensor)
    finally:
        k.stop()
