# AutoPR

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Qwen](https://img.shields.io/badge/Qwen-Max%20%2B%20Plus-orange.svg)](https://www.alibabacloud.com/en/product/modelstudio)
[![Alibaba Cloud](https://img.shields.io/badge/Alibaba%20Cloud-ECS%20%2F%20FC-ff6a00.svg)](https://www.alibabacloud.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Qwen%20Cloud-Global%20AI%20Hackathon%202026-purple)](https://qwencloud-hackathon.devpost.com)

> **An autonomous agent that finds open-source bounties, writes the fix, and submits the PR — without human input.**

Paste nothing. Click nothing. AutoPR runs a continuous loop: scan bounty platforms → Qwen decides if the issue is worth attempting → Qwen writes the fix using real coding tools → PR submitted → memory updated. Watch it all live on the dashboard.

## Demo

![AutoPR Dashboard](docs/dashboard.png)

```
🔍 scanned 47 issues — top: owner/repo#123 $250, owner/repo#89 $100
⚖️  triaging owner/repo#123 — Fix null pointer in CSV parser ($250)
💻 coding owner/repo#123: read csv_parser.py, patch line 47, run pytest
   → list_files(.)
   → read_file(src/csv_parser.py)
   → write_file(src/csv_parser.py, ...)
   → run_command(pytest tests/)
   exit=0 — 12 passed
✅ PR opened! owner/repo#123 → https://github.com/owner/repo/pull/456  ($250)
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        AutoPR Loop (15 min)                     │
│                                                                  │
│  Opire API ──┐                                                   │
│  Algora API ─┼──► Scanner ──► Triage (Qwen-Max) ──► skip?      │
│  GitHub  ────┘                       │                           │
│                                      ▼                           │
│                              Coder (Qwen-Plus)                   │
│                         ┌────────────────────┐                  │
│                         │  list_files        │                  │
│                         │  read_file         │◄── Qwen          │
│                         │  search_code       │    tool          │
│                         │  write_file        │    loop          │
│                         │  run_command       │                  │
│                         │  finish()          │                  │
│                         └────────────────────┘                  │
│                                      │                           │
│                              PR Submitter                        │
│                         fork → branch → push → PR               │
│                                      │                           │
│                              Memory (SQLite)                     │
│                         outcome → repo merge rate               │
└─────────────────────────────────────────────────────────────────┘
                                      │
                               Dashboard (SSE)
                          live feed · stats · PR list
```

### The five components

| Component | Model | Role |
|-----------|-------|------|
| **Scanner** | — | Polls Opire + Algora APIs, checks competing PRs, scores by $/competition |
| **Triage** | Qwen-Max | Reads issue title+body, outputs score (0–1), skip flag, and technical approach |
| **Coder** | Qwen-Plus | Tool-loop agent: explores repo, writes fix, runs tests, calls `finish()` |
| **PR Submitter** | — | Forks repo, pushes branch, opens PR with closes reference |
| **Memory** | SQLite | Tracks every attempt; learns per-repo merge rate to avoid low-signal repos |

## Alibaba Cloud Architecture

```
Alibaba Cloud ECS (t6-small, ~$8/month)
├── AutoPR agent process (Python)
│   ├── Qwen-Max API calls  ──► Alibaba Cloud Model Studio
│   └── Qwen-Plus API calls ──►     (pay-per-token)
├── FastAPI dashboard (port 7860)
├── SQLite database (autopr.db)
└── gh CLI (GitHub API)
```

All Qwen API calls go through Alibaba Cloud Model Studio at `dashscope.aliyuncs.com`. The agent uses `qwen-max` for triage (complex reasoning) and `qwen-plus` for coding (fast, code-tuned). Pay-per-token — the $40 coupon covers hundreds of full coding cycles.

## Quick Start

```bash
git clone https://github.com/64johnlee/autopr
cd autopr
cp .env.example .env
# edit .env: add DASHSCOPE_API_KEY and GITHUB_TOKEN
pip install -e .
python main.py
# open http://localhost:7860
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DASHSCOPE_API_KEY` | Yes | Alibaba Cloud Model Studio key |
| `GITHUB_TOKEN` / `GH_TOKEN` | Yes | GitHub token (repo + workflow scope) |
| `LOOP_INTERVAL_S` | No (900) | Seconds between full scans |
| `PORT` | No (7860) | Dashboard port |
| `MIN_BOUNTY_USD` | No (20) | Minimum bounty to attempt |

### Docker (Alibaba Cloud ECS)

```bash
docker build -t autopr .
docker run -d \
  -e DASHSCOPE_API_KEY=sk-... \
  -e GH_TOKEN=ghp_... \
  -p 7860:7860 \
  --name autopr autopr
```

## CLI

```bash
# Run one cycle and exit
autopr run --once

# Try a specific issue manually
autopr try-issue owner/repo 123

# Show stats
autopr stats
```

## Why Qwen?

Qwen-Max's reasoning depth makes triage accurate — it doesn't just look at keywords, it reads the issue body and outputs a structured judgment with a confidence score and a technical approach. Qwen-Plus's code quality is good enough to write real fixes on real repos. The Alibaba Cloud Model Studio API is OpenAI-compatible, so the integration is clean.

## Memory & Learning

AutoPR tracks every attempt in a local SQLite database. After 5+ attempts on a repo, it calculates a merge rate. Repos with <20% merge rate are skipped in future cycles — the agent learns which maintainers are responsive and which aren't.

```
autopr stats

══════════════════════════════════════════════
  AutoPR Stats
══════════════════════════════════════════════
  Total attempts : 47
  Total earned   : $680.00
  pr_open        : 8
  merged         : 12
  rejected       : 5
  skipped        : 22
──────────────────────────────────────────────
  Recent:
    2026-06-09T14:22  pr_open       owner/repo#456
    2026-06-09T13:01  merged        owner2/lib#89
```

## Built For

**Qwen Cloud Global AI Hackathon 2026** — Autopilot Agent track.

Powered by [Qwen](https://qwenlm.github.io/) · [Alibaba Cloud Model Studio](https://www.alibabacloud.com/en/product/modelstudio) · [FastAPI](https://fastapi.tiangolo.com/)
