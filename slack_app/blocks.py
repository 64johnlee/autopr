"""Block Kit builders for the AutoPR Slack agent."""
from __future__ import annotations

from typing import Any

_DIFF_LIMIT = 2800  # Slack section text caps at 3000 chars; leave room for fences.


def _code(text: str, limit: int) -> str:
    body = text if len(text) <= limit else text[:limit] + "\n… (truncated)"
    return f"```\n{body}\n```"


def working_blocks(repo: str, task: str) -> list[dict[str, Any]]:
    return [
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f":hammer_and_wrench: *AutoPR is on it* — `{repo}`\n>{task[:200]}"}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": "Cloning, reading the repo, and writing a fix… this can take a minute."}]},
    ]


def preview_blocks(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Diff preview with Open PR / Discard buttons. `result` is a code_fix payload."""
    repo = result.get("repo", "")
    session_id = result["session_id"]
    files = result.get("changed_files", [])
    commit = result.get("commit_message", "")
    diff = result.get("diff", "") or "(no diff)"
    elapsed = result.get("elapsed_s", 0)
    calls = result.get("tool_calls", 0)

    file_list = "\n".join(f"• `{f}`" for f in files[:20]) or "_(none)_"

    return [
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f":white_check_mark: *Proposed fix for* `{repo}`\n*{commit}*"}},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*Files changed*\n{file_list}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": _code(diff, _DIFF_LIMIT)}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f":robot_face: {calls} tool calls · {elapsed}s · powered by Qwen"}]},
        {"type": "actions", "elements": [
            {"type": "button", "style": "primary",
             "text": {"type": "plain_text", "text": "Open PR"},
             "action_id": "open_pr", "value": session_id},
            {"type": "button", "style": "danger",
             "text": {"type": "plain_text", "text": "Discard"},
             "action_id": "discard", "value": session_id},
        ]},
    ]


def pr_opened_blocks(pr_url: str) -> list[dict[str, Any]]:
    return [{"type": "section", "text": {"type": "mrkdwn",
             "text": f":rocket: *Pull request opened*\n<{pr_url}>"}}]


def discarded_blocks() -> list[dict[str, Any]]:
    return [{"type": "section", "text": {"type": "mrkdwn",
             "text": ":wastebasket: Fix discarded — nothing was pushed."}}]


def error_blocks(message: str) -> list[dict[str, Any]]:
    return [{"type": "section", "text": {"type": "mrkdwn",
             "text": f":warning: *AutoPR couldn't complete this*\n>{message[:500]}"}}]


def usage_blocks() -> list[dict[str, Any]]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": (
        "*AutoPR* fixes GitHub issues autonomously. Mention me with a repo:\n"
        "• `@AutoPR owner/repo#42 the CSV parser crashes on empty input`\n"
        "• `@AutoPR https://github.com/owner/repo/issues/42`\n"
        "I'll show you the diff first, then you click *Open PR* to ship it.")}}]
