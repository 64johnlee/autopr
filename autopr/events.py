"""In-process event bus for streaming live activity to the dashboard."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any

_subscribers: list[asyncio.Queue] = []
_history: deque[dict] = deque(maxlen=200)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(kind: str, data: Any) -> None:
    event = {"ts": _now(), "kind": kind, "data": data}
    _history.append(event)
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    # replay recent history so new clients see context
    for event in _history:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            break
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


def history() -> list[dict]:
    return list(_history)
