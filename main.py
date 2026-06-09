"""Entry point: runs agent loop + dashboard server concurrently."""
from __future__ import annotations

import asyncio
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()


async def _main():
    from autopr import agent_loop as agent
    from server import app

    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        agent.loop(),
    )


if __name__ == "__main__":
    asyncio.run(_main())
