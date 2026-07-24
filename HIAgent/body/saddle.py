"""Remote Saddle HTTP body backend."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class SaddleBodyBackend:
    """Talk to a running ReflexKernel remote server (Saddle)."""

    name = "saddle"

    def __init__(self, config: Any):
        self.config = config
        self.base_url = str(
            getattr(config, "saddle_url", None) or "http://127.0.0.1:8000"
        ).rstrip("/")
        self.api_key = str(
            getattr(config, "saddle_api_key", None) or "reflexkernel-dev"
        )
        self._started = False
        self._last_error: Optional[str] = None
        self.timeout = 15.0

    def start(self) -> None:
        # Probe health
        try:
            health = self._request("GET", "/health")
            self._started = True
            self._last_error = None
            if not health.get("ok", True) and "status" not in health:
                pass
        except Exception as exc:
            self._last_error = str(exc)
            # Still mark started so tools return clear connection errors
            self._started = True
            raise RuntimeError(
                f"Cannot reach Saddle at {self.base_url}: {exc}"
            ) from exc

    def stop(self) -> None:
        self._started = False

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        query: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self._headers(), method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {"ok": True}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._last_error = f"HTTP {e.code}: {detail[:500]}"
            return {"ok": False, "error": self._last_error, "status": e.code}
        except Exception as e:
            self._last_error = str(e)
            return {"ok": False, "error": str(e)}

    def feel(self, force: bool = False) -> Dict[str, Any]:
        r = self._request(
            "GET",
            "/api/v1/experience",
            query={"force": "true" if force else "false"},
        )
        if r.get("ok") is False:
            return r
        return {
            "ok": True,
            "force": force,
            "experience": r.get("experience"),
            "source": r.get("source", "saddle"),
            "cortex_attached": r.get("source") == "sensory_cortex",
        }

    def body_snapshot(self) -> Dict[str, Any]:
        r = self._request(
            "GET", "/api/v1/state", query={"detail_level": "normal"}
        )
        return {"ok": r.get("ok", True) is not False, "state": r}

    def inject_thought(
        self,
        emotion: str = "neutral",
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5,
        text: str = "",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/thought",
            body={
                "emotion": emotion,
                "intensity": float(intensity),
                "valence": float(valence),
                "arousal": float(arousal),
                "text": text or "",
            },
        )

    def send_reward(
        self, value: float, reason: str = "", window_steps: int = 6
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/reward",
            body={
                "value": float(value),
                "reason": reason,
                "window_steps": int(window_steps),
            },
        )

    def inject_stimulus(
        self,
        kind: str = "sudden_sound",
        intensity: float = 0.7,
        modality: str = "sim",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/stimulus",
            body={
                "modality": modality,
                "data": {
                    "kind": kind,
                    "intensity": float(intensity),
                    "sim": True,
                },
                "source": "hi_agent",
            },
        )

    def step(self, n: int = 1) -> Dict[str, Any]:
        return self._request(
            "POST", "/api/v1/step", body={"n": max(1, int(n))}
        )

    def begin_demo(self, name: str) -> Dict[str, Any]:
        return self._request(
            "POST", "/api/v1/demo/begin", body={"name": name}
        )

    def end_demo(self, outcome: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/demo/end",
            body={"outcome": outcome or {}},
        )

    def recall(self, max_age_minutes: int = 20) -> Dict[str, Any]:
        # Saddle has trend/status; full recall may be cortex-local only
        trend = self._request("GET", "/api/v1/cortex/trend")
        return {
            "ok": True,
            "note": "Remote recall limited; trend from Saddle cortex if attached",
            "trend": trend,
            "max_age_minutes": max_age_minutes,
        }

    def status(self) -> Dict[str, Any]:
        health = self._request("GET", "/health")
        cortex = self._request("GET", "/api/v1/cortex/status")
        return {
            "backend": self.name,
            "started": self._started,
            "base_url": self.base_url,
            "health": health,
            "cortex": cortex,
            "last_error": self._last_error,
        }
