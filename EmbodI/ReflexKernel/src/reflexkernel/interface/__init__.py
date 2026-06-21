"""Interface layer (higher intelligence ↔ ReflexKernel).

This package now provides robust remote connectivity in addition to the original
in-process (PythonAPI) and stdio options.

New in v0.2:
- Full FastAPI REST + WebSocket server (see server.py)
- create_app() and run_server() for remote "body as a service" use cases.
"""

from .python_api import PythonAPI
from .server import EventBroadcaster, create_app, run_server
from .stdio_adapter import StdioAdapter

__all__ = [
    "PythonAPI",
    "StdioAdapter",
    "create_app",
    "run_server",
    "EventBroadcaster",
]

try:
    from .websocket_server import run_server as legacy_run_server  # noqa: F401
    __all__.append("legacy_run_server")
except Exception:
    pass

