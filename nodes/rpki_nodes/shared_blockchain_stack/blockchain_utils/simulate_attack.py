#!/usr/bin/env python3
"""
Simulate BGP attack to test non-RPKI rating system
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from attack_detector import AttackDetector
from nonrpki_rating import NonRPKIRatingSystem
from attack_consensus import AttackConsensus
from bgpcoin_ledger import BGPCoinLedger
from pathlib import Path

def simulate_ip_hijacking():
    """Simulate IP prefix hijacking scenario"""

    # Use AS01's data directory
    state_dir = Path("/home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state")
    chain_dir = Path("/home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain")

    print("=" * 80)
    print("SIMULATING IP PREFIX HIJACKING ATTACK")
    print("=" * 80)
    print()

    # Initialize systems
    print("📋 Initializing attack detection systems...")
    detector = AttackDetector(
        roa_database_path=str(state_dir / "roa_database.json"),
        as_relationships_path=str(state_dir / "as_relationships.json")
    )

    rating_system = NonRPKIRatingSystem(rating_path=str(state_dir))
    bgpcoin = BGPCoinLedger(ledger_path=str(state_dir))

    print()
    print("🚨 ATTACK SCENARIO:")
    print("   Malicious AS666 announces 8.8.8.0/24 (Google's prefix)")
    print("   ROA database shows AS15169 (Google) is authorized")
    print()

    # Create malicious announcement
    announcement = {
        "sender_asn": 666,
        "ip_prefix": "8.8.8.0/24",
        "as_path": [666],
        "timestamp": datetime.now().isoformat()
    }

    # Detect attack
    print("🔍 Running attack detection...")
    attacks = detector.detect_attacks(announcement)

    if attacks:
        attack = attacks[0]
        print(f"\n✅ Attack Detected!")
        print(f"   Type: {attack['attack_type']}")
        print(f"   Attacker: AS{attack['attacker_as']}")
        print(f"   Victim Prefix: {attack['victim_prefix']}")
        print(f"   Legitimate Owner: AS{attack['legitimate_owner']}")
        print()

        # Record attack and update rating
        print("📉 Applying rating penalty...")
        rating = rating_system.record_attack(
            as_number=666,
            attack_type=attack['attack_type'],
            attack_details=attack
        )

        print()
        print("=" * 80)
        print("RATING SYSTEM STATUS")
        print("=" * 80)
        print()

        # Show AS666 rating
        as666_rating = rating_system.get_rating(666)
        if as666_rating:
            print(f"AS666 Rating:")
            print(f"  Trust Score: {as666_rating['trust_score']}")
            print(f"  Rating Level: {as666_rating['rating_level'].upper()}")
            print(f"  Attacks Detected: {as666_rating['attacks_detected']}")
            print(f"  Last Updated: {as666_rating['last_updated']}")

        print()

        # Show file locations
        print("=" * 80)
        print("FILES CREATED")
        print("=" * 80)
        print()
        print(f"📁 Rating File: {state_dir / 'nonrpki_ratings.json'}")
        print(f"📁 History File: {state_dir / 'rating_history.jsonl'}")
        print()

        # Show summary
        summary = rating_system.get_summary()
        print("📊 System Summary:")
        print(f"   Total ASes rated: {summary['total_ases']}")
        print(f"   Total attacks: {summary['total_attacks']}")
        print(f"   Average score: {summary['average_score']:.1f}")
        print()
        print("   Distribution by level:")
        for level, count in summary['by_level'].items():
            if count > 0:
                print(f"     {level}: {count}")

        print()
        print("=" * 80)
        print("✅ SIMULATION COMPLETE")
        print("=" * 80)

    else:
        print("❌ No attack detected (this shouldn't happen!)")

if __name__ == "__main__":
    simulate_ip_hijacking()
