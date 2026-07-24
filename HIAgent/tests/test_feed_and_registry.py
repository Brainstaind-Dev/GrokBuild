"""Unit tests for feed pause/resume and tool registry (no xAI / no RK required)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from HIAgent.loop.feed import FeedController
from HIAgent.tools.registry import ToolRegistry, compact_json
from HIAgent.config import HIAgentConfig


class MockBackend:
    name = "mock"

    def __init__(self):
        self.thoughts = []
        self.feel_calls = []

    def feel(self, force: bool = False):
        self.feel_calls.append(force)
        return {
            "ok": True,
            "force": force,
            "experience": {
                "affective_core": {
                    "overall_mood": "steady_attention",
                    "valence": 0.1,
                    "arousal": 0.4,
                    "dominance": 0.5,
                },
                "salient_sensations": [
                    {
                        "description": "Warm pressure",
                        "zone": "chest",
                        "intensity": 0.5,
                        "arousal_modulated_richness": 0.2,
                    }
                ],
                "delta_from_last": "stable",
                "trend": "relatively stable",
                "reflex_activity": ["autonomic"],
            },
        }

    def body_snapshot(self):
        return {"ok": True, "state": {"tick": 1}}

    def inject_thought(self, **kwargs):
        self.thoughts.append(kwargs)
        return {"dispatched": True, "command": kwargs}

    def send_reward(self, value, reason="", window_steps=6):
        return {"ok": True, "value": value}

    def inject_stimulus(self, **kwargs):
        return {"ok": True, **kwargs}

    def step(self, n=1):
        return {"ok": True, "steps": n}

    def begin_demo(self, name):
        return {"ok": True, "name": name}

    def end_demo(self, outcome=None):
        return {"ok": True}

    def recall(self, max_age_minutes=20):
        return {"ok": True, "items": []}

    def status(self):
        return {"backend": "mock", "started": True}


def test_compact_json_truncates():
    s = compact_json({"x": "a" * 100}, max_chars=50)
    assert "truncated" in s
    assert len(s) <= 50


def test_pause_resume_status():
    feed = FeedController(pause_poll_sec=0.05)
    r = feed.pause(reason="thinking")
    assert r["paused"] is True
    assert feed.is_paused
    assert feed.status()["pause_reason"] == "thinking"
    # Not due immediately
    assert feed.tick() is None
    time.sleep(0.06)
    prompt = feed.tick()
    assert prompt is not None
    assert "ready to resume" in prompt.lower()
    r2 = feed.resume(note="ok")
    assert r2["paused"] is False
    assert not feed.is_paused


def test_registry_pause_blocks_feel():
    cfg = HIAgentConfig(inject_cooldown_sec=0.0)
    backend = MockBackend()
    feed = FeedController(pause_poll_sec=30)
    reg = ToolRegistry(backend, cfg, feed_controller=feed)

    out = json.loads(reg.dispatch("feel", {}))
    assert out.get("ok") is True
    assert len(backend.feel_calls) == 1

    json.loads(reg.dispatch("pause_feed", {"reason": "quiet"}))
    out2 = json.loads(reg.dispatch("feel", {}))
    assert out2.get("paused") is True
    assert len(backend.feel_calls) == 1  # not called

    out3 = json.loads(reg.dispatch("feel", {"force": True}))
    assert out3.get("ok") is True
    assert len(backend.feel_calls) == 2

    json.loads(reg.dispatch("resume_feed", {}))
    out4 = json.loads(reg.dispatch("feel", {}))
    assert out4.get("ok") is True
    assert not out4.get("paused")


def test_registry_inject_and_status():
    cfg = HIAgentConfig(inject_cooldown_sec=0.0, max_step_n=5)
    backend = MockBackend()
    feed = FeedController()
    reg = ToolRegistry(backend, cfg, feed_controller=feed)

    r = json.loads(
        reg.dispatch(
            "inject_thought",
            {"emotion": "curiosity", "intensity": 0.6, "text": "hi"},
        )
    )
    assert r.get("dispatched") is True
    assert backend.thoughts

    r2 = json.loads(reg.dispatch("step", {"n": 99}))
    assert r2["steps"] == 5  # capped

    st = json.loads(reg.dispatch("get_status", {}))
    assert st.get("backend") == "mock"
    assert "feed" in st


def test_format_body_update():
    from HIAgent.llm.prompts import format_body_update

    text = format_body_update(
        {
            "ok": True,
            "experience": {
                "affective_core": {
                    "overall_mood": "calm_receptive",
                    "valence": 0.0,
                    "arousal": 0.3,
                    "dominance": 0.5,
                },
                "salient_sensations": [
                    {
                        "description": "A cool breeze",
                        "zone": "skin",
                        "intensity": 0.2,
                        "arousal_modulated_richness": 0.05,
                        "temporal_quality": "sustained",
                        "texture_qualities": ["soft"],
                    }
                ],
                "delta_from_last": "stable",
                "trend": "relatively stable",
                "reflex_activity": ["autonomic"],
                "token_estimate": 90,
            },
        }
    )
    assert "BODY UPDATE" in text
    assert "calm_receptive" in text
    assert "cool breeze" in text.lower() or "breeze" in text
