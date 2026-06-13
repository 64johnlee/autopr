# AutoPR for Slack — 3-minute demo video script

**Goal:** judges spend ~3 minutes and the first 60 seconds decide it. So the full
payoff — mention → diff → live PR — happens by 0:55. Everything after is depth.

**Format:** ~3:00 total. Screen recording of Slack + a browser tab on GitHub.
Record at 1080p+. Keep the cursor deliberate. Captions on (many judges watch muted).

**Pre-roll setup (before recording):**
- A Slack channel with `@AutoPR` already in it.
- The planted-bug demo repo open in a browser tab (`live_test.py --create-demo-repo`),
  showing `calc.py` with `return a - b` and the failing `test_calc.py`.
- A second take in reserve in case the agent run is slow — you can trim dead time.

---

## 0:00–0:15 — Hook (lead with the problem + the action)
**On screen:** Slack channel. Type and send:
`@AutoPR myname/autopr-demo#1 add() returns the wrong result — it subtracts instead of adding`

**VO:** "Your team finds a bug in Slack — then leaves Slack to fix it. What if the
fix happened right here? Watch. I mention AutoPR with the repo and the bug."

> Tip: have this message pre-typed; just hit send on camera so there's no typing lag.

## 0:15–0:45 — The agent works, then shows the diff (the "wow")
**On screen:** AutoPR replies in-thread: "🔧 AutoPR is on it…", then (trim any wait)
the **diff preview** appears — `- return a - b` / `+ return a + b` — with
**Open PR** and **Discard** buttons.

**VO:** "It clones the repo, reads the code, and writes a fix using a Qwen
tool-calling agent. No back-and-forth — it comes back with the actual diff, right
in the thread. I can read exactly what it changed before anything touches the repo."

## 0:45–0:58 — Ship it (payoff inside the first minute)
**On screen:** Click **Open PR**. AutoPR posts "🚀 Pull request opened" with a link.
Click it → the real PR on GitHub, `a - b` → `a + b`.

**VO:** "One click — Open PR. It forks, pushes, and opens a real pull request. From
a Slack message to a live PR in under a minute, and a human approved every step."

## 0:58–1:45 — How it works (Technological Implementation)
**On screen:** A simple architecture slide/diagram:
`Slack (Bolt, Socket Mode) → MCP client → autopr-mcp server → clone · Qwen loop · PR`

**VO:** "Here's what makes it tick. The coding agent is exposed as a Model Context
Protocol server — that's the challenge's required integration. The Slack app is a
true MCP client that calls it. Two tools: code_fix returns the diff to preview,
open_pr ships it. Because it's an MCP server, the same brain works behind Claude
Desktop or CI — Slack is just one front-end."

## 1:45–2:25 — Why it's safe and reliable (Design + depth)
**On screen:** Show the **Discard** path on a second mention, and the in-thread
"working…" state.

**VO:** "It's built for a shared channel. Nothing is pushed until you approve —
preview-then-ship. Long agent runs are handled in the background so Slack never
double-fires and opens duplicate PRs. The diff is the interface, because engineers
trust a patch they can read."

## 2:25–2:50 — Impact (Potential Impact + Quality of Idea)
**On screen:** Mention it on a *different* repo to show it's not hard-coded.

**VO:** "It works on any GitHub repo, no per-repo setup. Autonomous coding agents
usually live in an IDE — AutoPR puts one where the work is actually discussed, with
a human approval gate. Triage and fix, in the same place."

## 2:50–3:00 — Close
**On screen:** Title card: "AutoPR for Slack — Python · MCP · Slack Bolt · Qwen".

**VO:** "AutoPR for Slack. From the bug report to the pull request, without leaving
the conversation. Thanks for watching."

---

## Shot checklist
- [ ] First 60s contains the COMPLETE loop: mention → diff → live PR link.
- [ ] Diff is legible on screen (zoom Slack if needed).
- [ ] The opened PR on GitHub is shown (proof it's real, not mocked).
- [ ] Captions/subtitles burned in.
- [ ] Architecture diagram readable for 5+ seconds.
- [ ] Under 3:00. Trim agent "thinking" waits aggressively.

## One-line VO alternates (if you want a punchier hook)
- "From Slack message to merged-ready PR — in under a minute."
- "The bug is reported in Slack. Why isn't the fix?"
