#!/usr/bin/env python3
"""
=============================================================================
Attack Injection System - Controlled Attack Scenario Testing
=============================================================================

Purpose: Inject controlled attack scenarios into specific non-RPKI ASes
         for detection rate testing and rating system validation.

Features:
- Inject customizable number of attacks per AS
- Support multiple attack types (hijacking, route leak, sub-prefix)
- Track ground truth for detection rate calculation
- Monitor rating changes in real-time
- Generate post-hoc analysis reports

Author: BGP-Sentry Team
=============================================================================
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Import RPKI Node Registry
from rpki_node_registry import RPKINodeRegistry

class AttackInjectionSystem:
    """
    System for injecting controlled attacks and monitoring detection.

    Workflow:
    1. Generate attack scenarios with ground truth
    2. Inject into BGP data streams
    3. Monitor detection and rating changes
    4. Generate accuracy reports
    """

    def __init__(self, project_root: str = None):
        """
        Initialize attack injection system.

        Args:
            project_root: Root directory of BGP-Sentry project
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect project root (4 levels up from this file)
            self.project_root = Path(__file__).parent.parent.parent.parent.parent

        # Attack scenario storage
        self.attack_scenarios_file = (
            self.project_root /
            "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/attack_scenarios_injected.json"
        )

        # Ground truth ROA database
        self.roa_database_file = (
            self.project_root /
            "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/roa_database.json"
        )

        # IP-ASN mapping
        self.ip_asn_mapping_file = (
            self.project_root /
            "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ip_asn_mapping.json"
        )

        # Attack types with severity
        self.attack_types = {
            "ip_prefix_hijacking": {
                "severity": "CRITICAL",
                "rating_penalty": -20,
                "description": "AS announces prefix owned by another AS"
            },
            "sub_prefix_hijacking": {
                "severity": "HIGH",
                "rating_penalty": -15,
                "description": "AS announces more specific prefix of another AS"
            },
            "route_leak": {
                "severity": "MEDIUM",
                "rating_penalty": -10,
                "description": "AS leaks route it shouldn't announce"
            }
        }

        # Load existing data
        self._load_ground_truth()

        print(f"🎯 Attack Injection System Initialized")
        print(f"   Project Root: {self.project_root}")
        print(f"   Attack Scenarios: {self.attack_scenarios_file}")

    def _load_ground_truth(self):
        """Load ground truth data (ROA database, IP-ASN mappings)"""
        try:
            # Load ROA database
            if self.roa_database_file.exists():
                with open(self.roa_database_file, 'r') as f:
                    self.roa_database = json.load(f)
                print(f"   ✅ Loaded ROA database: {len(self.roa_database.get('roas', []))} entries")
            else:
                print(f"   ⚠️  ROA database not found, creating default...")
                self.roa_database = self._create_default_roa_database()

            # Load IP-ASN mapping
            if self.ip_asn_mapping_file.exists():
                with open(self.ip_asn_mapping_file, 'r') as f:
                    self.ip_asn_mapping = json.load(f)
                print(f"   ✅ Loaded IP-ASN mapping: {len(self.ip_asn_mapping)} prefixes")
            else:
                print(f"   ⚠️  IP-ASN mapping not found, creating default...")
                self.ip_asn_mapping = {}

        except Exception as e:
            print(f"   ❌ Error loading ground truth: {e}")
            self.roa_database = {}
            self.ip_asn_mapping = {}

    def _create_default_roa_database(self) -> Dict:
        """Create default ROA database with Google and common prefixes"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "roas": [
                # Google DNS
                {"prefix": "8.8.8.0/24", "max_length": 24, "asn": 15169, "source": "rpki"},
                {"prefix": "8.8.4.0/24", "max_length": 24, "asn": 15169, "source": "rpki"},

                # Cloudflare
                {"prefix": "1.1.1.0/24", "max_length": 24, "asn": 13335, "source": "rpki"},

                # Test prefixes for RPKI nodes
                {"prefix": "10.1.0.0/16", "max_length": 24, "asn": 1, "source": "rpki"},
                {"prefix": "10.3.0.0/16", "max_length": 24, "asn": 3, "source": "rpki"},
                {"prefix": "10.5.0.0/16", "max_length": 24, "asn": 5, "source": "rpki"},
                {"prefix": "10.7.0.0/16", "max_length": 24, "asn": 7, "source": "rpki"},

                # Non-RPKI legitimate prefixes
                {"prefix": "192.168.100.0/24", "max_length": 24, "asn": 100, "source": "irr"},
                {"prefix": "192.168.200.0/24", "max_length": 24, "asn": 200, "source": "irr"},
            ]
        }

    def inject_attack_scenarios(self, attacker_as_list: List[Tuple[int, int]],
                                 attack_ratio: float = 0.01) -> Dict:
        """
        Inject attack scenarios with legitimate announcements to maintain attack ratio.

        Args:
            attacker_as_list: List of (as_number, attack_count) tuples
                             Example: [(666, 12), (31337, 8)]
            attack_ratio: Attack percentage (default 0.01 = 1%)

        Returns:
            Dict with injection results and ground truth
        """
        print(f"\n{'='*80}")
        print(f"🚨 ATTACK INJECTION SYSTEM WITH LEGITIMATE TRAFFIC")
        print(f"{'='*80}\n")

        total_attacks = sum(count for _, count in attacker_as_list)

        # Calculate required legitimate announcements to maintain ratio
        # If attacks = 20 and ratio = 0.01 (1%), then:
        # total_needed = 20 / 0.01 = 2000
        # legitimate = 2000 - 20 = 1980
        total_needed = int(total_attacks / attack_ratio)
        legitimate_needed = total_needed - total_attacks

        print(f"📋 Injection Plan (Attack Ratio: {attack_ratio*100:.2f}%):")
        print(f"   Total Attacks: {total_attacks} ({attack_ratio*100:.1f}%)")
        print(f"   Legitimate Announcements: {legitimate_needed} ({(1-attack_ratio)*100:.1f}%)")
        print(f"   TOTAL Announcements: {total_needed}")
        print()

        print(f"   Attack Distribution:")
        for as_num, count in attacker_as_list:
            print(f"      AS{as_num}: {count} attacks")
        print()

        # Storage for all generated attacks
        all_attack_scenarios = {
            "injection_timestamp": datetime.now().isoformat(),
            "total_attacks": total_attacks,
            "attackers": {},
            "ground_truth": {},
            "detection_tracking": {}
        }

        # Generate attacks for each AS
        for attacker_as, attack_count in attacker_as_list:
            print(f"🔧 Generating {attack_count} attacks for AS{attacker_as}...")

            # Verify AS is non-RPKI
            if RPKINodeRegistry.is_rpki_node(attacker_as):
                print(f"   ⚠️  WARNING: AS{attacker_as} is an RPKI node! Skipping...")
                continue

            # Generate attack scenarios
            scenarios = self._generate_attacks_for_as(attacker_as, attack_count)

            # Store scenarios
            all_attack_scenarios["attackers"][attacker_as] = {
                "total_attacks": len(scenarios),
                "attack_breakdown": self._count_attack_types(scenarios),
                "scenarios": scenarios,
                "initial_rating": 50,  # Default starting rating
                "expected_final_rating": 50 - (len(scenarios) * 5)  # Rough estimate
            }

            # Create ground truth entries
            for i, scenario in enumerate(scenarios):
                attack_id = f"attack_{attacker_as}_{i+1:03d}"
                all_attack_scenarios["ground_truth"][attack_id] = {
                    "attacker_as": attacker_as,
                    "attack_type": scenario["attack_type"],
                    "victim_as": scenario["victim_as"],
                    "hijacked_prefix": scenario["hijacked_prefix"],
                    "timestamp": scenario["timestamp"],
                    "severity": scenario["severity"],
                    "should_detect": True,  # Ground truth: should be detected
                    "expected_penalty": scenario["expected_penalty"]
                }

                # Initialize detection tracking
                all_attack_scenarios["detection_tracking"][attack_id] = {
                    "detected": False,
                    "detection_time": None,
                    "detection_node": None,
                    "consensus_reached": False,
                    "rating_penalty_applied": False
                }

            print(f"   ✅ Generated {len(scenarios)} attack scenarios")
            print(f"   📊 Types: {all_attack_scenarios['attackers'][attacker_as]['attack_breakdown']}")

        # Generate legitimate announcements
        print(f"🔧 Generating {legitimate_needed} legitimate announcements...")
        legitimate_scenarios = self._generate_legitimate_announcements(legitimate_needed)

        all_attack_scenarios["legitimate_announcements"] = legitimate_scenarios
        all_attack_scenarios["total_legitimate"] = len(legitimate_scenarios)
        all_attack_scenarios["total_announcements"] = total_attacks + len(legitimate_scenarios)
        all_attack_scenarios["attack_ratio"] = total_attacks / (total_attacks + len(legitimate_scenarios))

        print(f"   ✅ Generated {len(legitimate_scenarios)} legitimate announcements")
        print()

        # Save attack scenarios to file
        self._save_attack_scenarios(all_attack_scenarios)

        # Display summary
        print(f"\n{'='*60}")
        print(f"✅ ATTACK INJECTION COMPLETE")
        print(f"{'='*60}")
        print(f"   Total Attacks: {total_attacks} ({attack_ratio*100:.2f}%)")
        print(f"   Total Legitimate: {len(legitimate_scenarios)} ({(1-attack_ratio)*100:.2f}%)")
        print(f"   Total Announcements: {all_attack_scenarios['total_announcements']}")
        print(f"   Actual Attack Ratio: {all_attack_scenarios['attack_ratio']*100:.3f}%")
        print(f"   Attackers: {len(attacker_as_list)}")
        print(f"   Ground Truth File: {self.attack_scenarios_file}")
        print()

        return all_attack_scenarios

    def _generate_attacks_for_as(self, attacker_as: int, count: int) -> List[Dict]:
        """Generate specific attack scenarios for an AS"""
        scenarios = []

        # Get available victim prefixes from ROA database
        available_prefixes = self.roa_database.get("roas", [])

        if not available_prefixes:
            print(f"   ⚠️  No ROA database entries, using defaults...")
            available_prefixes = [
                {"prefix": "8.8.8.0/24", "max_length": 24, "asn": 15169},
                {"prefix": "1.1.1.0/24", "max_length": 24, "asn": 13335}
            ]

        # Distribute attack types
        attack_distribution = self._distribute_attack_types(count)

        for attack_type, type_count in attack_distribution.items():
            for _ in range(type_count):
                scenario = self._create_attack_scenario(
                    attacker_as,
                    attack_type,
                    available_prefixes
                )
                if scenario:
                    scenarios.append(scenario)

        return scenarios

    def _distribute_attack_types(self, total_count: int) -> Dict[str, int]:
        """Distribute attacks across types"""
        # 50% hijacking, 30% sub-prefix, 20% route leak
        return {
            "ip_prefix_hijacking": int(total_count * 0.5),
            "sub_prefix_hijacking": int(total_count * 0.3),
            "route_leak": total_count - int(total_count * 0.5) - int(total_count * 0.3)
        }

    def _create_attack_scenario(self, attacker_as: int, attack_type: str,
                                 available_prefixes: List[Dict]) -> Dict:
        """Create a single attack scenario"""
        # Select random victim prefix
        victim_roa = random.choice(available_prefixes)
        victim_as = victim_roa["asn"]
        victim_prefix = victim_roa["prefix"]

        # Ensure attacker != victim
        if attacker_as == victim_as:
            # Find different victim
            other_prefixes = [p for p in available_prefixes if p["asn"] != attacker_as]
            if other_prefixes:
                victim_roa = random.choice(other_prefixes)
                victim_as = victim_roa["asn"]
                victim_prefix = victim_roa["prefix"]

        # Create attack based on type
        if attack_type == "sub_prefix_hijacking":
            # Make more specific prefix
            if "/24" in victim_prefix:
                hijacked_prefix = victim_prefix.replace("/24", "/25")
            elif "/16" in victim_prefix:
                hijacked_prefix = victim_prefix.replace("/16", "/24")
            else:
                hijacked_prefix = victim_prefix
        else:
            hijacked_prefix = victim_prefix

        # Generate timestamp (within last hour)
        minutes_ago = random.randint(1, 60)
        timestamp = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()

        attack_info = self.attack_types[attack_type]

        return {
            "attack_id": f"{attacker_as}_{attack_type}_{random.randint(1000, 9999)}",
            "attacker_as": attacker_as,
            "attack_type": attack_type,
            "victim_as": victim_as,
            "hijacked_prefix": hijacked_prefix,
            "legitimate_prefix": victim_prefix,
            "timestamp": timestamp,
            "severity": attack_info["severity"],
            "expected_penalty": attack_info["rating_penalty"],
            "description": attack_info["description"],
            # BGP announcement format
            "bgp_announcement": {
                "sender_asn": attacker_as,
                "ip_prefix": hijacked_prefix,
                "as_path": [attacker_as],
                "timestamp": timestamp,
                "type": "UPDATE"
            }
        }

    def _count_attack_types(self, scenarios: List[Dict]) -> Dict[str, int]:
        """Count attacks by type"""
        counts = {}
        for scenario in scenarios:
            attack_type = scenario["attack_type"]
            counts[attack_type] = counts.get(attack_type, 0) + 1
        return counts

    def _generate_legitimate_announcements(self, count: int) -> List[Dict]:
        """
        Generate legitimate BGP announcements.

        Args:
            count: Number of legitimate announcements to generate

        Returns:
            List of legitimate announcement scenarios
        """
        legitimate = []

        # Get list of legitimate ASes from ROA database
        roas = self.roa_database.get("roas", [])

        if not roas:
            print(f"   ⚠️  No ROA database, using default legitimate ASes")
            # Use RPKI nodes as legitimate sources
            legitimate_ases = RPKINodeRegistry.get_all_rpki_nodes()
            roas = [
                {"prefix": f"10.{as_num}.0.0/16", "asn": as_num}
                for as_num in legitimate_ases
            ]

        # Generate legitimate announcements
        for i in range(count):
            # Select random legitimate ROA
            roa = random.choice(roas)

            as_number = roa["asn"]
            prefix = roa["prefix"]

            # Generate timestamp (within last hour)
            minutes_ago = random.randint(1, 60)
            timestamp = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()

            announcement = {
                "announcement_id": f"legit_{as_number}_{i+1:05d}",
                "sender_asn": as_number,
                "announced_prefix": prefix,
                "timestamp": timestamp,
                "announcement_type": "legitimate",
                "bgp_announcement": {
                    "sender_asn": as_number,
                    "ip_prefix": prefix,
                    "as_path": [as_number],
                    "timestamp": timestamp,
                    "type": "UPDATE"
                }
            }

            legitimate.append(announcement)

        return legitimate

    def _save_attack_scenarios(self, scenarios: Dict):
        """Save attack scenarios to file"""
        try:
            # Ensure directory exists
            self.attack_scenarios_file.parent.mkdir(parents=True, exist_ok=True)

            # Save with pretty formatting
            with open(self.attack_scenarios_file, 'w') as f:
                json.dump(scenarios, f, indent=2)

            print(f"\n💾 Attack scenarios saved to:")
            print(f"   {self.attack_scenarios_file}")

        except Exception as e:
            print(f"❌ Error saving attack scenarios: {e}")

    def get_attack_summary(self) -> Dict:
        """Get summary of injected attacks"""
        if not self.attack_scenarios_file.exists():
            return {"error": "No attack scenarios found"}

        try:
            with open(self.attack_scenarios_file, 'r') as f:
                scenarios = json.load(f)

            return {
                "total_attacks": scenarios["total_attacks"],
                "attackers": list(scenarios["attackers"].keys()),
                "injection_time": scenarios["injection_timestamp"],
                "ground_truth_entries": len(scenarios["ground_truth"]),
                "pending_detection": sum(
                    1 for track in scenarios["detection_tracking"].values()
                    if not track["detected"]
                )
            }
        except Exception as e:
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("ATTACK INJECTION SYSTEM - TEST")
    print("="*80)
    print()

    # Initialize system
    injector = AttackInjectionSystem()

    # Inject 20 attacks: 12 into AS666, 8 into AS31337
    results = injector.inject_attack_scenarios([
        (666, 12),      # AS666 gets 12 attacks
        (31337, 8)      # AS31337 gets 8 attacks
    ])

    print("\n📊 Injection Summary:")
    summary = injector.get_attack_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    print("\n✅ Test complete!")
