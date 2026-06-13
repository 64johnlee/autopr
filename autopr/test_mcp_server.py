"""Hermetic tests that the MCP tool wrappers delegate to the shared service."""
import asyncio

import autopr.mcp_server as m


def test_code_fix_delegates_to_run_code_fix(monkeypatch):
    async def fake(repo, task, issue_number=0):
        return {"success": True, "echo": (repo, task, issue_number)}

    monkeypatch.setattr(m, "run_code_fix", fake)
    out = asyncio.run(m.code_fix("o/r", "t", 3))
    assert out == {"success": True, "echo": ("o/r", "t", 3)}


def test_open_pr_delegates_to_run_open_pr(monkeypatch):
    monkeypatch.setattr(m, "run_open_pr", lambda sid: {"ok": "pr", "sid": sid})
    assert asyncio.run(m.open_pr("s1")) == {"ok": "pr", "sid": "s1"}


def test_discard_delegates_to_run_discard(monkeypatch):
    monkeypatch.setattr(m, "run_discard", lambda sid: {"ok": "discard", "sid": sid})
    assert asyncio.run(m.discard("s2")) == {"ok": "discard", "sid": "s2"}
