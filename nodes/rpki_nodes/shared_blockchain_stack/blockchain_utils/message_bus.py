#!/usr/bin/env python3
"""
InMemoryMessageBus - Replaces TCP socket P2P with in-memory message passing.

Instead of each node binding a TCP socket and connecting to peers via
socket.connect(), all messages are routed through this shared singleton.
This scales to 100-1000 nodes without wasting OS sockets or network I/O.

Messages are dispatched asynchronously via a thread pool so the sender
is never blocked by the receiver's handler execution time.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class InMemoryMessageBus:
    """Replaces TCP socket P2P with in-memory message passing."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.handlers: Dict[int, Callable] = {}  # as_number -> callback
        self.lock = threading.Lock()
        self.stats = {"sent": 0, "delivered": 0, "dropped": 0}
        # Thread pool for async message dispatch — keeps sender non-blocking
        self._executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="MsgBus")

    @classmethod
    def get_instance(cls) -> "InMemoryMessageBus":
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (for test isolation or between experiments)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._executor.shutdown(wait=False)
                cls._instance.handlers.clear()
                cls._instance.stats = {"sent": 0, "delivered": 0, "dropped": 0}
            cls._instance = None

    def register(self, as_number: int, handler: Callable):
        """Register a node's message handler (replaces socket.bind)."""
        with self.lock:
            self.handlers[as_number] = handler
            logger.debug(f"MessageBus: AS{as_number} registered")

    def unregister(self, as_number: int):
        """Unregister a node (replaces socket.close)."""
        with self.lock:
            self.handlers.pop(as_number, None)

    def send(self, from_as: int, to_as: int, message: dict):
        """Send message to a specific node asynchronously via thread pool."""
        self.stats["sent"] += 1
        handler = self.handlers.get(to_as)
        if handler is not None:
            self._executor.submit(self._dispatch, handler, to_as, message)
        else:
            self.stats["dropped"] += 1

    def _dispatch(self, handler: Callable, to_as: int, message: dict):
        """Execute handler in thread pool worker."""
        try:
            handler(message)
            self.stats["delivered"] += 1
        except Exception as e:
            logger.warning(f"MessageBus: handler error AS{to_as}: {e}")
            self.stats["dropped"] += 1

    def broadcast(self, from_as: int, message: dict, targets: Optional[List[int]] = None):
        """Broadcast to multiple nodes (replaces loop of socket sends)."""
        if targets is None:
            targets = [n for n in self.handlers if n != from_as]
        for target in targets:
            self.send(from_as, target, message)

    def get_registered_nodes(self) -> List[int]:
        """Get list of registered node AS numbers."""
        return list(self.handlers.keys())

    def get_stats(self) -> dict:
        """Get message bus statistics."""
        return dict(self.stats)
