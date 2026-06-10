"""Record the AutoPR demo: intro card -> live dashboard replay -> outro card.

Produces a single 1280x720 webm in _video/out/.
Requires demo_app.py already running on 127.0.0.1:7860.
"""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

INTRO_SECONDS = 7
DASHBOARD_SECONDS = 99  # timeline is ~95s; small buffer
OUTRO_SECONDS = 9


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(OUT),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        page.goto((HERE / "intro.html").as_uri())
        time.sleep(INTRO_SECONDS)

        page.goto("http://127.0.0.1:7860/")
        page.wait_for_selector("#feed")
        time.sleep(1.0)  # let SSE connect
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:7860/demo-start", method="POST"),
            timeout=10,
        )
        time.sleep(DASHBOARD_SECONDS)

        page.goto((HERE / "outro.html").as_uri())
        time.sleep(OUTRO_SECONDS)

        video = page.video
        context.close()
        path = video.path()
        browser.close()
        print(f"VIDEO={path}")


if __name__ == "__main__":
    main()
