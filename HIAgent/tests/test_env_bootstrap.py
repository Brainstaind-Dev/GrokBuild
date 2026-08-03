"""Unit tests for Embodi env file loading (no real secrets)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from HIAgent.env_bootstrap import load_embodi_env, parse_env_file


def test_parse_export_and_comments():
    text = """
# comment
export XAI_API_KEY=xai-testkey123
REFLEXKERNEL_API_KEY="dev-key"
EMPTY=
export FOO=bar # trailing
"""
    pairs = dict(parse_env_file(text))
    assert pairs["XAI_API_KEY"] == "xai-testkey123"
    assert pairs["REFLEXKERNEL_API_KEY"] == "dev-key"
    assert pairs["FOO"] == "bar"


def test_load_does_not_override_existing(tmp_path, monkeypatch):
    env_file = tmp_path / "env"
    env_file.write_text("export XAI_API_KEY=xai-from-file\n", encoding="utf-8")
    monkeypatch.setenv("EMBODI_ENV_FILE", str(env_file))
    monkeypatch.setenv("XAI_API_KEY", "xai-already-set")
    # point home away so we don't load real user env
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    monkeypatch.delenv("APPDATA", raising=False)

    summary = load_embodi_env(override=False, repo_root=tmp_path / "emptyrepo")
    assert os.environ["XAI_API_KEY"] == "xai-already-set"
    assert "XAI_API_KEY" in summary["keys_skipped_existing"]


def test_load_sets_from_file(tmp_path, monkeypatch):
    env_file = tmp_path / "env"
    env_file.write_text("export XAI_API_KEY=xai-from-file-abcdef\n", encoding="utf-8")
    monkeypatch.setenv("EMBODI_ENV_FILE", str(env_file))
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    monkeypatch.delenv("APPDATA", raising=False)

    summary = load_embodi_env(override=False, repo_root=tmp_path / "emptyrepo")
    assert os.environ.get("XAI_API_KEY") == "xai-from-file-abcdef"
    assert summary["xai_api_key_present"] is True
