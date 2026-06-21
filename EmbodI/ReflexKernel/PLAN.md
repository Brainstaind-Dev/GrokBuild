# ReflexKernel — Detailed Project Plan & Architecture

**Project**: ReflexKernel  
**Location**: `I:\GrokBuild\EmbodI\ReflexKernel`  
**Goal**: A modular, trainable, low-level "nervous system / embodiment kernel" that lets a higher-level AI (LLM agent, symbolic system, etc.) **feel** grounded reality, exhibit believable involuntary reflexes, and incrementally learn new embodied reactions.

This is the **bottom layer** of an embodied stack. Higher intelligence talks to it; ReflexKernel owns fast reactive body and affective grounding.

---

## 1. Guiding Principles

- **Separation of timescales**: Reflexes are fast/involuntary (< ~50ms reaction). Learning and "thought" are slower.
- **Modularity first**: Every layer is replaceable. Hardware backends, ML models, viz, comms — all swappable via config + interfaces.
- **Simulation primary**: Full functionality without cameras/mics/hardware. Real sensors are additive.
- **Teachability**: The higher intelligence is the teacher. It demonstrates, rewards, seeds patterns, inspects, and overrides.
- **Persistence with versioning**: Learned reflexes survive restarts and can be inspected/rolled back.
- **Minimal core deps + graceful optionals**: Core must run with `numpy`, `pydantic`, `pyyaml`. Heavy ML/vision/viz are feature-flagged.
- **Observable & debuggable**: Every stimulus, fusion decision, reflex firing, and actuation is logged with rich context.
- **Future-proof**: Clear extension points for Raspberry Pi GPIO, Arduino serial, real servos, ROS2, etc.

---

## 2. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HIGHER INTELLIGENCE                       │
│   (LLM, Agent, Symbolic Reasoner, Human Operator via tools)     │
└─────────────────────────────────────────────────────────────────┘
                                │  ▲
                                │  │ (thought seeds, rewards,
                                │  │  demonstrations, commands,
                                ▼  │  subscriptions)
┌─────────────────────────────────────────────────────────────────┐
│                      INTERFACE LAYER                             │
│  - stdio (pipe-friendly for LLM wrappers)                        │
│  - WebSocket / FastAPI (pub/sub + RPC)                           │
│  - Python API (embed directly)                                   │
└─────────────────────────────────────────────────────────────────┘
                                │  ▲
                                ▼  │
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT / ACTUATION LAYER                      │
│  - Structured logging (events, traces)                           │
│  - Pygame simple avatar (face + body micro-expressions)          │
│  - Virtual actuators (muscle groups, expression params)          │
│  - (future) Serial / GPIO / ROS publishers                       │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │ actions / motor primitives
┌─────────────────────────────────────────────────────────────────┐
│                         LEARNER MODULE                           │
│  - Imitation Learning (demo recording + behavioral cloning)      │
│  - Reinforcement (scalar + shaped rewards from higher mind)      │
│  - Parameter / policy updates                                    │
│  - Persistent store (jsonl + optional numpy weights)             │
│  - Registry of named learned behaviors                           │
└─────────────────────────────────────────────────────────────────┘
                                │  ▲  (observe, reward, install)
                                ▼  │
┌─────────────────────────────────────────────────────────────────┐
│                         REFLEX CORE                              │
│  - Fast involuntary pathway (priority / direct dispatch)         │
│  - Composable state machines + procedural primitives             │
│  - Built-ins: flinch, orient, tension/relax, blink, freeze,      │
│    micro-expression generators, simulated autonomic (HR, tone)   │
│  - Can be modulated by affective state                           │
│  - Override / mask points for learned behaviors                  │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │ fused context + raw stimuli
┌─────────────────────────────────────────────────────────────────┐
│                  THOUGHT / EMOTION BRIDGE                        │
│  - Ingest from higher intelligence (JSON seeds, text, vectors)   │
│  - Pattern detection:                                            │
│      • Structured seeds (preferred fast path)                    │
│      • Keyword / regex rules                                     │
│      • Sentiment (lightweight or transformers)                   │
│      • Embedding similarity (sentence-transformers optional)     │
│  - Fusion engine: real-world stimuli + internal thought state    │
│    → unified AffectiveContext (valence, arousal, dominance,      │
│      salient_stimuli, active_patterns, urgency)                  │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │ raw stimuli stream
┌─────────────────────────────────────────────────────────────────┐
│                        PERCEPTION LAYER                          │
│  - Abstract Sensor base + registry                               │
│  - SimulationSensor (scripted + interactive keyboard events)     │
│  - VisionSensor (OpenCV + MediaPipe: face, hands, pose, motion)  │
│  - AudioSensor (energy, onset, optional VAD / STT)               │
│  - Extensible: IMU, depth, thermal, GPIO pins, etc.              │
│  - All produce normalized `Stimulus` events                      │
└─────────────────────────────────────────────────────────────────┘
```

**Data Flow (simplified)**:

```
Sensors ──▶ StimulusBatch ──▶ ThoughtBridge ( + Higher seeds )
                                   │
                                   ▼
                            AffectiveContext
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
           ReflexCore        Learner.observe()    Logger
                 │
                 ▼
           ActionBatch ──▶ Actuators / Viz / Interface publish
                 │
                 ▼
           (optional) Learner.record_demo_step(...)
```

**Reflex Firing Characteristics**:
- Reflexes run on every kernel tick or on relevant stimulus arrival.
- "Involuntary" means they fire unless explicitly masked by higher cognition or safety layer (future).
- Latency target in sim: sub-frame.

---

## 3. Core Data Models (types.py)

Key types (all Pydantic v2 / dataclasses with validation):

- `Stimulus(modality: str, data: dict, ts: float, confidence: float, source: str)`
- `AffectiveContext(valence: float, arousal: float, dominance: float, ... salient: list[Stimulus], patterns: list[PatternMatch])`
- `ReflexAction(kind: str, target: str, intensity: float, duration_ms: int, params: dict)`
- `ReflexTrace(reflex_name, trigger, action, latency_ms, modulated_by, ...)`
- `RewardSignal(value: float, reason: str, ts, meta)`
- `DemonstrationStep(stimuli, context, teacher_action, outcome)`

---

## 4. Folder Structure (Final)

```
ReflexKernel/
├── README.md                     # User-facing quickstart + integration guide
├── PLAN.md                       # This file (architecture + rationale)
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt              # Core
├── requirements-optional.txt     # vision, audio, ml, viz, server
├── configs/
│   └── default.yaml
│   └── sim_only.yaml
├── src/
│   └── reflexkernel/
│       ├── __init__.py
│       ├── kernel.py             # ReflexKernel main class + tick loop
│       ├── config.py             # Pydantic settings + loader
│       ├── types.py
│       ├── events.py             # Simple pub/sub bus (optional)
│       ├── perception/
│       │   ├── __init__.py
│       │   ├── base.py           # Sensor Protocol / ABC
│       │   ├── simulation.py
│       │   ├── vision.py         # (guarded import)
│       │   └── audio.py
│       ├── bridge/
│       │   ├── __init__.py
│       │   ├── thought_bridge.py
│       │   └── pattern_detector.py
│       ├── reflex/
│       │   ├── __init__.py
│       │   ├── core.py
│       │   ├── primitives.py     # flinch(), tension(), etc. + helpers
│       │   └── state_machines.py
│       ├── learner/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── imitation.py
│       │   ├── reinforcement.py
│       │   └── store.py          # JSONL + optional model persistence
│       ├── output/
│       │   ├── __init__.py
│       │   ├── actuation.py      # VirtualMuscle, Expression, Command
│       │   ├── visualizer.py     # PygameAvatar (head, eyes, posture)
│       │   └── logger.py         # Structured event logger
│       └── interface/
│           ├── __init__.py
│           ├── base.py
│           ├── stdio_adapter.py
│           ├── websocket_server.py (optional fastapi)
│           └── python_api.py     # Direct embedding class
├── scripts/
│   └── demo.py                   # Interactive sim demo
│   └── teacher_stub.py           # Example "higher intelligence"
├── tests/
│   ├── conftest.py
│   ├── test_types.py
│   ├── test_perception_sim.py
│   ├── test_reflex_core.py
│   ├── test_learner.py
│   └── test_fusion.py
├── docs/
│   └── architecture.mmd          # Extra diagrams if needed
│   └── integration_guide.md
├── .gitignore
└── LICENSE
```

---

## 5. Implementation Phases (This Session)

**Phase 0 (Current)**: Project scaffolding + this plan.

**Phase 1 — Foundations**:
- types, config, logging
- Perception: SimulationSensor only + base
- Minimal kernel loop that ticks and prints events

**Phase 2 — Reflexes & Viz**:
- Reflex Core + 4-6 primitive reflexes (flinch, blink, tension, orient, freeze, autonomic)
- Simple Pygame visualizer (or text fallback if no pygame)
- Actuation layer

**Phase 3 — Bridge & Fusion**:
- ThoughtBridge with JSON seed fast-path + simple detectors
- Fusion logic
- Optional advanced embedding path (graceful)

**Phase 4 — Learner**:
- Demonstration recorder
- Basic cloning (exemplar store + similarity match or tiny policy)
- Reward ingestion + simple value modulation
- JSONL persistence + load

**Phase 5 — Interface**:
- Stdio bidirectional (JSON lines)
- In-process API
- (optional) WS server skeleton

**Phase 6 — Polish**:
- Full demo that shows teaching a new reflex
- Tests
- README with examples
- Config examples
- Documentation strings everywhere

---

## 6. Key Design Decisions & Trade-offs

- **No heavy framework lock-in**: No ROS at v1. Use plain Python + numpy.
- **Reflex representation**: Start with Python functions + dataclass descriptors registered in a ReflexRegistry. Later allow loading small safe expression trees or user Python snippets (with sandbox warning).
- **Learning representation**: Hybrid. Fast path = lookup tables + similarity. Slow path = future sklearn / tiny torch policy head. Always keep human-readable traces of why a reflex fired or was learned.
- **Persistence**: Append-only JSONL for demos + rewards. Snapshot current policy params in a versioned .json + optional .npy. Simple, inspectable, git-friendly.
- **Time**: Use `time.perf_counter()` or monotonic. All stimuli carry `ts`.
- **Concurrency**: Main kernel loop is single-threaded for determinism in v1. Sensors that block (cam, mic) run in background threads or use non-blocking reads + queues. Interface server runs in its own thread/process.
- **Safety**: Higher intelligence can send "suppress_reflex" or "clamp_arousal" commands. Learner can be put in "observe-only" mode.

---

## 7. Hardware & LLM Integration Roadmap (Post v1)

- **Perception drivers**: `perception/drivers/rpi_camera.py`, `arduino_imu.py` etc. behind the same `Sensor` interface.
- **Actuation**: `output/drivers/servo_hat.py`, `serial_muscle.py`.
- **LLM usage patterns**:
  1. The LLM runs in a loop: observe current state via WS/JSON, decide high-level goal, send thought seeds + occasional rewards/demos.
  2. Tool-calling: expose ReflexKernel methods as tools (`teach_reflex(name, trigger_pattern, action)`, `reward_last(value)`, `get_recent_traces()`).
  3. Fine-grained: stream raw stimuli + reflex events into LLM context (summarized) so it develops grounded "somatic intuition".
- **Multi-agent**: Multiple ReflexKernels (different bodies) + shared higher mind.

---

## 8. Success Criteria for Initial Delivery

- `python -m reflexkernel.scripts.demo` (or equivalent) runs fully in simulation with interactive keyboard stimuli, visible pygame (or rich text) avatar that flinches, tenses, etc.
- Higher-intelligence stub can send JSON seeds via stdio and see fused reactions + receive logs.
- User can record a short demonstration, send a reward, and see the system prefer the taught behavior on similar stimuli.
- All core modules have clear docstrings + type hints.
- Adding a new primitive reflex is < 30 lines in one file + registration.
- No crashes when optional deps (cv2, pygame, sentence_transformers) are missing.
- Basic pytest suite passes.

---

## 9. Next Steps After Core

- Add real vision (MediaPipe face blendshapes → micro-expressions as stimuli).
- Add audio onset detection.
- Persistent policy as small neural net (numpy only or torch CPU).
- Better state machines (transitions, timers, hysteresis).
- Visualization upgrade (maybe simple 3D with moderngl or just better 2D).
- Web dashboard (FastAPI + nice frontend) for inspection/teaching.
- Formal evaluation harness (synthetic stimulus sequences + expected reflex distribution).

---

*This plan is the single source of truth for the initial build. Update it as decisions are validated in code.*

**End of PLAN.md**
