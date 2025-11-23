import json
from typing import Callable

import redis

from .models import ResonanceFrame


class Bus:
    """
    Thin wrapper around Redis pub/sub.

    Later, this can be swapped for NATS/MQTT by changing this file only.
    """

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self._redis = redis.from_url(url)

    def publish(self, topic: str, frame: ResonanceFrame) -> None:
        payload = frame.json()
        self._redis.publish(topic, payload)

    def subscribe(self, topic: str, handler: Callable[[ResonanceFrame], None]) -> None:
        pubsub = self._redis.pubsub()
        pubsub.subscribe(topic)

        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            frame = ResonanceFrame(**data)
            handler(frame)
