"""Preference shelf — hers to write, not assigned.

Revise-able form notes she accepts before anything is worn.
Seed echo (starting notes only, not a print order): dark / messy / pale.
Not an STL. Not a costume forced onto a mesh.
Human pen still wins if Bob later signs a mesh.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DEFAULT_SHELF_NAME = "preference_shelf.yaml"

SEED_NOTES = [
    {
        "id": "echo-dark",
        "label": "dark",
        "kind": "form",
        "status": "starting_note",
        "accepted": False,
        "body": "",
    },
    {
        "id": "echo-messy",
        "label": "messy",
        "kind": "form",
        "status": "starting_note",
        "accepted": False,
        "body": "",
    },
    {
        "id": "echo-pale",
        "label": "pale",
        "kind": "form",
        "status": "starting_note",
        "accepted": False,
        "body": "",
    },
]


def default_shelf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / DEFAULT_SHELF_NAME


def seed_document() -> Dict[str, Any]:
    return {
        "version": 1,
        "kind": "preference_shelf",
        "title": "Preference shelf (hers to revise)",
        "notes": deepcopy(SEED_NOTES),
        "meta": {
            "not_stl": True,
            "not_costume": True,
            "human_pen_wins": True,
            "seed": "dark/messy/pale starting notes only — not a print order",
        },
    }


def load_shelf(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path is not None else default_shelf_path()
    if not p.is_file():
        doc = seed_document()
        save_shelf(doc, p)
        return doc
    with p.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"preference shelf must be a mapping: {p}")
    doc.setdefault("version", 1)
    doc.setdefault("kind", "preference_shelf")
    doc.setdefault("notes", [])
    if "meta" not in doc:
        doc["meta"] = seed_document()["meta"]
    return doc


def save_shelf(doc: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = Path(path) if path is not None else default_shelf_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
    return p


def list_notes(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(doc.get("notes") or [])


def _find_note(doc: Dict[str, Any], note_id: str) -> Dict[str, Any]:
    for n in doc.get("notes") or []:
        if isinstance(n, dict) and n.get("id") == note_id:
            return n
    raise KeyError(f"no preference note id={note_id!r}")


def revise_note(
    doc: Dict[str, Any],
    note_id: str,
    *,
    label: Optional[str] = None,
    body: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    note = _find_note(doc, note_id)
    if label is not None:
        note["label"] = label
    if body is not None:
        note["body"] = body
    if status is not None:
        note["status"] = status
    elif note.get("status") == "starting_note" and (
        label is not None or body is not None
    ):
        note["status"] = "revised"
    return note


def accept_note(doc: Dict[str, Any], note_id: str) -> Dict[str, Any]:
    note = _find_note(doc, note_id)
    note["accepted"] = True
    if note.get("status") in (None, "starting_note", "revised"):
        note["status"] = "accepted"
    return note


def add_note(
    doc: Dict[str, Any],
    *,
    note_id: str,
    label: str,
    body: str = "",
    kind: str = "form",
) -> Dict[str, Any]:
    notes = doc.setdefault("notes", [])
    for n in notes:
        if isinstance(n, dict) and n.get("id") == note_id:
            raise ValueError(f"note id already exists: {note_id}")
    note = {
        "id": note_id,
        "label": label,
        "kind": kind,
        "status": "revised",
        "accepted": False,
        "body": body,
    }
    notes.append(note)
    return note
