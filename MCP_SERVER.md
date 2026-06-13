# AutoPR MCP Server

Exposes AutoPR's autonomous coder kernel as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so any MCP host — Claude Desktop, a Slack agent, or a UiPath-orchestrated
agent — can drive it. This is the shared component behind the Slack Agent Builder
and UiPath AgentHack entries: build once, integrate per platform.

## What it exposes

| Tool | Args | Does |
|------|------|------|
| `code_fix` | `repo`, `task`, `issue_number=0` | Clone repo → run the Qwen tool-loop coding agent → commit locally → return a unified **diff to preview**. Nothing is pushed. Returns a `session_id`. |
| `open_pr` | `session_id` | Fork, push the agent's branch, open the PR. Consumes the session. |
| `discard` | `session_id` | Drop a previewed fix and clean up its working dir. |

The two-step `code_fix` → `open_pr` split is deliberate: it gives a human-in-the-loop
**preview-then-ship** UX (review the diff in Slack, click to open the PR).

## Install

```bash
pip install -e ".[mcp]"     # adds the `mcp` SDK alongside the base app
```

Requires the same environment as the core app:

```
DASHSCOPE_API_KEY=sk-...     # Alibaba Cloud Model Studio (Qwen)
GITHUB_TOKEN=ghp_...         # repo scope; the `gh` CLI must be authenticated for open_pr
```

## Run

**stdio** (Claude Desktop / local hosts):

```bash
autopr-mcp
```

**HTTP/SSE** (so a remote Slack app can reach it):

```bash
AUTOPR_MCP_TRANSPORT=sse AUTOPR_MCP_PORT=8000 autopr-mcp
```

## Claude Desktop config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "autopr": {
      "command": "autopr-mcp",
      "env": {
        "DASHSCOPE_API_KEY": "sk-...",
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

Then ask: *"Use autopr to fix issue #123 in owner/repo, show me the diff first."*

## Slack wiring (next step)

The Slack Agent Builder entry uses the **MCP server integration** requirement.
The Slack agent runs the server over SSE and calls:

1. `code_fix(repo, task)` when a user mentions the bot on an issue/PR → posts the
   returned `diff` and `commit_message` as a Slack message with an **Open PR** button.
2. `open_pr(session_id)` when the button is clicked → posts the resulting `pr_url`.

That keeps ~70% of AutoPR (clone → agent loop → commit → PR) untouched; only the
trigger and the message surface are Slack-specific.

## Smoke test

```bash
python -c "import asyncio; from autopr import mcp_server as m; \
print(asyncio.run(m.mcp.list_tools()))"
```

Should list `code_fix`, `open_pr`, `discard` without needing any API key
(the Qwen key is only read when a tool actually runs).
