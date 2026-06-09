"""Shared data models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AttemptStatus(str, Enum):
    SCANNING = "scanning"
    TRIAGING = "triaging"
    CODING = "coding"
    TESTING = "testing"
    SUBMITTING = "submitting"
    PR_OPEN = "pr_open"
    MERGED = "merged"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    ERROR = "error"


class BountyIssue(BaseModel):
    source: str                     # 'opire' | 'algora' | 'issuehunt'
    repo: str                       # 'owner/name'
    issue_number: int
    title: str
    body: str = ""
    url: str
    amount_usd: float
    langs: list[str] = Field(default_factory=list)
    competing_prs: int = 0
    score: float = 0.0

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.issue_number}"


class CoderResult(BaseModel):
    success: bool
    changed_files: list[str] = Field(default_factory=list)
    commit_message: str = ""
    branch: str = ""
    error: str = ""
    tool_calls: int = 0
    elapsed_s: float = 0.0


class PRResult(BaseModel):
    success: bool
    pr_url: str = ""
    pr_number: int = 0
    error: str = ""


class Attempt(BaseModel):
    issue: BountyIssue
    status: AttemptStatus = AttemptStatus.SCANNING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    coder_result: Optional[CoderResult] = None
    pr_result: Optional[PRResult] = None
    notes: str = ""

    @property
    def earned(self) -> float:
        return self.issue.amount_usd if self.status == AttemptStatus.MERGED else 0.0
