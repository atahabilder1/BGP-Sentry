#!/usr/bin/env python3
"""
PrefixOwnershipState — Blockchain-Derived Prefix Ownership Verification.

Maintains a dynamic hash map of prefix → established origin AS, built from
accumulated CONFIRMED consensus decisions on the blockchain. This replaces
(or supplements) the static RPKI ROA database with a self-built, living
record of prefix ownership learned from network consensus.

Bootstrap: loads VRP (ROA) data as initial state at startup.
Learning:  every CONFIRMED transaction strengthens the mapping.
Detection: new announcements checked against established ownership.

Path to RPKI independence:
  Day 1:   RPKI + blockchain (hybrid)
  Day 30:  blockchain is authoritative (RPKI is backup)
  Day 365: RPKI optional (blockchain self-sufficient)
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PrefixOwnershipState:
    """Dynamic prefix-to-origin mapping built from blockchain consensus.

    Hash map structure:
        prefix_map[prefix] = {
            "established_origin": int,     # AS with most confirmations
            "confirmed_count": int,        # how many CONFIRMED for this origin
            "total_seen": int,             # total times this prefix appeared
            "first_seen": float,           # earliest timestamp
            "last_seen": float,            # latest timestamp
            "alternative_origins": {       # other ASes that claimed this prefix
                asn: count, ...
            },
            "co_owners": set,             # ASes recognised as legitimate MOAS
        }

    MOAS (Multi-Origin AS) handling:
        In production BGP, multiple ASes legitimately originate the same
        prefix (e.g. anycast, CDN, load-balancing).  When an alternative
        origin accumulates >= CONFIDENCE_THRESHOLD confirmations it is
        promoted to *co-owner* status and no longer triggers a hijack alert.
    """

    # Minimum confirmations before we trust the established origin
    CONFIDENCE_THRESHOLD = 3

    def __init__(self):
        self.prefix_map: Dict[str, dict] = {}
        self.lock = threading.Lock()

        # Stats
        self.total_updates = 0
        self.total_checks = 0
        self.detections = 0

    def bootstrap_from_vrp(self, vrp_path: str):
        """Load VRP (ROA) data as initial prefix ownership state.

        This gives immediate detection capability from day one.
        Each ROA entry becomes an established origin with high confidence.

        Args:
            vrp_path: Path to stayrtr/vrp_generated.json
        """
        vrp_file = Path(vrp_path)
        if not vrp_file.exists():
            logger.warning(f"VRP file not found: {vrp_path}, starting with empty state")
            return

        try:
            with open(vrp_file) as f:
                vrp_data = json.load(f)

            roas = vrp_data.get("roas", [])
            for roa in roas:
                prefix = roa.get("prefix")
                asn_str = roa.get("asn", "")
                # VRP format: "AS174" or 174
                if isinstance(asn_str, str) and asn_str.startswith("AS"):
                    asn = int(asn_str[2:])
                else:
                    asn = int(asn_str)

                if prefix in self.prefix_map:
                    # Multiple ROAs for the same prefix → MOAS co-owner
                    self.prefix_map[prefix]["co_owners"].add(asn)
                    continue

                self.prefix_map[prefix] = {
                    "established_origin": asn,
                    "confirmed_count": self.CONFIDENCE_THRESHOLD,  # trust ROA from start
                    "total_seen": 0,
                    "first_seen": 0,
                    "last_seen": 0,
                    "alternative_origins": {},
                    "co_owners": {asn},  # established origin is always a co-owner
                    "source": "vrp_bootstrap",
                }

            logger.info(
                f"PrefixOwnershipState bootstrapped from VRP: "
                f"{len(self.prefix_map)} prefixes loaded"
            )

        except Exception as e:
            logger.error(f"Failed to bootstrap from VRP: {e}")

    def update_from_confirmed(self, prefix: str, origin_asn: int,
                               timestamp: float = 0):
        """Update ownership state when a transaction is CONFIRMED on blockchain.

        Called after every successful CONFIRMED consensus write.
        Strengthens the mapping for this (prefix, origin) pair.

        Args:
            prefix: IP prefix (e.g., "10.0.0.0/8")
            origin_asn: AS number that claimed this prefix
            timestamp: BGP timestamp of the announcement
        """
        with self.lock:
            self.total_updates += 1

            if prefix not in self.prefix_map:
                # First time seeing this prefix — trust on first use
                self.prefix_map[prefix] = {
                    "established_origin": origin_asn,
                    "confirmed_count": 1,
                    "total_seen": 1,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "alternative_origins": {},
                    "co_owners": {origin_asn},
                    "source": "blockchain",
                }
                return

            entry = self.prefix_map[prefix]
            entry["total_seen"] += 1
            entry["last_seen"] = max(entry["last_seen"], timestamp)
            if entry["first_seen"] == 0:
                entry["first_seen"] = timestamp

            # Already a recognised co-owner — just strengthen
            if origin_asn in entry.get("co_owners", set()):
                if origin_asn == entry["established_origin"]:
                    entry["confirmed_count"] += 1
                return

            if origin_asn == entry["established_origin"]:
                # Same origin confirmed again — strengthen confidence
                entry["confirmed_count"] += 1
            else:
                # Different origin — track as alternative
                alt = entry["alternative_origins"]
                alt[origin_asn] = alt.get(origin_asn, 0) + 1

                # Promote to co-owner once it reaches CONFIDENCE_THRESHOLD
                if alt[origin_asn] >= self.CONFIDENCE_THRESHOLD:
                    co = entry.setdefault("co_owners", set())
                    co.add(origin_asn)
                    logger.info(
                        f"MOAS co-owner recognised: {prefix} "
                        f"AS{origin_asn} ({alt[origin_asn]} confirmations)"
                    )

                # If alternative has MORE confirmations, it becomes established
                if alt[origin_asn] > entry["confirmed_count"]:
                    # Ownership transfer — the new origin has more consensus
                    old_origin = entry["established_origin"]
                    old_count = entry["confirmed_count"]
                    entry["established_origin"] = origin_asn
                    entry["confirmed_count"] = alt[origin_asn]
                    # Move old established to alternatives
                    alt[old_origin] = old_count
                    del alt[origin_asn]
                    logger.info(
                        f"Prefix ownership transfer: {prefix} "
                        f"AS{old_origin} → AS{origin_asn} "
                        f"(new has {entry['confirmed_count']} confirmations)"
                    )

    def check_announcement(self, prefix: str, origin_asn: int) -> Optional[dict]:
        """Check if an announcement conflicts with established ownership.

        Accounts for MOAS: if the origin has been confirmed enough times
        to be a co-owner, it is treated as legitimate.

        Args:
            prefix: Announced IP prefix
            origin_asn: AS claiming this prefix

        Returns:
            Attack dict if conflict detected, None if legitimate or unknown
        """
        with self.lock:
            self.total_checks += 1

            if prefix not in self.prefix_map:
                # Unknown prefix — no opinion (will be learned)
                return None

            entry = self.prefix_map[prefix]
            established = entry["established_origin"]
            confidence = entry["confirmed_count"]

            if origin_asn == established:
                # Matches established owner — legitimate
                return None

            # Check MOAS co-owners
            if origin_asn in entry.get("co_owners", set()):
                return None

            if confidence < self.CONFIDENCE_THRESHOLD:
                # Not enough confidence to accuse — still learning
                return None

            # Also don't accuse if the alternative is approaching co-owner
            # status (at least half the threshold) — still learning
            alt_count = entry.get("alternative_origins", {}).get(origin_asn, 0)
            if alt_count >= self.CONFIDENCE_THRESHOLD // 2:
                return None

            # CONFLICT: different origin with sufficient confidence
            # and no co-owner history — likely a hijack
            self.detections += 1
            return {
                "attack_type": "PREFIX_HIJACK",
                "severity": "HIGH",
                "detection_method": "blockchain_state",
                "attacker_as": origin_asn,
                "victim_prefix": prefix,
                "legitimate_owner": established,
                "evidence": {
                    "established_origin": established,
                    "established_confirmations": confidence,
                    "claiming_origin": origin_asn,
                    "co_owners": list(entry.get("co_owners", set())),
                    "source": entry.get("source", "blockchain"),
                    "detected_by": "prefix_ownership_state",
                },
                "description": (
                    f"AS{origin_asn} claiming {prefix} but blockchain state "
                    f"shows AS{established} as established owner "
                    f"({confidence} confirmations)"
                ),
            }

    def get_stats(self) -> dict:
        """Return state statistics."""
        with self.lock:
            blockchain_learned = sum(
                1 for e in self.prefix_map.values()
                if e.get("source") == "blockchain"
            )
            vrp_bootstrap = sum(
                1 for e in self.prefix_map.values()
                if e.get("source") == "vrp_bootstrap"
            )
            moas_prefixes = sum(
                1 for e in self.prefix_map.values()
                if len(e.get("co_owners", set())) > 1
            )
            return {
                "total_prefixes_tracked": len(self.prefix_map),
                "vrp_bootstrapped": vrp_bootstrap,
                "blockchain_learned": blockchain_learned,
                "moas_prefixes": moas_prefixes,
                "total_updates": self.total_updates,
                "total_checks": self.total_checks,
                "detections": self.detections,
            }

    def get_ownership(self, prefix: str) -> Optional[dict]:
        """Get ownership info for a prefix."""
        with self.lock:
            entry = self.prefix_map.get(prefix)
            if entry is None:
                return None
            # Return a copy with co_owners as list for JSON serialization
            result = dict(entry)
            result["co_owners"] = list(result.get("co_owners", set()))
            return result
