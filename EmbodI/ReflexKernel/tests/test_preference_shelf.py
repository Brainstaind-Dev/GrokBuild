"""Tests for preference shelf."""
from __future__ import annotations

from pathlib import Path

from reflexkernel.preference_shelf import (
    accept_note,
    add_note,
    list_notes,
    load_shelf,
    revise_note,
    save_shelf,
    seed_document,
)


def test_seed_has_dark_messy_pale():
    doc = seed_document()
    labels = [n["label"] for n in doc["notes"]]
    assert labels == ["dark", "messy", "pale"]
    assert all(n["status"] == "starting_note" for n in doc["notes"])
    assert all(n["accepted"] is False for n in doc["notes"])
    assert doc["meta"]["not_stl"] is True
    assert doc["meta"]["human_pen_wins"] is True


def test_load_missing_writes_seed(tmp_path: Path):
    path = tmp_path / "preference_shelf.yaml"
    doc = load_shelf(path)
    assert path.is_file()
    assert [n["label"] for n in list_notes(doc)] == ["dark", "messy", "pale"]


def test_revise_and_accept_roundtrip(tmp_path: Path):
    path = tmp_path / "preference_shelf.yaml"
    doc = load_shelf(path)
    revise_note(doc, "echo-dark", body="soft charcoal, not costume")
    note = accept_note(doc, "echo-dark")
    assert note["accepted"] is True
    assert note["status"] == "accepted"
    assert note["body"] == "soft charcoal, not costume"
    save_shelf(doc, path)
    again = load_shelf(path)
    dark = next(n for n in again["notes"] if n["id"] == "echo-dark")
    assert dark["accepted"] is True
    assert dark["body"] == "soft charcoal, not costume"


def test_add_note(tmp_path: Path):
    path = tmp_path / "preference_shelf.yaml"
    doc = load_shelf(path)
    add_note(doc, note_id="echo-soft", label="soft", body="optional")
    labels = [n["label"] for n in list_notes(doc)]
    assert "soft" in labels
