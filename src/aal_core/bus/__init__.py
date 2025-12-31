"""
`aal_core.bus` package.

Contains:
- `EventBus`: simple publish/subscribe + append-only event log
- `frame`: ResonanceFrame construction helpers
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.

    Events are published to topics and can be subscribed to by handlers.
    All events are also logged to an append-only event log (one JSON object per line).
    """

    def __init__(self, log_path: Optional[Path] = None):
        self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._log_path = log_path

        if self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, topic: str, handler: Callable[[str, Any], None]) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        event = {
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self._log_path:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        for handler in self._subscribers.get(topic, []):
            handler(topic, payload)

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._log_path or not self._log_path.exists():
            return []
        with open(self._log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-limit:]]


__all__ = ["EventBus"]

