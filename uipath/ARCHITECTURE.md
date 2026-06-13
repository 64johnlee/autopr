# AutoPR × UiPath — architecture

**Entry:** UiPath AgentHack (Devpost). **Deadline:** June 29, 2026, 11:45pm EDT.
**Recommended track:** *Maestro BPMN* (it explicitly welcomes external frameworks
and coding agents, and a BPMN diagram demos beautifully). *Maestro Case* is the
alternative if you want to lean into exception-heavy, stage-based case management.

## The business problem
Engineering teams sit on a backlog of small, well-specified bugs. Each one costs a
context switch: read the issue, clone, fix, test, open a PR, get review. We make
that an **orchestrated, governed business process**: UiPath Maestro runs the
lifecycle; AutoPR (an autonomous coding agent) does the implementation; a human
approves before anything merges.

## Why this scores on UiPath's rubric
- **Platform Usage (deep, deliberate):** Maestro orchestrates the whole flow;
  AutoPR runs *under UiPath governance* (audit trail, approvals, retries) rather
  than as a standalone script. The rules state external frameworks "within UiPath
  governance score higher."
- **Business Impact:** measurable cycle-time reduction on backlog bugs.
- **Technical Execution & Exception Handling:** explicit failure branches.
- **Completeness:** end-to-end, intake → merged-ready PR.
- **Creativity:** an autonomous coding agent as a governed business worker.
- **+2 bonus:** the solution itself was built with Claude Code (see SUBMISSION_PLAN).

## The orchestrated flow (BPMN)

```
[Start: issue intake]                     (form / queue / webhook)
        │
        ▼
[Service Task: AutoPR /code_fix]  ──HTTP──►  AutoPR REST API
        │                                     (clone → Qwen agent → diff)
        ▼
[Gateway: success?]
   │no → [Exception path: notify + log + end]
   │yes
        ▼
[User Task: review diff]          (Action Center — human approves/rejects)
   │reject → [Service Task: /discard] → end
   │approve
        ▼
[Service Task: AutoPR /open_pr]   ──HTTP──►  AutoPR REST API (fork→push→PR)
        │
        ▼
[Gateway: PR opened?]
   │no → [Exception path: notify + retry/escalate]
   │yes
        ▼
[End: post PR link + close case]
```

Every box is a real Maestro node:
- **Service Task** — "start and wait" on an external call; this is how Maestro
  invokes AutoPR's REST endpoints and waits for the structured response.
- **User Task** — the human approval gate, surfaced in UiPath Action Center.
- **Gateways** — branch on `success` / `pr_opened` from AutoPR's JSON.
- **Script Task** (optional) — inline JS to shape payloads between steps.

## How Maestro calls AutoPR (the integration)
Maestro invokes agents by calling REST endpoints and expects structured JSON.
AutoPR exposes exactly that (`autopr/api_server.py`):

| Step | Method | Endpoint | Request | Key response fields |
|------|--------|----------|---------|---------------------|
| Implement fix | POST | `/code_fix` | `{repo, task, issue_number}` | `success`, `session_id`, `diff`, `changed_files`, `commit_message` |
| Open PR | POST | `/open_pr` | `{session_id}` | `success`, `pr_url`, `pr_number` |
| Reject | POST | `/discard` | `{session_id}` | `success` |
| Liveness | GET | `/health` | — | `status` |

Two ways to wire it in Studio Web (pick one):
1. **HTTP Request activity** inside a Service Task — simplest; set URL, method,
   JSON body, and a `Bearer` auth header (`AUTOPR_API_TOKEN`).
2. **Integration Service custom connector** — "expose any REST API to the UiPath
   Platform." Slightly more setup, but it makes AutoPR a first-class, reusable
   connector and reads as *deeper platform usage* to judges. Recommended if time
   allows.

### Example Service Task payloads
`/code_fix` request:
```json
{ "repo": "octo/widget", "task": "add() subtracts instead of adding", "issue_number": 1 }
```
`/code_fix` response (Maestro branches on `success`, shows `diff` in the User Task):
```json
{ "success": true, "session_id": "a1b2c3d4",
  "commit_message": "fix: correct add() operator",
  "changed_files": ["calc.py"], "diff": "--- a/calc.py\n+++ b/calc.py\n..." }
```
`/open_pr` request: `{ "session_id": "a1b2c3d4" }` →
`{ "success": true, "pr_url": "https://github.com/octo/widget/pull/7", "pr_number": 7 }`

## Reachability (AutoPR must be callable from UiPath Cloud)
UiPath Cloud needs a public URL for the AutoPR API. Options, easiest first:
- **Tunnel for the demo:** run `autopr-api` locally, expose with a tunnel
  (`cloudflared`/`ngrok`) → use the https URL in Maestro. Set `AUTOPR_API_TOKEN`.
- **Deploy:** the repo already has `deploy-aliyun.sh`; run the API on the same box
  (`autopr-api`, port 8800) behind https.

## Governance & exception handling (call this out in the demo)
- Nothing merges without the **User Task** approval — human-in-the-loop by design.
- Failure branches on `success=false` (clone failed, agent gave up) → notify/log.
- Bearer auth on the API; secrets in env (UiPath credential vault on their side).
- Maestro's durable execution gives the audit trail and retries for free.
