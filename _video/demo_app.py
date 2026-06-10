"""Demo wrapper: serves the real AutoPR dashboard and replays a scripted
agent cycle through the live event bus. For demo-video recording only."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from server import app  # noqa: E402
from autopr import events  # noqa: E402

ISSUE_A = "fastcsv/fastcsv#412"
ISSUE_B = "webly/webly-ui#88"

# (delay_seconds_after_previous, kind, data)
TIMELINE = [
    # last cycle's stats so the dashboard isn't empty on load
    (0.0, "cycle_done", {
        "total_attempts": 46, "total_earned": 430.0,
        "by_status": {"pr_open": {"count": 7}, "merged": {"count": 9},
                      "rejected": {"count": 5}, "skipped": {"count": 25}},
    }),
    (2.0, "agent", {"msg": "AutoPR loop started — scanning Opire + Algora + GitHub"}),
    (4.0, "scan_done", {
        "count": 47,
        "top": [
            {"key": ISSUE_A, "amount": 250},
            {"key": ISSUE_B, "amount": 100},
            {"key": "datakit/datakit#207", "amount": 75},
        ],
    }),
    (4.0, "triage_start", {
        "issue": ISSUE_A,
        "title": "NUL byte in quoted field crashes the CSV reader",
        "amount": 250,
    }),
    (6.0, "agent", {"msg": "qwen-max triage: score 0.82 — tractable parser bug, clear repro in issue body"}),
    (3.0, "coding_start", {
        "issue": ISSUE_A,
        "approach": "harden quoted-field state machine in reader.py against NUL bytes, add regression test",
    }),
    (3.5, "coder_event", {"msg": "→ list_files(.)"}),
    (3.5, "coder_event", {"msg": "→ read_file(src/fastcsv/reader.py)"}),
    (4.0, "coder_event", {"msg": "→ search_code(\"QUOTED_FIELD\")"}),
    (4.0, "coder_event", {"msg": "→ read_file(tests/test_reader.py)"}),
    (4.5, "coder_event", {"msg": "→ write_file(src/fastcsv/reader.py)  [+9 −2]"}),
    (4.0, "coder_event", {"msg": "→ write_file(tests/test_reader.py)  [+18]"}),
    (4.0, "coder_event", {"msg": "→ run_command(pytest tests/test_reader.py -q)"}),
    (4.5, "coder_event", {"msg": "   exit=1 — 1 failed: NUL inside escaped quote still raises"}),
    (3.5, "coder_event", {"msg": "→ read_file(src/fastcsv/reader.py)"}),
    (4.0, "coder_event", {"msg": "→ write_file(src/fastcsv/reader.py)  [+4 −1]"}),
    (4.0, "coder_event", {"msg": "→ run_command(pytest tests/ -q)"}),
    (4.5, "coder_event", {"msg": "   exit=0 — 84 passed in 6.12s"}),
    (3.0, "coder_event", {"msg": "→ finish(summary=\"NUL-safe quoted-field parsing + regression tests\")"}),
    (3.0, "submitting", {"issue": ISSUE_A, "files": ["src/fastcsv/reader.py", "tests/test_reader.py"]}),
    (4.0, "pr_opened", {
        "issue": ISSUE_A,
        "pr_url": "https://github.com/fastcsv/fastcsv/pull/418",
        "amount": 250,
    }),
    (5.0, "triage_start", {
        "issue": ISSUE_B,
        "title": "Dark mode flickers on route change",
        "amount": 100,
    }),
    (5.0, "triage_skip", {
        "issue": ISSUE_B,
        "reason": "2 competing PRs already open; needs design decision from maintainer",
    }),
    (4.0, "agent", {"msg": "memory: webly/webly-ui merge rate 12% over 8 attempts — deprioritized"}),
    (4.0, "cycle_done", {
        "total_attempts": 47, "total_earned": 680.0,
        "by_status": {"pr_open": {"count": 8}, "merged": {"count": 12},
                      "rejected": {"count": 5}, "skipped": {"count": 22}},
    }),
]

_started = False


@app.post("/demo-start")
async def demo_start():
    global _started
    if _started:
        return {"status": "already running"}
    _started = True

    async def replay() -> None:
        for delay, kind, data in TIMELINE:
            await asyncio.sleep(delay)
            events.emit(kind, data)

    asyncio.get_event_loop().create_task(replay())
    return {"status": "started"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")
