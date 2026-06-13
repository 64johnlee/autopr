# Live test — AutoPR MCP server

Validates the real path the Slack agent uses: spawn `autopr-mcp`, run `code_fix`
(clone → Qwen tool-loop → diff). **Preview mode has no side effects.**

## One-time setup

`gh` is already authenticated on this machine. You only need the Qwen key.

Create `.env` (copy from `.env.example`) and set it:

```
DASHSCOPE_API_KEY=sk-...        # Alibaba Cloud Model Studio key
GITHUB_TOKEN=ghp_...            # optional; gh CLI auth is already enough for cloning
```

Install the MCP deps if you haven't:

```
pip install -e ".[slack]"
```

> The script loads `.env` automatically, or you can `export DASHSCOPE_API_KEY=...`
> in your shell instead — either works.

## Run it

**Step 1 — make a safe target (optional, recommended).** Creates a public repo
*you own* with a planted bug + an issue. Also the ideal demo-video target.

```
python live_test.py --create-demo-repo autopr-demo
```

It prints the exact next command, e.g.:

```
python live_test.py <you>/autopr-demo "Fix the add() bug so tests pass" --issue 1
```

**Step 2 — preview a fix (no PR, no side effects).** This is the real validation:

```
python live_test.py <you>/autopr-demo "Fix the add() bug so tests pass" --issue 1
```

You'll see the agent's trace, then the unified diff (it should change
`return a - b` → `return a + b`).

**Step 3 — (optional) open a PR.** `pr_submitter` *forks* the target, so this is
meant for a repo you do **not** own (the bounty flow). Your submitted AutoPR
already proves this path works, so it's optional for validation:

```
python live_test.py owner/repo "..." --issue 1 --open-pr
```

## Running inside this Claude session

Prefix any command with `!` to run it here and share the output with me:

```
!python live_test.py --create-demo-repo autopr-demo
```

If the preview diff looks right, the MCP layer is fully validated end-to-end and
we move to wiring the Slack sandbox (tokens) or the UiPath track.
