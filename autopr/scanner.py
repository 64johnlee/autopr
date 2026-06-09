"""Bounty issue scanner — Opire + Algora GitHub labels."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from .models import BountyIssue

logger = logging.getLogger(__name__)

OPIRE_API  = "https://api.opire.dev/rewards"
_HEADERS   = {"User-Agent": "autopr/0.1"}

BLOCKED_REPOS: set[str] = {
    "archestra-ai/archestra",
    "tscircuit/cli",
    "lingdojo/kana-dojo",
    "orchestration-agent/AgentOrchestration",
}
BLOCKED_ORGS: set[str] = {
    "Scottcjn", "digitaldesignerjazz", "INDIGOAZUL", "relayhop", "xevrion-v2",
    "bolivian-peru", "SolFoundry", "SecureBananaLabs",
    "UnsafeLabs", "kcolbchain", "claude-builders-bounty", "Expensify",
}

ALGORA_LABELS = ["bounty", "%F0%9F%92%8E%20Bounty", "%24250", "%24500", "%24100"]


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _is_blocked(repo: str) -> bool:
    org = repo.split("/")[0]
    return repo in BLOCKED_REPOS or org in BLOCKED_ORGS


def _competing_prs(repo: str, issue_number: int) -> int:
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", "open",
             "--limit", "50", "--json", "body"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return 0
        prs = json.loads(result.stdout or "[]")
        pattern = rf"(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#?{issue_number}\b"
        return sum(1 for pr in prs if re.search(pattern, pr.get("body", ""), re.I))
    except Exception:
        return 0


def fetch_opire() -> list[BountyIssue]:
    issues: list[BountyIssue] = []
    page = 1
    while True:
        try:
            data = _get(f"{OPIRE_API}?page={page}&limit=50")
        except Exception as exc:
            logger.warning("Opire fetch error: %s", exc)
            break
        items = data if isinstance(data, list) else data.get("data", [])
        if not items:
            break
        for item in items:
            try:
                org_name = item.get("organization_name") or item.get("org") or ""
                repo = item.get("repository_full_name") or item.get("repo", "")
                if not repo or _is_blocked(repo):
                    continue
                amount = float(item.get("amount_usd") or item.get("total_usd") or 0)
                if amount < 20:
                    continue
                issue_url = item.get("issue_url") or item.get("url") or ""
                m = re.search(r"/issues/(\d+)", issue_url)
                issue_number = int(m.group(1)) if m else 0
                issues.append(BountyIssue(
                    source="opire",
                    repo=repo,
                    issue_number=issue_number,
                    title=item.get("title") or item.get("issue_title", ""),
                    url=issue_url,
                    amount_usd=amount,
                ))
            except Exception:
                continue
        page += 1
        if page > 10:
            break
    return issues


def fetch_algora() -> list[BountyIssue]:
    issues: list[BountyIssue] = []
    for label in ALGORA_LABELS:
        try:
            result = subprocess.run(
                ["gh", "search", "issues",
                 f"--label={label}", "--state=open",
                 "--limit=50", "--json=url,title,repository,body"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                continue
            for item in json.loads(result.stdout or "[]"):
                repo_info = item.get("repository", {})
                repo = repo_info.get("nameWithOwner", "")
                if not repo or _is_blocked(repo):
                    continue
                url = item.get("url", "")
                m = re.search(r"/issues/(\d+)", url)
                issue_number = int(m.group(1)) if m else 0
                # extract dollar amount from label or title
                amount = 0.0
                amt_match = re.search(r"\$(\d+)", label + " " + item.get("title", ""))
                if amt_match:
                    amount = float(amt_match.group(1))
                if amount < 20:
                    amount = 50.0  # algora bounty label without amount = estimate $50
                issues.append(BountyIssue(
                    source="algora",
                    repo=repo,
                    issue_number=issue_number,
                    title=item.get("title", ""),
                    body=item.get("body", "")[:2000],
                    url=url,
                    amount_usd=amount,
                ))
        except Exception as exc:
            logger.warning("Algora fetch error (label=%s): %s", label, exc)
    return issues


def fetch_issue_body(repo: str, issue_number: int) -> str:
    try:
        result = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "body"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            return json.loads(result.stdout).get("body", "")
    except Exception:
        pass
    return ""


def scan_all(min_amount: float = 20.0) -> list[BountyIssue]:
    """Fetch + deduplicate + score all available bounty issues."""
    raw = fetch_opire() + fetch_algora()

    seen: dict[str, BountyIssue] = {}
    for issue in raw:
        if issue.key in seen:
            # keep higher amount
            if issue.amount_usd > seen[issue.key].amount_usd:
                seen[issue.key] = issue
        else:
            seen[issue.key] = issue

    result = [i for i in seen.values() if i.amount_usd >= min_amount]

    # enrich with competing PR count (quick check)
    for issue in result:
        issue.competing_prs = _competing_prs(issue.repo, issue.issue_number)
        # simple score: amount / (1 + competitors)
        issue.score = issue.amount_usd / (1 + issue.competing_prs * 3)

    return sorted(result, key=lambda i: i.score, reverse=True)
