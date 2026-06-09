"""SQLite-backed memory: tracks every attempt and what the agent learned."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import AttemptStatus

_DB_PATH = Path(__file__).parent.parent / "autopr.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                repo        TEXT NOT NULL,
                issue       INTEGER NOT NULL,
                status      TEXT NOT NULL,
                amount      REAL DEFAULT 0,
                pr_url      TEXT DEFAULT '',
                notes       TEXT DEFAULT '',
                ts          TEXT NOT NULL,
                PRIMARY KEY (repo, issue)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS repo_learnings (
                repo        TEXT PRIMARY KEY,
                merge_rate  REAL DEFAULT 0,
                attempts    INTEGER DEFAULT 0,
                merged      INTEGER DEFAULT 0,
                notes       TEXT DEFAULT ''
            )
        """)


def upsert_attempt(
    repo: str,
    issue: int,
    status: AttemptStatus,
    amount: float = 0.0,
    pr_url: str = "",
    notes: str = "",
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute("""
            INSERT INTO attempts (repo, issue, status, amount, pr_url, notes, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, issue) DO UPDATE SET
                status=excluded.status,
                amount=excluded.amount,
                pr_url=excluded.pr_url,
                notes=excluded.notes,
                ts=excluded.ts
        """, (repo, issue, status.value, amount, pr_url, notes, ts))


def was_attempted(repo: str, issue: int) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT status FROM attempts WHERE repo=? AND issue=?", (repo, issue)
        ).fetchone()
    if row is None:
        return False
    # allow retry if previously errored or skipped
    return row["status"] not in (AttemptStatus.ERROR.value, AttemptStatus.SKIPPED.value)


def update_repo_learning(repo: str, merged: bool) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO repo_learnings (repo, attempts, merged)
            VALUES (?, 1, ?)
            ON CONFLICT(repo) DO UPDATE SET
                attempts = attempts + 1,
                merged   = merged + excluded.merged,
                merge_rate = CAST(merged + excluded.merged AS REAL) / (attempts + 1)
        """, (repo, 1 if merged else 0))


def repo_merge_rate(repo: str) -> Optional[float]:
    with _conn() as con:
        row = con.execute(
            "SELECT merge_rate, attempts FROM repo_learnings WHERE repo=?", (repo,)
        ).fetchone()
    if row is None or row["attempts"] < 2:
        return None
    return row["merge_rate"]


def stats() -> dict:
    with _conn() as con:
        rows = con.execute("SELECT status, COUNT(*) as n, SUM(amount) as total FROM attempts GROUP BY status").fetchall()
    result: dict = {"by_status": {}, "total_earned": 0.0, "total_attempts": 0}
    for r in rows:
        result["by_status"][r["status"]] = {"count": r["n"], "amount": r["total"] or 0}
        result["total_attempts"] += r["n"]
        if r["status"] == AttemptStatus.MERGED.value:
            result["total_earned"] += r["total"] or 0
    return result


def recent_attempts(limit: int = 20) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM attempts ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
