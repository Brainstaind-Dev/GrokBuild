# Vault — Software stack (Cortex / HIAgent / eval)

## Sensory Cortex

- Complementary HI packaging **above** RK Abstraction/Coherence  
- Embedded mode first (same process, low latency); service mode later  
- Public experience path: Saddle `/api/v1/experience`, sensations package  
- Tests: `SensoryCortex/tests/`  

## Abstraction → kernel.step (fixed 2026-08-15)

- `output.to_stimuli()` → **dicts**; `abstraction_to_stimuli()` → **Stimulus** objects  
- `kernel.step(extra_stimuli=…)` uses `normalize_stimuli()` — accepts both  
- Call sites (PythonAPI, Saddle drive, MCP) prefer **bridge** objects  
- Regression: `tests/test_abstraction_bridge.py`  
- Install: `pip install -e ".[all]"` (dev+server+audio+viz+mcp); pin **mcp&lt;2**

## Activation pattern v0 / rev 0.1 (2026-08-15)

- Plan: `Travelers/Docs/Activation_Pattern_Contract_v0_Plan.md`  
- Producer: `SensoryCortex/activation_pattern.py` + summarizer attach on `SensoryUpdate`  
- Samples: `data/activation_pattern_samples/` (+ `hi_feedback.md` from xAI pass)  
- Dump: `python SensoryCortex/scripts/dump_activation_patterns.py`  
- Compact address: `meta.feel_line` e.g. `feel: arousal=0.82 ear_L=0.92 orient=0.65`  
- **rev 0.1 (HI notes):** core zone `solar_plexus`; reflexes `jaw_clench`, `shoulder_elevation`, `breath_depth` (derived residuals); `meta.pattern_rev=0.1`

## HIAgent

- xAI chat over body: **embedded** or **Saddle**  
- Tree: `HIAgent/` (`body/`, `llm/`, `loop/`, `tools/`)  
- Standup helpers: `HIAgent/scripts/standup.*`  
- Endurance: `HIAgent/scripts/endurance_eval.py`  
- Eval artefacts: `data/hi_eval/`, catalogue in `Travelers/Docs/`  

## Key env

- `XAI_API_KEY` via `~/.config/embodi/env` (desktop + Pi)  

## UE avatar

Separate app — plan only: `Travelers/Docs/UE_Virtual_Avatar_Environment_Plan.md` (not blocking scaffold).
