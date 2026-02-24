from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from collections.abc import AsyncIterator


_SENTINEL = object()


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[tuple[str, str], set[asyncio.Queue[Any]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, entity_id: str, event: dict[str, Any]) -> None:
        key = (topic, entity_id)
        async with self._lock:
            queues = list(self._queues.get(key, set()))
        for queue in queues:
            await queue.put(event)

    async def close_topic(self, topic: str, entity_id: str) -> None:
        key = (topic, entity_id)
        async with self._lock:
            queues = list(self._queues.get(key, set()))
        for queue in queues:
            await queue.put(_SENTINEL)

    async def subscribe(self, topic: str, entity_id: str) -> AsyncIterator[dict[str, Any]]:
        key = (topic, entity_id)
        queue: asyncio.Queue[Any] = asyncio.Queue()
        async with self._lock:
            self._queues[key].add(queue)
        try:
            while True:
                event = await queue.get()
                if event is _SENTINEL:
                    break
                yield event
        finally:
            async with self._lock:
                subscribers = self._queues.get(key)
                if subscribers is not None:
                    subscribers.discard(queue)
                    if not subscribers:
                        del self._queues[key]
