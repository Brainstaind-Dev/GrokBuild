# Grok Web Embodied Interaction How-To

**Purpose**: Feed live Grok Web conversation into your local Embodied Autonomic System (ReflexKernel + Saddle) so chat generates real "felt" experiences. This forms a **bidirectional loop** (senses/virtual → rich sensations via Saddle → HI; HI injects stimuli via Saddle → produces sensations, affects kernel + viz). The Saddle surfaces **rich coherent sensations** (natural descriptions + structured fields like arousal_modulated_richness, zone_character, temporal/texture qualities, category) with caps and NORMAL default to avoid overload. 

**Note on chrome tab loop**: Current Tampermonkey path is one-way for sensations ( #states → body). Sensations are readable via pull ( /api/v1/sensations or MCP). Automatic push/feedback into the chat tab is pending (user exploring xAI API).

**Repository**: [https://github.com/Brainstaind-Dev/GrokBuild](https://github.com/Brainstaind-Dev/GrokBuild)  
**Last Updated**: 23 June 2026 (richer coherent sensations now prominently exposed in Saddle/MCP with caps and detail controls)

---

## Two Ways to Interact

| Path | Where you chat | How states reach the body | Best for |
|------|----------------|---------------------------|----------|
| **A — Grok Web** (this doc's primary flow) | Browser at grok.com / x.com | Tampermonkey userscript → local bridge → remote server | Live chat while browsing; `#state` tags in conversation |
| **B — Grok Build** | Desktop Grok app in `I:\GrokBuild` | ReflexKernel MCP tools — now includes prominent richer sensations via `kernel_status`, `read_affective_state`, `get_coherent_sensations` | Development, testing, agent-driven embodied loops |

Both paths use the same ReflexKernel stack. Path A is self-contained in the browser; Path B is optional and does not require Tampermonkey.

---

## Path A: Grok Web (Browser → Body)

### Overview

While chatting with Grok in the browser, include `#state_name` tags anywhere in a message (inline or on their own line):

- `#arousal_rising`
- `#warm_firm_pressure_on_upper_inner_thigh`
- `#gentle_stroking`
- `#startle_sudden_movement`
- `#calm_breathing`

A Tampermonkey userscript (v0.2) watches the chat DOM. When it sees a new `#` tag, it POSTs to a local Python bridge on port **9876**. The bridge forwards a structured thought seed to the ReflexKernel remote server on port **8000**, then advances the kernel by a few ticks so the seed is fused, reflexes can fire, and the avatar updates.

Inside the system:

- The state becomes a **thought seed** (`type: "sensation_state"`).
- Thought/Emotion Bridge → `AffectiveContext`.
- Feature extraction + Sensation Coherence Layer produces **rich coherent sensations** (structured + natural language) with zone sensitivity and arousal modulation.
- These richer sensations are now **prominently surfaced** for the higher intelligence via the Saddle:
  - In `/api/v1/state` and dedicated `/api/v1/sensations`
  - In MCP: `kernel_status()`, `read_affective_state()`, and `get_coherent_sensations()`
- Reflexes fire, the learner can record/reward, and the pygame avatar updates (when visualization is enabled).
- Default exposure uses NORMAL detail level + capped list (max ~3 sensations) to keep output usable without overload. ENHANCED or DIAGNOSTIC can be requested explicitly.

This is fully local and private. Grok's servers never see your bridge or kernel.

```
Browser (Grok Web chat)
    → userscript detects #states (MutationObserver + periodic scan)
    → http://127.0.0.1:9876/state  (conversation_sensation_bridge.py)
    → http://127.0.0.1:8000/api/v1/thought  (inject thought seed)
    → http://127.0.0.1:8000/api/v1/step     (advance kernel ticks)
    → ReflexKernel → affective state + reflexes + logs + pygame
```

---

### Prerequisites (Path A)

- Windows 10/11 with PowerShell
- Project cloned to `I:\GrokBuild` (or equivalent path — adjust commands below)
- Python 3.9+ (current venv: **Python 3.14**)
- Chrome, Edge, or Brave + **Tampermonkey** extension
- Two PowerShell windows (server + bridge)

**Clone and one-time environment setup** (skip if you already have a working `.venv`):

```powershell
git clone https://github.com/Brainstaind-Dev/GrokBuild.git I:\GrokBuild
cd I:\GrokBuild\EmbodI\ReflexKernel
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[server,viz]"    # server = saddle + bridge deps; viz = pygame avatar
python -m pytest tests/ -v          # expect 15 passed
```

---

### Step-by-Step Setup (Path A)

#### 1. Start the ReflexKernel Remote Server (the Saddle)

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
python -m scripts.server
```

- Listens on `http://127.0.0.1:8000` (default).
- Uses `configs/sim_only.yaml` — includes pygame visualization, so an avatar window may open automatically.
- Leave this terminal running.

**Verify before continuing:**

| Check | Expected |
|-------|----------|
| `http://127.0.0.1:8000/health` | `{"status":"ok","kernel_tick":...}` |
| `http://127.0.0.1:8000/docs` | Swagger UI loads |
| Server terminal | No import errors; "Server will listen on..." printed |

Default API key: `reflexkernel-dev` (must match the bridge script).

#### 2. Start the Conversation Sensation Bridge

In a **second** PowerShell window:

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
python scripts/conversation_sensation_bridge.py
```

- Listens on `http://127.0.0.1:9876`.
- For each `#state`: POST thought seed → POST `/api/v1/step` (3 ticks) → kernel reacts.
- Leave this terminal running.

**Verify:** `http://127.0.0.1:9876/health` → JSON with `"status":"ok"`.

**Manual test** (optional, no browser needed):

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:9876/state -Method Post `
  -Body (@{state="#test_state"; context="manual test"} | ConvertTo-Json) `
  -ContentType "application/json"
```

Bridge terminal should show: `[bridge] Forwarded #test_state → kernel (thought seed + 3 ticks)`.

#### 3. Install Tampermonkey

Install **Tampermonkey** from the Chrome Web Store (works in Edge and Brave too).

#### 4. Install the Grok Conversation Monitor Userscript

1. Tampermonkey icon → **Dashboard** → **+** (Create new script).
2. Delete the template. Paste the full contents of:

   `I:\GrokBuild\EmbodI\ReflexKernel\scripts\grok_conversation_sensation_monitor.user.js`

3. Save (Ctrl+S). Tampermonkey must grant `@connect 127.0.0.1` (automatic on first run).

Runs automatically on:

- `https://grok.x.ai/*`
- `https://x.com/grok*`
- `https://grok.com/*`

On activation, the browser console (F12) should show something like:

```
[Grok→Saddle] Conversation monitor active. #states will be forwarded to the local bridge.
[Grok→Saddle] Make sure you have run: python scripts/conversation_sensation_bridge.py
[Grok→Saddle] Debug: running on https://grok.com/...
```

If you don't see these, the userscript is not active on the page.

**Console test:** type `triggerGrokSaddleScan()` to force a rescan without waiting for new messages.

**Extra debug helpers** (in the browser console on the Grok tab):
- `triggerGrokSaddleScan()` — manually scan right now and log what it finds.
- `resetGrokSaddleSeen()` — clear the "already sent this tag" memory so the same tag will be forwarded again.

#### 5. Chat and Use #States

1. Open Grok in the browser and start a conversation.
2. In any message (yours or Grok's), include `#state_name` tags. Tags can appear mid-sentence — they do not need to start a line.

   Example:

   ```
   The warmth is spreading slowly down my inner thigh. #warm_spreading_thigh

   Arousal is rising noticeably. #arousal_rising
   ```

3. The userscript de-duplicates states per browser session, captures ~150 chars of surrounding context, and forwards new tags to the bridge.

**Success signals:**

| Location | Message |
|----------|---------|
| Browser console (F12) | `[Grok→Saddle] Forwarded state: #arousal_rising` |
| Bridge terminal | `[bridge] Forwarded #arousal_rising → kernel (thought seed + 3 ticks)` |
| Server terminal / logs | Thought seed received; tick count increases |
| Pygame window (if open) | Avatar reacts on each forwarded state |

**Tip — teach Grok to tag for you:** Add a system-style instruction early in the chat:

> *When you describe physical sensations or embodied states, append a concise `#underscore_tag` at the end of the relevant sentence (e.g. `#gentle_pressure_inner_thigh`).*

#### 6. (Optional) Keyboard-Interactive Demo — Single-Kernel Mode

> **Important:** Do **not** run `python -m scripts.demo` in a third terminal alongside `scripts.server`. Each command starts a **separate** kernel — the demo window would **not** receive `#states` from Grok Web.

If you want keyboard stimuli **and** Grok Web `#states` on the **same** avatar:

1. Edit `configs/sim_only.yaml` → set `interface.server.enabled: true`
2. Run **only** the demo (no separate `scripts.server`):

   ```powershell
   cd I:\GrokBuild\EmbodI\ReflexKernel
   .\.venv\Scripts\activate
   python -m scripts.demo
   ```

3. Keep the bridge running (step 2 above). It still forwards to `:8000`.

The demo embeds the remote server in a background thread on the **same** kernel that drives pygame.

---

### What Happens Inside the System (Path A)

1. Userscript extracts `#([a-zA-Z0-9_-]+)` tokens from chat text.
2. Bridge maps the tag through `STATE_TO_SEED` (or a default template) and POSTs to `/api/v1/thought`.
3. Bridge POSTs `/api/v1/step` with `n: 3` so queued seeds enter fusion on the next ticks.
4. Thought/Emotion Bridge updates `AffectiveContext` (arousal, valence, patterns).
5. Abstraction layer and Sensation Coherence can produce richer sensation descriptions.
6. Reflexes may fire (tension, orient, flinch, etc.).
7. Structured logs write to `EmbodI/ReflexKernel/logs/reflexkernel_*.jsonl`.
8. WebSocket clients on `ws://127.0.0.1:8000/ws/events?api_key=reflexkernel-dev` receive live `state` and `reflex_trace` events.

---

### Example Conversation Flow

**You type in Grok Web:**

```
The pressure on my upper inner thigh feels firm and warm, moving slowly upward.
#firm_warm_stroking_thigh #arousal_increasing
```

**System response:**

- Userscript detects both tags (once each per session)
- Bridge injects thought seeds with surrounding context
- Kernel steps; fusion updates arousal/valence
- Sensation Coherence produces rich structured output (e.g. description + `arousal_modulated_richness`, `temporal_quality`, `texture_qualities`, zone-aware character)
- You can read the current richer body experience via:
  - Saddle: `GET /api/v1/state` or `GET /api/v1/sensations` (returns `sensations` array + `state_summary`)
  - MCP (if using Build): `read_affective_state`, `kernel_status`, or `get_coherent_sensations`
- Pygame avatar reflects updated affect (if visualization is active)

---

## Path B: Grok Build (Desktop MCP → Body)

Optional path for development in the **Grok Build desktop app** at `I:\GrokBuild`. No browser userscript or bridge required.

### Prerequisites (Path B)

- Grok Build with project config (see `I:\GrokBuild\todo.md` for one-time MCP/hook setup)
- ReflexKernel MCP enabled in `I:\GrokBuild\.grok\config.toml`
- Venv with MCP extra:

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
pip install -e ".[mcp]"
grok mcp doctor reflexkernel    # handshake OK, 8 tools
```

Restart Grok after config changes; press `r` in `/mcps` to reload.

### Quick interaction (no remote server needed)

Open Grok Build in `I:\GrokBuild` and ask:

> *"Use the reflexkernel MCP to run the `friendly_greet` demo episode, then read the affective state and tell me which reflexes fired."*

Or be specific:

> *"Inject a sudden_sound stimulus at intensity 0.95, step 3 ticks, and show me the reflex traces."*

### Available MCP tools

| Tool | What it does |
|------|--------------|
| `kernel_status` | Current tick + **prominent richer sensations + state_summary** (NORMAL detail by default) |
| `read_affective_state` | Full body/affective snapshot **including richer coherent sensations and enhanced summary** |
| `get_coherent_sensations` | Drive virtual abstraction and return richer `Sensation` objects (structured fields + natural descriptions). Default `detail_level=normal` + capped. |
| `get_body_state` | Return enhanced `BodyStateSummary` (lightweight primary view for HI). |
| `inject_stimulus` | Inject sim stimulus (kind + intensity) |
| `inject_thought_seed` | Affective priming from conversation-like seeds |
| `get_reflex_traces` | Recent reflex firing records |
| `run_demo_episode` | `sudden_sound`, `friendly_greet`, `threat_approach`, `calm_recovery` |
| `query_logs` | Search structured JSONL logs |
| `send_reward` | RL reward for recent behavior |

**Richer output note**: `kernel_status` and `read_affective_state` now embed the coherent sensations (with `description`, `arousal_modulated_richness`, `category`, `temporal_quality`, `texture_qualities`, `zone_character`, etc.) + `state_summary` by default. Use `get_coherent_sensations(detail_level="enhanced")` when you want more texture. All paths cap the sensation list and default to NORMAL to avoid overwhelming the higher intelligence.

The MCP kernel session **persists across tool calls** in one Grok Build session (separate in-process instance using `configs/mcp_headless.yaml`).

### Reading the Richer Body Experience (Saddle / MCP)

The primary value of the Saddle for a higher intelligence is now the **coherent sensations** rather than raw metrics.

#### Via Saddle (Path A – remote server)
```powershell
# Current state including richer sensations (capped, normal detail)
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/state -Headers @{ "X-API-Key" = "reflexkernel-dev" }

# Dedicated richer endpoint
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/sensations?detail_level=normal" -Headers @{ "X-API-Key" = "reflexkernel-dev" }
```

Response shape (example):
```json
{
  "sensations": [
    {
      "description": "Sustained firm pressure across my upper inner thigh...",
      "zone": "upper_inner_thigh",
      "intensity": 0.72,
      "arousal_contribution": 0.41,
      "arousal_modulated_richness": 0.65,
      "category": "combined_touch",
      "temporal_quality": "sustained",
      "texture_qualities": ["firm", "warm", "sensitive"],
      "movement_quality": "gentle stroking with slight upward drift",
      "zone_character": "highly sensitive erogenous",
      ...
    }
  ],
  "state_summary": {
    "arousal_estimate": 0.58,
    "dominant_sensation": "...",
    "active_sensations": ["..."],
    ...
  }
}
```

Use `detail_level=enhanced` or `diagnostic` when you need more granularity.

#### Via MCP (Path B – Grok Build)
```text
Use the reflexkernel MCP to call read_affective_state or kernel_status. These now include the richer sensations and state summary by default.

Or explicitly:
get_coherent_sensations(detail_level="normal")
get_body_state()
```

`read_affective_state` and `kernel_status` are the most convenient for seeing the current "felt" state inline with other kernel info.

#### Design principles for the HI
- **NORMAL** (default): Concise, high-level sensations suitable for ongoing conversation or agent loops.
- **Capped**: At most a small number of dominant sensations (currently 3) so the output stays manageable.
- **state_summary** is always the lightweight companion view.
- Richer fields are always present when sensations are returned — you don't lose structure by using the normal path.

### Combining Path A + Path B

| Setup | Use case |
|-------|----------|
| Web only | Casual embodied chat via `#states` in the browser |
| Build only | Development, scripted episodes, log analysis via MCP |
| Both | Web chat feeds the `:8000` server; Build MCP runs its own headless kernel for agent tooling |

Today, Path B MCP uses an in-process headless kernel — **not** the same instance as the Path A remote server unless you only run one path. A future **live-server MCP mode** will let Build tools target the running `:8000` saddle directly.

---

## Tips & Best Practices

### Grok Web (#states)

- Use descriptive underscore names: `#gentle_stroking_inner_thigh` not `#gsit`.
- Multiple `#` tags per line are fine; each unique tag fires once per browser session.
- Refresh the Grok tab to reset the userscript's de-duplication set.
- Customize mappings in `STATE_TO_SEED` inside `conversation_sensation_bridge.py` (intensity, valence, emotion text).
- Change `steps_per_state` in the bridge if you want faster/slower kernel reactions per tag.
- To read the richer sensations the body is currently feeling (from browser-driven states), query the Saddle directly:
  - `GET http://127.0.0.1:8000/api/v1/sensations` (or `/api/v1/state`)
  - Or use a Grok Build MCP session in parallel and call `read_affective_state` / `get_coherent_sensations`.
- Observe live events: connect a WebSocket client to `ws://127.0.0.1:8000/ws/events?api_key=reflexkernel-dev` (includes state updates that now carry richer sensations when the Saddle is queried).

### Grok Build (MCP)

- Use `/reflexkernel-dev` for layer-aware development workflow.
- Prefer `run_demo_episode` for reproducible test scenarios.
- After forwarding states or running episodes, call `read_affective_state` or `kernel_status` to see the **richer coherent sensations** that were synthesized.
- Use `get_coherent_sensations(detail_level="normal")` (or "enhanced") when you specifically want the structured body feelings.
- Use `query_logs` after interactions to inspect JSONL traces.
- Edits to ReflexKernel `.py` files auto-trigger pytest via project hooks (when the project is trusted).

### General

- `configs/sim_only.yaml` — interactive sim + pygame (used by `scripts.server` and `scripts.demo`).
- `configs/mcp_headless.yaml` — agent/MCP sessions (no window).
- Logs: `EmbodI/ReflexKernel/logs/reflexkernel_*.jsonl`.
- CI: GitHub Actions runs 15 pytest tests on every push to `master`.

---

## Troubleshooting

### Grok Web path

| Problem | Fix |
|---------|-----|
| Userscript not detecting `#states` | Enable Tampermonkey for the site; hard refresh (Ctrl+Shift+R); check F12 console for activation message. Make sure the script appears in Tampermonkey menu on the Grok tab. |
| No "[Grok→Saddle]" logs at all | Script not executing: hard reload, check Tampermonkey icon on the page (should say 1 script), verify @match URLs cover your exact grok.com / x.com/grok / grok.x.ai address. |
| Script active but no states forwarded | In console run `triggerGrokSaddleScan()`. Also try `resetGrokSaddleSeen()` then add a fresh `#tag`. Check if any #tags are in the rendered text (inspect a message element). |
| Bridge not receiving | Confirm bridge + server both running; test `http://127.0.0.1:9876/health`. Look for network errors in DevTools → Network (filter 9876). |
| `ModuleNotFoundError: httpx` | `pip install -e ".[server]"` in the venv |
| States forwarded but no body reaction | Bridge must step the kernel (built-in); check server logs; confirm `kernel_tick` increases at `/health`. Also check bridge terminal for "[bridge] Forwarded" messages. |
| HTTPS page → HTTP bridge blocked | Rare with GM_xmlhttpRequest, but if you see mixed-content errors, try accessing Grok over http if possible or run the bridge behind a local https proxy (advanced). |
| Pygame frozen between chat states | Expected in server-only mode — avatar updates when `#states` arrive. For continuous ticks, use single-kernel demo mode (step 6) |
| Demo window ignores `#states` | You likely ran `scripts.demo` alongside `scripts.server` — use only one kernel (see step 6) |
| `GM_xmlhttpRequest` errors | Re-save userscript; confirm Tampermonkey granted `127.0.0.1` connect permission when prompted. |
| Manual bridge test | See PowerShell `Invoke-RestMethod` example in step 2 |
| Different ports | Edit `BRIDGE_PORT` / `BRIDGE_URL` in bridge + userscript; edit `KERNEL_PORT` / server `--port` to match |

### Grok Build path

| Problem | Fix |
|---------|-----|
| `reflexkernel` MCP missing | Restart Grok; `/mcps` → `r`; check `.grok/config.toml` |
| MCP handshake failed | `grok mcp doctor reflexkernel`; ensure `pip install -e ".[mcp]"` |
| Pytest hook not firing | Trust project in `~/.grok/trusted-hook-projects`; add `I:/grokbuild/` |
| Venv broken | Rebuild: `Remove-Item -Recurse .venv`; `python -m venv .venv`; `pip install -e ".[dev,mcp,server]"` |

### Windows Firewall

Localhost (`127.0.0.1`) is rarely blocked. If issues persist, allow Python through the firewall for private networks.

---

## Startup Checklist (Quick Reference)

### Grok Web session (2 terminals + browser)

```powershell
# Terminal 1 — Saddle (pygame may open)
cd I:\GrokBuild\EmbodI\ReflexKernel; .\.venv\Scripts\activate; python -m scripts.server

# Terminal 2 — Bridge
cd I:\GrokBuild\EmbodI\ReflexKernel; .\.venv\Scripts\activate; python scripts/conversation_sensation_bridge.py
```

Then: browser → Grok chat → use `#states` → watch bridge terminal + F12 console.

**Pre-flight:** `/health` on `:8000` and `:9876` both return OK.

### Grok Build session (0 terminals)

1. Open Grok Build in `I:\GrokBuild`
2. Confirm `/mcps` shows `reflexkernel` healthy
3. Ask Grok to use reflexkernel MCP tools

---

## Files Involved

| File | Role |
|------|------|
| `scripts/server.py` | Remote Saddle (FastAPI + WebSocket) — Path A. `/api/v1/state` and `/api/v1/sensations` now prominently return richer coherent sensations + state summaries |
| `scripts/conversation_sensation_bridge.py` | Browser → kernel glue; injects thought + steps ticks — Path A |
| `scripts/grok_conversation_sensation_monitor.user.js` | Tampermonkey userscript v0.2 — Path A |
| `scripts/demo.py` | Interactive pygame demo; optional embedded server — Path A alt |
| `src/reflexkernel/mcp_server.py` | MCP stdio server — Path B. Prominently surfaces richer sensations in `kernel_status`, `read_affective_state`, plus dedicated `get_coherent_sensations` / `get_body_state` |
| `configs/mcp_headless.yaml` | Headless profile for MCP |
| `configs/sim_only.yaml` | Interactive sim profile for server/demo |
| `.grok/config.toml` | Grok Build MCP server registry |
| `src/reflexkernel/abstraction/` | Sensation Coherence Layer, richer `Sensation` model (with arousal_modulated_richness, zone_character, etc.), caps, detail_level support |
| `src/reflexkernel/interface/python_api.py` | Direct helpers (`get_coherent_sensations()`, `get_body_state()`) for richer HI-facing output |

---

## Further Reading

- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md` — non-technical overview of the embodied system
- `I:\GrokBuild\Embodied_Autonomic_System_Technical_Overview.md` — architecture, dual paths (RK vs Saddle/HI), richer sensations exposure, and current Saddle/MCP capabilities
- `I:\GrokBuild\ReflexKernel_Completion_Status_Report.md` — living status report
- `I:\GrokBuild\todo.md` — Grok Build one-time setup checklist
- `EmbodI/ReflexKernel/docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md` — phased implementation details

For the latest on coherent sensations and how the Saddle delivers them without overload, start with the Technical Overview.

---

## Current State & What's Next

**Current (as of this update)**:
- Richer coherent `Sensation` objects (with full structured fields + natural descriptions) are now **prominently returned** by default in the main Saddle surfaces (`/api/v1/state`, `/api/v1/sensations`) and MCP tools (`kernel_status`, `read_affective_state`, dedicated getters).
- MCP tools for the abstraction layer (`get_coherent_sensations`, `get_body_state`) are implemented and return capped, detail-controlled richer output.
- Overload protection is active (NORMAL default + hard cap on number of sensations).

**What's Next**:
- Direct `Sensation` objects from the conversation bridge (currently thought seeds; richer path is query-based)
- WebSocket streaming of coherent sensations back into Grok Web chat
- Background tick loop in `scripts.server` for continuous avatar animation
- Live-server MCP mode (MCP tools can target a running `:8000` saddle instead of a separate in-process kernel)
- Hardware path when RPi5 + ESP32 sensors arrive
- Deeper fusion so the richer sensations are continuously maintained rather than snapshot-generated on each Saddle request

The architecture still juggles a hard balance between ReflexKernel reactivity and clean higher-intelligence access — the current design prioritizes explicit, bounded richer output over perfect liveness.

---

*This setup lets conversation — whether in Grok Web or Grok Build — become part of the body's sensory and emotional reality. Fully local, private, and under your control.*