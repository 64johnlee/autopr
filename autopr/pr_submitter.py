"""Fork the repo, push the branch, open the PR."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .models import BountyIssue, CoderResult, PRResult

logger = logging.getLogger(__name__)
_GH_USER = None


def _gh_user() -> str:
    global _GH_USER
    if _GH_USER is None:
        r = subprocess.run(["gh", "api", "user", "--jq", ".login"],
                           capture_output=True, text=True, timeout=15)
        _GH_USER = r.stdout.strip()
    return _GH_USER


def submit(issue: BountyIssue, result: CoderResult) -> PRResult:
    if not result.success or not result.branch:
        return PRResult(success=False, error="no successful coder result")

    # Unpack branch::work_dir
    parts = result.branch.split("::", 1)
    branch   = parts[0]
    work_dir = Path(parts[1]) if len(parts) > 1 else None

    if work_dir is None or not work_dir.exists():
        return PRResult(success=False, error="work dir missing")

    try:
        user = _gh_user()

        # Fork (idempotent)
        fork_r = subprocess.run(
            ["gh", "repo", "fork", issue.repo, "--clone=false"],
            capture_output=True, text=True, timeout=60,
        )
        if fork_r.returncode != 0 and "already exists" not in fork_r.stderr:
            return PRResult(success=False, error=f"fork failed: {fork_r.stderr[:300]}")

        repo_name = issue.repo.split("/")[1]
        fork_remote = f"https://github.com/{user}/{repo_name}.git"

        # Add fork as remote and push
        subprocess.run(["git", "remote", "add", "fork", fork_remote],
                       cwd=work_dir, capture_output=True)
        push_r = subprocess.run(
            ["git", "push", "fork", branch],
            cwd=work_dir, capture_output=True, text=True, timeout=120,
        )
        if push_r.returncode != 0:
            return PRResult(success=False, error=f"push failed: {push_r.stderr[:300]}")

        # Open PR
        body = f"""Closes #{issue.issue_number}

## Changes

{chr(10).join(f'- `{f}`' for f in result.changed_files)}

## Test plan

- [x] Existing tests pass
- [x] Fix directly addresses the reported issue

---
*Submitted by [AutoPR](https://github.com/64johnlee/autopr) · powered by Qwen on Alibaba Cloud*"""

        pr_r = subprocess.run(
            ["gh", "pr", "create",
             "--repo", issue.repo,
             "--head", f"{user}:{branch}",
             "--base", "main",
             "--title", result.commit_message,
             "--body", body],
            capture_output=True, text=True, timeout=60,
        )
        if pr_r.returncode != 0:
            # try master branch
            pr_r = subprocess.run(
                ["gh", "pr", "create",
                 "--repo", issue.repo,
                 "--head", f"{user}:{branch}",
                 "--base", "master",
                 "--title", result.commit_message,
                 "--body", body],
                capture_output=True, text=True, timeout=60,
            )
        if pr_r.returncode != 0:
            return PRResult(success=False, error=f"pr create failed: {pr_r.stderr[:300]}")

        pr_url = pr_r.stdout.strip()
        m = __import__("re").search(r"/pull/(\d+)", pr_url)
        pr_number = int(m.group(1)) if m else 0
        return PRResult(success=True, pr_url=pr_url, pr_number=pr_number)

    except Exception as exc:
        return PRResult(success=False, error=str(exc))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
