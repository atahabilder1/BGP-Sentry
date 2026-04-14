import asyncio
import time
import threading


class SimulationClock:
    """Shared clock that replays BGP timestamps in real time.

    Anchors the earliest BGP timestamp to wall-clock ``start_time``.
    Each node calls ``wait_until(bgp_timestamp)`` before processing an
    observation, which sleeps until real time catches up.

    A ``speed_multiplier`` allows faster-than-real-time runs for testing
    (e.g. 10.0 = 10x faster).
    """

    def __init__(self, speed_multiplier: float = 1.0):
        self.speed_multiplier = speed_multiplier  # 1.0 = real-time
        self._anchor_bgp_ts: float | None = None  # earliest BGP timestamp (Unix epoch)
        self._anchor_wall_ts: float | None = None  # wall-clock time when simulation started
        self._started = threading.Event()
        self._async_started = None  # asyncio.Event, created lazily

    def set_epoch(self, earliest_bgp_timestamp: float):
        """Called once before start — sets the BGP time origin."""
        self._anchor_bgp_ts = earliest_bgp_timestamp

    def start(self):
        """Anchors BGP epoch to current wall-clock and unblocks all waiting nodes."""
        self._anchor_wall_ts = time.time()
        self._started.set()
        if self._async_started is not None:
            self._async_started.set()

    def start_async(self):
        """Anchors BGP epoch and unblocks async waiters."""
        self._anchor_wall_ts = time.time()
        self._started.set()
        if self._async_started is None:
            self._async_started = asyncio.Event()
        self._async_started.set()

    def _get_sleep_needed(self, bgp_timestamp: float) -> float:
        """Calculate how long to sleep for a given BGP timestamp."""
        bgp_offset = bgp_timestamp - self._anchor_bgp_ts
        wall_target = self._anchor_wall_ts + (bgp_offset / self.speed_multiplier)
        return wall_target - time.time()

    def wait_until(self, bgp_timestamp: float):
        """Block until real time catches up to this BGP timestamp."""
        self._started.wait()  # block until clock started
        sleep_needed = self._get_sleep_needed(bgp_timestamp)
        if sleep_needed > 0:
            time.sleep(sleep_needed)

    async def wait_until_async(self, bgp_timestamp: float):
        """Async version: yield control instead of blocking a thread."""
        if self._async_started is None:
            self._async_started = asyncio.Event()
        if not self._async_started.is_set():
            await self._async_started.wait()
        sleep_needed = self._get_sleep_needed(bgp_timestamp)
        if sleep_needed > 0:
            await asyncio.sleep(sleep_needed)

    def sim_time(self) -> float:
        """Current simulation time in seconds since epoch."""
        if self._anchor_wall_ts is None:
            return 0.0
        return (time.time() - self._anchor_wall_ts) * self.speed_multiplier


# Backward-compatible alias so existing imports still work.
SharedClockManager = SimulationClock
