"""Qwen client via Alibaba Cloud Model Studio (OpenAI-compatible API)."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_TRIAGE_MODEL = os.environ.get("QWEN_TRIAGE_MODEL", "qwen-max")
_CODER_MODEL  = os.environ.get("QWEN_CODER_MODEL", "qwen-plus")
# Region must match the API key's region. Beijing (default) vs Singapore intl:
#   https://dashscope-intl.aliyuncs.com/compatible-mode/v1
_BASE_URL     = os.environ.get("DASHSCOPE_BASE_URL",
                               "https://dashscope.aliyuncs.com/compatible-mode/v1")
_MAX_RETRIES  = 6


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=_BASE_URL,
    )


async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = _CODER_MODEL,
    temperature: float = 0.1,
    system: str | None = None,
) -> Any:
    """Call Qwen with optional tools. Returns the raw response object."""
    if system:
        messages = [{"role": "system", "content": system}] + messages

    kwargs: dict[str, Any] = dict(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    client = _client()
    for attempt in range(_MAX_RETRIES):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as exc:
            err = str(exc)
            if any(x in err for x in ["429", "rate_limit", "RESOURCE_EXHAUSTED"]):
                wait = 65
                m = re.search(r"retry in ([0-9.]+)s", err, re.I)
                if m:
                    wait = int(float(m.group(1))) + 5
                logger.warning("Rate limited — sleeping %ds", wait)
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError("Qwen rate limit: max retries exceeded")


async def triage(messages: list[dict], system: str | None = None) -> Any:
    return await chat(messages, model=_TRIAGE_MODEL, system=system)


async def code(messages: list[dict], tools: list[dict], system: str | None = None) -> Any:
    return await chat(messages, tools=tools, model=_CODER_MODEL, system=system)
