"""
Production-grade FastAPI + WebSocket server for remote higher intelligences.

This module provides:
- Full REST API matching the PythonAPI and kernel.command() surface.
- WebSocket real-time event streaming (implemented after core REST).
- API key authentication via X-API-Key header.
- CORS support.
- Basic rate limiting (in-memory).
- Excellent auto-generated OpenAPI docs at /docs.
- Clean separation so local use (PythonAPI, demo, Pygame) is completely unaffected.

Usage (standalone):
    from reflexkernel import ReflexKernel
    from reflexkernel.config import load_config
    from reflexkernel.interface.server import create_app, run_server

    cfg = load_config("configs/sim_only.yaml")
    kernel = ReflexKernel(config=cfg)
    app = create_app(kernel, cfg.interface.server)
    # then uvicorn or run_server(app, ...)

Or via the scripts/server.py CLI.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Set

from ..config import ServerConfig
from ..kernel import ReflexKernel
from .models import (
    AckResponse,
    BeginDemo,
    BeginDemoRequest,
    CommandRequest,
    EndDemo,
    EndDemoRequest,
    EventMessage,
    InjectStimulus,
    InjectStimulusRequest,
    Reward,
    RewardRequest,
    StateResponse,
    Step,
    StepRequest,
    StepResponse,
    ThoughtSeed,
    ThoughtSeedRequest,
    SensationsResponse,
)
from ..abstraction import VirtualSensorSimulator, get_coherent_sensations, get_capped_coherent_sensations
from ..abstraction.schema import DetailLevel, Sensation, AbstractionOutput

# FastAPI imports are attempted at import time but the module remains usable
# without the [server] extra (symbols that require FastAPI are only used when
# the server is explicitly started).
_FASTAPI_AVAILABLE = False
try:
    from fastapi import (
        Depends,
        FastAPI,
        Header,
        HTTPException,
        WebSocket,
        WebSocketDisconnect,
        status,
    )
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    # Will be checked inside create_app / run_server
    pass

logger = logging.getLogger("reflexkernel.server")


# ------------------------------------------------------------------
# Simple in-memory rate limiter (token bucket style, per key)
# ------------------------------------------------------------------

class SimpleRateLimiter:
    """Very lightweight rate limiter. Not distributed, sufficient for single-server dev/prod small setups."""

    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.window = 60.0
        self._buckets: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        # Remove old timestamps
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) < self.requests_per_minute:
            bucket.append(now)
            return True
        return False


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------

def _make_auth_dependency(server_config: ServerConfig):
    """Factory that returns a FastAPI dependency closed over the expected key."""
    async def get_api_key(
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ) -> str:
        expected = server_config.api_key if server_config else "reflexkernel-dev"
        if not x_api_key or x_api_key != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return x_api_key
    return get_api_key


# ------------------------------------------------------------------
# Event Broadcaster (for WebSocket + future use)
# ------------------------------------------------------------------

class EventBroadcaster:
    """Lightweight pub/sub for server clients.

    Clients (WebSocket connections) register queues. The server (or kernel)
    calls broadcast() to push to all active subscribers.
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        async with self._lock:
            dead = []
            for q in list(self._subscribers):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop oldest if full (simple backpressure)
                    try:
                        q.get_nowait()
                        q.put_nowait(event)
                    except Exception:
                        dead.append(q)
                except Exception:
                    dead.append(q)
            for d in dead:
                self._subscribers.discard(d)


# ------------------------------------------------------------------
# FastAPI Application Factory
# ------------------------------------------------------------------

def create_app(
    kernel: Optional[ReflexKernel] = None,
    server_config: Optional[ServerConfig] = None,
    broadcaster: Optional[EventBroadcaster] = None,
) -> "FastAPI":
    """
    Create a configured FastAPI application wired to a ReflexKernel instance.

    If kernel is None, a default simulation kernel will be created (for quick testing).
    """
    # Local import so the package can be imported without [server] extras
    try:
        from fastapi import (
            Depends,
            FastAPI,
            Header,
            HTTPException,
            WebSocket,
            WebSocketDisconnect,
            status,
        )
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as e:
        raise RuntimeError(
            "FastAPI server requires optional dependencies. Install with: pip install -e .[server]"
        ) from e

    if server_config is None:
        server_config = ServerConfig()

    if kernel is None:
        # Lazy default for standalone quick starts / testing
        from ..config import load_config

        default_cfg = load_config()
        kernel = ReflexKernel(config=default_cfg)
        logger.warning("No kernel provided to create_app(); created a default one.")

    if broadcaster is None:
        broadcaster = EventBroadcaster()

    # Shared VirtualSensorSimulator so that signals received via the Saddle (interface)
    # can drive the abstraction layer. This lets coherent sensations be produced as part
    # of processing web/Grok inputs, and the resulting stimuli can affect the kernel
    # state, reflexes, and thus the visualization.
    virtual_sim = VirtualSensorSimulator()

    # Optional Sensory Cortex (soft import — never hard-require for Saddle boot)
    _cortex_holder: Dict[str, Any] = {"cortex": None, "last_experience": None}
    try:
        import sys
        from pathlib import Path as _Path

        # interface/server.py → …/GrokBuild (parents: interface, reflexkernel, src, ReflexKernel, EmbodI, GrokBuild)
        _grok_root = _Path(__file__).resolve().parents[5]
        if str(_grok_root) not in sys.path:
            sys.path.insert(0, str(_grok_root))
        from SensoryCortex.integration import try_create_cortex  # type: ignore
        from reflexkernel.interface.python_api import PythonAPI as _PyAPI

        _cortex_holder["cortex"] = try_create_cortex(
            mode="embedded", bind_api=_PyAPI(kernel)
        )
        if _cortex_holder["cortex"] is not None:
            logger.info("Sensory Cortex attached to Saddle (embedded mode)")
    except Exception as _cortex_exc:
        logger.debug("Sensory Cortex not attached: %s", _cortex_exc)

    def _feed_cortex(last_out: Optional[AbstractionOutput] = None) -> None:
        cortex = _cortex_holder.get("cortex")
        if cortex is None:
            return
        body = None
        sens = None
        if last_out is not None:
            sens = list(last_out.sensations or [])[:3]
            if last_out.state_summary is not None:
                body = (
                    last_out.state_summary.to_dict()
                    if hasattr(last_out.state_summary, "to_dict")
                    else None
                )
        try:
            from SensoryCortex.integration import experience_to_dict, feed_cortex_from_kernel

            update = feed_cortex_from_kernel(
                cortex,
                kernel,
                body_state=body,
                sensations=sens,
                respect_gate=True,
                force=False,
            )
            exp = experience_to_dict(update)
            if exp is not None:
                _cortex_holder["last_experience"] = exp
        except Exception as exc:
            logger.debug("Cortex feed failed (non-fatal): %s", exc)

    def _drive_abstraction_and_feed(num_steps: int = 1):
        """Drive the virtual sim (producing rich sensations) and feed stimuli into the kernel.
        Call this when the interface receives signals so the sensations are reflected in the body/viz.
        The produced sensations are also attached to the kernel so the visualizer can display them.
        """
        last_out = None
        for _ in range(max(1, num_steps)):
            raw = virtual_sim.read_all()
            out: AbstractionOutput = virtual_sim.process(raw)
            last_out = out
            from ..abstraction.bridge import abstraction_to_stimuli

            extras = abstraction_to_stimuli(out)
            if extras:
                kernel.step(extra_stimuli=extras)
        if last_out is not None:
            # Attach for the visualizer / Sensory Cortex / HI consumers
            if hasattr(kernel, "set_last_sensations"):
                kernel.set_last_sensations(list(last_out.sensations or []), max_count=3)
            else:
                kernel._last_sensations = list(last_out.sensations or [])[:3]
            _feed_cortex(last_out)
        return last_out  # caller can use the sensations if desired

    # Rate limiter
    rate_limiter = SimpleRateLimiter(server_config.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("ReflexKernel server starting (server enabled=%s)", server_config.enabled)
        if not kernel._running:  # type: ignore[attr-defined]
            kernel.start()
        # Initial drive of abstraction so the visualization has some sensation data from the start
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(3)
        except Exception:
            pass
        yield
        # Shutdown
        logger.info("ReflexKernel server shutting down...")
        if kernel._running:  # type: ignore[attr-defined]
            kernel.stop()

    app = FastAPI(
        title="ReflexKernel Remote API",
        description=(
            "Remote control surface (Saddle) for ReflexKernel — the low-level trainable nervous system.\n\n"
            "PRIMARY FOR HIGHER INTELLIGENCE: Use GET /api/v1/state and /api/v1/sensations (default detail=normal) "
            "to receive coherent rich Sensation objects (structured + natural descriptions, zone-aware, arousal-modulated) "
            "and BodyStateSummary. This is the clean 'felt body' view — not raw sensors.\n\n"
            "GET /api/v1/experience returns the Sensory Cortex HI package (mood, deltas, trend) when available.\n\n"
            "Higher intelligences (Grok, agents, LLMs) can use this API to feel stimuli, "
            "trigger and observe reflexes, teach new behaviors via demonstration, and send rewards.\n\n"
            "Authentication: Include header `X-API-Key: <your-key>` (default dev key: reflexkernel-dev).\n\n"
            "See /docs for interactive Swagger UI."
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Control", "description": "Core operations: thought, reward, demo, step, state."},
            {"name": "Cortex", "description": "Sensory Cortex HI packaging (experience, trend)."},
            {"name": "Events", "description": "WebSocket real-time streaming."},
        ],
        lifespan=lifespan,
    )

    # Expose shared objects so endpoints and background logic can drive sensations from interface inputs
    app.state.kernel = kernel
    app.state.virtual_sim = virtual_sim
    app.state._drive_abstraction_and_feed = _drive_abstraction_and_feed
    app.state.broadcaster = broadcaster
    app.state.cortex = _cortex_holder.get("cortex")
    app.state.cortex_holder = _cortex_holder

    # CORS - important for browser-based clients and local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    get_api_key = _make_auth_dependency(server_config)

    async def require_auth(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
        return await get_api_key(x_api_key)

    async def check_rate_limit(x_api_key: str = Depends(require_auth)) -> str:
        if server_config.enable_rate_limit:
            if not rate_limiter.is_allowed(x_api_key or "anonymous"):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down.",
                )
        return x_api_key

    # ------------------------------------------------------------------
    # REST Endpoints
    # ------------------------------------------------------------------

    @app.post("/api/v1/thought", response_model=AckResponse, tags=["Control"])
    async def inject_thought(
        body: ThoughtSeedRequest,
        _: str = Depends(check_rate_limit),
    ) -> AckResponse:
        """Inject a thought / affective seed (equivalent to inject_thought_seed).

        When a signal arrives from the higher intelligence (e.g. via Grok Web bridge),
        we also drive the shared virtual abstraction layer. This produces coherent sensations
        as part of the interface processing, and the resulting stimuli are fed to the kernel
        so the visualization (and reflexes) can reflect the sensations.
        """
        logger.info("Remote thought seed received: %s", {k: v for k, v in body.model_dump().items() if v is not None})
        kernel.inject_thought_seed(body.model_dump(exclude_unset=True))
        # Drive abstraction from the interface so sensations are generated and reflected in viz
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(2)
        except Exception as e:
            logger.debug("Abstraction drive on thought failed (non-fatal): %s", e)
        return AckResponse(ok=True)

    @app.post("/api/v1/reward", response_model=AckResponse, tags=["Control"])
    async def send_reward_endpoint(
        body: RewardRequest,
        _: str = Depends(check_rate_limit),
    ) -> AckResponse:
        """Send a scalar reward signal to the learner."""
        logger.info("Remote reward: value=%.3f reason=%s", body.value, body.reason)
        kernel.send_reward(body.value, body.reason, body.window_steps)
        return AckResponse(ok=True)

    @app.post("/api/v1/demo/begin", response_model=AckResponse, tags=["Control"])
    async def begin_demo(
        body: BeginDemoRequest,
        _: str = Depends(check_rate_limit),
    ) -> AckResponse:
        """Start recording a demonstration for imitation learning."""
        name = body.name
        kernel.begin_demonstration(name)
        logger.info("Remote demo begin: %s", name)
        return AckResponse(ok=True, demo=name)

    @app.post("/api/v1/demo/end", response_model=AckResponse, tags=["Control"])
    async def end_demo(
        body: EndDemoRequest = EndDemoRequest(),
        _: str = Depends(check_rate_limit),
    ) -> AckResponse:
        """End the current demonstration and ingest it into the learner."""
        outcome = body.outcome
        name = kernel.end_demonstration(outcome)
        logger.info("Remote demo ended: %s", name)
        return AckResponse(ok=True, ended=name)

    @app.post("/api/v1/stimulus", response_model=AckResponse, tags=["Control"])
    async def inject_stimulus_endpoint(
        body: InjectStimulusRequest,
        _: str = Depends(check_rate_limit),
    ) -> AckResponse:
        """Inject a raw stimulus (useful for remote simulation of world events).

        Signals received via the Saddle also drive the abstraction layer so that
        the generated rich sensations can influence the kernel and be reflected
        in the visualization.
        """
        stim_dict = body.model_dump(exclude_unset=True)
        from ..types import Stimulus  # local import to avoid circular issues at top level

        try:
            stim = Stimulus.from_dict(stim_dict)
        except Exception:
            stim = Stimulus(modality=body.modality, data=body.data, confidence=body.confidence, source=body.source)
        kernel.step(extra_stimuli=[stim])
        # Drive abstraction so interface-received signals produce sensations that the body/viz can reflect
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(1)
        except Exception as e:
            logger.debug("Abstraction drive on stimulus failed (non-fatal): %s", e)
        return AckResponse(ok=True)

    @app.get("/api/v1/state", response_model=StateResponse, tags=["Control"])
    async def get_state_endpoint(
        detail_level: str = "normal",
        _: str = Depends(check_rate_limit),
    ) -> StateResponse:
        """Return the current observable state of the kernel.

        Richer output (coherent sensations + state_summary) is exposed prominently.
        Defaults to normal detail + capped sensations so higher intelligence receives
        meaningful felt-body info without overload.
        """
        state = kernel.get_state()
        dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
        # Use the shared virtual_sim (driven by interface inputs) so sensations reflect
        # signals received via the Saddle. Drive once on query to keep fresh.
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(1)
        except Exception:
            pass
        sim = app.state.virtual_sim or VirtualSensorSimulator()
        raw = sim.read_all()
        out: AbstractionOutput = sim.process(raw, detail_level=dl)
        # Use shared capped getter for overload safeguard + prominent richer output
        capped = get_capped_coherent_sensations(out)
        sensations = [s.to_dict() for s in capped]
        summary = out.state_summary.to_dict() if out.state_summary else {}
        summary["detail_level"] = dl.value
        resp = StateResponse(**state)
        resp.sensations = sensations
        resp.state_summary = summary
        return resp


    @app.get("/api/v1/sensations", response_model=SensationsResponse, tags=["Control"])
    async def get_sensations_endpoint(
        detail_level: str = "normal",
        _: str = Depends(check_rate_limit),
    ) -> SensationsResponse:
        """Dedicated endpoint for richer coherent sensations (with all structured fields: category, temporal, textures, arousal_modulated_richness, zone_character, etc.) + summary.

        This is the prominent, preferred path for higher intelligence / Saddle to consume the synthesized body experience.
        Default normal keeps it lightweight and non-overloading; use enhanced/diagnostic only when needed.
        Sensations are capped.
        """
        dl = DetailLevel(detail_level) if detail_level in ("normal", "enhanced", "diagnostic") else DetailLevel.NORMAL
        # Use shared sim so sensations are consistent with those driven by Saddle inputs.
        # Drive on query to ensure up-to-date with any recent interface activity.
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(1)
        except Exception:
            pass
        sim = app.state.virtual_sim or VirtualSensorSimulator()
        raw = sim.read_all()
        out: AbstractionOutput = sim.process(raw, detail_level=dl)
        # Use shared capped getter for overload safeguard + prominent richer output
        capped = get_capped_coherent_sensations(out)
        sensations = [s.to_dict() for s in capped]
        summary = out.state_summary.to_dict() if out.state_summary else {}
        summary["detail_level"] = dl.value
        return SensationsResponse(detail_level=dl.value, sensations=sensations, state_summary=summary)

    @app.get("/api/v1/experience", tags=["Cortex"])
    async def get_experience_endpoint(
        force: bool = False,
        _: str = Depends(check_rate_limit),
    ) -> Dict[str, Any]:
        """Return Sensory Cortex HI package (mood, salient sensations, delta, trend).

        Soft-dependent: if Cortex is not available, returns available cached experience
        or builds a minimal envelope from sensations/state.
        """
        try:
            _drive = app.state._drive_abstraction_and_feed
            _drive(1)
        except Exception:
            pass

        holder = getattr(app.state, "cortex_holder", None) or {}
        cortex = getattr(app.state, "cortex", None) or holder.get("cortex")
        if cortex is not None:
            try:
                from SensoryCortex.adapters import from_kernel
                from SensoryCortex.integration import experience_to_dict

                coherent = from_kernel(kernel)
                update = cortex.process_coherent_input(
                    coherent, respect_gate=not force, force=force
                )
                exp = experience_to_dict(update) or holder.get("last_experience")
                if exp is not None:
                    holder["last_experience"] = exp
                    return {"ok": True, "experience": exp, "source": "sensory_cortex"}
            except Exception as exc:
                logger.debug("experience endpoint cortex path failed: %s", exc)

        # Fallback: raw sensations package without Cortex
        sens = []
        if hasattr(kernel, "get_last_sensations"):
            for s in kernel.get_last_sensations():
                if hasattr(s, "to_dict"):
                    sens.append(s.to_dict())
                elif isinstance(s, dict):
                    sens.append(s)
        state = kernel.get_state()
        return {
            "ok": True,
            "experience": {
                "affective_core": state.get("context"),
                "salient_sensations": sens,
                "source": "fallback_no_cortex",
            },
            "source": "fallback",
        }

    @app.get("/api/v1/cortex/status", tags=["Cortex"])
    async def cortex_status_endpoint(
        _: str = Depends(check_rate_limit),
    ) -> Dict[str, Any]:
        cortex = getattr(app.state, "cortex", None)
        if cortex is None:
            return {"ok": False, "attached": False}
        try:
            return {"ok": True, "attached": True, "status": cortex.status()}
        except Exception as exc:
            return {"ok": False, "attached": True, "error": str(exc)}

    @app.get("/api/v1/cortex/trend", tags=["Cortex"])
    async def cortex_trend_endpoint(
        _: str = Depends(check_rate_limit),
    ) -> Dict[str, Any]:
        cortex = getattr(app.state, "cortex", None)
        if cortex is None:
            return {"ok": False, "trend": None}
        return {"ok": True, "trend": cortex.get_trend()}

    @app.post("/api/v1/step", response_model=StepResponse, tags=["Control"])
    async def step_endpoint(
        body: StepRequest = StepRequest(),
        _: str = Depends(check_rate_limit),
    ) -> StepResponse:
        """Advance the kernel by one or more ticks. Returns actions taken.

        Each step also drives the shared abstraction layer so that sensations
        originating from (or queried via) the interface are kept live and can
        influence the visualization.
        """
        n = body.n
        all_actions: List[Dict[str, Any]] = []
        last_tick = None

        for _ in range(n):
            # Support optional extra stimuli in the request
            extra = None
            if body.extra_stimuli:
                from ..types import normalize_stimuli

                extra = normalize_stimuli(list(body.extra_stimuli))

            actions = kernel.step(extra_stimuli=extra)
            all_actions.extend([a.to_dict() for a in actions])
            last_tick = kernel.state.tick if hasattr(kernel, "state") else None

            # Drive abstraction on steps so interface signals keep producing rich sensations
            # that the visualization can reflect.
            try:
                _drive = app.state._drive_abstraction_and_feed
                _drive(1)
            except Exception as e:
                logger.debug("Abstraction drive during step failed (non-fatal): %s", e)

        return StepResponse(actions=all_actions, tick=last_tick)

    # Generic command fallback for maximum compatibility with existing command surface
    @app.post("/api/v1/command", response_model=Dict[str, Any], tags=["Control"])
    async def generic_command(
        body: CommandRequest,
        _: str = Depends(check_rate_limit),
    ) -> Dict[str, Any]:
        """Generic command passthrough (for tools already using the dict-based command surface)."""
        cmd_dict = body.model_dump(exclude_unset=True)
        result = kernel.command(cmd_dict)
        return result

    # ------------------------------------------------------------------
    # WebSocket (real-time events) - basic version, enhanced in next step
    # ------------------------------------------------------------------

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket, api_key: Optional[str] = None):
        # Simple auth for WS: query param or header (header harder in some clients)
        # For production, prefer query ?api_key=... or proper subprotocol, but we support header via upgrade.
        provided_key = api_key or websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")

        expected = server_config.api_key
        if not provided_key or provided_key != expected:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
            return

        await websocket.accept()
        logger.info("WebSocket client connected for events")

        client_queue = await broadcaster.subscribe()

        try:
            # Send hello
            await websocket.send_json(
                EventMessage(type="hello", data={"version": "0.2.0", "msg": "connected to ReflexKernel events"}).model_dump()
            )

            # Background task to forward events from the queue
            async def forwarder():
                while True:
                    try:
                        event = await client_queue.get()
                        await websocket.send_json(event)
                    except Exception:
                        break

            forward_task = asyncio.create_task(forwarder())

            # Listen for client messages (subscriptions, pings, etc.)
            while True:
                try:
                    msg = await websocket.receive_json()
                    # Simple protocol
                    if msg.get("ping"):
                        await websocket.send_json({"type": "pong", "ts": time.time()})
                    elif "subscribe" in msg:
                        # For now we broadcast everything; client can filter
                        await websocket.send_json({"type": "subscribed", "filters": msg["subscribe"]})
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.debug("WS receive error: %s", e)
                    break

            forward_task.cancel()
        except Exception as e:
            logger.warning("WebSocket error: %s", e)
        finally:
            await broadcaster.unsubscribe(client_queue)
            logger.info("WebSocket client disconnected")

    # ------------------------------------------------------------------
    # Health & Meta
    # ------------------------------------------------------------------

    @app.get("/health", tags=["Meta"])
    async def health() -> Dict[str, Any]:
        return {"status": "ok", "kernel_tick": kernel.state.tick if hasattr(kernel, "state") else -1}

    @app.get("/", tags=["Meta"])
    async def root() -> Dict[str, Any]:
        return {
            "name": "ReflexKernel Remote Interface",
            "version": "0.2.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": [
                "/api/v1/thought", "/api/v1/reward", "/api/v1/demo/begin", "/api/v1/demo/end",
                "/api/v1/stimulus", "/api/v1/state", "/api/v1/step", "/api/v1/command",
                "/ws/events", "/docs"
            ],
        }

    # ------------------------------------------------------------------
    # Wire kernel events -> broadcaster (powers the WebSocket /ws/events)
    # ------------------------------------------------------------------
    def _kernel_event_to_broadcaster(event_type: str, payload: Dict[str, Any]) -> None:
        try:
            msg = EventMessage(type=event_type, data=payload, ts=time.time()).model_dump()
            # Fire-and-forget into the async broadcaster
            asyncio.create_task(broadcaster.broadcast(msg))
        except Exception:
            # Never let event forwarding break anything
            pass

    if hasattr(kernel, "add_event_callback"):
        kernel.add_event_callback(_kernel_event_to_broadcaster)

    # Expose for debugging / advanced use
    app.state.broadcaster = broadcaster
    app.state.kernel = kernel
    app.state.server_config = server_config

    return app


# ------------------------------------------------------------------
# Convenience runner (used by scripts/server.py)
# ------------------------------------------------------------------

def run_server(
    kernel: Optional[ReflexKernel] = None,
    server_config: Optional[ServerConfig] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    log_level: str = "info",
) -> None:
    """Run the server with uvicorn (blocking)."""
    try:
        import uvicorn
    except ImportError as e:
        raise RuntimeError("uvicorn is required for run_server. Install with: pip install -e .[server]") from e

    app = create_app(kernel=kernel, server_config=server_config)

    effective_host = host or (server_config.host if server_config else "127.0.0.1")
    effective_port = port or (server_config.port if server_config else 8000)

    logger.info("Starting ReflexKernel remote server on http://%s:%d", effective_host, effective_port)
    uvicorn.run(
        app,
        host=effective_host,
        port=effective_port,
        log_level=log_level,
        access_log=True,
    )


__all__ = ["create_app", "run_server", "EventBroadcaster", "SimpleRateLimiter"]
