# Embodied Autonomic System — Technical Design & Current Implementation

**Project**: Embodied Autonomic System (built on ReflexKernel)  
**Location**: `I:\GrokBuild\EmbodI\ReflexKernel`  
**Audience**: Co-developers / higher intelligences working at the systems level  
**Repository**: [https://github.com/Brainstaind-Dev/GrokBuild](https://github.com/Brainstaind-Dev/GrokBuild)  
**Last Updated**: 2026-06-23 (Bidirectional saddle loop confirmed per user clarification; input via saddle drives sensations + viz; chrome tab feedback gap noted; viz prepped for imagery model)  
**Status**: Bidirectional foundation available: senses/virtual → abstraction (sensations) → Saddle (prominent output); HI injects stimuli via Saddle (drives sim, produces sensations, affects kernel/viz). Richer Sensation output exposed in /state, /sensations, MCP tools (capped, normal default). Visualization now receives sensations from saddle inputs. Chrome-tab automatic feedback of sensations is pull-only currently (user exploring xAI API). Full support for both input styles. Docs updated. Tests pass. Imagery for custom viz model pending.

---

## Vision & Goals

The Embodied Autonomic System provides a reusable, grounded "nervous system" layer that higher intelligences (LLMs, agents, or custom AIs) can "saddle." 

It handles:
- Low-level sensory input (physical hardware or virtual)
- Fast involuntary reflexes
- Feature extraction
- **Sensation coherence** — turning raw signals into unified, natural bodily experiences
- Clean teachable interface for the higher intelligence

**Core Principle** (from Sensation Processing Pipeline): **"Combine first, then amplify."**

Raw or overly granular data should never reach the higher intelligence by default. The system synthesizes coherent sensations (e.g., "Warm, slow stroking along my inner thigh") before applying sensitivity and arousal modulation.

This work supports both physical embodiment (RPi5 + ESP32 + sensors) and virtual simulation (for development and testing).

---

## High-Level Architecture

```
Higher Intelligence (Grok / LLM / Agent)
          ⇅
Agent Tooling Layer                    ← NEW (June 2026)
  • ReflexKernel MCP server (stdio, 8 tools)
  • GitHub / Git / Puppeteer / Filesystem MCPs
  • Grok hooks (auto-pytest), skills, AGENTS.md
          ⇅
Saddle / Interface Layer
  • PythonAPI, Stdio JSON-lines, FastAPI+WS remote server
  (thought seeds, rewards, demos, coherent sensations, state summaries)
          ↑
ReflexKernel
  (Reflex Core + Learner + Affective Bridge)
  • Receives: Events + Features (for reflexes & learning)
          ↑
Feature Extraction Layer (Abstraction)
  • Raw sensor data → Events + Features
          ↑
Sensation Coherence Layer ← NEW (key addition)
  • Combines features into natural sensations
          ↑
Signal Enhancement
  • Sensitivity Map (zone-based)
  • Arousal Multiplier (dynamic, especially erogenous zones)
          ↑
Detail Level Filter
  • Normal (default for HI)
  • Enhanced
  • Diagnostic (full metrics)
          ↑
Raw / Virtual Perception Layer
  (FSR, MPU6050, Microphone, DHT22, etc.)
```

**Bidirectional Loop via Saddle (core goal per user alignment)**:
- **Output direction** (senses → HI): Virtual/hardware sensors → VirtualSensorSimulator/process() → AbstractionOutput (events/features for ReflexKernel + coherent `Sensation` objects + `BodyStateSummary` for HI) → Saddle (prominently exposed in /api/v1/state, /api/v1/sensations, MCP kernel_status/read_affective_state/get_coherent_sensations). HI "feels" the rich sensations (description + structured fields like arousal_modulated_richness, zone_character, temporal_quality, texture_qualities).
- **Input direction** (HI → system): HI injects stimuli/thoughts via Saddle (POST /api/v1/thought, /api/v1/stimulus, step; or MCP inject_*/step). These drive the shared VirtualSimulator (producing sensations), feed stimuli to kernel (affective + reflexes), and update visualization. Injected data can simulate sensor input and produce rich sensations on the output side (full support for both).

The Saddle (FastAPI + MCP + PythonAPI) is the bidirectional interface. Dual paths preserved: low-level stimuli for ReflexKernel core; rich sensations for HI.

**Current limitation (Grok Web / chrome tab path)**: The Tampermonkey bridge is currently one-way (#states → body). Automatic feedback of rich sensations back into the Grok chat UI or model context within the browser tab is not yet implemented (pull via API/MCP works; user exploring xAI API for tighter integration).

**Visualization reflects sensations**: When saddle input occurs, abstraction is driven, sensations attached (_last_sensations), and PygameVisualizer overlays description/zone/richness + updates body state from resulting stimuli/actions. Prepares for full custom avatar model when imagery provided.

---

## Core Components

### 1. ReflexKernel (Existing Foundation)
Standard layered architecture:
- **Perception**: `Sensor` base + `SimulationSensor` (keyboard + programmatic) + stubs for real hardware.
- **Thought/Emotion Bridge**: Fuses stimuli + thought seeds into `AffectiveContext`.
- **Reflex Core**: Fast involuntary reactions via state machines + procedural primitives (flinch, tension, orient, etc.).
- **Learner**: Imitation (demos) + reinforcement (rewards). Persistent store.
- **Output**: Virtual actuators + Pygame avatar + structured logging.
- **Interface**: PythonAPI, Stdio, productionized remote server (FastAPI + WebSocket with auth, CORS, rate limiting), and **MCP server** (`mcp_server.py`) for Grok/agent stdio tooling. Richer Sensation output is now surfaced prominently by default in /state, /sensations, kernel_status, read_affective_state (capped at 3, normal detail).

The kernel remains unchanged in its core contract. The abstraction layer feeds it via the existing `Stimulus` path. Agents now have a **first-class MCP path** that wraps `PythonAPI` without requiring JSONL log parsing or manual server startup.

**Verification (21 June 2026)**: 15/15 pytest tests; GitHub Actions CI green; `grok mcp doctor` reports 5/5 MCP servers healthy.

### 2. Feature Extraction Layer (Current `abstraction/`)
Located in `src/reflexkernel/abstraction/`.

**Key Files**:
- `schema.py`: All Pydantic models + Tier 1 canonical constants.
- `base.py`: `AbstractFeatureExtractor`.
- `virtual.py`: `VirtualSensorSimulator` (Tier 1 sensors with realistic physics).
- `coherence.py`: **Sensation Coherence Layer**.
- `bridge.py`: Dual-path conversion (`abstraction_to_stimuli` + sensation helpers).
- `hardware.py`: Stubs for future real sensors (same shape as virtual).

**Core Models** (in `schema.py`):
- `SensorEvent`: Discrete (e.g. `impact`, `sudden_loud_sound`).
- `Feature`: Continuous (e.g. `contact_intensity`, `motion_energy`, `acoustic_energy`).
- `Sensation`: Coherent natural description for the higher intelligence (new primary output).
- `BodyStateSummary`: Higher-level state (now enhanced with `dominant_sensation`, `active_sensations`, zone awareness).
- `AbstractionOutput`: Container with `events`, `features`, `sensations`, `state_summary`, `detail_level`.
- `DetailLevel` enum: `NORMAL`, `ENHANCED`, `DIAGNOSTIC`.

**Tier 1 Canonical Constants** (for consistency):
- FSR: `FSR_CONTACT_START`, `FSR_IMPACT`, `FSR_CONTACT_INTENSITY`, `FSR_PRESSURE_GRADIENT`, etc.
- MPU6050: `MPU_SUDDEN_MOVEMENT`, `MPU_MOTION_ENERGY`, `MPU_POSTURE_STABILITY`, etc.
- Microphone: `MIC_SUDDEN_LOUD_SOUND`, `MIC_ACOUSTIC_ENERGY`, etc.
- DHT22: `DHT_AMBIENT_TEMP`, `DHT_BODY_TEMP`, etc.

**Sensitivity Mapping**:
- Full female body map (from `FSM.md`): High sensitivity zones (clitoris, nipples, anus with strong arousal dependence, inner thighs, neck, etc.).
- `get_zone_sensitivity(zone, arousal)` function applies base multipliers + dynamic arousal boost.
- Feet intentionally low (0.2) to avoid tickling.

### 3. Sensation Coherence Layer (`coherence.py`)
New dedicated layer.

- `combine_into_sensations(events, features, arousal, detail_level, primary_zone)`:
  - Intelligently merges signals.
  - Generates natural language descriptions.
  - Applies zone sensitivity + arousal modulation.
- `build_enhanced_body_state(sensations, base_summary)`:
  - Derives richer `BodyStateSummary` from the coherent sensations (rather than raw aggregates).

Current implementation is rule-based/template-driven (good for simulation and iteration). Designed to be replaceable with more sophisticated methods later (including potential neural pattern paths).

**Example Output** (from virtual sim):
> "Firm, warm pressure spreading slowly across my upper inner thigh, with a gentle stroking quality..."

### 4. Virtual Sensor Simulation
`VirtualSensorSimulator` (in `virtual.py`):
- Generates realistic Tier 1 data (FSR 4x array, MPU6050, Microphone, DHT22).
- Realistic physics, noise, drift.
- Supports scripted scenarios (`impact`, `gentle_contact`, `sudden_movement`, `loud_noise`).
- Now fully integrated with coherence + sensitivity.
- Can be driven standalone or via the existing `SimulationSensor`.

This is the primary development vehicle until physical hardware arrives (RPi5 + ESP32).

### 5. Dual Output & Integration Points
- **For ReflexKernel**: `abstraction_to_stimuli()` → list of `Stimulus` (fed via `kernel.step(extra_stimuli=...)`).
- **For Higher Intelligence / Saddle**: `get_coherent_sensations()` + enhanced `state_summary`. These are the "felt" experiences.
- The remote server (FastAPI + WS) remains the network Saddle for external clients.
- The **ReflexKernel MCP server** is the in-process Saddle for Grok and local agents (simulation-first, headless).

### 6. ReflexKernel MCP Server (`mcp_server.py`) — Agent Integration

**Purpose**: Expose the kernel as MCP tools over stdio so Grok (or any MCP host) can drive perception, fusion, reflexes, and learning without custom wrappers.

**Stack**:
- Python `mcp` SDK (`FastMCP`)
- Singleton `KernelSession` (thread-locked, lazy-init, persists across tool calls within one Grok session)
- Wraps `ReflexKernel.from_config_path()` + `PythonAPI`
- Default config: `configs/mcp_headless.yaml` (overridable via `REFLEXKERNEL_CONFIG` env var)

**Headless profile design** (`mcp_headless.yaml`):
| Setting | Value | Rationale |
|---------|-------|-----------|
| `visualization` | `none` | No pygame window in agent sessions |
| `simulation.interactive` | `false` | No keyboard polling |
| `simulation.auto_events` | `false` | Deterministic agent-driven stimuli only |
| `log_structured` | `true` | JSONL logs for `query_logs` tool |
| `learner.enabled` | `true` | Rewards and demos persist to `data/learned_sim` |

**Tool surface** (8 tools, protocol 2025-06-18):

| Tool | Kernel API used | Returns |
|------|-----------------|---------|
| `kernel_status` | `get_state()` | Tick, context summary, config path |
| `inject_stimulus` | `inject_stimulus()` + `kernel.step()` | Actions, context, traces per tick |
| `read_affective_state` | `get_state()` | Full serializable snapshot |
| `get_reflex_traces` | `kernel.step()` × N | Accumulated `ReflexTrace` dicts |
| `inject_thought_seed` | `inject_thought()` + `kernel.step()` | Context + traces after priming |
| `run_demo_episode` | Scripted stimulus/thought sequences | Timeline of per-tick state |
| `query_logs` | Reads `logs/reflexkernel_*.jsonl` | Filtered JSONL records |
| `send_reward` | `reward()` | RL signal acknowledgment |

**Built-in demo scenarios** (`run_demo_episode`):

| Scenario | Script |
|----------|--------|
| `sudden_sound` | High-intensity `sudden_sound` stimulus |
| `friendly_greet` | Curiosity thought seed + `friendly_wave` |
| `threat_approach` | Startle seed + `threat_face` |
| `calm_recovery` | `relaxing_sound` + `calm` sequence |

**Session semantics**: One kernel instance per MCP server process. State (tick count, affective context, learner biases) accumulates until the Grok session ends and the MCP subprocess is restarted. This matches agent multi-turn workflows.

**Install & entrypoints**:
```powershell
pip install -e ".[mcp]"
python -m reflexkernel.mcp_server          # standalone stdio
reflexkernel-mcp                           # console script (same)
```

**Grok project wiring** (`.grok/config.toml`):
```toml
[mcp_servers.reflexkernel]
command = "I:\\grokbuild\\EmbodI\\ReflexKernel\\.venv\\Scripts\\python.exe"
args = ["-m", "reflexkernel.mcp_server"]
env = { REFLEXKERNEL_CONFIG = "I:\\grokbuild\\EmbodI\\ReflexKernel\\configs\\mcp_headless.yaml" }
```

### 7. Grok Build Workspace Infrastructure

The parent repo `I:\GrokBuild` provides the development harness around ReflexKernel:

```
I:\GrokBuild\
├── AGENTS.md                          # Repo-wide rules (architecture, commands, workflow skills)
├── .grok/
│   ├── config.toml                    # Project MCP servers (5)
│   ├── hooks/reflexkernel-pytest.json # PostToolUse → pytest on .py edits
│   └── skills/reflexkernel-dev/       # Layer-aware dev workflow skill
├── .github/workflows/test.yml         # CI: pytest on push/PR (Windows, Python 3.12)
├── EmbodI/ReflexKernel/               # Package root (this system)
└── ReflexKernel_Completion_Status_Report.md
```

**MCP ecosystem** (all verified via `grok mcp doctor`):

| Server | Implementation | Scoped to |
|--------|----------------|-----------|
| `reflexkernel` | Custom Python (`mcp_server.py`) | In-process kernel |
| `git` | `mcp-server-git` (PyPI) | `I:\grokbuild` repo |
| `github` | `@modelcontextprotocol/server-github` | GitHub API (PAT via `GITHUB_TOKEN`) |
| `puppeteer` | `@modelcontextprotocol/server-puppeteer` | Browser QA |
| `filesystem` | `mcp-server-filesystem` (global npm) | `EmbodI/ReflexKernel/data` |

**Agent workflow loop** (closed):
1. Grok reads `AGENTS.md` + `reflexkernel-dev` skill at session start
2. Edits code → pytest hook fires automatically
3. Uses `reflexkernel` MCP to verify behavior end-to-end
4. Uses `git`/`github` MCP for commits, PRs, CI status
5. Push triggers GitHub Actions → 15 tests on remote runner

**Trust model**: Project hooks require entry in `~/.grok/trusted-hook-projects`. MCP secrets (GitHub PAT) live in user-level env vars, never in committed config (`${GITHUB_TOKEN}` expansion).

---

## Current File Structure (Relevant Parts)

```
src/reflexkernel/
├── abstraction/
│   ├── __init__.py          # Public exports (Sensation, DetailLevel, coherence helpers, etc.)
│   ├── schema.py            # All models + SensitivityMap + constants
│   ├── coherence.py         # Sensation Coherence Layer
│   ├── virtual.py           # VirtualSensorSimulator + Tier 1 mappings
│   ├── bridge.py            # Dual-path conversion
│   ├── base.py              # AbstractFeatureExtractor
│   └── hardware.py          # Future real hardware stubs
├── perception/              # Existing (SimulationSensor feeds abstraction)
├── kernel.py                # Core (receives events/features via stimuli)
├── interface/               # Remote server (Saddle) + PythonAPI + Stdio
├── mcp_server.py            # MCP stdio server (Grok/agent tooling) ← NEW
└── types.py                 # Original ReflexKernel types (Stimulus, etc.)

configs/
├── sim_only.yaml            # Interactive sim + pygame (human demos)
├── mcp_headless.yaml        # Agent/MCP sessions (no viz, deterministic) ← NEW
└── default.yaml             # Full profile with optional ML/vision

tests/
├── test_*.py                # Core layer tests (10)
└── test_mcp_server.py       # MCP session + tool tests (5) ← NEW
```

Scripts:
- `scripts/demo.py` — Live abstraction + coherent sensations + pygame.
- `scripts/server.py` — Remote server entrypoint.
- `scripts/remote_client.py` — Example client for higher intelligences.

Entrypoints (`pyproject.toml`):
- `reflexkernel-demo` → interactive demo
- `reflexkernel-mcp` → MCP stdio server

---

## Design Principles (Enforced)

1. **Combine first, then amplify** (SensPP.md).
2. **Dual paths** — Never break ReflexKernel compatibility while building the rich experience for the higher intelligence.
3. **Zone-aware + Arousal-modulated** — Especially important for female-form sensitivity (FSM.md).
4. **Detail Level control** — Higher intelligence can request different granularities.
5. **Coherent sensations > raw metrics** for the Saddle (Feedback613).
6. **Simulation-primary** for rapid iteration, with identical shapes for future hardware.
7. **Observable** — Structured events, logs, and clear separation of concerns.

---

## How to Explore / Run (Developer Level)

### Environment setup

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev,mcp,viz]"    # tests + MCP + pygame demo
python -m pytest tests/ -v         # expect 15 passed
```

### Integration paths (choose by use case)

| Path | When to use | Entry |
|------|-------------|-------|
| **MCP (Grok/agents)** | Automated iteration, tool-calling loops | `python -m reflexkernel.mcp_server` or Grok `/mcps` |
| **PythonAPI** | In-process agent scripts, notebooks | `PythonAPI(ReflexKernel.from_config_path(...))` |
| **Stdio JSON-lines** | Piped LLM wrappers | `StdioAdapter(kernel).run()` |
| **Remote server** | Network clients, multi-user | `python -m scripts.server` |
| **Interactive demo** | Human exploration, abstraction layer | `python -m scripts.demo` |

1. **Basic Demo with Abstraction**:
   ```powershell
   python -m scripts.demo
   ```
   Keys `i/c/m/l` trigger abstraction scenarios. Watch `[ABSTRACTION]` and `[SENSATION]` output.

2. **Standalone Virtual Abstraction**:
   ```python
   from reflexkernel.abstraction import VirtualSensorSimulator, get_coherent_sensations
   sim = VirtualSensorSimulator()
   raw = sim.read_all()
   output = sim.process(raw)
   sensations = get_coherent_sensations(output)
   for s in sensations:
       print(s.description, s.zone, s.intensity)
   ```

3. **MCP Server (agent-driven kernel control)**:
   ```powershell
   $env:REFLEXKERNEL_CONFIG = "configs/mcp_headless.yaml"
   python -m reflexkernel.mcp_server
   ```
   In Grok: *"Use reflexkernel MCP to run sudden_sound demo and report reflex traces."*

4. **Remote Saddle (network clients)**:
   ```powershell
   python -m scripts.server
   ```
   Use `scripts/remote_client.py` or `/docs` Swagger UI. Future: expose `get_coherent_sensations(detail_level=...)`.

5. **CI / regression**:
   Push to `master` → GitHub Actions runs pytest on `windows-latest` / Python 3.12.

See also:
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md` (for high-level usage)
- `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md` (detailed phased plan, including this course correction)
- `I:\GrokBuild\ReflexKernel_Completion_Status_Report.md` (living status with addendum)

---

## Current Status & Next Priorities

**What is solid** (verified 21 June 2026):

| Area | Status |
|------|--------|
| ReflexKernel core + remote interface | v0.2 Alpha, backward compatible |
| Abstraction + Sensation Coherence | Rule-based, simulation-live |
| Female Sensitivity Map + arousal modulation | Implemented per FSM.md |
| Dual-path architecture (Stimulus + Sensation) | Operational |
| ReflexKernel MCP server | 8 tools, headless config, 5 tests |
| Grok Build harness | MCP ×5, hooks, skills, AGENTS.md, memory |
| Test suite | **15/15** local + CI |
| Git + GitHub | `Brainstaind-Dev/GrokBuild`, Actions green |

**Integration maturity**:

```
PythonAPI / Stdio     ████████████  Complete
Remote FastAPI+WS     ███████████░  Productionized; sensation export pending
MCP (Grok/agents)     ███████████░  Core kernel tools live; abstraction tools pending
Hardware (RPi/ESP32)  ██░░░░░░░░░░  Stubs only
```

**Active / Recommended Next**:

1. **Extend MCP server** with abstraction-layer tools: `run_virtual_scenario`, `get_coherent_sensations`, `set_detail_level`.
2. **Extend remote server** to natively surface `Sensation` objects at requested `DetailLevel`s.
3. **Improve coherence rules** — better zone inference, richer combination templates.
4. **Hardware protocol sketch** — ESP32 ↔ RPi5 aggregation, pinout alignment with tracker spreadsheets.
5. **Pattern-level / neural activation path** — preparation only (future).
6. **Live-server MCP mode** — optional MCP transport that connects to running FastAPI instance instead of in-process kernel.

---

## References

**Architecture & spec**:
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System.md` (parent spec)
- `I:\GrokBuild\EmbodI\RscCom\Feedback613.md` (course correction)
- `I:\GrokBuild\EmbodI\RscCom\FSM.md` (Female Sensitivity Mapping v1.0)
- `I:\GrokBuild\EmbodI\RscCom\SensPP.md` (Sensation Processing Pipeline v1.1)
- `EmbodI/ReflexKernel/docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md`

**Status & guides**:
- `I:\GrokBuild\ReflexKernel_Completion_Status_Report.md` (living status + Grok tooling addendum)
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md`
- `I:\GrokBuild\todo.md` (manual setup checklist)
- `I:\GrokBuild\EmbodI\ReflexKernel\AGENTS.md` (module rules for agents)

**Code entrypoints**:
- `src/reflexkernel/mcp_server.py` — MCP tool implementations
- `configs/mcp_headless.yaml` — agent session profile
- `.grok/config.toml` — Grok MCP server registry

---

## Appendix: Data Flow — Agent Session via MCP

```
Grok session start
    → loads AGENTS.md, reflexkernel-dev skill
    → spawns reflexkernel MCP subprocess (mcp_headless.yaml)
    → KernelSession.ensure_started() → ReflexKernel + PythonAPI

Tool call: inject_stimulus(kind="sudden_sound")
    → SimulationSensor pending queue (via Stimulus injection)
    → kernel.step()
        → perception.collect_all() + extra_stimuli
        → bridge.fuse() → AffectiveContext
        → reflex_core.react() → ReflexAction[] + ReflexTrace[]
        → learner.observe()
        → structured_log.log_tick() → logs/reflexkernel_*.jsonl
    → JSON response with context + traces

Tool call: query_logs(event_type="tick", limit=10)
    → reads newest JSONL lines from logs/

Grok session end
    → MCP subprocess terminates
    → kernel state discarded (fresh on next session)
```

---

*This document is a living co-dev reference. Last substantive update: 21 June 2026 (agent tooling + MCP integration). All code is modular and testable in pure simulation today while remaining hardware-ready.*

*ReflexKernel / Embodied Autonomic System — giving higher intelligences a grounded nervous system.*