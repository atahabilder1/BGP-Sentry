"""Utility classes for aligning node processing with the shared simulation clock.

The synchronizer provides a thin convenience wrapper around ``SharedClockManager``
so individual node processes can register with the global experiment clock and
sleep until a target simulation time is reached.  The accompanying
``BGPTimeWindowManager`` offers simple helpers for working with discrete time
windows while consuming BGP announcements.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .shared_clock import SharedClockManager


class NodeTimeSynchronizer:
    """Coordinate node activity with the shared simulation clock.

    The class intentionally keeps the interface small—most callers only need to
    register their node, query the current simulation time, and optionally block
    until a target time is reached before processing their next batch of work.
    """

    def __init__(
        self,
        clock_manager: SharedClockManager,
        node_id: str,
        *,
        time_tolerance: float = 0.5,
    ) -> None:
        self._clock = clock_manager
        self._node_id = node_id
        self._tolerance = max(time_tolerance, 0.0)
        self._registered = False

    def register_node(self) -> None:
        """Register the node with the shared clock exactly once."""

        if not self._registered:
            self._clock.register_node(self._node_id)
            self._registered = True

    def get_simulation_time(self) -> float:
        """Return the current simulation time from the shared clock."""

        return float(self._clock.get_simulation_time())

    def wait_until(
        self,
        target_time: float,
        *,
        poll_interval: float = 0.5,
        timeout: Optional[float] = None,
    ) -> bool:
        """Block until ``target_time`` (in simulation seconds) is reached.

        Args:
            target_time: Desired simulation time to wait for.
            poll_interval: Real-time seconds to wait between clock checks.
            timeout: Optional real-time timeout; ``None`` waits indefinitely.

        Returns:
            ``True`` if the target time was reached, ``False`` on timeout.
        """

        target_time = max(0.0, float(target_time))
        poll_interval = max(0.01, float(poll_interval))
        start_real = time.time()

        while True:
            current_sim = self.get_simulation_time()
            if current_sim + self._tolerance >= target_time:
                return True

            if timeout is not None and time.time() - start_real >= timeout:
                return False

            time.sleep(poll_interval)


@dataclass
class TimeWindow:
    """Simple container describing a simulation time window."""

    start: float
    end: float

    def contains(self, timestamp: float) -> bool:
        return self.start <= timestamp < self.end


class BGPTimeWindowManager:
    """Track rolling simulation windows for batching BGP announcements."""

    def __init__(
        self,
        synchronizer: NodeTimeSynchronizer,
        *,
        window_size: float = 30.0,
        step_size: Optional[float] = None,
    ) -> None:
        self._sync = synchronizer
        self._window_size = max(1.0, float(window_size))
        self._step_size = float(step_size) if step_size is not None else self._window_size
        self._current_window = self._initial_window()

    def _initial_window(self) -> TimeWindow:
        sim_time = self._sync.get_simulation_time()
        start = sim_time - (sim_time % self._step_size)
        return TimeWindow(start=start, end=start + self._window_size)

    def current_window(self) -> TimeWindow:
        """Return the current window, refreshing it if the clock advanced."""

        sim_time = self._sync.get_simulation_time()
        if sim_time >= self._current_window.end:
            self.advance_to(sim_time)
        return self._current_window

    def advance(self) -> TimeWindow:
        """Advance the window by ``step_size`` and return the new window."""

        new_start = self._current_window.start + self._step_size
        self._current_window = TimeWindow(new_start, new_start + self._window_size)
        return self._current_window

    def advance_to(self, simulation_time: float) -> TimeWindow:
        """Advance windows until ``simulation_time`` falls within the window."""

        while simulation_time >= self._current_window.end:
            self.advance()
        return self._current_window

    def window_bounds(self) -> Tuple[float, float]:
        """Return ``(start, end)`` of the active window for convenience."""

        window = self.current_window()
        return window.start, window.end

    def reset(self) -> None:
        """Realign the window with the current simulation time."""

        self._current_window = self._initial_window()
