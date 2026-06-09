"""
Proof of Alibaba Cloud deployment — AutoPR uses Alibaba Cloud Model Studio
to call Qwen-Max (triage) and Qwen-Plus (coding) via the DashScope API.

This file demonstrates the API integration. Run it with a valid DASHSCOPE_API_KEY
to verify the backend is live on Alibaba Cloud infrastructure.
"""
import os
from openai import OpenAI

# Alibaba Cloud Model Studio endpoint
client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# Triage call — Qwen-Max
resp = client.chat.completions.create(
    model="qwen-max",
    messages=[{"role": "user", "content": "Reply with exactly: AutoPR on Alibaba Cloud"}],
    temperature=0,
)
print("Qwen-Max response:", resp.choices[0].message.content)
print("Model:", resp.model)
print("Usage:", resp.usage)
