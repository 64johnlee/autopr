# AutoPR for UiPath AgentHack

AutoPR — an autonomous coding agent — wrapped as a **REST service** that **UiPath
Maestro** orchestrates end-to-end: intake a bug → AutoPR writes the fix → a human
approves in Action Center → AutoPR opens the PR. UiPath is the orchestration and
governance layer; AutoPR is the agent it calls.

- **Architecture & integration:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Submission plan, deck, judging map, bonus:** [SUBMISSION_PLAN.md](SUBMISSION_PLAN.md)

## The endpoint UiPath calls
`autopr/api_server.py` (FastAPI) — Maestro calls these and branches on the JSON:

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/code_fix` | `{repo, task, issue_number}` | `success, session_id, diff, …` |
| POST | `/open_pr` | `{session_id}` | `success, pr_url, pr_number` |
| POST | `/discard` | `{session_id}` | `success` |
| GET | `/health` | — | `status` |

Same kernel as the Slack/MCP build (via `autopr/agent_service.py`) — one core,
three front-ends (Slack MCP, REST for UiPath, CLI).

## Run the API locally
```bash
pip install -e .            # fastapi/uvicorn are already base deps
export AUTOPR_API_TOKEN=choose-a-secret   # optional but recommended
autopr-api                  # serves on 0.0.0.0:8800
```
Smoke test:
```bash
curl -s localhost:8800/health
curl -s -X POST localhost:8800/code_fix -H "Authorization: Bearer $AUTOPR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo":"you/autopr-demo","task":"Fix the add() bug","issue_number":1}'
```

## Make it reachable from UiPath Cloud
UiPath Cloud needs a public https URL:
```bash
# easiest for a demo — tunnel to the local API:
cloudflared tunnel --url http://localhost:8800
# or: ngrok http 8800
```
Use the printed https URL in your Maestro Service Task / HTTP Request, with header
`Authorization: Bearer <AUTOPR_API_TOKEN>`. Interactive docs at `/<url>/docs`.

## What needs your UiPath account
The Maestro process is built in **UiPath Studio Web** — that's the part only you can
do. Start with the **Day-1 go/no-go spike** in SUBMISSION_PLAN.md before committing
the week: a 2-node process hitting `/health` then `/code_fix` proves the integration.
