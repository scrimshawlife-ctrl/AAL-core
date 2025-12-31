"""
AAL-core Event Bus
==================
Simple in-memory event bus for system events.
"""

from typing import Any, Callable, Dict, List
import json
from pathlib import Path
from datetime import datetime


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.

    Events are published to topics and can be subscribed to by handlers.
    All events are also logged to an append-only event log.
    """

    def __init__(self, log_path: Path = None):
        """
        Initialize event bus.

        Args:
            log_path: Optional path to event log file (JSONL format)
        """
        self._subscribers: Dict[str, List[Callable]] = {}
        self._log_path = log_path

        # Ensure log directory exists
        if self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, topic: str, handler: Callable[[str, Any], None]) -> None:
        """
        Subscribe to events on a topic.

        Args:
            topic: Topic name (e.g., "fn.registry.updated")
            handler: Callback function (topic: str, payload: Any) -> None
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []

        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        """
        Publish an event to a topic.

        Args:
            topic: Topic name
            payload: Event payload (must be JSON-serializable)
        """
        # Build event
        event = {
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Log to file (append-only)
        if self._log_path:
            try:
                with open(self._log_path, "a") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception as e:
                print(f"Warning: Failed to log event to {self._log_path}: {e}")

        # Notify subscribers
        handlers = self._subscribers.get(topic, [])
        for handler in handlers:
            try:
                handler(topic, payload)
            except Exception as e:
                print(f"Warning: Event handler for '{topic}' raised exception: {e}")

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events from the log.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dicts, most recent last
        """
        if not self._log_path or not self._log_path.exists():
            return []

        try:
            with open(self._log_path, "r") as f:
                lines = f.readlines()

            events = [json.loads(line) for line in lines[-limit:]]
            return events

        except Exception as e:
            print(f"Warning: Failed to read event log: {e}")
            return []
