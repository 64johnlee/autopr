"""Triage agent: Qwen decides if an issue is worth attempting."""
from __future__ import annotations

import json
import logging

from . import qwen
from .models import BountyIssue
from .memory import repo_merge_rate
from .prompts import TRIAGE_SYSTEM

logger = logging.getLogger(__name__)


async def should_attempt(issue: BountyIssue) -> tuple[bool, str]:
    """Returns (attempt, reason). Uses Qwen-Max for smart triage."""
    # fast reject: too many competing PRs
    if issue.competing_prs >= 3:
        return False, f"saturated ({issue.competing_prs} competing PRs)"

    # memory: repo has <20% merge rate after 5+ attempts → skip
    rate = repo_merge_rate(issue.repo)
    if rate is not None and rate < 0.2:
        return False, f"low merge rate for {issue.repo} ({rate:.0%})"

    prompt = f"""Repository: {issue.repo}
Issue #{issue.issue_number}: {issue.title}

{issue.body[:3000]}

Bounty: ${issue.amount_usd:.0f}
Competing PRs: {issue.competing_prs}"""

    try:
        resp = await qwen.triage(
            [{"role": "user", "content": prompt}],
            system=TRIAGE_SYSTEM,
        )
        text = resp.choices[0].message.content or ""
        # strip markdown fences if present
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        score = float(data.get("score", 0))
        reason = data.get("reason", "")
        skip = data.get("skip", False)
        approach = data.get("approach", "")

        if skip or score < 0.45:
            return False, reason or "low score"

        issue.score = score  # upgrade score with Qwen's judgment
        return True, approach or reason

    except Exception as exc:
        logger.warning("Triage failed for %s: %s", issue.key, exc)
        # fall back to heuristic score
        return issue.score >= 30.0, "heuristic fallback"
