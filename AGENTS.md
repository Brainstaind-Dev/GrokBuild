# GrokBuild — Project Rules

## Repository layout

| Path | Purpose |
|------|---------|
| `EmbodI/ReflexKernel/` | Core embodied nervous-system kernel (Python package) |
| `EmbodI/*.md` | Architecture specs and layman guides |
| `EmbodI/*.xlsx` | Sensor platform trackers |
| `Travelers/` | Related travel/autonomic research assets |
| `ReflexKernel_Completion_Status_Report.md` | Status report — update only when asked |

## ReflexKernel architecture (layered, bottom-up)

```
Perception → Thought/Emotion Bridge → Reflex Core → Learner → Output/Actuation → Interface
```

Higher intelligence interacts via the **Interface** layer (Python API, stdio JSON-lines, WebSocket/FastAPI).

## Development principles

- **Simulation-first**: implement and test in simulation before requiring hardware.
- **Modularity**: each layer is swappable via config and interfaces.
- **Graceful degradation**: optional deps (vision, audio, ML, viz) must not break core paths.
- **Observability**: structured logs in `EmbodI/ReflexKernel/logs/` for stimuli, fusion, reflexes.
- **Tests required**: all ReflexKernel code changes must pass `pytest` in `EmbodI/ReflexKernel/tests/`.

## Common commands

```powershell
cd I:\grokbuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest tests/ -v
python -m scripts.demo          # interactive sim demo
```

Config profiles live in `EmbodI/ReflexKernel/configs/` (`sim_only.yaml` for hardware-free work).

## Workflow skills

Use bundled Grok skills for multi-step work:

- `/design` — architecture doc + PR plan for new subsystems
- `/execute-plan` — implement PR DAG (requires git branches)
- `/implement` — single feature with implement → review → fix loop
- `/check-work` — post-change verification
- `/reflexkernel-dev` — ReflexKernel-specific layer-aware workflow

## What not to do

- Do not commit `.venv/`, `logs/`, `data/`, or `cloudflared*.exe`.
- Do not update status reports or tracker spreadsheets unless explicitly asked.
- Do not require webcam/microphone/RPi hardware for feature development.