"""xAI chat adapter with client-side tool loop."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple


class XAIChatSession:
    """
    Thin wrapper around xai_sdk Client + multi-round tool calling.

    tool_dispatch(name, arguments_dict) -> str result for tool_result.
    """

    def __init__(
        self,
        model: str,
        tools: List[Any],
        tool_dispatch: Callable[[str, Dict[str, Any]], str],
        max_tool_rounds: int = 6,
        system_prompt: str = "",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.tools = tools
        self.tool_dispatch = tool_dispatch
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = system_prompt
        key = api_key or os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError(
                "XAI_API_KEY is not set. Set the user environment variable and restart the terminal."
            )
        from xai_sdk import Client

        self._client = Client(api_key=key)
        self._chat = None
        self._ensure_chat()

    def _ensure_chat(self) -> None:
        from xai_sdk.chat import system

        self._chat = self._client.chat.create(model=self.model, tools=self.tools)
        if self.system_prompt:
            self._chat.append(system(self.system_prompt))

    def reset(self) -> None:
        self._ensure_chat()

    def run_turn(
        self,
        user_text: str,
        *,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Tuple[str, int]:
        """
        Append a user message, sample, run tool loop, return (final_text, tool_rounds).
        """
        from xai_sdk.chat import user, tool_result

        assert self._chat is not None
        self._chat.append(user(user_text))
        if on_event:
            on_event("user", {"text": user_text[:2000]})

        rounds = 0
        final_content = ""

        while True:
            try:
                response = self._chat.sample()
            except Exception as exc:
                msg = f"[xAI error] {exc}"
                if on_event:
                    on_event("error", {"error": str(exc)})
                return msg, rounds

            content = getattr(response, "content", None) or ""
            tool_calls = list(getattr(response, "tool_calls", None) or [])

            if content:
                final_content = content
                if on_event:
                    on_event("assistant_partial", {"content": content[:2000]})

            if not tool_calls:
                if on_event:
                    on_event("assistant", {"content": final_content})
                return final_content or "", rounds

            if rounds >= self.max_tool_rounds:
                if on_event:
                    on_event(
                        "tool_limit",
                        {"max_tool_rounds": self.max_tool_rounds},
                    )
                return (
                    final_content
                    or f"[stopped: max tool rounds {self.max_tool_rounds} reached]",
                    rounds,
                )

            # Append assistant message that requested tools, then results
            self._chat.append(response)
            for tc in tool_calls:
                rounds += 1
                fn = getattr(tc, "function", None) or tc
                name = getattr(fn, "name", None) or getattr(tc, "name", "unknown")
                raw_args = getattr(fn, "arguments", None) or "{}"
                if isinstance(raw_args, dict):
                    args = raw_args
                else:
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}
                if on_event:
                    on_event("tool_call", {"name": name, "args": args})
                result_str = self.tool_dispatch(name, args)
                if on_event:
                    on_event(
                        "tool_result",
                        {"name": name, "result_preview": result_str[:500]},
                    )
                self._chat.append(tool_result(result_str))
