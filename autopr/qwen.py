"""Provider-agnostic LLM client (OpenAI-compatible chat + tool calling).

Default provider is **Google Gemini** via the AI Studio OpenAI-compatible endpoint
— card-free (free tier, no billing required). Set ``AUTOPR_LLM_PROVIDER=qwen`` to
fall back to Alibaba Cloud Model Studio (Qwen), which needs an activated DashScope
account. The module name is kept as ``qwen`` for import compatibility; it is no
longer Qwen-specific.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_PROVIDER = os.environ.get("AUTOPR_LLM_PROVIDER", "gemini").lower()
_MAX_RETRIES = 6

# provider -> (api_key_env, base_url, default_triage_model, default_coder_model)
_PROVIDERS: dict[str, tuple[str, str, str, str]] = {
    "gemini": (
        "GEMINI_API_KEY",
        os.environ.get(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        "gemini-2.5-flash",
        "gemini-2.5-flash",
    ),
    "qwen": (
        "DASHSCOPE_API_KEY",
        os.environ.get(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "qwen-max",
        "qwen-plus",
    ),
}

if _PROVIDER not in _PROVIDERS:
    raise RuntimeError(
        f"Unknown AUTOPR_LLM_PROVIDER {_PROVIDER!r}; expected 'gemini' or 'qwen'"
    )

_API_KEY_ENV, _BASE_URL, _DEFAULT_TRIAGE, _DEFAULT_CODER = _PROVIDERS[_PROVIDER]

# Model overrides: provider-neutral LLM_* wins; legacy QWEN_* still honored.
_TRIAGE_MODEL = (
    os.environ.get("LLM_TRIAGE_MODEL")
    or os.environ.get("QWEN_TRIAGE_MODEL")
    or _DEFAULT_TRIAGE
)
_CODER_MODEL = (
    os.environ.get("LLM_CODER_MODEL")
    or os.environ.get("QWEN_CODER_MODEL")
    or _DEFAULT_CODER
)


def _client() -> AsyncOpenAI:
    api_key = os.environ.get(_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"{_API_KEY_ENV} must be set for AUTOPR_LLM_PROVIDER={_PROVIDER}"
        )
    return AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)


async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 0.1,
    system: str | None = None,
) -> Any:
    """Call the active provider with optional tools. Returns the raw response object."""
    model = model or _CODER_MODEL
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
            # Gemini uses RESOURCE_EXHAUSTED; Qwen/OpenAI use 429/rate_limit.
            if any(x in err for x in ["429", "rate_limit", "RESOURCE_EXHAUSTED"]):
                wait = 65
                m = re.search(r"retry in ([0-9.]+)s", err, re.I)
                if m:
                    wait = int(float(m.group(1))) + 5
                logger.warning("Rate limited — sleeping %ds", wait)
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError("LLM rate limit: max retries exceeded")


async def triage(messages: list[dict], system: str | None = None) -> Any:
    return await chat(messages, model=_TRIAGE_MODEL, system=system)


async def code(messages: list[dict], tools: list[dict], system: str | None = None) -> Any:
    return await chat(messages, tools=tools, model=_CODER_MODEL, system=system)
