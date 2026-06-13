"""AutoPR MCP server — exposes the autonomous coder kernel as MCP tools.

Thin MCP adapter over `agent_service` (the shared kernel-facing operations). Any
MCP host (a Slack agent, Claude Desktop, or a UiPath-orchestrated agent) can drive
AutoPR. The REST API in `api_server.py` wraps the same service for UiPath Maestro.

Two-step, human-in-the-loop flow:
    1. ``code_fix(repo, task)``  → clone, run the agent, return a unified diff to
                                   PREVIEW. Nothing is pushed.
    2. ``open_pr(session_id)``   → fork, push the branch, open the PR. SHIP it.

Run (stdio, for Claude Desktop / local hosts):
    autopr-mcp

Run (HTTP/SSE, for a remote Slack app to reach):
    AUTOPR_MCP_TRANSPORT=sse AUTOPR_MCP_PORT=8000 autopr-mcp
"""
from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .agent_service import run_code_fix, run_discard, run_open_pr

load_dotenv()

logger = logging.getLogger("autopr.mcp")

mcp = FastMCP("autopr")


@mcp.tool()
async def code_fix(repo: str, task: str, issue_number: int = 0) -> dict[str, Any]:
    """Autonomously write a fix for a task in a GitHub repo and return a diff to preview.

    Clones the repo, runs the Qwen tool-loop coding agent (read/search/write/run
    tools in a sandbox), commits locally, and returns the patch WITHOUT pushing.
    Hand the returned ``session_id`` to ``open_pr`` to actually open the PR.

    Args:
        repo: GitHub repo as "owner/name".
        task: What to fix — an issue body, a bug report, or a plain instruction.
        issue_number: Optional issue number to reference (branch naming, "Closes #N").

    Returns:
        dict with success, changed_files, commit_message, diff, tool_calls,
        elapsed_s, trace, and session_id (for open_pr).
    """
    return await run_code_fix(repo, task, issue_number)


@mcp.tool()
async def open_pr(session_id: str) -> dict[str, Any]:
    """Open a pull request from a previously previewed fix.

    Forks the target repo, pushes the agent's branch, and opens the PR. Consumes
    the session created by ``code_fix``; the working directory is cleaned up after.
    """
    return run_open_pr(session_id)


@mcp.tool()
async def discard(session_id: str) -> dict[str, Any]:
    """Discard a previewed fix without opening a PR, cleaning up its working dir."""
    return run_discard(session_id)


def main() -> None:
    """Console entrypoint. Defaults to stdio; set AUTOPR_MCP_TRANSPORT=sse for HTTP."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    transport = os.environ.get("AUTOPR_MCP_TRANSPORT", "stdio").lower()
    if transport in ("sse", "http", "streamable-http"):
        port = int(os.environ.get("AUTOPR_MCP_PORT", "8000"))
        mcp.settings.port = port
        logger.info("AutoPR MCP serving over %s on :%d", transport, port)
        mcp.run(transport="sse" if transport == "sse" else "streamable-http")
    else:
        logger.info("AutoPR MCP serving over stdio")
        mcp.run()


if __name__ == "__main__":
    main()
