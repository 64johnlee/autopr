# AutoPR for Slack — Devpost submission

> Drop-in copy for the Slack Agent Builder Challenge project page. Sections map to
> Devpost's standard fields and the four judging criteria: Technological
> Implementation, Design, Potential Impact, and Quality of the Idea.

## Tagline
Fix GitHub issues without leaving Slack. Mention `@AutoPR`, get a diff, click **Open PR**.

## Inspiration
Every engineering team triages bugs in Slack — then context-switches to an editor,
a terminal, and GitHub to actually fix them. The discussion and the work live in
two different worlds. We wanted the fix to happen *where the conversation already
is*: an autonomous coding agent you summon with a mention, that shows its work and
waits for your approval before touching the repo.

## What it does
- You mention `@AutoPR owner/repo#42 <describe the bug>` in any channel.
- The agent clones the repo, reads it, writes a fix, and runs the tests — then
  posts the **unified diff** back in-thread with **Open PR** / **Discard** buttons.
- Click **Open PR** and it forks, pushes, and opens the pull request — link posted
  in the thread. Nothing is pushed until you approve. Human-in-the-loop by design.

## How we built it
- **MCP server integration** (the challenge's required technology). The agent's
  coding brain — clone → tool-loop → commit → PR — is exposed as a Model Context
  Protocol server (`autopr-mcp`) with three tools: `code_fix`, `open_pr`,
  `discard`. The Slack app is a true MCP **client** that drives it over stdio.
- **Agentic core (Qwen on Alibaba Cloud).** A function-calling loop with
  sandboxed tools (`list_files`, `read_file`, `search_code`, `write_file`,
  `run_command`, `finish`) lets the model explore the repo and write a minimal,
  test-passing fix.
- **Slack layer (Bolt, Socket Mode).** `app_mention` triggers the run; Block Kit
  renders the diff and action buttons. Socket Mode means no public URL — it runs
  straight from a dev sandbox.
- **Preview-then-ship UX.** `code_fix` returns a diff to review; `open_pr` ships
  it. The two-step split is what makes an autonomous agent safe to use in a
  shared channel.

## Technological implementation (judging)
- Satisfies the **MCP server integration** requirement literally: a standalone MCP
  server, consumed by an MCP client. The same server is reusable by any host
  (Claude Desktop, CI, other agents) — Slack is just one front-end.
- **Reliability under Slack's constraints:** long agent runs (30–120s) are
  offloaded to background tasks so the Socket Mode envelope is acknowledged
  immediately — preventing Slack's 3-second redelivery from triggering duplicate
  clones or duplicate PRs. A persistent, lock-serialized MCP session keeps
  `code_fix` and `open_pr` on the same process so a preview can be shipped later.

## Design (judging)
- The diff is the interface. Engineers trust a patch they can read; the agent
  leads with it, not with a wall of prose.
- Primary/destructive button styling (**Open PR** vs **Discard**), in-thread
  replies that keep channels clean, and a live "working…" state so the channel
  always knows what the agent is doing.

## Potential impact (judging)
- Collapses triage-to-fix from a multi-tool context switch into one Slack action.
- Works on **any** GitHub repo — no per-repo setup. Great for maintainers drowning
  in small issues and for teams that want a first-draft fix attached to the bug
  report automatically.

## Quality of the idea (judging)
- Autonomous coding agents usually live in an IDE. Surfacing one *where work is
  discussed*, with a mandatory human approval gate, is a genuinely different
  posture — collaborative, auditable, and safe for a shared workspace.

## Challenges we ran into
- Socket Mode acks the envelope only *after* the listener returns — a slow agent
  run would be redelivered and fire twice. We fixed it by acking fast and running
  the agent in a background task.
- Keeping the MCP session alive across asyncio tasks without tripping anyio's
  cancel-scope rules — solved with a single persistent, lock-serialized session.

## Accomplishments we're proud of
- ~70% of the codebase is a reusable, platform-neutral MCP server. Slack is a thin
  client; the same core can back other platforms with no changes to the engine.

## What we learned
- For agent UX in chat, the winning pattern is **preview-then-ship**: show the
  diff, let a human approve. Autonomy plus a one-click gate beats full autonomy.

## What's next
- Trigger on GitHub issue links pasted in Slack; multi-file PR summaries; a
  "explain this diff" follow-up; running the same MCP server behind other hosts.

## Built with
`python` · `model-context-protocol` · `slack-bolt` · `qwen` · `alibaba-cloud` ·
`socket-mode` · `block-kit` · `github` · `gh-cli`

## Try it / repo
- Repo: this project. Setup in `slack_app/README.md`, architecture in `MCP_SERVER.md`.
- The Slack app is created from `slack_app/manifest.yaml` (Socket Mode, no public URL).
