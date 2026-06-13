"""Shared agent service — the kernel-facing operations behind every front-end.

Both the MCP server (`mcp_server.py`, for Slack/Claude Desktop) and the REST API
(`api_server.py`, for UiPath Maestro) are thin adapters over these functions, so
there is a single source of truth for: clone → Qwen tool-loop → commit → diff
(`run_code_fix`), fork → push → PR (`run_open_pr`), and cleanup (`run_discard`).

`run_code_fix` returns a structured dict and stores a session; `run_open_pr`
consumes it. Decoupled from the bounty scanner via a synthetic BountyIssue.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from .coder import fix_issue
from .models import BountyIssue, CoderResult
from .pr_submitter import submit

logger = logging.getLogger("autopr.service")

# session_id → (issue, coder_result); a preview can be shipped by run_open_pr later.
# In-process registry; fine for a single-worker server.
_SESSIONS: dict[str, tuple[BountyIssue, CoderResult]] = {}

_MAX_TRACE = 40  # cap the agent trace returned to callers


def _synthetic_issue(repo: str, task: str, issue_number: int) -> BountyIssue:
    """Build a BountyIssue from a free-form task so the bounty-shaped kernel can be
    reused for arbitrary 'fix this in that repo' requests."""
    title = task.strip().splitlines()[0][:120] if task.strip() else f"task in {repo}"
    return BountyIssue(
        source="service",
        repo=repo,
        issue_number=issue_number,
        title=title,
        body=task,
        url=f"https://github.com/{repo}",
        amount_usd=0.0,
    )


def _unpack_work_dir(result: CoderResult) -> Path | None:
    """coder.fix_issue packs the work dir into branch as 'branch::path'."""
    if "::" not in result.branch:
        return None
    work_dir = Path(result.branch.split("::", 1)[1])
    return work_dir if work_dir.exists() else None


def _compute_diff(work_dir: Path) -> str:
    """Unified diff of the single commit the agent just made."""
    r = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        cwd=work_dir, capture_output=True, text=True, timeout=30,
    )
    return (r.stdout or "")[:20000]


async def run_code_fix(repo: str, task: str, issue_number: int = 0) -> dict[str, Any]:
    """Clone, run the coding agent, commit locally, and return a diff to preview.

    Returns a structured dict (success, session_id, changed_files, commit_message,
    diff, tool_calls, elapsed_s, trace). Nothing is pushed. Hand session_id to
    run_open_pr to open the PR.
    """
    trace: list[str] = []
    issue = _synthetic_issue(repo, task, issue_number)
    result = await fix_issue(issue, on_event=trace.append)

    if not result.success:
        return {
            "success": False,
            "error": result.error,
            "tool_calls": result.tool_calls,
            "elapsed_s": result.elapsed_s,
            "trace": trace[-_MAX_TRACE:],
        }

    work_dir = _unpack_work_dir(result)
    diff = _compute_diff(work_dir) if work_dir else "(diff unavailable)"

    session_id = uuid.uuid4().hex[:8]
    _SESSIONS[session_id] = (issue, result)

    return {
        "success": True,
        "session_id": session_id,
        "repo": repo,
        "changed_files": result.changed_files,
        "commit_message": result.commit_message,
        "diff": diff,
        "tool_calls": result.tool_calls,
        "elapsed_s": result.elapsed_s,
        "trace": trace[-_MAX_TRACE:],
    }


def run_open_pr(session_id: str) -> dict[str, Any]:
    """Open a PR from a previously previewed fix. Consumes the session."""
    entry = _SESSIONS.pop(session_id, None)
    if entry is None:
        return {"success": False, "error": f"unknown or already-consumed session: {session_id}"}
    issue, result = entry
    pr = submit(issue, result)  # forks, pushes, opens PR, cleans up work_dir
    return {
        "success": pr.success,
        "pr_url": pr.pr_url,
        "pr_number": pr.pr_number,
        "error": pr.error,
    }


def run_discard(session_id: str) -> dict[str, Any]:
    """Discard a previewed fix without opening a PR, cleaning up its working dir."""
    entry = _SESSIONS.pop(session_id, None)
    if entry is None:
        return {"success": False, "error": f"unknown session: {session_id}"}
    _, result = entry
    work_dir = _unpack_work_dir(result)
    if work_dir is not None:
        shutil.rmtree(work_dir, ignore_errors=True)
    return {"success": True, "discarded": session_id}
