"""
Integration helpers between Sensory Cortex and ReflexKernel / Saddle.

Soft dependencies: functions degrade gracefully if RK or network libs missing.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure repo root importable when loaded from ReflexKernel tree
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def try_create_cortex(
    mode: str = "embedded",
    bind_api: Any = None,
) -> Optional[Any]:
    """Create a SensoryCortex instance; return None if package unavailable."""
    try:
        from SensoryCortex import SensoryCortex, load_config
    except ImportError:
        return None
    cfg = load_config()
    d = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg.dict()
    d.setdefault("interface", {})["mode"] = mode
    cortex = SensoryCortex(config=d, mode=mode)
    if bind_api is not None:
        cortex.bind_reflex(bind_api)
    return cortex


def feed_cortex_from_kernel(
    cortex: Any,
    kernel: Any,
    *,
    body_state: Optional[Dict[str, Any]] = None,
    sensations: Optional[List[Any]] = None,
    respect_gate: bool = True,
    force: bool = False,
) -> Optional[Any]:
    """Package live kernel state into a SensoryUpdate (or None if gated)."""
    if cortex is None:
        return None
    try:
        from SensoryCortex.adapters import from_kernel
    except ImportError:
        return None
    coherent = from_kernel(
        kernel,
        sensations=sensations,
        body_state=body_state,
    )
    try:
        return cortex.process_coherent_input(
            coherent, respect_gate=respect_gate, force=force
        )
    except Exception:
        return None


def experience_to_dict(update: Any) -> Optional[Dict[str, Any]]:
    if update is None:
        return None
    if hasattr(update, "model_dump"):
        return update.model_dump(mode="json")
    if hasattr(update, "dict"):
        return update.dict()
    return None


class SaddleEventConsumer:
    """
    Service-mode background client: listen to Saddle ``/ws/events`` and
    optionally poll ``/api/v1/state``, feeding Sensory Cortex.

    Runs in a daemon thread. Requires ``websockets`` or stdlib is not enough
    for WS easily — use urllib for poll fallback + optional websockets.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        api_key: str = "reflexkernel-dev",
        cortex: Any = None,
        poll_interval: float = 0.5,
        use_websocket: bool = True,
        on_experience: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.cortex = cortex or try_create_cortex(mode="service")
        self.poll_interval = poll_interval
        self.use_websocket = use_websocket
        self.on_experience = on_experience
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_experience: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    @property
    def last_experience(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last_experience

    def start(self) -> "SaddleEventConsumer":
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="saddle-cortex-consumer", daemon=True
        )
        self._thread.start()
        return self

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def _run(self) -> None:
        # Prefer poll loop (robust on Windows without extra deps).
        # Optional websocket upgrade if library present and use_websocket.
        if self.use_websocket:
            try:
                self._run_websocket()
                return
            except Exception:
                pass
        self._run_poll()

    def _run_poll(self) -> None:
        try:
            from urllib.request import Request, urlopen
        except ImportError:
            return
        url = f"{self.base_url}/api/v1/state?detail_level=normal"
        while not self._stop.is_set():
            try:
                req = Request(url, headers=self._headers())
                with urlopen(req, timeout=5) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                self._ingest_state_payload(payload)
            except Exception:
                pass
            self._stop.wait(self.poll_interval)

    def _run_websocket(self) -> None:
        """Optional websockets-based path; falls back by raising."""
        import asyncio

        try:
            import websockets  # type: ignore
        except ImportError as exc:
            raise RuntimeError("websockets not installed") from exc

        ws_base = self.base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        # Default saddle path is often /ws/events
        uri = f"{ws_base}/ws/events?api_key={self.api_key}"

        async def _loop():
            async with websockets.connect(uri) as ws:
                while not self._stop.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    data = msg.get("data") if isinstance(msg, dict) else None
                    if isinstance(data, dict) and (
                        "sensations" in data or "context" in data or "tick" in data
                    ):
                        self._ingest_state_payload(data)
                    elif isinstance(msg, dict) and msg.get("type") == "state":
                        self._ingest_state_payload(msg.get("data") or {})

        asyncio.run(_loop())

    def _ingest_state_payload(self, payload: Dict[str, Any]) -> None:
        if self.cortex is None or not isinstance(payload, dict):
            return
        try:
            from SensoryCortex.adapters import from_state_payload
        except ImportError:
            return
        coherent = from_state_payload(payload)
        update = self.cortex.process_coherent_input(
            coherent, respect_gate=True, force=False
        )
        if update is None:
            return
        exp = experience_to_dict(update)
        if exp is None:
            return
        with self._lock:
            self._last_experience = exp
        if self.on_experience:
            try:
                self.on_experience(exp)
            except Exception:
                pass
