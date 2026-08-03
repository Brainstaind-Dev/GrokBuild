"""
Load Embodi secrets/config from standard user locations into os.environ.

Supported files (first match wins per variable; does not override existing env):

  1. $EMBODI_ENV_FILE (explicit path)
  2. ~/.config/embodi/env          (Linux / Pi / macOS / Windows home)
  3. %APPDATA%/embodi/env         (Windows extra)
  4. <repo>/.env                  (project-local, gitignored)

File format (shell-friendly):

  # comment
  export XAI_API_KEY=xai-...
  XAI_API_KEY=xai-...
  REFLEXKERNEL_API_KEY=reflexkernel-dev

Never commit these files. Prefer chmod 600 on Unix.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Variables we care about for Embodi / HIAgent (others in the file are still loaded)
KNOWN_KEYS = (
    "XAI_API_KEY",
    "REFLEXKERNEL_API_KEY",
    "REFLEXKERNEL_CONFIG",
    "EMBODI_ROOT",
)

_LINE_RE = re.compile(
    r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$"""
)


def _strip_value(raw: str) -> str:
    val = raw.strip()
    if not val:
        return ""
    # strip matching quotes
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    # inline comment for unquoted values: KEY=foo # bar
    if " #" in val and not val.startswith(("'", '"')):
        val = val.split(" #", 1)[0].rstrip()
    return val


def parse_env_file(text: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        pairs.append((key, _strip_value(raw)))
    return pairs


def candidate_env_files(repo_root: Optional[Path] = None) -> List[Path]:
    paths: List[Path] = []
    explicit = os.environ.get("EMBODI_ENV_FILE")
    if explicit:
        paths.append(Path(explicit).expanduser())

    home = Path.home()
    paths.append(home / ".config" / "embodi" / "env")

    # Windows roaming app data
    appdata = os.environ.get("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "embodi" / "env")

    if repo_root is None:
        # HIAgent/env_bootstrap.py → repo root
        repo_root = Path(__file__).resolve().parents[1]
    paths.append(repo_root / ".env")
    paths.append(repo_root / ".env.local")

    # de-dupe while preserving order
    seen = set()
    out: List[Path] = []
    for p in paths:
        try:
            key = str(p.resolve()) if p.exists() else str(p)
        except OSError:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def load_embodi_env(
    *,
    override: bool = False,
    repo_root: Optional[Path] = None,
) -> dict:
    """
    Load env files into os.environ.

    By default does **not** override variables already set (so shell export wins).
    Returns a summary dict for logging (never includes secret values).
    """
    loaded_from: List[str] = []
    keys_set: List[str] = []
    keys_skipped_existing: List[str] = []
    missing_files: List[str] = []

    for path in candidate_env_files(repo_root=repo_root):
        if not path.is_file():
            missing_files.append(str(path))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        pairs = parse_env_file(text)
        if not pairs:
            continue
        loaded_from.append(str(path))
        for key, val in pairs:
            if not key:
                continue
            if key in os.environ and os.environ.get(key) and not override:
                keys_skipped_existing.append(key)
                continue
            os.environ[key] = val
            keys_set.append(key)

    # status helpers (safe)
    xai = os.environ.get("XAI_API_KEY", "")
    return {
        "loaded_from": loaded_from,
        "keys_set": sorted(set(keys_set)),
        "keys_skipped_existing": sorted(set(keys_skipped_existing)),
        "xai_api_key_present": bool(xai.startswith("xai-") or (len(xai) > 20)),
        "xai_api_key_len": len(xai) if xai else 0,
        "searched": [str(p) for p in candidate_env_files(repo_root=repo_root)],
    }


def ensure_xai_key(*, require: bool = False) -> bool:
    """Load env files then check XAI_API_KEY. Optionally raise."""
    summary = load_embodi_env()
    ok = bool(summary.get("xai_api_key_present"))
    if require and not ok:
        paths = "\n  ".join(summary.get("searched") or [])
        raise RuntimeError(
            "XAI_API_KEY is not set after loading Embodi env files.\n"
            "Create one of:\n"
            "  ~/.config/embodi/env   with:  export XAI_API_KEY=xai-...\n"
            "  (Windows) %USERPROFILE%\\.config\\embodi\\env\n"
            "  or set the user environment variable XAI_API_KEY\n"
            f"Searched:\n  {paths}"
        )
    return ok


def format_load_summary(summary: dict) -> str:
    lines = []
    if summary.get("loaded_from"):
        lines.append("Loaded env from: " + ", ".join(summary["loaded_from"]))
    else:
        lines.append("No Embodi env file found (using process environment only)")
    if summary.get("keys_set"):
        lines.append("Set keys: " + ", ".join(summary["keys_set"]))
    if summary.get("xai_api_key_present"):
        lines.append(f"XAI_API_KEY: present (len={summary.get('xai_api_key_len')})")
    else:
        lines.append("XAI_API_KEY: not set")
    return "\n".join(lines)
