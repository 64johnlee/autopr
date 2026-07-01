"""
Proof of Deployment — AutoPR runs on Alibaba Cloud Model Studio (Qwen).

AutoPR calls Qwen-Max (triage) and Qwen-Plus (coding) through Alibaba Cloud
Model Studio's OpenAI-compatible DashScope endpoint. This standalone script is
the code-level proof required by the Qwen Cloud Global AI Hackathon:

    "A link to a code file that clearly uses Qwen Cloud APIs."

The Base URL below is the international Model Studio endpoint listed in the
hackathon's Proof-of-Deployment guide:

    https://dashscope-intl.aliyuncs.com/compatible-mode/v1

Run it with a valid DASHSCOPE_API_KEY to produce a live transcript (model name,
response, request id, and token usage) proving the backend executed on Alibaba
Cloud infrastructure:

    export DASHSCOPE_API_KEY=sk-...            # from Model Studio > API-KEY
    python docs/alibaba-cloud-proof.py

The printed request_id + usage is the evidence to pair with a screenshot of the
running resources in the Alibaba Cloud Model Studio workbench.
"""
import os

from openai import OpenAI

# Alibaba Cloud Model Studio — international OpenAI-compatible endpoint.
# Override with DASHSCOPE_BASE_URL for the China (dashscope.aliyuncs.com) or
# Token-Plan (token-plan.ap-southeast-1.maas.aliyuncs.com) endpoints.
BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=BASE_URL,
)


def _call(model: str, prompt: str) -> None:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    print(f"--- {model} @ {BASE_URL} ---")
    print("response:  ", resp.choices[0].message.content)
    print("model:     ", resp.model)
    print("request_id:", getattr(resp, "id", None))
    print("usage:     ", resp.usage)
    print()


if __name__ == "__main__":
    # Triage model (Qwen-Max) and coder model (Qwen-Plus) — the two models
    # AutoPR actually uses in production.
    _call("qwen-max", "Reply with exactly: AutoPR triage on Alibaba Cloud")
    _call("qwen-plus", "Reply with exactly: AutoPR coder on Alibaba Cloud")
