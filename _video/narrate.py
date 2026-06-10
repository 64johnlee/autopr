"""Generate timed narration segments with edge-tts and print their durations."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
VOICE = "en-US-AndrewNeural"

# (start_second_in_video, filename, text)
SEGMENTS = [
    (0.8, "n1", "This is AutoPR — an autonomous agent that finds open-source bounties, "
                "writes the fix, and submits the pull request. No prompts, no clicks. "
                "Built with Qwen on Alibaba Cloud."),
    (12.0, "n2", "The agent wakes up for a new cycle and scans Opire, Algora, and GitHub "
                 "for funded issues. Forty-seven found, ranked by payout versus competition."),
    (24.0, "n3", "Qwen-Max triages the top issue: a two-hundred-fifty-dollar parser bug. "
                 "Score: zero point eight two. Tractable, with a clear repro. Worth attempting."),
    (36.0, "n4", "Now Qwen-Plus takes over in a real tool loop — listing files, reading the "
                 "parser, writing the patch, and running the tests."),
    (63.0, "n5", "The first test run fails. So the agent reads its own diff, fixes the edge "
                 "case, and runs the full suite again. Eighty-four tests pass."),
    (84.0, "n6", "Fork, branch, push — pull request opened, with the two-hundred-fifty-dollar "
                 "bounty attached."),
    (94.0, "n7", "The next issue gets skipped — two competing PRs are already open. Every "
                 "outcome lands in SQLite memory, and repos that never merge get "
                 "deprioritized. The agent learns."),
    (108.0, "n8", "AutoPR. Qwen-Max for judgment, Qwen-Plus for code, Alibaba Cloud for the "
                  "loop. Built for the Qwen Cloud Global AI Hackathon."),
]


async def main() -> None:
    for start, name, text in SEGMENTS:
        path = OUT / f"{name}.mp3"
        await edge_tts.Communicate(text, VOICE, rate="+4%").save(str(path))
        print(f"{name} start={start}s file={path.name}")


if __name__ == "__main__":
    asyncio.run(main())
