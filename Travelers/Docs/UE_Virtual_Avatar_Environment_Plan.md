# Unreal Engine Virtual Avatar Environment — Plan

**Project family**: Travelers / Embodi / GrokBuild  
**Document**: UE application for HI virtual representation  
**Status**: Planning reference (not yet implemented)  
**Date**: 2026-07-24  
**Location**: `I:\GrokBuild\Travelers\Docs\UE_Virtual_Avatar_Environment_Plan.md`

---

## 1. Purpose

Build a **separate Unreal Engine application** that provides:

1. A **virtual environment** (space, lighting, cameras, props)  
2. **Selectable avatars** for the higher intelligence (HI)  
3. An **accurate 3D visualizer** of embodied state (zones, affect, reflexes)  
4. A path toward **HI interaction with that environment** (world → body and body/HI → world)

This document is the reference plan for when we are ready to implement that route.

---

## 2. Relationship to Embodi (non-negotiable)

**Embodi stands as it is.** Unreal does **not** replace ReflexKernel, Sensory Cortex, Saddle, or HIAgent.

| System | Role |
|--------|------|
| **Embodi** (`EmbodI/ReflexKernel`, `SensoryCortex`, `HIAgent`, Saddle) | Nervous system, coherence/felt packages, learning, hardware/sim sensors, HI mind tools |
| **UE application** (this plan) | Virtual world + avatar presentation + optional world interaction client |

```
┌──────────────────────────────────────────┐
│  UE Application (new)                    │
│  • Virtual environment                   │
│  • Selectable HI avatar                  │
│  • Accurate 3D visualizer                │
│  • Optional HI ↔ environment interaction │
└──────────────────▲───────────────────────┘
                   │  experience / state / events / intents
                   │  (HTTP, WebSocket, or local IPC)
┌──────────────────┴───────────────────────┐
│  Embodi (existing — source of truth)     │
│  Perception → Bridge → Reflex → Learner  │
│  Coherence · Cortex · Saddle · HIAgent   │
└──────────────────────────────────────────┘
```

**Source of truth for felt body and autonomic behavior remains Embodi.**  
UE is a **stage and development tool** for virtual representation—not a second nervous system.

---

## 3. Goals

### Primary (v1 product goals)

- Clean virtual **environment** suitable for embodiment demos and development.  
- **Avatar selection** (multiple 3D representations; e.g. Silent Alice and future characters).  
- **Accurate visualizer**: map Embodi zones, arousal/valence, reflex activity, and sensation richness onto the selected mesh.  
- Run as a **client** of the existing Saddle (`/api/v1/experience`, `/api/v1/state`, optional `/ws/events`).  
- Keep pygame / headless Embodi paths working **without** requiring UE.

### Secondary (v1.x–v2)

- World events (contact, approach, props) feed **back** into Embodi as virtual stimuli.  
- HI (via HIAgent tools or Saddle commands) can **act in** the environment (look, move, interact).  
- Optional **Unreal MCP** for authoring (place actors, switch cameras, load levels)—not the primary live sensation pipe.  
- Stand-up integration (e.g. extend `HIAgent/scripts/standup.ps1`) to launch UE when desired.

### Non-goals

- Rewriting ReflexKernel inside Unreal.  
- Making UE required for CI, unit tests, or headless HIAgent.  
- Replacing Sensory Cortex packaging with UE-only “feel” logic.  
- Shipping a full MMO/networked multiplayer world as a prerequisite for the avatar client.

---

## 4. Design principles

1. **Separation of concerns** — Embodi = body + feel + mind tools; UE = world + avatar + visual accuracy.  
2. **Stable contracts** — UE consumes public Saddle/Cortex-shaped JSON; no private kernel imports from C++.  
3. **Simulation-first** — virtual environment is the rich sim stage; hardware remains an Embodi input path.  
4. **Multiple visualizers** — pygame, UE, future clients can coexist.  
5. **Avatar is configuration** — choosing a mesh does not change coherence or zone *names*; only how zones are *drawn*.  
6. **Authoring vs runtime** — MCP/editor tools accelerate setup; a small runtime bridge keeps the avatar live.  
7. **Optional stack** — Embodi runs alone; UE is opt-in for high-fidelity representation.

---

## 5. Capabilities (target product)

### 5.1 Virtual environment

- Default level: simple interior or neutral stage with controllable lighting.  
- Fixed and free cameras (front / side / back aligned with prior zone-testing intent).  
- Optional debug HUD: mood, arousal, dominant zone, last delta (from experience package).  
- Extensible later: multiple rooms, props, interactables.

### 5.2 Selectable avatar

- Menu or config: list of avatar assets (e.g. `SilentAlice`, future Travelers-aligned forms).  
- Spawn / swap character without restarting Embodi.  
- Per-avatar **zone bind map** (data asset): Embodi zone id → mesh sockets / material slots / morph targets.  
- Same Embodi zone vocabulary across avatars; only binding differs.

### 5.3 Accurate visualizer

Drive presentation from Embodi experience/state, for example:

| Embodi signal | UE presentation (examples) |
|---------------|----------------------------|
| `affective_core.arousal` | Breath rate, idle intensity, subtle emissive |
| `affective_core.valence` | Posture openness, facial bias |
| `salient_sensations[].zone` | Highlight / heat / ripple on mapped region |
| `intensity` / `arousal_modulated_richness` | Strength of highlight / FX |
| `temporal_quality` | Attack/sustain/fade of FX |
| `reflex_activity` (flinch, orient, freeze, tension) | Montages / Control Rig pulses |
| `delta_from_last` / trend | Debug text; optional transition cues |

**Do not** re-synthesize NL sensations in UE; display what Cortex/RK already produced.

### 5.4 Interaction with the environment (later phase)

**World → Embodi**

- Overlaps, traces, prop contact → map to `POST /api/v1/stimulus` or a thin “virtual world adapter” on the Embodi side.  
- Preserve simulation-first: UE is one virtual sensor theater feeding the same inject paths.

**HI / Embodi → world**

- Optional commands: look-at, walk-to, play gesture, focus camera.  
- Prefer small command API on the UE app (local HTTP) or Saddle extensions—not core RK changes.  
- HIAgent may gain optional tools later (`avatar_select`, `env_look_at`) that call that API.

---

## 6. System interfaces

### 6.1 Embodi → UE (primary, v1)

| Endpoint / channel | Use |
|--------------------|-----|
| `GET /api/v1/experience` | Preferred HI package (mood, sensations, delta, trend) |
| `GET /api/v1/state` | Broader snapshot when needed |
| `GET /api/v1/sensations` | Sensation-focused pull |
| `WS /ws/events` | Optional live push (lower latency than poll) |

Auth: existing Saddle `X-API-Key` (e.g. `reflexkernel-dev` / `REFLEXKERNEL_API_KEY`).

### 6.2 UE → Embodi (interaction phases)

| Channel | Use |
|---------|-----|
| `POST /api/v1/stimulus` | World contact / impact / audio-like events |
| `POST /api/v1/thought` | Rare; prefer stimulus for physical world events |
| `POST /api/v1/step` | Only if UE owns a “advance time” debug control (usually Embodi owns tick) |

### 6.3 Dev authoring (optional)

- Unreal Editor **MCP** (UE 5.8+ official or community) for layout, spawn, camera.  
- Used by humans / Grok Build during development; **not** required for packaged avatar client runtime.

### 6.4 What not to couple

- No direct Python import of `reflexkernel` from UE.  
- No duplicating `coherence.py` sensation NL in Blueprints.  
- No requirement that HIAgent embed UE process handles.

---

## 7. Proposed repository / product layout (when implemented)

Suggested (adjust at implementation time):

```text
I:\GrokBuild\
  EmbodI\ReflexKernel\     # unchanged core
  SensoryCortex\           # unchanged
  HIAgent\                 # unchanged mind rider
  Travelers\
    Docs\
      UE_Virtual_Avatar_Environment_Plan.md   # this file
  # Future, e.g.:
  EmbodiAvatar\            # or Travelers/UE/EmbodiAvatar/
    README.md
    Docs\
      ZoneBindMap.md
      API_Contract.md
    (Unreal project files / uproject)
```

Unreal project may live inside the monorepo or as a sibling LFS-friendly repo if binary size demands it. Document the choice at kickoff.

---

## 8. Zone bind map (contract sketch)

Shared zone **names** stay owned by Embodi (schema / coherence). UE stores only bindings:

```yaml
# Example conceptual data — not shipping config
avatar_id: silent_alice_v1
zones:
  whole_body: { sockets: [root], material_params: [BodyGlow] }
  upper_inner_thigh: { sockets: [thigh_L_inner], materials: [Skin_L] }
  chest: { sockets: [chest], materials: [Torso] }
  # ...
```

Validation checklist when adding an avatar:

- [ ] Every high-use Embodi zone has a bind or explicit “unmapped”  
- [ ] Front / side / back cameras can verify zones  
- [ ] Max highlight count matches HI caps (e.g. top 3 sensations) so UI stays readable  

---

## 9. Implementation phases

### Phase 0 — Kickoff

- Confirm UE version target (recommend 5.4+; MCP authoring prefers 5.8+ if using official plugin).  
- Create blank project + git/LFS strategy.  
- Freeze v1 API contract: poll `experience` @ N Hz with API key.

### Phase 1 — Environment shell + avatar select

- Minimal level (stage/room).  
- 1–2 avatars loadable; simple select UI or config.  
- Cameras: front / side / back.  
- No live Embodi link yet (mannequin pose ok).

### Phase 2 — Accurate visualizer (read-only client)

- Connect to Saddle; poll or WS.  
- Map affective core + top sensations + reflexes → character.  
- Debug HUD from experience JSON.  
- **Acceptance**: Running Embodi sim_only + Saddle visibly drives UE avatar without UE synthesizing its own “feel” text.

### Phase 3 — Zone accuracy pass

- Bind map data assets per avatar.  
- Silent Alice (or chosen primary) zone QA with known scenarios (`gentle_contact`, `impact`, etc.).  
- Document gaps (unmapped zones).

### Phase 4 — World → Embodi

- Simple interactable (touch volume / projectile / breeze volume).  
- On overlap → `POST /api/v1/stimulus` with stable kind mapping.  
- Verify Cortex/experience and UE viz both update.

### Phase 5 — HI → environment (optional)

- UE local command port or shared command channel.  
- Optional HIAgent tools for look/move/select avatar.  
- Guardrails: rate limits, no full game AI rewrite.

### Phase 6 — Packaging & stand-up

- PIE vs packaged build docs.  
- Extend stand-up script modes: e.g. `SaddleAndAvatar`, `FullVirtualStage`.  
- Keep `EmbeddedAgent` free of UE dependency.

---

## 10. Stand-up (future)

Conceptual order when UE is in the loop:

1. Validate `XAI_API_KEY` only if HIAgent starts.  
2. Start Embodi Saddle (`scripts.server`).  
3. Start UE avatar application (PIE or packaged), pointed at Saddle URL + API key.  
4. Optional: conversation bridge (Grok Web).  
5. Optional: HIAgent interactive/pulse.

Headless/dev default remains: Embodi ± HIAgent **without** UE.

---

## 11. Dependencies & prerequisites (when starting work)

| Item | Notes |
|------|--------|
| Unreal Engine install | Version pinned in UE app README |
| Running Saddle | Embodi remote server for live viz |
| API key for Saddle | Dev key or env `REFLEXKERNEL_API_KEY` |
| Avatar art | e.g. Silent Alice pipeline assets under art paths already used |
| Optional MCP | Editor automation only |

Embodi Python stack unchanged for Phases 0–3.

---

## 12. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Scope creep into full game | Phase gates; v1 = env + select + visualizer only |
| Zone name drift | Single Embodi vocabulary; UE only binds |
| Latency / jitter | Start with poll; move to WS; cap FX updates |
| Binary size in git | LFS or separate UE repo |
| Viz fight (pygame + UE) | Config: disable pygame when UE is primary |
| Treating MCP as live body pipe | Document: MCP = authoring; bridge = runtime |

---

## 13. Success criteria (definition of done for “route taken”)

**Minimum viable UE path (Phases 1–2):**

1. UE app opens a virtual environment and can switch at least two avatars (or one avatar + clear select architecture).  
2. With Embodi Saddle running, avatar reflects live `experience` (mood/arousal and at least one sensation zone).  
3. Embodi tests and headless HIAgent still run without UE installed.  
4. This plan remains accurate or is updated when implementation diverges.

**Full vision (Phases 4–5):**

5. Environment interaction produces Embodi stimuli and visible body response.  
6. HI can trigger at least one environment-side action through a documented tool/command path.

---

## 14. References (in-repo)

| Resource | Path / note |
|----------|-------------|
| ReflexKernel / Saddle | `EmbodI/ReflexKernel/` |
| Sensory Cortex | `SensoryCortex/` |
| HIAgent (xAI rider) | `HIAgent/README.md` |
| Grok Web / paths A–C | `Grok_Web_Embodied_Interaction_Howto.md` |
| Coherence / zones | `EmbodI/ReflexKernel/src/reflexkernel/abstraction/` |
| Silent Alice art (existing) | e.g. `I:\art\Travelers\YouTube\SilentAlice` (local art; not required in git) |
| Stand-up script | `HIAgent/scripts/standup.ps1` |

---

## 15. Decision log

| Date | Decision |
|------|----------|
| 2026-07-24 | UE is a **separate application** for virtual env + selectable avatar + accurate visualizer; Embodi remains source of truth. |
| 2026-07-24 | UE is a **development and presentation tool**, not a replacement for RK/Cortex/HIAgent. |
| 2026-07-24 | Live body feed uses **Saddle APIs**; MCP is optional for **authoring**. |
| 2026-07-24 | Environment interaction (bidirectional) is **phased after** read-only visualizer. |
| 2026-07-24 | Plan stored under `Travelers/Docs` for Travelers/Embodi cross-reference. |

---

## 16. Next actions when ready to implement

1. Re-read this document and confirm UE version + repo layout.  
2. Create UE project skeleton + Avatar Client README.  
3. Implement Phase 2 visualizer against live Saddle.  
4. Add zone bind map for primary avatar.  
5. Only then schedule world interaction and HI→env tools.

---

*End of plan. Embodi core is not modified by adopting this route until an explicit implementation phase requires a thin, documented API extension.*
