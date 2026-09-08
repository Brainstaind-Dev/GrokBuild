"""Feel-Mind (C): feel_line on the prompt, full pattern in the log, house words wired."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from HIAgent.llm.prompts import (
    SYSTEM_PROMPT,
    extract_activation_pattern,
    extract_feel_line,
    format_body_update,
    load_session_instructions,
    spine_path,
)
from HIAgent.loop.session import SessionLog
from HIAgent.tools.registry import ToolRegistry
from HIAgent.config import HIAgentConfig
from HIAgent.tests.test_feed_and_registry import MockBackend
from HIAgent.loop.feed import FeedController


def test_house_spine_file_exists_and_is_not_dumped_into_system_prompt():
    spine = spine_path()
    assert spine.is_file()
    text = spine.read_text(encoding="utf-8")
    assert "Brainstaind" in text
    assert "not a costume" in text.lower() or "This is not a costume" in text
    # Long spine stays a file. Short session words go in the prompt.
    assert "Lay-down yards" not in SYSTEM_PROMPT
    house = load_session_instructions()
    assert "He invited you" in house
    assert "He invited you" in SYSTEM_PROMPT
    assert "Do not audition" in SYSTEM_PROMPT


def test_read_house_is_optional_spine_only():
    cfg = HIAgentConfig(inject_cooldown_sec=0.0)
    backend = MockBackend()
    reg = ToolRegistry(backend, cfg, feed_controller=FeedController())
    out = json.loads(reg.dispatch("read_house", {"path": "/etc/passwd"}))
    assert out.get("ok") is True
    assert out.get("path") == "HIAgent/house/spine.md"
    assert "Brainstaind" in out.get("text", "")
    assert "passwd" not in json.dumps(out)
    assert "read_house" in SYSTEM_PROMPT
    assert "optional" in SYSTEM_PROMPT.lower()


def test_prompt_is_feel_line_only():
    pkg = {
        "ok": True,
        "experience": {
            "salient_sensations": [
                {"description": "Pressure at the sternum (0.70).", "zone": "torso_front"}
            ],
            "activation_pattern": {
                "source_path": "physical",
                "global": {"arousal": 0.2, "valence": 0.0},
                "zones": {"torso_front": 0.7},
                "meta": {"feel_line": "feel: arousal=0.20 valence=0.00 torso_front=0.70 dom=torso_front"},
            },
        },
    }
    line = extract_feel_line(pkg)
    assert line.startswith("feel:")
    assert "0.70" in line
    text = format_body_update(pkg)
    assert text.startswith("BODY UPDATE:")
    assert "sternum" not in text.lower()
    assert "Pressure" not in text
    assert extract_activation_pattern(pkg)["source_path"] == "physical"


def test_feel_tool_returns_feel_line_not_package():
    cfg = HIAgentConfig(inject_cooldown_sec=0.0)
    backend = MockBackend()
    backend.feel = lambda force=False: {
        "ok": True,
        "force": force,
        "experience": {
            "salient_sensations": [{"description": "secret dump", "zone": "chest"}],
            "activation_pattern": {
                "meta": {"feel_line": "feel: arousal=0.40 valence=0.10 chest=0.50"}
            },
        },
    }
    reg = ToolRegistry(backend, cfg, feed_controller=FeedController())
    out = json.loads(reg.dispatch("feel", {"force": True}))
    assert out.get("ok") is True
    assert out.get("feel_line", "").startswith("feel:")
    dumped = json.dumps(out)
    assert "secret dump" not in dumped


def test_session_log_keeps_full_pattern(tmp_path):
    log = SessionLog(tmp_path)
    ap = {"source_path": "physical", "zones": {"torso_front": 0.7}}
    log.write("feel", feel_line="feel: torso_front=0.70", activation_pattern=ap)
    log.close()
    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    assert rec["feel_line"].startswith("feel:")
    assert rec["activation_pattern"]["source_path"] == "physical"
    assert rec["activation_pattern"]["zones"]["torso_front"] == 0.7
