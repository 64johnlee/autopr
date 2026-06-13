"""Parse an AutoPR request out of a Slack mention.

Accepts forms like:
    @autopr fix owner/repo#42 the CSV parser crashes on empty input
    @autopr https://github.com/owner/repo/issues/42 please fix
    @autopr owner/repo make the README build badge link to CI
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Slack wraps the bot mention as <@U0123ABCD> — strip those.
_MENTION = re.compile(r"<@[\w]+>")
# A GitHub issue/PR URL.
_URL = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)")
# owner/repo#123 shorthand.
_SHORTHAND = re.compile(r"\b([\w.-]+/[\w.-]+)#(\d+)\b")
# bare owner/repo (fallback; matched last so the forms above win).
_REPO_ONLY = re.compile(r"\b([\w][\w.-]*/[\w][\w.-]*)\b")
# polite/filler prefixes to drop from the task text.
_FILLER = re.compile(r"^(please\s+|can you\s+|could you\s+|fix\s+|pls\s+)+", re.I)


@dataclass(frozen=True)
class ParsedRequest:
    repo: str
    issue_number: int
    task: str


def parse_request(text: str) -> ParsedRequest | None:
    """Extract repo, issue number, and task description. None if no repo found."""
    if not text:
        return None

    cleaned = _MENTION.sub(" ", text).strip()

    repo: str | None = None
    issue_number = 0
    matched_span: tuple[int, int] | None = None

    if (m := _URL.search(cleaned)):
        repo, issue_number, matched_span = m.group(1), int(m.group(2)), m.span()
    elif (m := _SHORTHAND.search(cleaned)):
        repo, issue_number, matched_span = m.group(1), int(m.group(2)), m.span()
    elif (m := _REPO_ONLY.search(cleaned)):
        repo, matched_span = m.group(1), m.span()

    if repo is None:
        return None

    # Task = everything except the matched repo token.
    task = (cleaned[: matched_span[0]] + " " + cleaned[matched_span[1] :]).strip()
    task = _FILLER.sub("", task).strip()
    if not task:
        task = f"Fix issue #{issue_number}" if issue_number else f"Address the open work in {repo}"

    return ParsedRequest(repo=repo, issue_number=issue_number, task=task)
