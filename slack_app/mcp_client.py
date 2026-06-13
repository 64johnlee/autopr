"""Persistent MCP stdio client for the AutoPR server.

The Slack agent is an MCP *client*: it spawns the `autopr-mcp` server as a
subprocess and calls its tools over stdio. The session is kept open for the life
of the app so that a `code_fix` preview and a later `open_pr` hit the *same*
server process (the session registry lives in that process's memory).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("autopr.slack.mcp")


def _parse_tool_result(res: Any) -> dict[str, Any]:
    """Normalize an MCP CallToolResult into a plain dict: structuredContent first
    (our tools return dicts), then JSON text content, else an error dict."""
    if getattr(res, "structuredContent", None) is not None:
        return res.structuredContent
    for c in getattr(res, "content", None) or []:
        text = getattr(c, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": False, "error": text}
    return {"success": False, "error": "empty MCP response"}


class AutoPRMCP:
    """A long-lived connection to the AutoPR MCP server."""

    def __init__(self, command: str = "autopr-mcp", args: list[str] | None = None) -> None:
        # Inherit the full parent environment so the server sees DASHSCOPE_API_KEY,
        # GITHUB_TOKEN, PATH, and the gh CLI config.
        self._params = StdioServerParameters(
            command=command,
            args=args or [],
            env=dict(os.environ),
        )
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()  # serialize calls; one server, one session

    async def start(self) -> None:
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(self._params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        tools = await self._session.list_tools()
        logger.info("AutoPR MCP connected — tools: %s", [t.name for t in tools.tools])

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("AutoPRMCP.start() not called")
        async with self._lock:
            res = await self._session.call_tool(name, arguments)
        return _parse_tool_result(res)

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None
