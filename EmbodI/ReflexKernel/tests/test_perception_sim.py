"""Simulation perception tests."""

from reflexkernel.config import load_config
from reflexkernel.perception.simulation import SimulationSensor
from reflexkernel.types import Stimulus


def test_simulation_inject_and_poll():
    s = SimulationSensor({"interactive": False, "auto_events": False})
    s.start()
    stim = s.inject("test_event", intensity=0.77)
    assert isinstance(stim, Stimulus)
    polled = s.poll()
    assert len(polled) == 1
    assert polled[0].data["kind"] == "test_event"
    s.stop()


def test_key_map_injection():
    s = SimulationSensor({"interactive": False, "auto_events": False})
    s.start()
    stim = s.inject_from_key("s")
    assert stim is not None
    assert "sudden" in str(stim.data.get("kind", ""))
    s.stop()
