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
)

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

    # Rate limiter
    rate_limiter = SimpleRateLimiter(server_config.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("ReflexKernel server starting (server enabled=%s)", server_config.enabled)
        if not kernel._running:  # type: ignore[attr-defined]
            kernel.start()
        yield
        # Shutdown
        logger.info("ReflexKernel server shutting down...")
        if kernel._running:  # type: ignore[attr-defined]
            kernel.stop()

    app = FastAPI(
        title="ReflexKernel Remote API",
        description=(
            "Remote control surface for ReflexKernel — the low-level trainable nervous system.\n\n"
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
            {"name": "Events", "description": "WebSocket real-time streaming."},
        ],
        lifespan=lifespan,
    )

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
        """Inject a thought / affective seed (equivalent to inject_thought_seed)."""
        logger.info("Remote thought seed received: %s", {k: v for k, v in body.model_dump().items() if v is not None})
        kernel.inject_thought_seed(body.model_dump(exclude_unset=True))
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
        """Inject a raw stimulus (useful for remote simulation of world events)."""
        stim_dict = body.model_dump(exclude_unset=True)
        from ..types import Stimulus  # local import to avoid circular issues at top level

        try:
            stim = Stimulus.from_dict(stim_dict)
        except Exception:
            stim = Stimulus(modality=body.modality, data=body.data, confidence=body.confidence, source=body.source)
        kernel.step(extra_stimuli=[stim])
        return AckResponse(ok=True)

    @app.get("/api/v1/state", response_model=StateResponse, tags=["Control"])
    async def get_state_endpoint(
        _: str = Depends(check_rate_limit),
    ) -> StateResponse:
        """Return the current observable state of the kernel."""
        state = kernel.get_state()
        return StateResponse(**state)

    @app.post("/api/v1/step", response_model=StepResponse, tags=["Control"])
    async def step_endpoint(
        body: StepRequest = StepRequest(),
        _: str = Depends(check_rate_limit),
    ) -> StepResponse:
        """Advance the kernel by one or more ticks. Returns actions taken."""
        n = body.n
        all_actions: List[Dict[str, Any]] = []
        last_tick = None

        for _ in range(n):
            # Support optional extra stimuli in the request
            extra = None
            if body.extra_stimuli:
                from ..types import Stimulus
                extra = [Stimulus.from_dict(s) for s in body.extra_stimuli]

            actions = kernel.step(extra_stimuli=extra)
            all_actions.extend([a.to_dict() for a in actions])
            last_tick = kernel.state.tick if hasattr(kernel, "state") else None

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
