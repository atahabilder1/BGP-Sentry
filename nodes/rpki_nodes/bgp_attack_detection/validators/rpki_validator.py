#!/usr/bin/env python3
"""
RPKI Validator

Validates BGP announcements against RPKI ROA database using StayRTR VRP data.
"""

import logging
import sys
from pathlib import Path

# Add blockchain_utils to path for StayRTRClient
_blockchain_utils = Path(__file__).resolve().parent.parent.parent / "shared_blockchain_stack" / "blockchain_utils"
sys.path.insert(0, str(_blockchain_utils))

logger = logging.getLogger(__name__)


class RPKIValidator:
    """RPKI Route Origin Authorization validator backed by StayRTR VRP data."""

    def __init__(self, registry_path=None, vrp_path="stayrtr/vrp_generated.json"):
        self.registry_path = registry_path
        self._client = None
        self._vrp_path = vrp_path

    def _ensure_client(self):
        if self._client is None:
            try:
                from stayrtr_client import StayRTRClient
                self._client = StayRTRClient(vrp_path=self._vrp_path)
                self._client.load()
            except Exception as e:
                logger.warning(f"StayRTR client unavailable: {e}")
                self._client = None

    def validate(self, announcement):
        """
        Validate announcement against RPKI ROAs.

        Args:
            announcement: dict with 'ip_prefix'/'prefix' and 'origin_asn'/'sender_asn'

        Returns:
            dict with 'valid', 'status', 'message' keys
        """
        self._ensure_client()

        prefix = announcement.get("ip_prefix") or announcement.get("prefix")
        origin = announcement.get("origin_asn") or announcement.get("sender_asn")

        if not prefix or not origin:
            return {
                "valid": False,
                "status": "error",
                "message": "Missing prefix or origin_asn"
            }

        if self._client is None:
            return {
                "valid": True,
                "status": "not_found",
                "message": "VRP data unavailable, assuming not_found"
            }

        result = self._client.validate_route(prefix, int(origin))

        if result == "valid":
            return {
                "valid": True,
                "status": "valid",
                "message": f"RPKI valid: {prefix} from AS{origin}"
            }
        elif result == "invalid":
            return {
                "valid": False,
                "status": "invalid",
                "message": f"RPKI invalid: {prefix} from AS{origin} (wrong origin)"
            }
        else:
            return {
                "valid": True,
                "status": "not_found",
                "message": f"No ROA found for {prefix}"
            }
