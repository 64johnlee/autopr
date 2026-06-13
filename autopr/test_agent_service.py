"""Hermetic unit tests for the shared agent service (no network / API keys)."""
from autopr.agent_service import (
    _synthetic_issue,
    _unpack_work_dir,
    run_discard,
    run_open_pr,
)
from autopr.models import CoderResult


def test_synthetic_issue_uses_first_line_as_title():
    iss = _synthetic_issue("o/r", "Fix the bug\nmore details here", 7)
    assert iss.repo == "o/r"
    assert iss.issue_number == 7
    assert iss.title == "Fix the bug"
    assert iss.body == "Fix the bug\nmore details here"
    assert iss.source == "service"
    assert iss.amount_usd == 0.0


def test_synthetic_issue_truncates_long_title():
    iss = _synthetic_issue("o/r", "x" * 200, 0)
    assert len(iss.title) == 120


def test_synthetic_issue_empty_task_has_fallback_title():
    iss = _synthetic_issue("o/r", "   ", 0)
    assert iss.title == "task in o/r"


def test_unpack_work_dir_without_marker_returns_none():
    assert _unpack_work_dir(CoderResult(success=True, branch="just-a-branch")) is None


def test_unpack_work_dir_nonexistent_path_returns_none():
    assert _unpack_work_dir(CoderResult(success=True, branch="b::/no/such/path/xyz")) is None


def test_run_open_pr_unknown_session_is_graceful():
    r = run_open_pr("nope")
    assert r["success"] is False
    assert "session" in r["error"]


def test_run_discard_unknown_session_is_graceful():
    assert run_discard("nope")["success"] is False


def test_session_registry_is_bounded(monkeypatch):
    import autopr.agent_service as svc

    svc._SESSIONS.clear()
    monkeypatch.setattr(svc, "_MAX_SESSIONS", 3)
    iss = svc._synthetic_issue("o/r", "t", 0)
    res = CoderResult(success=True, branch="nodir")  # no '::' → nothing to rmtree
    for i in range(5):
        svc._remember(f"s{i}", iss, res)
    assert len(svc._SESSIONS) <= 3
    assert "s4" in svc._SESSIONS       # newest kept
    assert "s0" not in svc._SESSIONS   # oldest evicted
    svc._SESSIONS.clear()


def test_run_code_fix_success_path(monkeypatch, tmp_path):
    import asyncio

    import autopr.agent_service as svc

    svc._SESSIONS.clear()
    fake = CoderResult(
        success=True, changed_files=["calc.py"], commit_message="fix: x",
        branch=f"autopr/issue-1::{tmp_path}", tool_calls=5, elapsed_s=1.0,
    )

    async def fake_fix(issue, on_event=None):
        if on_event:
            on_event("agent did work")
        return fake

    monkeypatch.setattr(svc, "fix_issue", fake_fix)
    out = asyncio.run(svc.run_code_fix("o/r", "fix it", 1))
    assert out["success"] is True
    assert out["session_id"] in svc._SESSIONS
    assert out["changed_files"] == ["calc.py"]
    assert out["commit_message"] == "fix: x"
    assert "agent did work" in out["trace"]
    svc._SESSIONS.clear()
