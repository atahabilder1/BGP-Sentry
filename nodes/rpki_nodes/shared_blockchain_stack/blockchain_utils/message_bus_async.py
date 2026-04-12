#!/usr/bin/env python3
"""
AsyncMessageBus - Replaces ThreadPoolExecutor-based P2P with pure asyncio.

Instead of dispatching messages via a ThreadPoolExecutor (which creates
2,400+ threads at 400 nodes and triggers GIL contention), messages are
dispatched as lightweight asyncio tasks on a single event loop.

Performance comparison:
  - Threaded (400 nodes): 2,400 threads, 38% delivery, consensus collapse
  - Async (400 nodes):    ~5 tasks per message, 0 threads, no GIL contention
"""

import asyncio
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AsyncMessageBus:
    """Replaces InMemoryMessageBus with pure asyncio dispatch."""

    _instance = None

    def __init__(self):
        self.handlers: Dict[int, Callable] = {}  # as_number -> async callback
        self.stats = {"sent": 0, "delivered": 0, "dropped": 0}

    @classmethod
    def get_instance(cls) -> "AsyncMessageBus":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (for test isolation or between experiments)."""
        if cls._instance is not None:
            cls._instance.handlers.clear()
            cls._instance.stats = {"sent": 0, "delivered": 0, "dropped": 0}
        cls._instance = None

    def register(self, as_number: int, handler: Callable):
        """Register a node's async message handler."""
        self.handlers[as_number] = handler
        logger.debug(f"AsyncMessageBus: AS{as_number} registered")

    def unregister(self, as_number: int):
        """Unregister a node."""
        self.handlers.pop(as_number, None)

    async def send(self, from_as: int, to_as: int, message: dict):
        """Send message to a specific node as an asyncio task."""
        self.stats["sent"] += 1
        handler = self.handlers.get(to_as)
        if handler is not None:
            asyncio.create_task(self._dispatch(handler, to_as, message))
        else:
            self.stats["dropped"] += 1

    async def _dispatch(self, handler: Callable, to_as: int, message: dict):
        """Execute handler as a coroutine."""
        try:
            await handler(message)
            self.stats["delivered"] += 1
        except Exception as e:
            logger.warning(f"AsyncMessageBus: handler error AS{to_as}: {e}")
            self.stats["dropped"] += 1

    async def broadcast(self, from_as: int, message: dict,
                        targets: Optional[List[int]] = None):
        """Broadcast to multiple nodes."""
        if targets is None:
            targets = [n for n in self.handlers if n != from_as]
        for target in targets:
            await self.send(from_as, target, message)

    async def wait_idle(self, timeout: float = 30.0) -> bool:
        """Wait until all dispatched asyncio tasks have completed.

        Yields control to the event loop repeatedly; when no pending
        _dispatch tasks remain we consider the bus idle.  Returns True
        if idle, False if timed out.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Gather all pending _dispatch tasks
            pending = [
                t for t in asyncio.all_tasks()
                if not t.done() and t.get_coro().__qualname__.startswith("AsyncMessageBus._dispatch")
            ]
            if not pending:
                return True
            await asyncio.sleep(0.1)
        return False

    def get_registered_nodes(self) -> List[int]:
        """Get list of registered node AS numbers."""
        return list(self.handlers.keys())

    def get_stats(self) -> dict:
        """Get message bus statistics."""
        return dict(self.stats)
