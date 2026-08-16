1. Dependency & Compatibility Pass
On the desktop, confirm these still install and work cleanly:

Core: pydantic, pyyaml, numpy, rich
Optional but used: fastapi, uvicorn, websockets (for the Saddle)
Audio-related (for later MAX9814 work): whatever you’re currently using
Make sure nothing is pinned to very old versions that will break on the Pi’s Python 3.11+

Update pyproject.toml / requirements / extras so a fresh pip install -e . is reliable on both Windows and the Pi.
2. Fix the current integration break — **DONE 2026-08-15**
Abstraction dicts vs Stimulus: `normalize_stimuli()` in kernel.step; bridge preferred at call sites; `tests/test_abstraction_bridge.py` green (suite 27).
3. Git hygiene

Confirm .gitignore properly excludes:
.venv/
__pycache__/
*.pyc
any local logs, data dumps, or IDE files

Make sure all important source is actually tracked:
src/reflexkernel/ (including abstraction/)
scripts/
configs/
docs, tests if they exist

Do a clean git status and review what’s staged before committing.