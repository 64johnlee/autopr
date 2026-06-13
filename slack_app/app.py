"""AutoPR Slack agent (Bolt, Socket Mode).

Flow:
    @AutoPR owner/repo#42 <describe the fix>
      → code_fix (MCP)  → posts a diff preview with Open PR / Discard buttons
      → [Open PR]        → open_pr (MCP)  → posts the PR URL
      → [Discard]        → discard (MCP)  → cleans up

Long-running work (code_fix can take minutes, open_pr ~seconds) is offloaded to
background tasks so the Socket Mode envelope is acknowledged immediately. Without
this, Slack would redeliver the event/action after ~3s and we would clone/open a
PR more than once. Results are posted via the web client from the background task.

Run:
    autopr-slack          # needs SLACK_BOT_TOKEN (xoxb-…) and SLACK_APP_TOKEN (xapp-…)
"""
from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from . import blocks
from .mcp_client import AutoPRMCP
from .parse import parse_request

load_dotenv()

logger = logging.getLogger("autopr.slack")

# Keep strong refs to background tasks so they are not garbage-collected mid-run.
_BG_TASKS: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)


def _thread_ts(message: dict | None, fallback: str | None) -> str | None:
    message = message or {}
    return message.get("thread_ts") or message.get("ts") or fallback


def build_app(autopr: AutoPRMCP) -> AsyncApp:
    app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
    client = app.client

    async def _post(channel: str, thread_ts: str | None, blks: list, text: str) -> None:
        await client.chat_postMessage(channel=channel, thread_ts=thread_ts, blocks=blks, text=text)

    async def _do_code_fix(channel: str, thread_ts: str | None, req) -> None:
        try:
            result = await autopr.call("code_fix", {
                "repo": req.repo, "task": req.task, "issue_number": req.issue_number,
            })
        except Exception as exc:  # MCP transport / server crash
            logger.exception("code_fix failed")
            await _post(channel, thread_ts, blocks.error_blocks(str(exc)), "AutoPR error")
            return
        if result.get("success"):
            await _post(channel, thread_ts, blocks.preview_blocks(result), "AutoPR proposed a fix")
        else:
            await _post(channel, thread_ts,
                        blocks.error_blocks(result.get("error", "unknown error")),
                        "AutoPR could not fix this")

    async def _do_open_pr(channel: str, thread_ts: str | None, session_id: str) -> None:
        try:
            result = await autopr.call("open_pr", {"session_id": session_id})
        except Exception as exc:
            logger.exception("open_pr failed")
            await _post(channel, thread_ts, blocks.error_blocks(str(exc)), "AutoPR error")
            return
        if result.get("success"):
            await _post(channel, thread_ts, blocks.pr_opened_blocks(result["pr_url"]), "Pull request opened")
        else:
            await _post(channel, thread_ts, blocks.error_blocks(result.get("error", "PR failed")), "AutoPR error")

    async def _do_discard(channel: str, thread_ts: str | None, session_id: str) -> None:
        try:
            await autopr.call("discard", {"session_id": session_id})
        except Exception:
            logger.exception("discard failed")
        await _post(channel, thread_ts, blocks.discarded_blocks(), "Discarded")

    @app.event("app_mention")
    async def on_mention(event, say):
        req = parse_request(event.get("text", ""))
        if req is None:
            await say(blocks=blocks.usage_blocks(), text="How to use AutoPR")
            return
        channel = event["channel"]
        thread_ts = event.get("thread_ts") or event.get("ts")
        # Quick ack-path post, then offload the long agent run.
        await say(blocks=blocks.working_blocks(req.repo, req.task),
                  text=f"AutoPR is working on {req.repo}", thread_ts=thread_ts)
        _spawn(_do_code_fix(channel, thread_ts, req))

    @app.action("open_pr")
    async def on_open_pr(ack, body):
        await ack()
        session_id = body["actions"][0]["value"]
        channel = body["channel"]["id"]
        thread_ts = _thread_ts(body.get("message"), None)
        _spawn(_do_open_pr(channel, thread_ts, session_id))

    @app.action("discard")
    async def on_discard(ack, body):
        await ack()
        session_id = body["actions"][0]["value"]
        channel = body["channel"]["id"]
        thread_ts = _thread_ts(body.get("message"), None)
        _spawn(_do_discard(channel, thread_ts, session_id))

    return app


async def _run() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    autopr = AutoPRMCP()
    await autopr.start()
    try:
        app = build_app(autopr)
        handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        logger.info("AutoPR Slack agent running (Socket Mode)")
        await handler.start_async()
    finally:
        await autopr.stop()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
