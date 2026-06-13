#!/usr/bin/env python
"""Live test for the AutoPR MCP server — drives it through the real stdio client.

This exercises the full path the Slack agent uses: spawn `autopr-mcp`, call
`code_fix` (clone → Qwen tool-loop → commit → diff), and optionally `open_pr`.

PREVIEW is the default and has NO side effects — it clones a repo, lets the agent
write a fix locally, and prints the diff. Nothing is pushed.

Usage
-----
  # 0. (optional, one-time) make a safe planted-bug repo you own to test against:
  python live_test.py --create-demo-repo autopr-demo

  # 1. preview a fix (no PR) — validates clone + Qwen loop + diff:
  python live_test.py owner/repo "Fix the add() bug in calc.py" --issue 1

  # 2. ship it (fork → push → PR). NOTE: pr_submitter FORKS the target, so this
  #    is meant for a repo you do NOT own (the bounty flow):
  python live_test.py owner/repo "..." --issue 1 --open-pr

Requirements: DASHSCOPE_API_KEY in .env, and an authenticated `gh` CLI.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from slack_app.mcp_client import AutoPRMCP  # the same client the Slack app uses

load_dotenv()  # pull DASHSCOPE_API_KEY / GITHUB_TOKEN from the repo .env

SERVER_CMD = sys.executable
SERVER_ARGS = ["-m", "autopr.mcp_server"]


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def preflight(need_gh: bool) -> None:
    problems: list[str] = []
    if not os.environ.get("DASHSCOPE_API_KEY"):
        problems.append("DASHSCOPE_API_KEY is not set (add it to .env).")
    gh = _run(["gh", "auth", "status"])
    if gh.returncode != 0:
        problems.append("`gh` is not authenticated — run:  gh auth login")
    if problems:
        print("Preflight failed:")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(1)
    print("Preflight OK — DASHSCOPE_API_KEY set, gh authenticated.\n")


def create_demo_repo(name: str) -> None:
    """Create a public repo you own with a planted bug + an issue describing it."""
    preflight(need_gh=True)
    who = _run(["gh", "api", "user", "--jq", ".login"])
    user = who.stdout.strip()
    if not user:
        print("Could not determine your GitHub login.")
        sys.exit(1)
    full = f"{user}/{name}"
    print(f"Creating demo repo {full} …")

    c = _run(["gh", "repo", "create", name, "--public", "--add-readme",
              "--description", "AutoPR demo target (planted bug)"])
    if c.returncode != 0 and "already exists" not in (c.stderr + c.stdout):
        print("repo create failed:\n", c.stderr)
        sys.exit(1)

    work = tempfile.mkdtemp(prefix="autopr_demo_")
    if _run(["gh", "repo", "clone", full, work]).returncode != 0:
        print("clone failed")
        sys.exit(1)

    (Path(work) / "calc.py").write_text(
        "def add(a, b):\n    # BUG: subtracts instead of adding\n    return a - b\n")
    (Path(work) / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    _run(["git", "add", "-A"], cwd=work)
    _run(["git", "commit", "-m", "init: calculator with a planted bug"], cwd=work)
    push = _run(["git", "push"], cwd=work)
    if push.returncode != 0:
        print("push failed:\n", push.stderr)
        sys.exit(1)

    issue = _run(["gh", "issue", "create", "--repo", full,
                  "--title", "add() returns the wrong result",
                  "--body", "`add(2, 3)` returns -1 but should return 5. "
                            "`test_calc.py` fails. Fix the bug in `calc.py`."])
    url = issue.stdout.strip()
    number = url.rstrip("/").split("/")[-1] if url else "1"
    print(f"\n✓ Demo repo ready: https://github.com/{full}")
    print(f"✓ Issue #{number}: add() returns the wrong result\n")
    print("Now run the preview test:")
    print(f'  python live_test.py {full} "Fix the add() bug so tests pass" --issue {number}')


async def run_fix(repo: str, task: str, issue: int, open_pr: bool) -> None:
    preflight(need_gh=True)
    print(f"Target : {repo}  (issue #{issue})")
    print(f"Task   : {task}")
    print(f"Mode   : {'OPEN PR (forks + pushes + opens PR)' if open_pr else 'PREVIEW only (no push)'}\n")

    cli = AutoPRMCP(command=SERVER_CMD, args=SERVER_ARGS)
    await cli.start()
    try:
        print("Running code_fix … (cloning, then the Qwen agent works — this can take a minute)\n")
        result = await cli.call("code_fix", {"repo": repo, "task": task, "issue_number": issue})

        if not result.get("success"):
            print("✗ code_fix did not produce a fix")
            print("  error:", result.get("error"))
            _print_trace(result)
            return

        print("✓ Fix produced")
        print("  commit :", result.get("commit_message"))
        print("  files  :", ", ".join(result.get("changed_files", [])))
        print(f"  stats  : {result.get('tool_calls')} tool calls · {result.get('elapsed_s')}s")
        _print_trace(result)
        print("\n----- DIFF -----")
        print(result.get("diff") or "(empty)")
        print("----------------\n")

        if open_pr:
            print("Opening PR …")
            pr = await cli.call("open_pr", {"session_id": result["session_id"]})
            if pr.get("success"):
                print("✓ PR opened:", pr.get("pr_url"))
            else:
                print("✗ open_pr failed:", pr.get("error"))
        else:
            print("PREVIEW done. Re-run with --open-pr to fork, push, and open the PR.")
    finally:
        await cli.stop()


def _print_trace(result: dict) -> None:
    trace = result.get("trace") or []
    if trace:
        print("\n  agent trace (last steps):")
        for line in trace[-12:]:
            print("   ·", line)


def main() -> None:
    p = argparse.ArgumentParser(description="Live test for the AutoPR MCP server")
    p.add_argument("repo", nargs="?", help="owner/repo to fix")
    p.add_argument("task", nargs="?", help="what to fix (free text)")
    p.add_argument("--issue", type=int, default=0, help="issue number to reference")
    p.add_argument("--open-pr", action="store_true", help="actually fork+push+open the PR")
    p.add_argument("--create-demo-repo", metavar="NAME",
                   help="create a planted-bug repo you own to test against")
    args = p.parse_args()

    if args.create_demo_repo:
        create_demo_repo(args.create_demo_repo)
        return
    if not args.repo or not args.task:
        p.error("provide REPO and TASK, or use --create-demo-repo NAME")
    asyncio.run(run_fix(args.repo, args.task, args.issue, args.open_pr))


if __name__ == "__main__":
    main()
