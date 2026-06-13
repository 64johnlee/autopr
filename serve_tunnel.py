#!/usr/bin/env python
"""One command to expose the AutoPR REST API to UiPath Cloud.

Boots `autopr-api`, waits until it's healthy, opens a public tunnel
(cloudflared preferred, ngrok fallback), and prints the public URL plus the exact
Authorization header to paste into a UiPath Maestro Service Task / HTTP Request.

Usage:
    python serve_tunnel.py
    AUTOPR_API_PORT=8800 python serve_tunnel.py

Ctrl+C stops both the API and the tunnel.
Requires cloudflared (`winget install cloudflare.cloudflared`) or ngrok.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.error import URLError

from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("AUTOPR_API_PORT", "8800"))
LOCAL_URL = f"http://localhost:{PORT}"
_CF_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def _ensure_token() -> str:
    """Use AUTOPR_API_TOKEN if set, else generate one for this session."""
    token = os.environ.get("AUTOPR_API_TOKEN")
    if not token:
        token = secrets.token_urlsafe(24)
        os.environ["AUTOPR_API_TOKEN"] = token
        print(f"[setup] no AUTOPR_API_TOKEN found — generated one for this run:\n        {token}")
    else:
        print("[setup] using AUTOPR_API_TOKEN from environment/.env")
    return token


def _wait_healthy(timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{LOCAL_URL}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except (URLError, OSError):
            time.sleep(0.5)
    return False


def _start_api(env: dict) -> subprocess.Popen:
    print(f"[api] starting autopr-api on :{PORT} …")
    return subprocess.Popen(
        [sys.executable, "-m", "autopr.api_server"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )


def _pick_tunnel() -> str | None:
    for tool in ("cloudflared", "ngrok"):
        if shutil.which(tool):
            return tool
    return None


def _start_cloudflared(url_box: dict) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", LOCAL_URL],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )

    def _drain() -> None:
        for line in proc.stdout:  # type: ignore[union-attr]
            if "url" not in url_box and (m := _CF_URL_RE.search(line)):
                url_box["url"] = m.group(0)

    threading.Thread(target=_drain, daemon=True).start()
    return proc


def _start_ngrok(url_box: dict) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["ngrok", "http", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # ngrok exposes a local API with the public URL
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
                import json
                data = json.load(r)
                for t in data.get("tunnels", []):
                    if t.get("public_url", "").startswith("https"):
                        url_box["url"] = t["public_url"]
                        return proc
        except (URLError, OSError):
            time.sleep(0.5)
    return proc


def _print_instructions(public_url: str, token: str) -> None:
    bar = "─" * 64
    print(f"\n{bar}\n  AutoPR is live and reachable from UiPath Cloud\n{bar}")
    print(f"  Public base URL : {public_url}")
    print(f"  Health check    : {public_url}/health")
    print(f"  OpenAPI docs    : {public_url}/docs")
    print(f"  Auth header     : Authorization: Bearer {token}")
    print("\n  UiPath Service Task / HTTP Request:")
    print(f"    POST {public_url}/code_fix")
    print(f"    Header: Authorization = Bearer {token}")
    print('    Body  : {"repo":"you/autopr-demo","task":"Fix the add() bug","issue_number":1}')
    print("\n  Quick local check:")
    print(f"    curl {public_url}/health")
    print(f"\n  Press Ctrl+C to stop the API and the tunnel.\n{bar}\n")


def main() -> None:
    token = _ensure_token()
    tunnel_tool = _pick_tunnel()
    if not tunnel_tool:
        print("[error] no tunnel tool found. Install one:")
        print("        cloudflared:  winget install cloudflare.cloudflared")
        print("        ngrok:        https://ngrok.com/download")
        sys.exit(1)

    env = dict(os.environ)
    api = _start_api(env)

    if not _wait_healthy():
        print("[error] API did not become healthy in time. Is the port free / deps installed?")
        api.terminate()
        sys.exit(1)
    print("[api] healthy ✓")

    url_box: dict[str, str] = {}
    print(f"[tunnel] opening {tunnel_tool} tunnel to {LOCAL_URL} …")
    tunnel = _start_cloudflared(url_box) if tunnel_tool == "cloudflared" else _start_ngrok(url_box)

    for _ in range(60):
        if "url" in url_box:
            break
        if tunnel.poll() is not None:
            print("[error] tunnel process exited unexpectedly.")
            api.terminate()
            sys.exit(1)
        time.sleep(0.5)

    if "url" not in url_box:
        print("[error] could not detect the public tunnel URL in time.")
        api.terminate()
        tunnel.terminate()
        sys.exit(1)

    _print_instructions(url_box["url"], token)

    try:
        while True:
            if api.poll() is not None:
                print("[exit] API process stopped.")
                break
            if tunnel.poll() is not None:
                print("[exit] tunnel process stopped.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[shutdown] stopping tunnel and API …")
    finally:
        for proc in (tunnel, api):
            try:
                proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
