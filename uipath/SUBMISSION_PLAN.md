# AutoPR × UiPath — submission plan

**Deadline:** June 29, 2026, 11:45pm EDT. **Scoring:** 5 criteria × 1–5 (equal
weight) = 25, **+2 coding-agent bonus = 27 max**. One reviewer in Phase 1; top 10
per track go to a live Zoom Phase 2 (presentation matters).

## Required deliverables (checklist)
- [ ] Functional project built with **UiPath Studio Web** (the Maestro process).
- [ ] **Public GitHub repo** (MIT/Apache-2.0) with README stating: description,
      **UiPath components used**, **agent type** (Coded / Low-code / both), setup.
      → This repo is MIT; the README must add a "UiPath components used" section.
- [ ] **Text description**: business problem + solution (use ARCHITECTURE.md).
- [ ] **Demo video ≤ 5 min** (YouTube/Vimeo/Youku).
- [ ] **Presentation deck** (UiPath's template) via shared link.
- [ ] Complete the **UiPath Labs access form** (locks team roster — do this early).
- [ ] If finalist: post the solution as a use case on the **UiPath Community Forum**.

## The +2 coding-agent bonus — you've basically already earned it
The bonus rewards building the submission with an AI dev tool (Claude Code, Codex,
…). **This entire integration layer was built with Claude Code**, so document it.
The rules require three things — put this block in the Devpost description AND README:

> **(a) Tool used:** Claude Code (Anthropic).
> **(b) How it contributed:** Claude Code designed and implemented the AutoPR REST
> API (`autopr/api_server.py`), the shared agent service (`autopr/agent_service.py`),
> the MCP server, and this UiPath integration architecture; it also wrote the tests
> and caught/fixed real bugs (e.g., a `.env` token override breaking clones).
> **(c) Verifiable evidence:** commit history on this repo + the session
> transcript/screenshots showing the prompts and generated diffs.

**Action:** save 2–3 screenshots of this Claude Code session (a prompt + a diff +
the test run) into `uipath/evidence/` and reference them. That moves the bonus from
1 point ("partial") to 2 points ("meaningfully integrated, verifiable").

## Demo video outline (≤ 5 min; lead with the orchestration)
1. **0:00–0:30 — Problem.** Backlog of small bugs; each one a context switch.
2. **0:30–1:30 — The Maestro process.** Show the BPMN canvas in Studio Web; walk
   the flow: intake → Service Task (AutoPR) → human approval → open PR.
3. **1:30–3:00 — Live run.** Kick off a case; Maestro calls AutoPR `/code_fix`;
   the **diff appears in Action Center**; approve; Maestro calls `/open_pr`; show
   the real PR on GitHub. (Use the planted-bug demo repo from `live_test.py`.)
4. **3:00–4:00 — Governance & exceptions.** Show the failure branch and the audit
   trail / approval record — this is the "deep platform usage" judges reward.
5. **4:00–5:00 — Coding-agent bonus + close.** 20 seconds showing Claude Code built
   it (the evidence), then the impact recap.

## Deck outline (fill UiPath's template)
1. Title + one-line pitch. 2. Problem & business impact. 3. Solution overview.
4. Architecture (drop the BPMN diagram from ARCHITECTURE.md). 5. UiPath components
used (Maestro, Service Task, User Task/Action Center, Integration Service).
6. Live results / metrics. 7. Governance & exception handling. 8. Coding-agent
bonus evidence. 9. What's next.

## Map each judging criterion to a slide/scene
| Criterion | Where you win it |
|-----------|------------------|
| Business Impact & Adoption | Problem slide + cycle-time framing |
| Platform Usage (deep) | BPMN canvas + Action Center approval + custom connector |
| Technical Execution & Versatility | Live run + exception branch + the REST API |
| Completeness of Delivery | End-to-end intake → merged-ready PR in one run |
| Creativity & Innovation | Autonomous coding agent as a governed business worker |
| +2 Bonus | Claude Code evidence block (a/b/c above) |

## Build order (what's left — and who does it)
**Done (code, by Claude Code):** REST API (`autopr-api`), shared service, MCP
server, tests, this plan + architecture.

**You, on UiPath (the feasibility-gated part):**
1. **Day 1 spike (go/no-go):** create a UiPath Automation Cloud account; in Studio
   Web build a 2-node Maestro process that calls `GET /health` then `POST /code_fix`
   against the tunneled AutoPR API. If you get a green response back, the rest is
   wiring — proceed. If the platform fights you, reconsider scope before sinking days.
2. Build the full BPMN flow (intake → /code_fix → User Task → /open_pr + exceptions).
3. Expose AutoPR (tunnel or deploy) with `AUTOPR_API_TOKEN` set.
4. Record the demo, fill the deck, write the "UiPath components used" README section.
5. Submit + UiPath Labs form (early) + Community Forum post if finalist.

## Honest risk note
This is the tightest deadline (Jun 29) and the only track needing a platform you
haven't used. The code side is ready and proven; the risk is entirely the UiPath
Cloud learning curve. Treat **step 1 as a hard go/no-go** before committing the week.
