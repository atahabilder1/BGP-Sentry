#!/usr/bin/env python3
"""
=============================================================================
BGP Attack Detector - Route Leak & IP Prefix Hijacking Detection
=============================================================================

Purpose: Detect malicious BGP announcements and protect against attacks

Attack Types Detected:
1. IP Prefix Hijacking - AS announces prefix it doesn't own
2. Route Leak - AS announces route it shouldn't (violates BGP policies)

Detection Methods:
- ROA (Route Origin Authorization) database checking
- AS relationship validation (customer, peer, provider)
- Prefix ownership verification
- AS path validity checking

Author: BGP-Sentry Team
=============================================================================
"""

import json
import ipaddress
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import cfg

# Bogon prefix ranges (RFC 1918 / RFC 2544 / RFC 5737 / RFC 6598 etc.)
BOGON_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    # RFC 6598 — Shared/CGN address space
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),     # RFC 2544 — Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]


class AttackDetector:
    """
    Detects BGP attacks in announcements.

    Checks for:
    - IP prefix hijacking (unauthorized prefix announcements)
    - Route leaks (violating valley-free routing)
    """

    def __init__(self, roa_database_path: str = "shared_data/roa_database.json",
                 as_relationships_path: str = "shared_data/as_relationships.json"):
        """
        Initialize attack detector.

        Args:
            roa_database_path: Path to ROA database (IP prefix → authorized AS)
            as_relationships_path: Path to AS relationship database
        """
        self.roa_db_path = Path(roa_database_path)
        self.as_rel_path = Path(as_relationships_path)

        # Load databases
        self.roa_database = self._load_roa_database()
        self.as_relationships = self._load_as_relationships()

        # Route flapping tracking: (prefix, origin_asn) -> list of *unique event* timestamps
        # We dedup observations arriving within FLAP_DEDUP_SECONDS of each other
        # (since multiple nodes may process the same announcement nearly simultaneously)
        self._flap_history: Dict[Tuple, List[float]] = defaultdict(list)
        self._flap_lock = threading.Lock()
        self.FLAP_WINDOW_SECONDS = cfg.FLAP_WINDOW_SECONDS
        self.FLAP_THRESHOLD = cfg.FLAP_THRESHOLD
        self.FLAP_DEDUP_SECONDS = cfg.FLAP_DEDUP_SECONDS

    def _load_roa_database(self) -> Dict:
        """
        Load ROA database mapping IP prefixes to authorized ASes.

        Format:
        {
          "8.8.8.0/24": {
            "authorized_as": 15169,
            "max_length": 24,
            "description": "Google DNS"
          }
        }
        """
        try:
            if self.roa_db_path.exists():
                with open(self.roa_db_path, 'r') as f:
                    return json.load(f)
            else:
                # Initialize with some common prefixes for testing
                default_roa = {
                    "8.8.8.0/24": {
                        "authorized_as": 15169,
                        "max_length": 24,
                        "description": "Google DNS"
                    },
                    "1.1.1.0/24": {
                        "authorized_as": 13335,
                        "max_length": 24,
                        "description": "Cloudflare DNS"
                    },
                    "203.0.113.0/24": {
                        "authorized_as": 12,
                        "max_length": 24,
                        "description": "Test prefix"
                    }
                }

                # Save default database
                self.roa_db_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.roa_db_path, 'w') as f:
                    json.dump(default_roa, f, indent=2)

                return default_roa

        except Exception as e:
            print(f"Error loading ROA database: {e}")
            return {}

    def _load_as_relationships(self) -> Dict:
        """
        Load AS relationship database.

        Format:
        {
          "1": {
            "customers": [2, 3],      # ASes that buy transit from AS1
            "providers": [],           # ASes that AS1 buys transit from
            "peers": [4, 5]           # ASes that AS1 peers with
          }
        }

        Valley-free routing rules:
        - Customer → Any (can announce to anyone)
        - Provider → Customer only (cannot announce provider routes to peers/providers)
        - Peer → Customer only (cannot announce peer routes to peers/providers)
        """
        try:
            if self.as_rel_path.exists():
                with open(self.as_rel_path, 'r') as f:
                    return json.load(f)
            else:
                # Initialize with simple test relationships
                default_relationships = {
                    "1": {"customers": [2, 3], "providers": [], "peers": [5, 7]},
                    "3": {"customers": [6], "providers": [1], "peers": [5]},
                    "5": {"customers": [8], "providers": [7], "peers": [1, 3]},
                    "7": {"customers": [10], "providers": [], "peers": [5, 9]},
                    "9": {"customers": [12], "providers": [11], "peers": [7, 13]},
                    "11": {"customers": [14], "providers": [], "peers": [13, 15]},
                    "13": {"customers": [16], "providers": [11], "peers": [9, 15]},
                    "15": {"customers": [18], "providers": [17], "peers": [13]},
                    "17": {"customers": [20], "providers": [], "peers": [15]}
                }

                # Save default database
                self.as_rel_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.as_rel_path, 'w') as f:
                    json.dump(default_relationships, f, indent=2)

                return default_relationships

        except Exception as e:
            print(f"Error loading AS relationships: {e}")
            return {}

    def detect_attacks(self, announcement: Dict) -> List[Dict]:
        """
        Detect all attacks in a BGP announcement.

        Args:
            announcement: BGP announcement with sender_asn, ip_prefix, as_path

        Returns:
            List of detected attacks (empty if legitimate)
        """
        detected_attacks = []

        # Check for IP prefix hijacking
        hijacking = self.detect_ip_prefix_hijacking(announcement)
        if hijacking:
            detected_attacks.append(hijacking)

        # Check for sub-prefix hijacking
        subprefix = self.detect_subprefix_hijack(announcement)
        if subprefix:
            detected_attacks.append(subprefix)

        # Check for bogon injection
        bogon = self.detect_bogon_injection(announcement)
        if bogon:
            detected_attacks.append(bogon)

        # Check for forged-origin prefix hijack (AS-path plausibility)
        forged = self.detect_forged_origin(announcement)
        if forged:
            detected_attacks.append(forged)

        # Check for route flapping
        flapping = self.detect_route_flapping(announcement)
        if flapping:
            detected_attacks.append(flapping)

        # Valley-free route-leak detection.  Enabled because scripts/inject_attacks.py
        # now injects valley-free-violating ROUTE_LEAK events so this detector has
        # attack instances to evaluate (BGPy's own ACCIDENTAL_ROUTE_LEAK scenarios
        # are forged-origin rather than valley-free and are filtered).
        leak = self.detect_route_leak(announcement)
        if leak:
            detected_attacks.append(leak)

        # Path-poisoning detection (AS-path manipulation).  Fires when the path
        # contains a consecutive AS pair that has no documented CAIDA relationship —
        # a strong indicator that a bogus AS was inserted to inflate / disguise
        # the path.
        poisoning = self.detect_path_poisoning(announcement)
        if poisoning:
            detected_attacks.append(poisoning)

        return detected_attacks

    def detect_ip_prefix_hijacking(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect IP prefix hijacking.

        Hijacking occurs when:
        - AS announces a prefix it's not authorized to announce
        - ROA database shows different authorized AS

        Args:
            announcement: BGP announcement

        Returns:
            Attack details if hijacking detected, None otherwise
        """
        try:
            sender_asn = announcement.get('sender_asn')
            ip_prefix = announcement.get('ip_prefix')

            if not sender_asn or not ip_prefix:
                return None

            # Check ROA database
            roa_entry = self.roa_database.get(ip_prefix)

            if not roa_entry:
                # Prefix not in ROA database - cannot verify
                # Not necessarily an attack, just unverifiable
                return None

            authorized_as = roa_entry['authorized_as']

            # Check if sender is authorized
            if sender_asn != authorized_as:
                # HIJACKING DETECTED!
                attack = {
                    "attack_type": "PREFIX_HIJACK",
                    "severity": "HIGH",
                    "attacker_as": sender_asn,
                    "victim_prefix": ip_prefix,
                    "legitimate_owner": authorized_as,
                    "evidence": {
                        "roa_authorized_as": authorized_as,
                        "announcing_as": sender_asn,
                        "mismatch": True
                    },
                    "description": f"AS{sender_asn} claiming {ip_prefix} but ROA shows AS{authorized_as}",
                    "detected_at": datetime.now().isoformat()
                }

                print(f"🚨 IP PREFIX HIJACKING DETECTED!")
                print(f"   Attacker: AS{sender_asn}")
                print(f"   Stolen Prefix: {ip_prefix}")
                print(f"   Legitimate Owner: AS{authorized_as}")

                return attack

            return None  # Legitimate announcement

        except Exception as e:
            print(f"Error detecting IP hijacking: {e}")
            return None

    def detect_route_leak(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect route leak violations.

        Route leak occurs when:
        - AS receives route from provider/peer
        - AS incorrectly announces it to provider/peer (violates valley-free)

        Valley-free routing:
        - Provider → Customer → Any (OK)
        - Peer → Customer → Any (OK)
        - Customer → Provider/Peer → Customer ONLY

        Args:
            announcement: BGP announcement with as_path

        Returns:
            Attack details if route leak detected, None otherwise
        """
        try:
            as_path = announcement.get('as_path', [])

            if len(as_path) < 3:
                # Need at least 3 ASes to detect leak
                return None

            # Check each hop in AS path for valley-free violations
            for i in range(len(as_path) - 2):
                prev_as = str(as_path[i])
                current_as = str(as_path[i + 1])
                next_as = str(as_path[i + 2])

                # Get relationships
                current_relations = self.as_relationships.get(current_as, {})

                # Determine relationship type
                prev_is_provider = int(prev_as) in current_relations.get('providers', [])
                prev_is_peer = int(prev_as) in current_relations.get('peers', [])
                next_is_provider = int(next_as) in current_relations.get('providers', [])
                next_is_peer = int(next_as) in current_relations.get('peers', [])

                # Valley-free violation check:
                # If received from provider or peer, can only send to customers
                if (prev_is_provider or prev_is_peer) and (next_is_provider or next_is_peer):
                    # ROUTE LEAK DETECTED!
                    attack = {
                        "attack_type": "ROUTE_LEAK",
                        "severity": "MEDIUM",
                        "leaker_as": int(current_as),
                        "as_path": as_path,
                        "leak_location": {
                            "received_from": int(prev_as),
                            "leaked_to": int(next_as),
                            "leaker": int(current_as)
                        },
                        "evidence": {
                            "received_from_type": "provider" if prev_is_provider else "peer",
                            "leaked_to_type": "provider" if next_is_provider else "peer",
                            "valley_free_violation": True
                        },
                        "description": f"AS{current_as} leaked route from {'provider' if prev_is_provider else 'peer'} AS{prev_as} to {'provider' if next_is_provider else 'peer'} AS{next_as}",
                        "detected_at": datetime.now().isoformat()
                    }

                    print(f"🚨 ROUTE LEAK DETECTED!")
                    print(f"   Leaker: AS{current_as}")
                    print(f"   Received from: AS{prev_as} ({'provider' if prev_is_provider else 'peer'})")
                    print(f"   Leaked to: AS{next_as} ({'provider' if next_is_provider else 'peer'})")
                    print(f"   Path: {' → '.join(map(str, as_path))}")

                    return attack

            return None  # No route leak detected

        except Exception as e:
            print(f"Error detecting route leak: {e}")
            return None

    def detect_path_poisoning(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect AS-path poisoning — a fabricated AS inserted into the path.

        An adversary constructs a BGP UPDATE whose AS-path contains two
        consecutive ASes that, per the canonical CAIDA relationship graph,
        have no declared business relationship (neither peer, customer, nor
        provider of each other).  In legitimate BGP propagation such an
        edge cannot appear.

        Conservative by design:
          - We only fire when BOTH ASes of the pair appear in our local
            CAIDA relationship database.  If either AS is absent the
            check is skipped (avoids false positives from incomplete data).
          - The adjacency test is symmetric: any relationship (a→b OR b→a
            across customer/provider/peer) exempts the pair.

        Args:
            announcement: BGP announcement with as_path

        Returns:
            Attack dict on detection, None otherwise.
        """
        try:
            as_path = announcement.get('as_path', [])
            if len(as_path) < 2:
                return None

            for i in range(len(as_path) - 1):
                a_str = str(as_path[i])
                b_str = str(as_path[i + 1])
                a_int = int(as_path[i])
                b_int = int(as_path[i + 1])

                rels_a = self.as_relationships.get(a_str)
                rels_b = self.as_relationships.get(b_str)
                if rels_a is None or rels_b is None:
                    # Missing relationship data — cannot determine, skip
                    continue

                has_rel = (
                    b_int in rels_a.get('customers', [])
                    or b_int in rels_a.get('providers', [])
                    or b_int in rels_a.get('peers', [])
                    or a_int in rels_b.get('customers', [])
                    or a_int in rels_b.get('providers', [])
                    or a_int in rels_b.get('peers', [])
                )
                if has_rel:
                    continue

                # No documented relationship between a and b — path is poisoned.
                return {
                    "attack_type": "PATH_POISONING",
                    "severity": "HIGH",
                    "as_path": as_path,
                    "invalid_edge": [a_int, b_int],
                    "edge_position": i,
                    "evidence": {
                        "no_relationship_between": [a_int, b_int],
                        "path_length": len(as_path),
                    },
                    "description": (
                        f"AS-path contains adjacency AS{a_int}↔AS{b_int} "
                        f"that has no documented CAIDA relationship "
                        f"(likely fabricated insertion)"
                    ),
                    "detected_at": datetime.now().isoformat(),
                }

            return None

        except Exception as e:
            print(f"Error in path-poisoning detection: {e}")
            return None

    def detect_subprefix_hijack(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect sub-prefix hijacking.

        Occurs when an AS announces a more-specific prefix of an existing ROA
        entry with a different origin AS.

        Example: ROA has 1.2.0.0/16 -> AS6300, attacker announces 1.2.3.0/24 -> AS999
        """
        try:
            sender_asn = announcement.get('sender_asn')
            ip_prefix = announcement.get('ip_prefix')
            if not sender_asn or not ip_prefix:
                return None

            try:
                announced = ipaddress.ip_network(ip_prefix, strict=False)
            except ValueError:
                return None

            # Check if announced prefix is a more-specific of any ROA prefix
            for roa_prefix_str, roa_entry in self.roa_database.items():
                try:
                    roa_net = ipaddress.ip_network(roa_prefix_str, strict=False)
                except ValueError:
                    continue

                # Skip exact match (handled by prefix hijack detector)
                if announced == roa_net:
                    continue

                # Check if announced is a subnet of the ROA prefix
                if announced.subnet_of(roa_net):
                    authorized_as = roa_entry.get('authorized_as')
                    max_length = roa_entry.get('max_length', roa_net.prefixlen)

                    # If the origin doesn't match AND prefix length exceeds max_length
                    if sender_asn != authorized_as:
                        return {
                            "attack_type": "SUBPREFIX_HIJACK",
                            "severity": "HIGH",
                            "attacker_as": sender_asn,
                            "victim_prefix": roa_prefix_str,
                            "hijacked_subprefix": ip_prefix,
                            "legitimate_owner": authorized_as,
                            "evidence": {
                                "roa_prefix": roa_prefix_str,
                                "roa_authorized_as": authorized_as,
                                "roa_max_length": max_length,
                                "announced_prefix": ip_prefix,
                                "announced_length": announced.prefixlen,
                                "announcing_as": sender_asn,
                            },
                            "description": (
                                f"AS{sender_asn} announces {ip_prefix} (sub-prefix of "
                                f"{roa_prefix_str} owned by AS{authorized_as})"
                            ),
                            "detected_at": datetime.now().isoformat(),
                        }

            return None
        except Exception as e:
            print(f"Error detecting sub-prefix hijack: {e}")
            return None

    def detect_forged_origin(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect forged-origin prefix hijack via AS-path plausibility.

        Forged-origin attacks bypass ROA validation: the attacker prepends the
        legitimate origin to its own AS-path, so the announcement shows a
        valid origin even though the attacker is the actual source. The
        signature of the attack is that the *penultimate* AS in the path
        has no real business relationship (customer / provider / peer) with
        the claimed origin in CAIDA's canonical AS-relationship data.

        Detection rule:
          Given as_path [..., penultimate, origin], flag the announcement if
          `origin` is not found among `penultimate`'s customers, providers,
          or peers in the loaded AS relationship database.

        Notes:
          - Requires canonical CAIDA relationships (see build_as_relationships.py).
          - If `penultimate` has no relationship data at all, the detector
            abstains (returns None) rather than flagging, to avoid false
            positives on ASes outside the relationship database.
        """
        try:
            as_path = announcement.get('as_path', [])
            sender_asn = announcement.get('sender_asn')
            if not sender_asn or len(as_path) < 2:
                return None

            penultimate = as_path[-2]
            claimed_origin = as_path[-1]

            # The claimed origin in the path must equal the announcement's origin;
            # if not, the announcement is malformed — let other detectors handle it.
            if claimed_origin != sender_asn:
                return None

            # Self-loop or single-hop path: nothing meaningful to check.
            if penultimate == claimed_origin:
                return None

            rels = self.as_relationships.get(str(penultimate))
            if not rels:
                # No relationship data for the penultimate AS — abstain.
                return None

            has_relationship = (
                claimed_origin in rels.get('customers', []) or
                claimed_origin in rels.get('providers', []) or
                claimed_origin in rels.get('peers', [])
            )

            if has_relationship:
                return None  # Plausible path.

            return {
                "attack_type": "FORGED_ORIGIN_PREFIX_HIJACK",
                "severity": "HIGH",
                "attacker_as": penultimate,
                "claimed_origin": claimed_origin,
                "victim_prefix": announcement.get('ip_prefix'),
                "evidence": {
                    "as_path": as_path,
                    "penultimate_as": penultimate,
                    "claimed_origin": claimed_origin,
                    "no_business_relationship": True,
                },
                "description": (
                    f"Implausible AS-path: AS{penultimate} has no CAIDA "
                    f"relationship with claimed origin AS{claimed_origin}"
                ),
                "detected_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"Error detecting forged origin: {e}")
            return None

    def detect_bogon_injection(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect bogon prefix injection.

        Bogon prefixes are IP address ranges that should never appear in the
        global routing table (RFC 5737 / RFC 1918 / RFC 6598 etc.).
        """
        try:
            ip_prefix = announcement.get('ip_prefix')
            sender_asn = announcement.get('sender_asn')
            if not ip_prefix or not sender_asn:
                return None

            try:
                announced = ipaddress.ip_network(ip_prefix, strict=False)
            except ValueError:
                return None

            for bogon in BOGON_RANGES:
                if announced.subnet_of(bogon) or announced == bogon:
                    return {
                        "attack_type": "BOGON_INJECTION",
                        "severity": "CRITICAL",
                        "attacker_as": sender_asn,
                        "bogon_prefix": ip_prefix,
                        "matching_bogon_range": str(bogon),
                        "evidence": {
                            "announced_prefix": ip_prefix,
                            "bogon_range": str(bogon),
                            "announcing_as": sender_asn,
                        },
                        "description": (
                            f"AS{sender_asn} announces bogon prefix {ip_prefix} "
                            f"(falls within {bogon})"
                        ),
                        "detected_at": datetime.now().isoformat(),
                    }

            return None
        except Exception as e:
            print(f"Error detecting bogon injection: {e}")
            return None

    def detect_route_flapping(self, announcement: Dict) -> Optional[Dict]:
        """
        Detect route flapping.

        Occurs when the same (prefix, origin_asn) pair is withdrawn and
        re-announced repeatedly (>FLAP_THRESHOLD times within FLAP_WINDOW_SECONDS).
        """
        try:
            ip_prefix = announcement.get('ip_prefix')
            sender_asn = announcement.get('sender_asn')
            if not ip_prefix or not sender_asn:
                return None

            key = (ip_prefix, sender_asn)
            now = datetime.now().timestamp()
            cutoff = now - self.FLAP_WINDOW_SECONDS

            with self._flap_lock:
                # Dedup: only count if last recorded event for this key is
                # older than FLAP_DEDUP_SECONDS (avoids counting multiple
                # nodes processing the same announcement as separate flaps)
                history = self._flap_history[key]
                if history and (now - history[-1]) < self.FLAP_DEDUP_SECONDS:
                    # Same event observed by another node — skip
                    return None

                # Record this unique event
                history.append(now)

                # Trim to window
                self._flap_history[key] = [
                    t for t in history if t > cutoff
                ]

                count = len(self._flap_history[key])

            if count > self.FLAP_THRESHOLD:
                return {
                    "attack_type": "ROUTE_FLAPPING",
                    "severity": "MEDIUM",
                    "attacker_as": sender_asn,
                    "flapping_prefix": ip_prefix,
                    "flap_count": count,
                    "window_seconds": self.FLAP_WINDOW_SECONDS,
                    "evidence": {
                        "prefix": ip_prefix,
                        "origin_asn": sender_asn,
                        "announcements_in_window": count,
                        "threshold": self.FLAP_THRESHOLD,
                    },
                    "description": (
                        f"AS{sender_asn} flapping prefix {ip_prefix} "
                        f"({count} announcements in {self.FLAP_WINDOW_SECONDS}s, "
                        f"threshold={self.FLAP_THRESHOLD})"
                    ),
                    "detected_at": datetime.now().isoformat(),
                }

            return None
        except Exception as e:
            print(f"Error detecting route flapping: {e}")
            return None

    def add_roa_entry(self, ip_prefix: str, authorized_as: int, max_length: int = None,
                     description: str = ""):
        """
        Add new ROA entry to database.

        Args:
            ip_prefix: IP prefix (e.g., "192.0.2.0/24")
            authorized_as: AS authorized to announce this prefix
            max_length: Maximum prefix length allowed
            description: Description of this prefix
        """
        try:
            if max_length is None:
                # Extract prefix length from ip_prefix
                max_length = int(ip_prefix.split('/')[1])

            self.roa_database[ip_prefix] = {
                "authorized_as": authorized_as,
                "max_length": max_length,
                "description": description
            }

            # Save to file
            with open(self.roa_db_path, 'w') as f:
                json.dump(self.roa_database, f, indent=2)

            print(f"✅ Added ROA entry: {ip_prefix} → AS{authorized_as}")

        except Exception as e:
            print(f"Error adding ROA entry: {e}")

    def add_as_relationship(self, as_number: int, customers: List[int] = None,
                          providers: List[int] = None, peers: List[int] = None):
        """
        Add or update AS relationship entry.

        Args:
            as_number: AS number
            customers: List of customer ASes
            providers: List of provider ASes
            peers: List of peer ASes
        """
        try:
            as_str = str(as_number)

            self.as_relationships[as_str] = {
                "customers": customers or [],
                "providers": providers or [],
                "peers": peers or []
            }

            # Save to file
            with open(self.as_rel_path, 'w') as f:
                json.dump(self.as_relationships, f, indent=2)

            print(f"✅ Updated AS{as_number} relationships")

        except Exception as e:
            print(f"Error updating AS relationships: {e}")


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("BGP ATTACK DETECTOR - TEST")
    print("=" * 80)
    print()

    # Initialize detector
    detector = AttackDetector(
        roa_database_path="test_data/roa_database.json",
        as_relationships_path="test_data/as_relationships.json"
    )

    print()
    print("🧪 Test 1: Legitimate Announcement")
    print("-" * 40)
    legitimate = {
        "sender_asn": 15169,
        "ip_prefix": "8.8.8.0/24",
        "as_path": [15169, 1234, 5678]
    }
    attacks = detector.detect_attacks(legitimate)
    print(f"Result: {'✅ Legitimate' if not attacks else f'⚠️ {len(attacks)} attacks detected'}")
    print()

    print("🧪 Test 2: IP Prefix Hijacking")
    print("-" * 40)
    hijacking = {
        "sender_asn": 666,  # Attacker
        "ip_prefix": "8.8.8.0/24",  # Google's prefix
        "as_path": [666, 1234, 5678]
    }
    attacks = detector.detect_attacks(hijacking)
    if attacks:
        for attack in attacks:
            print(f"⚠️  Attack Type: {attack['attack_type']}")
            print(f"   Severity: {attack['severity']}")
            print(f"   Description: {attack['description']}")
    print()

    print("🧪 Test 3: Route Leak")
    print("-" * 40)
    route_leak = {
        "sender_asn": 5,
        "ip_prefix": "203.0.113.0/24",
        "as_path": [5, 7, 5, 3, 1]  # AS5 leaked route from provider AS7 to peer AS5
    }
    attacks = detector.detect_attacks(route_leak)
    if attacks:
        for attack in attacks:
            print(f"⚠️  Attack Type: {attack['attack_type']}")
            print(f"   Severity: {attack['severity']}")
            print(f"   Description: {attack['description']}")
    print()
