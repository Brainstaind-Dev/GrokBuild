# ReflexKernel Remote Interface Enhancement Plan (v0.2)

**Goal**: Evolve the Interface Layer to provide robust, production-ready remote connectivity for higher-level AIs (e.g. Grok, other agents) via REST + WebSocket, while preserving 100% backward compatibility with local PythonAPI, stdio, simulation, and Pygame visualization.

**Version Target**: v0.2.0 (Interface-focused release)
**Priority**: Remote-first for "higher intelligences" without breaking local use.
**Start Date**: Current session

## 1. Background & Rationale

The existing `interface/` contains:
- `PythonAPI`: Direct in-process wrapper (excellent for embedded agents).
- `StdioAdapter`: JSON-lines for piping/LLM tool use.
- `websocket_server.py`: Minimal stub (only basic WS + command forwarding, no REST, no auth, no real events, no production features).

Current configs have a stub `interface.websocket` section that is disabled by default.

To make ReflexKernel usable as a **remote "body service"** for Grok or similar:
- Need full REST API matching the existing command surface.
- Need real-time push of events (reflex traces, state updates, learner events).
- Need simple but real security (API key).
- Need easy run modes (standalone server + integrated).
- Need clients and docs so a remote intelligence can connect immediately.

All existing local functionality (demo, PythonAPI, simulation sensors, viz, learner persistence, etc.) must remain untouched and continue to work when server is not enabled.

## 2. Scope (In / Out)

### In Scope (This Iteration)
- Productionize FastAPI server with all specified endpoints.
- WebSocket for real-time event subscription.
- Simple API key auth + CORS.
- Server config in YAML (default disabled).
- Standalone CLI script: `python -m scripts.server ...`
- Optional integration in demo.
- Pydantic models for requests/responses (exact match to PythonAPI/command).
- Basic rate limiting, validation, logging, graceful shutdown.
- Example clients (Python async, curl, Grok snippet).
- README update with "Remote Intelligence Integration" section.
- OpenAPI / Swagger at /docs.
- Maintainability: clean typing, separation of concerns, minimal changes to kernel.

### Out of Scope (Future)
- Full OAuth/JWT, user management.
- Persistent sessions / multi-kernel management.
- Advanced rate limiting (Redis-backed).
- TLS termination (recommend reverse proxy).
- GraphQL or other protocols.
- Automatic kernel scaling.
- Full async kernel rewrite (keep sync kernel + thread for now).

## 3. Architecture Decisions

### 3.1 Server Implementation
- Use FastAPI + uvicorn (already in optional `[server]` deps).
- Create `src/reflexkernel/interface/server.py` (or `api.py` + `ws.py`).
- Use APIRouter for clean organization.
- Dependency for API key auth (Header).
- CORS middleware (allow localhost/* for browser testing, configurable).
- Pydantic v2 models for all bodies (reuse/extend existing types where possible).
- Background event broadcaster using `asyncio.Queue` + a simple `EventBroadcaster` class.
  - Kernel will gain lightweight `add_event_listener` / `emit_event` hooks (non-breaking).
  - For integrated mode: run kernel in a background thread, server in asyncio.
- For standalone: create kernel from config, start server, optionally start kernel.

### 3.2 Endpoints (REST)
All JSON shapes must be compatible with existing `kernel.command()` and `PythonAPI` methods.

- `POST /api/v1/thought` → inject_thought_seed
- `POST /api/v1/reward` → send_reward
- `POST /api/v1/demo/begin` , `POST /api/v1/demo/end` 
- `POST /api/v1/stimulus` → inject_stimulus
- `GET  /api/v1/state` → get_state
- `POST /api/v1/step` → step(n=1 or more)
- (Optional) `POST /api/v1/command` for generic compatibility with old command dicts.

Use consistent response envelopes where helpful, but prefer direct data for simplicity.

### 3.3 WebSocket
- `WS /ws/events?token=...` or header auth.
- Subscription model: client sends `{"subscribe": ["traces", "state", "learner", "logs"]}` or all by default.
- Server pushes:
  - `{"type": "reflex_trace", "data": {...}}`
  - `{"type": "state", "data": {...}}`
  - `{"type": "learner_update", ...}`
  - `{"type": "log", "level": "...", "msg": "..."}`
  - Heartbeats / errors.

Use a shared broadcaster that the kernel (or a wrapper) feeds.

### 3.4 Authentication & Security
- Simple `X-API-Key` header (configurable per deployment).
- Default key in dev: "reflexkernel-dev" (clearly documented as dev-only).
- In code: `api_key` in config under `interface.server`.
- Rate limiting: use `slowapi` (lightweight) or simple in-memory token bucket for basics. Add to pyproject optional if needed. For minimal, implement a simple decorator first.
- Input validation: full Pydantic.
- Logging: every call logged with key (sanitized), path, timing.

### 3.5 Configuration
Extend `InterfaceConfig`:
```yaml
interface:
  mode: "stdio"   # existing
  server:
    enabled: false
    host: "127.0.0.1"
    port: 8000
    api_key: "reflexkernel-dev"
    cors_origins: ["*"]   # or list
    enable_rate_limit: true
    rate_limit_per_minute: 120
  # keep stdio, websocket (for legacy name?) or merge
```

Add `ServerConfig` Pydantic model.

Default `enabled: false` everywhere for full backward compat.

### 3.6 Run Modes
1. **Standalone server**:
   - `python -m scripts.server --config configs/sim_only.yaml --host 0.0.0.0 --port 8000 --api-key mykey`
   - Or `reflexkernel-server` entry point (add to pyproject).
   - Creates kernel internally, starts server (kernel ticks can be driven by server or background loop).

2. **Integrated**:
   - In demo or user code: if `cfg.interface.server.enabled`, start server in background thread alongside the main loop / Pygame.

Kernel itself stays fully synchronous. Server uses threads/queues for integration.

### 3.7 Event System (Minimal Addition to Kernel)
Add to `ReflexKernel` (private, non-breaking):
- `_event_listeners: List[Callable]`
- `emit_event(event_type: str, payload: dict)`
- Public: `add_event_callback(callback)` or internal only for the server.

In critical places (after reflex, after learner, on state change, on log) call emit.

For logs, we can hook into the logger or use a custom handler.

This keeps kernel clean.

### 3.8 Clients & Docs
- `scripts/remote_client.py`: full async example using httpx + websockets.
- `docs/remote_examples.md` or in README: curl blocks for every endpoint + WS.
- Grok wrapper snippet: ready-to-paste code that a Grok instance (or tool) could use.

### 3.9 OpenAPI
FastAPI auto-generates excellent docs at `/docs` (Swagger) and `/redoc`.
Add title, description, version, tags for nice organization.

## 4. Implementation Order (Iterative)

1. **Plan** (this doc) + update main README skeleton if needed.
2. **Config extension** (config.py + both YAMLs + InterfaceConfig/ServerConfig).
3. **Pydantic Models** (`interface/models.py`): ThoughtSeedRequest, RewardRequest, DemoRequest, StimulusRequest, StateResponse, etc. Make them mirror PythonAPI signatures.
4. **Core Server** (`interface/server.py`):
   - FastAPI app factory `create_app(kernel: ReflexKernel, config: ServerConfig)`
   - Auth dependency.
   - CORS.
   - All REST endpoints first (using models + delegating to kernel/PythonAPI methods).
   - Basic logging middleware.
   - Simple rate limit (in-memory).
5. **WebSocket & Events**:
   - Add minimal event emission to kernel (in step, command paths, etc.).
   - EventBroadcaster class (asyncio.Queue per client + broadcast task).
   - WS endpoint that subscribes and streams.
6. **Standalone Script** (`scripts/server.py` + CLI with argparse or typer if light).
7. **Integration**:
   - Optional start in `demo.py` if server enabled.
   - Expose `start_server_in_thread` helper.
8. **Clients & Examples**.
9. **Docs & Polish** (README section, update __init__.py exports, pyproject entrypoint, robustness).
10. **Verification**: Install `[server]`, run standalone, curl tests, Python client, confirm local demo unaffected, WS events flow.

## 5. Risks & Mitigations

- **Breaking kernel changes**: Mitigate by making event emission optional and behind try/except or private methods. Add no new public required APIs initially.
- **Threading / asyncio mix**: Document clearly. Use `threading` for kernel when server runs, or run server in separate process recommendation for production.
- **Auth simplicity**: Explicitly document that `api_key` default is for local/dev only. Recommend proxy or env var for real deployments.
- **Performance**: Kernel tick rate remains independent. Server endpoints are thin wrappers.
- **Backcompat**: `interface.server.enabled: false` by default + no change to existing config loading.

## 6. Success Criteria

- `pip install -e .[server]`
- `python -m scripts.server` starts server with Swagger at http://localhost:8000/docs
- All listed endpoints work with correct shapes and return values matching PythonAPI.
- WS connection receives live reflex_trace and state events when demo runs or stimuli injected.
- API key required (wrong key → 401).
- CORS allows browser fetch.
- Local `python -m scripts.demo` still works perfectly with Pygame and keyboard.
- Full README section with copy-paste examples for Grok/remote use.
- All existing tests still pass.

## 7. Files to Touch / Create

- `docs/REMOTE_INTERFACE_ENHANCEMENT_PLAN.md` (this)
- `src/reflexkernel/config.py` (new ServerConfig)
- `configs/*.yaml` (add server section)
- `src/reflexkernel/interface/server.py` (new main impl)
- `src/reflexkernel/interface/models.py` (new)
- `src/reflexkernel/interface/__init__.py` (export new)
- `scripts/server.py` (new)
- `scripts/remote_client.py` (new)
- `README.md` (major new section)
- Possibly `pyproject.toml` (console script)
- Minor: `kernel.py` (event hooks), `demo.py` (optional integration), logging.

## 8. Post-Implementation

- Update VERIFICATION.md or create new remote verification notes.
- Consider adding basic integration tests for the server (optional in this pass).

This plan keeps the spirit of modularity and "higher intelligence as teacher" while making remote use first-class.

---
*Plan written to guide iterative implementation. Follow sections in order.*