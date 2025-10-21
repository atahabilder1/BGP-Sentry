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
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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

        print(f"🔍 Attack Detector initialized")
        print(f"   ROA entries: {len(self.roa_database)}")
        print(f"   AS relationships: {len(self.as_relationships)}")

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

        # Check for route leak
        route_leak = self.detect_route_leak(announcement)
        if route_leak:
            detected_attacks.append(route_leak)

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
                    "attack_type": "ip_prefix_hijacking",
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
                        "attack_type": "route_leak",
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
