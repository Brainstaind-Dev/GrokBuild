---
name: reflexkernel-dev
description: >
  ReflexKernel layer-aware development workflow for the Embodied Autonomic System.
  Use when editing ReflexKernel, working on perception/reflex/learner/interface layers,
  abstraction layer features, or when the user says "reflexkernel", "embodied autonomic",
  or runs /reflexkernel-dev.
---

# ReflexKernel Dev Workflow

You are working on **ReflexKernel** at `EmbodI/ReflexKernel/`. Follow this workflow for every change.

## Before editing

1. Read `AGENTS.md` in this directory and the relevant layer's source under `src/reflexkernel/`.
2. If the change touches the abstraction layer, read `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md`.
3. If the change touches remote access, read `docs/REMOTE_INTERFACE_ENHANCEMENT_PLAN.md`.
4. Identify which layer owns the change: perception, bridge, reflex_core, learner, output, interface, or abstraction.

## Implementation rules

- **Simulation-first**: use `SimulationSensor` / virtual paths; do not require hardware.
- **Layer boundaries**: do not leak layer concerns across modules without an explicit interface.
- **Optional deps**: guard imports for viz, vision, audio, ml, server extras.
- **Persistence**: learner data goes under `data/` (gitignored); do not hardcode absolute paths outside the package.

## After editing

1. Add or update tests in `tests/test_<layer>.py`.
2. Run from `EmbodI/ReflexKernel/`:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/ -v
   ```
3. For behavioral changes, run the sim demo with `configs/sim_only.yaml`:
   ```powershell
   .\.venv\Scripts\python.exe -m scripts.demo
   ```
4. Inspect structured logs in `logs/` if behavior is unexpected.
5. Do **not** update `ReflexKernel_Completion_Status_Report.md` unless the user asks.

## Verification checklist

- [ ] All existing pytest tests pass
- [ ] New behavior has a test
- [ ] No new hard dependency on hardware
- [ ] Config changes documented in `configs/` if applicable
- [ ] Interface JSON message types remain backward-compatible (or migration noted)

## Multi-layer features

For changes spanning multiple layers, use `/design` first to produce a design doc and PR plan, then `/execute-plan` or `/implement` depending on scope.