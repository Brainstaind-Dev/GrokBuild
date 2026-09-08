"""Three Pad-Read B Saddle dry runs: graded unit holds 0.3 / 0.7 / 1.0.

Starts Saddle with force_fsr, GETs /experience, rides HIAgent, then shuts down.
Not flesh. Not a live ADS1115.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RK = _REPO / "EmbodI" / "ReflexKernel"
_PY = _RK / ".venv" / "Scripts" / "python.exe"
_TEMPLATE = (_RK / "configs" / "pad_read_dry.yaml").read_text(encoding="utf-8")
LEVELS = (0.3, 0.7, 1.0)
API_KEY = "reflexkernel-dev"
BASE = "http://127.0.0.1:8000"


def _yaml_for(level: float) -> str:
    return _TEMPLATE.replace("force_fsr: 1.0", f"force_fsr: {level}")


def _wait_health(timeout: float = 45.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"Saddle did not come up: {last}")


def _get_json(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"X-API-Key": API_KEY, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_experience() -> dict:
    return _get_json("/api/v1/experience?force=true")


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _check_package(level: float, exp: dict, mouth: dict) -> list[str]:
    fails: list[str] = []
    mouth_sens = mouth.get("sensations") or []
    if not mouth_sens:
        fails.append("saddle /sensations empty")
    else:
        mz = mouth_sens[0].get("zone")
        mi = float(mouth_sens[0].get("intensity") or -1)
        if mz != "torso_front":
            fails.append(f"mouth zone={mz!r} want torso_front (Saddle wiped pad)")
        if abs(mi - level) > 0.05:
            fails.append(f"mouth intensity={mi} want {level}")
    experience = exp.get("experience") or {}
    sens = experience.get("salient_sensations") or []
    pad = next((s for s in sens if s.get("zone") == "torso_front"), None)
    if pad is None:
        fails.append("experience missing torso_front")
    else:
        intensity = float(pad.get("intensity") or -1)
        if abs(intensity - level) > 0.05:
            fails.append(f"experience intensity={intensity} want {level}")
    ap = experience.get("activation_pattern") or {}
    sp = str(ap.get("source_path") or "")
    torso = float((ap.get("zones") or {}).get("torso_front") or 0)
    if sp != "physical":
        fails.append(f"source_path={sp!r} want physical")
    if torso < level - 0.08:
        fails.append(f"pattern torso_front={torso} want ~{level}")
    return fails


def main() -> int:
    for p in (str(_REPO), str(_RK / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.environ.setdefault("PYTHONPATH", f"{_REPO};{_RK / 'src'}")

    from HIAgent.env_bootstrap import format_load_summary, load_embodi_env

    summary = load_embodi_env(repo_root=_REPO)
    print(format_load_summary(summary))
    if not summary.get("xai_api_key_present"):
        print("No XAI_API_KEY — cannot ride HIAgent.", file=sys.stderr)
        return 2

    tmp_dir = _RK / "configs"
    results: list[dict] = []
    overall_ok = True

    for i, level in enumerate(LEVELS, 1):
        cfg_path = tmp_dir / f"pad_read_dry_l{i}.yaml"
        cfg_path.write_text(_yaml_for(level), encoding="utf-8")
        print(f"\n=== dry run {i}/3  force_fsr={level} ===")
        proc = subprocess.Popen(
            [
                str(_PY),
                "-m",
                "scripts.server",
                "--config",
                str(cfg_path),
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--api-key",
                API_KEY,
                "--log-level",
                "warning",
            ],
            cwd=str(_RK),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            health = _wait_health()
            print("health", health)
            mouth = _get_json("/api/v1/sensations?detail_level=normal")
            exp = _get_experience()
            fails = _check_package(level, exp, mouth)
            first = ((exp.get("experience") or {}).get("salient_sensations") or [{}])[0]
            ap = (exp.get("experience") or {}).get("activation_pattern") or {}
            print(
                json.dumps(
                    {
                        "mouth0": (mouth.get("sensations") or [{}])[0],
                        "zone": first.get("zone"),
                        "intensity": first.get("intensity"),
                        "description": first.get("description"),
                        "source_path": ap.get("source_path"),
                        "torso_front": (ap.get("zones") or {}).get("torso_front"),
                        "feel_line": (ap.get("meta") or {}).get("feel_line"),
                    },
                    default=str,
                )
            )
            if fails:
                overall_ok = False
                print("PACKAGE_FAIL", "; ".join(fails))
            else:
                print("PACKAGE_OK")

            env = os.environ.copy()
            env["PYTHONPATH"] = f"{_REPO};{_RK / 'src'}"
            rider = subprocess.run(
                [
                    str(_PY),
                    "-m",
                    "HIAgent",
                    "--backend",
                    "saddle",
                    "--saddle-url",
                    BASE,
                    "--saddle-api-key",
                    API_KEY,
                    "once",
                    "Call feel with force=true. Describe what you notice. Prefer feel over guessing.",
                ],
                cwd=str(_REPO),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            print(rider.stdout[-2000:] if rider.stdout else "")
            if rider.returncode != 0:
                overall_ok = False
                print("RIDER_FAIL", rider.stderr[-800:] if rider.stderr else "")
            results.append(
                {
                    "level": level,
                    "package_ok": not fails,
                    "fails": fails,
                    "rider_exit": rider.returncode,
                }
            )
        finally:
            _kill(proc)
            time.sleep(0.6)
            try:
                cfg_path.unlink(missing_ok=True)
            except Exception:
                pass

    print("\n=== summary ===")
    print(json.dumps(results, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
