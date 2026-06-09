"""Coder agent: Qwen tool-loop that clones a repo and writes a fix."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from . import qwen
from .models import BountyIssue, CoderResult
from .prompts import CODER_SYSTEM

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 20
_SAFE_COMMANDS  = {"cargo", "go", "python", "python3", "pytest", "npm", "yarn",
                   "mvn", "gradle", "make", "rustfmt", "gofmt", "black", "ruff"}


# ── Tool definitions (OpenAI function-calling format) ────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files/directories at a path in the repo",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path (use '.' for root)"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repo",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "description": "1-based, optional"},
                    "end_line":   {"type": "integer", "description": "1-based, optional"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern across the repo (grep -rn)",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern":   {"type": "string"},
                    "file_glob": {"type": "string", "description": "e.g. '*.py' (optional)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a file in the repo",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a build/test command (safe commands only)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. 'cargo test', 'pytest tests/'"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal completion. Call when the fix is ready or you give up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "success":        {"type": "boolean"},
                    "commit_message": {"type": "string"},
                    "reason":         {"type": "string", "description": "if success=false, explain why"},
                },
                "required": ["success", "commit_message"],
            },
        },
    },
]


# ── Tool executor ─────────────────────────────────────────────────────────────

class _ToolExecutor:
    def __init__(self, repo_path: Path, on_event: Callable[[str], None]) -> None:
        self.repo_path = repo_path
        self.on_event  = on_event
        self.finished: dict | None = None

    def _rel(self, path: str) -> Path:
        p = (self.repo_path / path).resolve()
        if not str(p).startswith(str(self.repo_path)):
            raise ValueError(f"Path escapes repo: {path}")
        return p

    def list_files(self, path: str) -> str:
        p = self._rel(path)
        if not p.exists():
            return f"ERROR: {path} does not exist"
        if p.is_file():
            return f"(file) {path}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []
        for e in entries[:80]:
            prefix = "  " if e.is_file() else "📁 "
            lines.append(f"{prefix}{e.name}")
        return "\n".join(lines) or "(empty)"

    def read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        p = self._rel(path)
        if not p.exists():
            return f"ERROR: {path} not found"
        try:
            lines = p.read_text(errors="replace").splitlines()
        except Exception as exc:
            return f"ERROR: {exc}"
        if start_line or end_line:
            s = (start_line or 1) - 1
            e = end_line or len(lines)
            lines = lines[s:e]
        numbered = "\n".join(f"{i+1:4}: {l}" for i, l in enumerate(lines, start=(start_line or 1) - 1))
        return numbered[:20000]

    def search_code(self, pattern: str, file_glob: str | None = None) -> str:
        cmd = ["grep", "-rn", "--include", file_glob or "*", pattern, "."]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=self.repo_path)
            out = r.stdout[:8000]
            return out or "(no matches)"
        except Exception as exc:
            return f"ERROR: {exc}"

    def write_file(self, path: str, content: str) -> str:
        p = self._rel(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        self.on_event(f"wrote {path} ({len(content)} chars)")
        return f"OK: wrote {path}"

    def run_command(self, command: str) -> str:
        parts = command.split()
        if not parts or parts[0] not in _SAFE_COMMANDS:
            return f"ERROR: command '{parts[0] if parts else ''}' not in allowlist"
        self.on_event(f"$ {command}")
        try:
            r = subprocess.run(
                parts, capture_output=True, text=True,
                timeout=120, cwd=self.repo_path
            )
            out = (r.stdout + r.stderr)[-6000:]
            return f"exit={r.returncode}\n{out}"
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out (120s)"
        except Exception as exc:
            return f"ERROR: {exc}"

    def finish(self, success: bool, commit_message: str, reason: str = "") -> str:
        self.finished = {"success": success, "commit_message": commit_message, "reason": reason}
        return "OK"

    def execute(self, name: str, args: dict) -> str:
        fn = getattr(self, name, None)
        if fn is None:
            return f"ERROR: unknown tool {name}"
        try:
            return fn(**args)
        except Exception as exc:
            return f"ERROR: {exc}"


# ── Main coder agent ──────────────────────────────────────────────────────────

async def fix_issue(
    issue: BountyIssue,
    on_event: Callable[[str], None] | None = None,
) -> CoderResult:
    """Clone the repo, run the Qwen tool loop, return CoderResult."""

    if on_event is None:
        on_event = lambda msg: logger.info("[coder] %s", msg)

    start = time.monotonic()
    work_dir = Path(tempfile.mkdtemp(prefix="autopr_"))

    try:
        # Clone (shallow)
        on_event(f"cloning {issue.repo}…")
        result = subprocess.run(
            ["gh", "repo", "clone", issue.repo, str(work_dir), "--", "--depth=1"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return CoderResult(success=False, error=f"clone failed: {result.stderr[:500]}")

        executor = _ToolExecutor(work_dir, on_event)

        prompt = f"""Repository: {issue.repo}
Issue #{issue.issue_number}: {issue.title}

{issue.body[:4000]}

Fix this issue. Start by exploring the repo structure, then read the relevant files."""

        messages: list[dict] = [{"role": "user", "content": prompt}]
        tool_calls = 0

        for iteration in range(_MAX_ITERATIONS):
            on_event(f"iteration {iteration + 1}/{_MAX_ITERATIONS}")

            resp = await qwen.code(messages, tools=_TOOLS, system=CODER_SYSTEM)
            msg  = resp.choices[0].message
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in (msg.tool_calls or [])
            ]})

            if not msg.tool_calls:
                # Model stopped without calling finish — treat as done if files changed
                break

            results = []
            for tc in msg.tool_calls:
                tool_calls += 1
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                on_event(f"→ {name}({_fmt(args)})")
                output = executor.execute(name, args)
                results.append({"role": "tool", "tool_call_id": tc.id, "content": output})

            messages.extend(results)

            if executor.finished is not None:
                break

        elapsed = time.monotonic() - start

        if executor.finished and not executor.finished["success"]:
            return CoderResult(
                success=False,
                error=executor.finished.get("reason", "agent gave up"),
                tool_calls=tool_calls,
                elapsed_s=round(elapsed, 2),
            )

        # Collect changed files
        diff = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=work_dir
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=work_dir
        )
        changed = [
            l.strip() for l in
            (diff.stdout + untracked.stdout).splitlines()
            if l.strip()
        ]

        if not changed:
            return CoderResult(
                success=False, error="no files changed",
                tool_calls=tool_calls, elapsed_s=round(elapsed, 2),
            )

        commit_msg = (executor.finished or {}).get("commit_message") or f"fix: address #{issue.issue_number}"
        branch = f"autopr/issue-{issue.issue_number}"

        # Create branch + commit inside work_dir
        subprocess.run(["git", "checkout", "-b", branch], cwd=work_dir, capture_output=True)
        subprocess.run(["git", "add"] + changed, cwd=work_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=work_dir, capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "AutoPR", "GIT_AUTHOR_EMAIL": "autopr@autopr.dev",
                 "GIT_COMMITTER_NAME": "AutoPR", "GIT_COMMITTER_EMAIL": "autopr@autopr.dev"},
        )

        # Stash work_dir path in branch field so pr_submitter can find it
        return CoderResult(
            success=True,
            changed_files=changed,
            commit_message=commit_msg,
            branch=f"{branch}::{work_dir}",  # packed: branch::path
            tool_calls=tool_calls,
            elapsed_s=round(elapsed, 2),
        )

    except Exception as exc:
        return CoderResult(success=False, error=str(exc),
                           elapsed_s=round(time.monotonic() - start, 2))
    finally:
        # work_dir cleaned up by pr_submitter after push, or here on failure
        pass


def _fmt(args: dict) -> str:
    s = json.dumps(args, default=str)
    return (s[:60] + "…") if len(s) > 60 else s
