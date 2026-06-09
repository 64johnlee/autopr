"""AutoPR orchestrator — runs the full scan → triage → code → PR loop."""
from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from autopr import events
from autopr.models import AttemptStatus
from autopr.memory import init_db, upsert_attempt, was_attempted, update_repo_learning, stats
from autopr.scanner import scan_all, fetch_issue_body
from autopr.triage import should_attempt
from autopr.coder import fix_issue
from autopr.pr_submitter import submit

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("autopr.agent")

_LOOP_INTERVAL_S = int(os.environ.get("LOOP_INTERVAL_S", "900"))  # 15 min between full scans


async def run_one(issues_override=None):
    """One full scan-triage-code-PR cycle."""
    emit = events.emit

    emit("agent", {"msg": "scanning bounty platforms…"})
    issues = issues_override or scan_all(min_amount=20.0)
    emit("scan_done", {"count": len(issues), "top": [
        {"key": i.key, "amount": i.amount_usd, "score": round(i.score, 1)} for i in issues[:5]
    ]})
    logger.info("Found %d issues after dedup+filter", len(issues))

    for issue in issues:
        if was_attempted(issue.repo, issue.issue_number):
            logger.debug("Skipping already-attempted %s", issue.key)
            continue

        emit("triage_start", {"issue": issue.key, "title": issue.title, "amount": issue.amount_usd})
        upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.TRIAGING)

        # Fetch body if scanner didn't get it
        if not issue.body:
            issue.body = fetch_issue_body(issue.repo, issue.issue_number)

        ok, reason = await should_attempt(issue)
        if not ok:
            emit("triage_skip", {"issue": issue.key, "reason": reason})
            upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.SKIPPED, notes=reason)
            continue

        emit("coding_start", {"issue": issue.key, "approach": reason})
        upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.CODING)

        def on_event(msg):
            emit("coder_event", {"issue": issue.key, "msg": msg})

        coder_result = await fix_issue(issue, on_event=on_event)

        if not coder_result.success:
            emit("coding_fail", {"issue": issue.key, "error": coder_result.error})
            upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.ERROR,
                           notes=coder_result.error)
            continue

        emit("submitting", {"issue": issue.key, "files": coder_result.changed_files})
        upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.SUBMITTING)

        pr = submit(issue, coder_result)

        if pr.success:
            emit("pr_opened", {
                "issue": issue.key, "pr_url": pr.pr_url,
                "amount": issue.amount_usd, "files": coder_result.changed_files,
            })
            upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.PR_OPEN,
                           pr_url=pr.pr_url)
            logger.info("PR opened: %s → %s", issue.key, pr.pr_url)
        else:
            emit("pr_fail", {"issue": issue.key, "error": pr.error})
            upsert_attempt(issue.repo, issue.issue_number, AttemptStatus.ERROR,
                           notes=f"PR failed: {pr.error}")

        # one issue per cycle to avoid flooding; remove this to run all
        break

    emit("cycle_done", stats())


async def loop():
    init_db()
    events.emit("agent", {"msg": "AutoPR started — Qwen × Alibaba Cloud"})
    while True:
        try:
            await run_one()
        except Exception as exc:
            logger.exception("Cycle error: %s", exc)
            events.emit("error", {"msg": str(exc)})
        await asyncio.sleep(_LOOP_INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(loop())
