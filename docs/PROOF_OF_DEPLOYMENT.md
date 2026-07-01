# Proof of Deployment — Qwen Cloud Global AI Hackathon

The hackathon requires **two** pieces of proof, or the submission is not eligible
(deadline: **July 9, 2026, 5 PM EDT**). Already-submitted entries must be updated
to include the screenshot.

## Requirement 1 — code file using the Qwen Cloud Base URL ✅ DONE

- [`docs/alibaba-cloud-proof.py`](./alibaba-cloud-proof.py) calls Qwen-Max and
  Qwen-Plus through the international Model Studio endpoint
  `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
- [`autopr/qwen.py`](../autopr/qwen.py) is the production client; set
  `AUTOPR_LLM_PROVIDER=qwen` and it uses `DASHSCOPE_BASE_URL` + the Qwen models.

Link either file in the Devpost submission's Proof-of-Deployment question.

## Requirement 2 — screenshot of running resources on Alibaba Cloud ⏳ NEEDS A WORKING KEY

The `.env` `DASHSCOPE_API_KEY` is dead (HTTP 401 `invalid_api_key`, verified
2026-07-01). A valid key is the only blocker. Card-safe steps:

1. **Get a working key (card-free).**
   - Sign in at the **international** Model Studio console:
     `https://modelstudio.console.alibabacloud.com/` (Singapore/intl account).
   - Activate Model Studio's **free tier** or redeem the hackathon **$40 voucher**
     (from the Devpost "Qwen Cloud credits" email).
   - ⚠️ If activation asks to **add a credit card**, STOP — use the voucher /
     free-tier path instead. Do not add a card.
   - Copy a key from **API-KEY** (`sk-...`).

2. **Run the live proof** (produces a real request_id + token usage):
   ```bash
   cd autopr
   export DASHSCOPE_API_KEY=sk-your-new-key
   python docs/alibaba-cloud-proof.py
   ```
   Expected: two `--- qwen-* @ ...dashscope-intl... ---` blocks with a response,
   `request_id`, and `usage`. Save this terminal output.

3. **Screenshot the workbench.** In the Model Studio console, capture a page that
   shows **running resources / usage** tied to your account — e.g. the
   **Usage/Billing** or **API-KEY** page after the call above registers activity.

4. **Update the Devpost submission** (`autopr-j27atz`): attach the screenshot to
   the refined Proof-of-Deployment question and confirm the code link points at
   `docs/alibaba-cloud-proof.py`. Repeat for the 2nd Qwen entry if kept.

Once you have a working key, hand it over and steps 2–4 can be automated
(run the proof, capture the console screenshot via the browser bridge, refill
the Devpost form).
