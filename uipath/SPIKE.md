# UiPath Day-1 spike — does UiPath talk to AutoPR? (≈1 hour)

A throwaway 2-step test to de-risk the whole track **before** building the full
flow. Goal: get UiPath to call AutoPR and receive a response. Green → proceed;
painful → rethink scope. You throw this process away afterward.

> Exact button labels in Studio Web / Maestro shift between releases — match by
> intent. The two things that matter are an HTTP call to `/health` and an HTTP
> call to `/code_fix` that comes back with a JSON body.

## Before you start (on your machine)
1. Make sure your **Qwen key works** only matters for `/code_fix`; `/health`
   works regardless. (If the key is still parked, you can run the spike with just
   the `/health` step and still prove the integration.)
2. Start the API + public tunnel:
   ```
   python serve_tunnel.py
   ```
   Copy the printed **Public base URL** (e.g. `https://xxxx.trycloudflare.com`)
   and the **`Authorization: Bearer <token>`** header. Leave this running.
3. Sanity check from a browser: open `<public-url>/health` → you should see
   `{"status":"ok","service":"autopr"}`.

## In UiPath (the actual spike)
1. **Create a free UiPath account** → open **Automation Cloud** →
   **Studio Web**.
2. **New project** → choose an **Agentic process / Maestro process** (a BPMN
   canvas). Name it `autopr-spike`.
3. **Step 1 — health check.** Add an **HTTP Request** activity (inside a Service
   Task if the canvas requires one):
   - Method: `GET`
   - URL: `<public-url>/health`
   - Run it. **Expected:** status `200`, body `{"status":"ok"}`.
   - ✅ If you see that, UiPath can reach AutoPR. Half the risk is gone.
4. **Step 2 — call the agent.** Add a second **HTTP Request**:
   - Method: `POST`
   - URL: `<public-url>/code_fix`
   - Headers: `Authorization = Bearer <token>`, `Content-Type = application/json`
   - Body (raw JSON):
     ```json
     { "repo": "<you>/autopr-demo", "task": "Fix the add() bug so tests pass", "issue_number": 1 }
     ```
     (Create the target first with `python live_test.py --create-demo-repo autopr-demo`.)
   - Run it. This takes a minute (clone + agent). **Expected:** a JSON body with
     `"success": true`, a `session_id`, and a `diff`.
5. **Read the output.** If Step 2 returns that JSON, **the integration works
   end-to-end** — UiPath orchestrated an autonomous coding agent and got a diff
   back.

## The go/no-go decision
- **Green** (both steps return JSON): proceed to the full BPMN flow in
  [ARCHITECTURE.md](ARCHITECTURE.md) — add the User Task approval, the `/open_pr`
  call, and the exception branches. The plumbing is proven; the rest is wiring.
- **Yellow** (`/health` works, `/code_fix` errors): the integration is fine; the
  error is on AutoPR's side (Qwen key / repo). Fix that, re-run Step 2.
- **Red** (can't get UiPath to make the call work in ~an hour): you've spent an
  hour, not a week. Decide whether to push through the platform learning curve or
  drop UiPath and double down on the Slack + Qwen entries.

## If something fails
- `/health` unreachable from UiPath → the tunnel isn't public or stopped; check
  `serve_tunnel.py` is still running and the URL is current (trycloudflare URLs
  change each run).
- `401` on `/code_fix` → the `Authorization: Bearer <token>` header is missing or
  wrong; copy it exactly from the `serve_tunnel.py` output.
- `/code_fix` returns `success:false` with a clone error → the `repo` doesn't
  exist or `gh` auth/Qwen key issue; test it directly first with
  `python live_test.py <you>/autopr-demo "..." --issue 1`.
