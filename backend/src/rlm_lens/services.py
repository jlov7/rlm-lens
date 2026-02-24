from __future__ import annotations

import asyncio
from pathlib import Path
from collections.abc import Coroutine

from .db import Database
from .evaluation import EvaluationEngine
from .events import EventBroker
from .exporter import Exporter
from .indexer import CorpusReader, Indexer
from .policy import PolicyEngine
from .runtime.runner import RuntimeRunner
from .starter_corpora import StarterCorpusService
from .watcher import WatchManager


class Services:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db = Database(data_dir / "db.sqlite")
        self.broker = EventBroker()
        self.indexer = Indexer(self.db, self.broker)
        self.reader = CorpusReader(self.db)
        self.runner = RuntimeRunner(self.db, self.broker, data_dir)
        self.exporter = Exporter(self.db, data_dir)
        self.policy = PolicyEngine(self.db)
        self.watch_manager = WatchManager(self.db, self.indexer)
        self.evaluation = EvaluationEngine(self.db, self.runner)
        self.starter_corpora = StarterCorpusService(data_dir)
        self._tasks: set[asyncio.Task[None]] = set()

    def spawn(self, coro: Coroutine[object, object, None]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))

    async def shutdown(self) -> None:
        await self.watch_manager.shutdown()
        for task in list(self._tasks):
            task.cancel()
        self.db.close()
