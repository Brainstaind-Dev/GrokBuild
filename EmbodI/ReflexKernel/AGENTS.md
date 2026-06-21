# ReflexKernel — Module Rules

## Package layout

```
src/reflexkernel/
  perception/       # Sensors (SimulationSensor primary; vision/audio stubs)
  bridge/           # Thought/emotion fusion → AffectiveContext
  reflex_core/      # Fast involuntary reflexes + state machines
  learner/          # Imitation + RL, persisted to data/
  output/           # VirtualBody, pygame avatar, structured logger
  interface/        # PythonAPI, stdio JSON-lines, FastAPI/WebSocket server
  abstraction/      # Feature extraction layer (Event + Feature schema)
  types.py          # Stimulus, AffectiveContext, ReflexTrace, etc.
```

## Change workflow

1. Read the relevant layer before editing — do not cross layer boundaries without reason.
2. Prefer extending `SimulationSensor` / `VirtualSensorSimulator` over adding hardware deps.
3. Add or update tests in `tests/test_<layer>.py` for every behavior change.
4. Run `python -m pytest tests/ -v` from this directory before finishing.
5. Use `configs/sim_only.yaml` for verification without peripherals.

## Config

- Default: `configs/default.yaml`
- Simulation-only: `configs/sim_only.yaml`
- Optional feature groups in `pyproject.toml`: `viz`, `vision`, `audio`, `ml`, `server`, `dev`

## Interface contract (higher intelligence)

Stdio / WebSocket messages use JSON-lines. Common types:

- `thought_seed` — affective priming from higher mind
- `begin_demo` / `end_demo` — imitation learning episodes
- `reward` — RL signal for recent behavior
- `inject_stimulus` — direct perception input (sim or abstracted)

## Testing

| Test file | Covers |
|-----------|--------|
| `test_types.py` | Pydantic models and serialization |
| `test_perception_sim.py` | SimulationSensor |
| `test_fusion.py` | Thought/emotion bridge |
| `test_reflex_core.py` | Reflex primitives and state machines |
| `test_learner.py` | Imitation + RL persistence |

## Key docs

- `README.md` — quick start
- `PLAN.md` — full architecture diagram
- `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md` — abstraction layer plan
- `docs/REMOTE_INTERFACE_ENHANCEMENT_PLAN.md` — remote server enhancements
- `VERIFICATION.md` — manual verification checklist