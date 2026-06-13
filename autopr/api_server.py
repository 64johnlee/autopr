"""AutoPR REST API — the endpoint UiPath Maestro calls.

UiPath Maestro orchestrates external agents by calling REST endpoints and expects
a structured JSON response. This FastAPI service exposes the same kernel as the MCP
server (via `agent_service`) so a Maestro Service Task / HTTP Request activity /
custom connector can:

    POST /code_fix   {repo, task, issue_number}  → {success, session_id, diff, …}
    POST /open_pr    {session_id}                → {success, pr_url, pr_number}
    POST /discard    {session_id}                → {success}
    GET  /health                                 → {status: "ok"}

Auth: set AUTOPR_API_TOKEN to require a Bearer token (recommended when exposed to
UiPath Cloud via a tunnel). If unset, the API is open (local/dev only).

Run:
    autopr-api                         # 0.0.0.0:8800 by default
    AUTOPR_API_PORT=8800 autopr-api
"""
from __future__ import annotations

import logging
import os
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .agent_service import run_code_fix, run_discard, run_open_pr

load_dotenv()

logger = logging.getLogger("autopr.api")

app = FastAPI(
    title="AutoPR REST API",
    description="Autonomous coding agent for UiPath Maestro orchestration",
    version="1.0.0",
)


def _check_auth(authorization: str | None) -> None:
    """Enforce a Bearer token if AUTOPR_API_TOKEN is configured."""
    expected = os.environ.get("AUTOPR_API_TOKEN")
    if not expected:
        return  # open mode (local/dev)
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


class CodeFixRequest(BaseModel):
    repo: str = Field(..., description="GitHub repo as 'owner/name'")
    task: str = Field(..., description="What to fix (issue body or instruction)")
    issue_number: int = Field(0, description="Optional issue number to reference")


class SessionRequest(BaseModel):
    session_id: str = Field(..., description="Session id from a prior /code_fix")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "autopr"}


@app.post("/code_fix")
async def code_fix(req: CodeFixRequest,
                   authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Run the coding agent and return a diff to preview. Nothing is pushed."""
    _check_auth(authorization)
    logger.info("code_fix: repo=%s issue=%s", req.repo, req.issue_number)
    return await run_code_fix(req.repo, req.task, req.issue_number)


@app.post("/open_pr")
async def open_pr(req: SessionRequest,
                 authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Open a PR from a previewed fix (consumes the session)."""
    _check_auth(authorization)
    logger.info("open_pr: session=%s", req.session_id)
    return run_open_pr(req.session_id)


@app.post("/discard")
async def discard(req: SessionRequest,
                 authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Discard a previewed fix and clean up."""
    _check_auth(authorization)
    return run_discard(req.session_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = int(os.environ.get("AUTOPR_API_PORT", "8800"))
    logger.info("AutoPR REST API serving on :%d (auth %s)",
                port, "ON" if os.environ.get("AUTOPR_API_TOKEN") else "OFF")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
