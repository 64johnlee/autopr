# AutoPR — Autonomous Open-Source Bounty Agent

## Inspiration

I've been manually hunting open-source bounties for months — scanning Algora, Opire, checking competing PRs, reading issues, writing fixes, submitting PRs. It works, but it's tedious. Every step follows the same pattern. I thought: what if I just automated myself?

AutoPR is that automation. It runs a continuous loop: find a bounty → decide if it's worth attempting → write the fix → submit the PR → learn from the outcome.

## What It Does

AutoPR is an autonomous agent that earns open-source bounties without human intervention:

1. **Scans** Opire and Algora APIs every 15 minutes for funded GitHub issues
2. **Triages** each issue with Qwen-Max — scores tractability, identifies technical approach, skips anything too vague or contested
3. **Codes** the fix using a Qwen-Plus tool loop — the model explores the repo by reading files, searching code, writing changes, and running tests, then calls `finish()` when done
4. **Submits** the PR via GitHub API, with the issue closed reference and a clear description
5. **Learns** — stores every attempt outcome in SQLite, calculates per-repo merge rates, avoids repos where PRs consistently get ignored

The live dashboard streams every agent action in real time via Server-Sent Events. You can watch it find an issue, read the codebase, write the fix, and submit the PR — all without touching a keyboard.

## How I Built It

**Backend:** Python 3.11, FastAPI, SQLite
**AI:** Qwen-Max (triage) + Qwen-Plus (coding) via Alibaba Cloud Model Studio
**Deployment:** Alibaba Cloud ECS (t6-small), Docker
**GitHub integration:** `gh` CLI for forking, pushing, and PR creation

The core innovation is the **Qwen tool-loop coder**: the model is given 6 tools (`list_files`, `read_file`, `search_code`, `write_file`, `run_command`, `finish`) and works autonomously on a cloned repo until it either fixes the issue or decides it can't. This is the same pattern as professional AI coding assistants, but applied to real bounty issues.

The **triage agent** is what makes the economics work. Qwen-Max reads the full issue body and outputs a structured JSON response: `{score, reason, approach, skip}`. Issues with score < 0.45 are skipped. This prevents wasting compute on vague feature requests or issues that need design discussion.

The **memory system** makes the agent smarter over time. After 5+ attempts on a repository, it tracks the merge rate. Maintainers who are responsive get more attempts; maintainers who ignore PRs get skipped.

## Challenges

**The honeypot problem:** About 40% of "bounty" issues on Opire are from fake repos that never pay out. I had to build an aggressive blocklist and add a competing-PR check before each attempt.

**Tool-loop reliability:** Qwen sometimes calls `finish()` too early without making any file changes, or writes syntactically broken code. I handled this by checking for empty `git diff` output after the loop and treating it as a failure.

**Rate limits:** Both Qwen and GitHub APIs have rate limits. The agent has exponential backoff with proper retry detection built in.

## Accomplishments

- End-to-end autonomous PR submission working on real repos
- Live dashboard with SSE streaming — judges can watch the agent work in real time
- Memory system that improves selection over time
- Runs entirely on Alibaba Cloud for < $10/month in compute (+ token costs)

## What I Learned

Qwen-Max's structured output is remarkably reliable for triage — it rarely misclassifies tractable issues. Qwen-Plus is good enough at coding to handle well-scoped bugs (null pointers, missing test coverage, small API changes) but struggles with architectural issues. That's fine — the triage layer filters those out.

The economics are interesting: at $0.10–0.50/Qwen call and $20–$250/bounty, the agent only needs a ~2–5% success rate to be profitable.

## What's Next

- Multi-model comparison: run Qwen-Max for coding too, measure merge rate improvement vs. cost
- PR follow-up: monitor review comments and push fixes automatically
- Bounty marketplace integration: IssueHunt, Gitcoin
- Web interface for managing the blocklist and per-repo settings

## Built With

- Python
- Qwen-Max
- Qwen-Plus
- Alibaba Cloud Model Studio
- Alibaba Cloud ECS
- FastAPI
- SQLite
- GitHub API
