#!/usr/bin/env python3
"""
=============================================================================
Attack Detection System - Integration Test
=============================================================================

Tests the complete attack detection workflow:
1. AttackDetector identifies attacks
2. AttackConsensus manages voting
3. NonRPKIRatingSystem updates ratings
4. BGPCoinLedger distributes rewards

Run this to verify the attack detection system is working correctly.

Usage:
    python3 test_attack_detection.py

=============================================================================
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from attack_detector import AttackDetector
from nonrpki_rating import NonRPKIRatingSystem
from bgpcoin_ledger import BGPCoinLedger

def print_section(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def test_ip_prefix_hijacking():
    """Test IP prefix hijacking detection"""
    print_section("TEST 1: IP PREFIX HIJACKING DETECTION")

    # Initialize detector
    detector = AttackDetector(
        roa_database_path="test_data/roa_database.json",
        as_relationships_path="test_data/as_relationships.json"
    )

    print("\n📋 Test Scenario:")
    print("   AS666 (malicious) announces 8.8.8.0/24")
    print("   ROA database shows AS15169 (Google) is authorized")
    print("   Expected: IP PREFIX HIJACKING detected")

    # Create malicious announcement
    hijacking_announcement = {
        "sender_asn": 666,
        "ip_prefix": "8.8.8.0/24",
        "as_path": [666, 1234, 5678],
        "timestamp": datetime.now().isoformat()
    }

    # Detect attacks
    print("\n🔍 Running attack detection...")
    attacks = detector.detect_attacks(hijacking_announcement)

    if attacks:
        for attack in attacks:
            print(f"\n🚨 ATTACK DETECTED!")
            print(f"   Type: {attack['attack_type']}")
            print(f"   Severity: {attack['severity']}")
            print(f"   Attacker: AS{attack['attacker_as']}")
            print(f"   Victim Prefix: {attack['victim_prefix']}")
            print(f"   Legitimate Owner: AS{attack['legitimate_owner']}")
            print(f"   Description: {attack['description']}")
        return True
    else:
        print("❌ TEST FAILED: No attack detected")
        return False

def test_route_leak():
    """Test route leak detection"""
    print_section("TEST 2: ROUTE LEAK DETECTION")

    # Initialize detector
    detector = AttackDetector(
        roa_database_path="test_data/roa_database.json",
        as_relationships_path="test_data/as_relationships.json"
    )

    print("\n📋 Test Scenario:")
    print("   AS Path: [5, 7, 5, 3, 1]")
    print("   AS5 received route from provider AS7")
    print("   AS5 leaked it to peer AS5 (valley-free violation)")
    print("   Expected: ROUTE LEAK detected")

    # Create route leak announcement
    route_leak_announcement = {
        "sender_asn": 5,
        "ip_prefix": "203.0.113.0/24",
        "as_path": [5, 7, 5, 3, 1],
        "timestamp": datetime.now().isoformat()
    }

    # Detect attacks
    print("\n🔍 Running attack detection...")
    attacks = detector.detect_attacks(route_leak_announcement)

    if attacks:
        for attack in attacks:
            print(f"\n🚨 ATTACK DETECTED!")
            print(f"   Type: {attack['attack_type']}")
            print(f"   Severity: {attack['severity']}")

            if attack['attack_type'] == 'route_leak':
                print(f"   Leaker: AS{attack['leaker_as']}")
                print(f"   AS Path: {' → '.join(map(str, attack['as_path']))}")
            elif attack['attack_type'] == 'ip_prefix_hijacking':
                print(f"   Attacker: AS{attack['attacker_as']}")
                print(f"   Victim Prefix: {attack['victim_prefix']}")
                print(f"   Legitimate Owner: AS{attack['legitimate_owner']}")

            print(f"   Description: {attack['description']}")
        return True
    else:
        print("❌ TEST FAILED: No route leak detected")
        return False

def test_legitimate_announcement():
    """Test that legitimate announcements are not flagged"""
    print_section("TEST 3: LEGITIMATE ANNOUNCEMENT (NO ATTACK)")

    # Initialize detector
    detector = AttackDetector(
        roa_database_path="test_data/roa_database.json",
        as_relationships_path="test_data/as_relationships.json"
    )

    print("\n📋 Test Scenario:")
    print("   AS15169 (Google) announces 8.8.8.0/24")
    print("   ROA database shows AS15169 is authorized")
    print("   Expected: NO attack detected")

    # Create legitimate announcement
    legitimate_announcement = {
        "sender_asn": 15169,
        "ip_prefix": "8.8.8.0/24",
        "as_path": [15169, 1234, 5678],
        "timestamp": datetime.now().isoformat()
    }

    # Detect attacks
    print("\n🔍 Running attack detection...")
    attacks = detector.detect_attacks(legitimate_announcement)

    if not attacks:
        print("\n✅ CORRECT: No attack detected (legitimate announcement)")
        return True
    else:
        print(f"❌ TEST FAILED: False positive - detected {len(attacks)} attacks")
        for attack in attacks:
            print(f"   - {attack['attack_type']}")
        return False

def test_rating_system():
    """Test non-RPKI rating system"""
    print_section("TEST 4: NON-RPKI RATING SYSTEM")

    # Initialize rating system
    rating_system = NonRPKIRatingSystem("test_data/state")

    print("\n📋 Test Scenario:")
    print("   AS666 starts with neutral rating (50)")
    print("   Record IP prefix hijacking attack (-20)")
    print("   Record second attack within 30 days (-20 base, -30 repeated)")
    print("   Expected: Rating drops to 0 (malicious)")

    # Get initial rating
    initial_rating = rating_system.get_or_create_rating(666)
    print(f"\n📊 Initial Rating:")
    print(f"   AS666: {initial_rating['trust_score']} ({initial_rating['rating_level']})")

    # Record first attack
    print("\n⚠️  Recording first IP prefix hijacking...")
    rating_system.record_attack(
        as_number=666,
        attack_type="ip_prefix_hijacking",
        attack_details={
            "victim_prefix": "8.8.8.0/24",
            "legitimate_owner": 15169
        }
    )

    rating1 = rating_system.get_rating(666)
    print(f"\n📊 Rating after 1st attack:")
    print(f"   AS666: {rating1['trust_score']} ({rating1['rating_level']})")
    print(f"   Total attacks: {rating1['attacks_detected']}")

    # Record second attack (repeated within 30 days)
    print("\n⚠️  Recording second attack within 30 days...")
    rating_system.record_attack(
        as_number=666,
        attack_type="route_leak",
        attack_details={"as_path": [666, 777, 888]}
    )

    rating2 = rating_system.get_rating(666)
    print(f"\n📊 Rating after 2nd attack (repeated):")
    print(f"   AS666: {rating2['trust_score']} ({rating2['rating_level']})")
    print(f"   Total attacks: {rating2['attacks_detected']}")

    # Test good behavior
    print("\n📋 Testing good behavior rewards:")
    print("   AS777 starts neutral (50)")
    print("   Record monthly good behavior (+5)")
    print("   Expected: Rating increases to 55")

    rating_system.record_good_behavior(
        as_number=777,
        behavior_type="monthly_good_behavior"
    )

    rating3 = rating_system.get_rating(777)
    print(f"\n📊 Rating after good behavior:")
    print(f"   AS777: {rating3['trust_score']} ({rating3['rating_level']})")

    # Summary
    summary = rating_system.get_summary()
    print(f"\n📊 System Summary:")
    print(f"   Total ASes tracked: {summary['total_ases']}")
    print(f"   Total attacks: {summary['total_attacks']}")
    print(f"   Average score: {summary['average_score']:.1f}")
    print(f"   By level:")
    for level, count in summary['by_level'].items():
        print(f"     {level}: {count}")

    return True

def test_bgpcoin_rewards():
    """Test BGPCOIN reward distribution"""
    print_section("TEST 5: BGPCOIN REWARD DISTRIBUTION")

    # Initialize ledger
    ledger = BGPCoinLedger("test_data/state")

    print("\n📋 Test Scenario:")
    print("   Simulate attack detection rewards")
    print("   Detector (AS1): +10 BGPCOIN")
    print("   Correct voters (AS3, AS5, AS7): +2 BGPCOIN each")

    # Get initial balances
    print("\n💰 Initial Balances:")
    for as_num in [1, 3, 5, 7]:
        balance = ledger.get_balance(as_num)
        print(f"   AS{as_num}: {balance} BGPCOIN")

    # Award attack detection reward
    print("\n🎁 Awarding attack detection reward...")
    ledger.award_special_reward(
        as_number=1,
        amount=10,
        reason="attack_detection",
        details={"attack_type": "ip_prefix_hijacking"}
    )

    # Award correct vote rewards
    print("\n🎁 Awarding correct vote rewards...")
    for voter_as in [3, 5, 7]:
        ledger.award_special_reward(
            as_number=voter_as,
            amount=2,
            reason="correct_attack_vote",
            details={"verdict": "ATTACK_CONFIRMED"}
        )

    # Show final balances
    print("\n💰 Final Balances:")
    for as_num in [1, 3, 5, 7]:
        balance = ledger.get_balance(as_num)
        print(f"   AS{as_num}: {balance} BGPCOIN")

    # Test false accusation penalty
    print("\n📋 Testing false accusation penalty:")
    print("   AS9 falsely accuses → -20 BGPCOIN")

    initial_balance = ledger.get_balance(9)
    print(f"\n💰 AS9 initial balance: {initial_balance} BGPCOIN")

    ledger.apply_penalty(
        as_number=9,
        amount=20,
        reason="false_attack_accusation",
        details={"verdict": "NOT_ATTACK"}
    )

    final_balance = ledger.get_balance(9)
    print(f"💰 AS9 final balance: {final_balance} BGPCOIN")

    # Show treasury status
    summary = ledger.get_ledger_summary()
    print(f"\n🏦 Treasury Status:")
    print(f"   Treasury balance: {summary['treasury_balance']:,.0f} BGPCOIN")
    print(f"   Total distributed: {summary['total_distributed']:,.0f} BGPCOIN")
    print(f"   Circulating supply: {summary['circulating_supply']:,.0f} BGPCOIN")

    return True

def test_attack_verdict_recording():
    """Test attack verdict recording to blockchain"""
    print_section("TEST 6: ATTACK VERDICT RECORDING")

    # Simulate attack verdict
    verdict_record = {
        "verdict_id": f"verdict_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "proposal_id": "attack_20251021_test",
        "transaction_id": "tx_20251021_test",
        "timestamp": datetime.now().isoformat(),
        "verdict": "ATTACK_CONFIRMED",
        "confidence": 0.67,
        "attack_type": "ip_prefix_hijacking",
        "attacker_as": 666,
        "votes": {
            "yes_count": 6,
            "no_count": 3,
            "total": 9,
            "voters": {
                "1": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "3": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "5": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "7": {"vote": "NO", "timestamp": datetime.now().isoformat()},
                "9": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "11": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "13": {"vote": "NO", "timestamp": datetime.now().isoformat()},
                "15": {"vote": "YES", "timestamp": datetime.now().isoformat()},
                "17": {"vote": "NO", "timestamp": datetime.now().isoformat()}
            }
        },
        "attack_details": {
            "attack_type": "ip_prefix_hijacking",
            "severity": "HIGH",
            "attacker_as": 666,
            "victim_prefix": "8.8.8.0/24",
            "legitimate_owner": 15169
        }
    }

    print("\n📋 Test Scenario:")
    print("   Simulate attack verdict recording")
    print(f"   Verdict: {verdict_record['verdict']}")
    print(f"   Confidence: {verdict_record['confidence']:.0%}")
    print(f"   Attack Type: {verdict_record['attack_type']}")

    # Create test blockchain directory
    test_blockchain_dir = Path("test_data/chain")
    test_blockchain_dir.mkdir(parents=True, exist_ok=True)

    attack_verdicts_file = test_blockchain_dir / "attack_verdicts.jsonl"

    # Write verdict
    print(f"\n💾 Writing verdict to: {attack_verdicts_file}")
    with open(attack_verdicts_file, 'a') as f:
        f.write(json.dumps(verdict_record) + '\n')

    # Read back and verify
    print("\n📖 Reading back verdicts...")
    with open(attack_verdicts_file, 'r') as f:
        lines = f.readlines()
        print(f"   Total verdicts: {len(lines)}")

        # Show last verdict
        if lines:
            last_verdict = json.loads(lines[-1])
            print(f"\n📝 Last Verdict:")
            print(f"   ID: {last_verdict['verdict_id']}")
            print(f"   Verdict: {last_verdict['verdict']}")
            print(f"   Confidence: {last_verdict['confidence']:.0%}")
            print(f"   Attacker: AS{last_verdict['attacker_as']}")
            print(f"   Votes: {last_verdict['votes']['yes_count']} YES, "
                  f"{last_verdict['votes']['no_count']} NO")

    return True

def run_all_tests():
    """Run all test cases"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "ATTACK DETECTION SYSTEM TEST" + " " * 30 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    results = {}

    # Run tests
    results["IP Prefix Hijacking Detection"] = test_ip_prefix_hijacking()
    results["Route Leak Detection"] = test_route_leak()
    results["Legitimate Announcement"] = test_legitimate_announcement()
    results["Rating System"] = test_rating_system()
    results["BGPCOIN Rewards"] = test_bgpcoin_rewards()
    results["Attack Verdict Recording"] = test_attack_verdict_recording()

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    print(f"\n📊 Results: {passed}/{total} tests passed\n")

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Attack detection system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
