#!/usr/bin/env python3
"""
BGPMonitor class for monitoring BGP announcements.

Supports two modes:
  1. File-based: reads from bgpd.json (legacy, for mininet/live simulation)
  2. In-memory: reads from pre-loaded observations (for CAIDA dataset mode)
"""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class BGPMonitor:
    """Monitor BGP announcements from file or in-memory data."""

    def __init__(self, bgpd_path=None, as_number=None, network_stack_path="../network_stack",
                 observations_data=None):
        """
        Args:
            bgpd_path: Path to bgpd.json file (file-based mode)
            as_number: AS number of this node
            network_stack_path: Path to network stack directory
            observations_data: List of observation dicts (in-memory mode, from DatasetLoader)
        """
        self.as_number = as_number
        self.last_processed = 0

        # In-memory mode (CAIDA datasets)
        if observations_data is not None:
            self._memory_mode = True
            self._observations = self._adapt_caida_observations(observations_data)
        else:
            self._memory_mode = False
            self._observations = []
            if bgpd_path:
                self.bgpd_path = Path(bgpd_path)
            else:
                self.bgpd_path = Path(network_stack_path) / "bgpd.json"

    def _adapt_caida_observations(self, raw_observations):
        """
        Convert CAIDA observation format to the internal announcement format.

        CAIDA format has: prefix, origin_asn, as_path, timestamp, label, is_attack, ...
        Internal format expects: sender_asn, ip_prefix, announced_prefixes, timestamp, ...
        """
        adapted = []
        for obs in raw_observations:
            adapted.append({
                "sender_asn": obs.get("origin_asn"),
                "ip_prefix": obs.get("prefix"),
                "announced_prefixes": [obs.get("prefix")],
                "timestamp": obs.get("timestamp_readable") or str(obs.get("timestamp", "")),
                "as_path": obs.get("as_path", []),
                "label": obs.get("label", "LEGITIMATE"),
                "is_attack": obs.get("is_attack", False),
                "origin_asn": obs.get("origin_asn"),
                "observed_by_asn": obs.get("observed_by_asn"),
                "observer_is_rpki": obs.get("observer_is_rpki", False),
            })
        return adapted

    def get_new_announcements(self):
        """Get new BGP announcements since last check."""
        if self._memory_mode:
            new = self._observations[self.last_processed:]
            self.last_processed = len(self._observations)
            return new

        # File-based mode
        try:
            if not self.bgpd_path.exists():
                return []

            with open(self.bgpd_path, "r") as f:
                data = json.load(f)

            announcements = data.get("bgp_announcements", [])
            new_announcements = announcements[self.last_processed:]
            self.last_processed = len(announcements)
            return new_announcements

        except Exception as e:
            logger.error(f"Error reading BGP announcements: {e}")
            return []

    def get_latest_announcements(self):
        """Get all latest BGP announcements."""
        return self.get_new_announcements()

    def get_total_count(self):
        """Get total number of announcements available."""
        if self._memory_mode:
            return len(self._observations)
        return self.last_processed
