# AutoPR for Slack

Fix GitHub issues without leaving Slack. Mention `@AutoPR` with a repo and a
description; the agent clones the repo, writes a fix, and shows you the **diff**.
Click **Open PR** and it forks, pushes, and opens the pull request.

> Built for the **Slack Agent Builder Challenge**. Satisfies the challenge's
> *MCP server integration* requirement: this Slack app is an MCP **client** that
> drives the [`autopr-mcp`](../MCP_SERVER.md) server over stdio.

## Architecture

```
Slack  ──@AutoPR owner/repo#42 …──►  Bolt app (Socket Mode)
                                         │  MCP client (stdio)
                                         ▼
                                   autopr-mcp server
                                         │
                            code_fix → clone → Qwen tool-loop → commit
                            open_pr  → fork → push → PR
```

- `parse.py` — pulls `repo`, issue number, and task out of the mention.
- `mcp_client.py` — one persistent MCP session (so `code_fix` and `open_pr` hit the same process).
- `blocks.py` — Block Kit: diff preview + Open PR / Discard buttons.
- `app.py` — Bolt Socket-Mode app and handlers.

## 1. Create the Slack app (sandbox)

1. Go to <https://api.slack.com/apps> → **Create New App → From a manifest**.
2. Pick your **developer sandbox** workspace.
3. Paste [`manifest.yaml`](manifest.yaml). Create.
4. **Basic Information → App-Level Tokens →** generate a token with scope
   `connections:write`. Copy it → this is `SLACK_APP_TOKEN` (`xapp-…`).
5. **Install App** to the workspace. Copy the **Bot User OAuth Token** →
   this is `SLACK_BOT_TOKEN` (`xoxb-…`).

## 2. Configure environment

Add to `.env` (same file the core app uses):

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
DASHSCOPE_API_KEY=sk-...      # Qwen (already set for the core app)
GITHUB_TOKEN=ghp_...          # gh CLI must be authenticated for Open PR
```

## 3. Run

```bash
pip install -e ".[slack]"
autopr-slack
```

The agent connects over Socket Mode (no public URL needed). Invite it to a
channel, then:

```
@AutoPR owner/repo#42 the CSV parser throws on an empty file
@AutoPR https://github.com/owner/repo/issues/7
```

It replies in-thread with a diff and an **Open PR** button.

## 4. Submission checklist (Slack Agent Builder)

- [ ] App runs in the provisioned **developer sandbox**.
- [ ] Invite testers to the sandbox: `slackhack@salesforce.com` and `testing@devpost.com` (Member role).
- [ ] ~3-minute demo video — **make the first 60 seconds land**: mention → diff → Open PR → live PR link.
- [ ] Public GitHub repo (this one) with README.
- [ ] Devpost project page.

## Tests

```bash
python -m pytest slack_app/test_parse.py -q
```
