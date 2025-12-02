#!/usr/bin/env python3
"""
=============================================================================
Manual Integration Test - Timeout and Sampling
=============================================================================

This script manually tests the timeout and sampling mechanisms in a real
BGP-Sentry environment without mocking dependencies.

Run this script to verify:
1. Regular transactions timeout after 60 seconds
2. Attack transactions timeout after 180 seconds
3. Sampling prevents duplicate announcements within 1 hour
4. Vote deduplication prevents replay attacks

Usage:
    python3 manual_test_timeout_sampling.py

Author: BGP-Sentry Team
=============================================================================
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add blockchain_utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"))

from p2p_transaction_pool import P2PTransactionPool


def test_timeout_mechanism():
    """
    Manual test for timeout mechanism.

    Test cases:
    1. Create regular transaction, wait 70 seconds, verify timeout
    2. Create attack transaction, wait 70 seconds, verify NOT timed out
    3. Wait another 120 seconds, verify attack timed out
    """
    print("\n" + "="*70)
    print("TEST 1: Transaction Timeout Mechanism")
    print("="*70)

    try:
        # Initialize P2P pool
        print("Initializing P2P transaction pool...")
        pool = P2PTransactionPool(as_number=1)
        pool.start_p2p_server()

        # Test 1A: Regular transaction timeout (60 seconds)
        print("\n[1A] Testing regular transaction timeout (60 seconds)...")

        regular_tx = {
            "transaction_id": f"tx_manual_regular_{int(time.time())}",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        print(f"Broadcasting regular transaction: {regular_tx['transaction_id']}")
        pool.broadcast_transaction(regular_tx)

        print("Waiting 70 seconds for timeout...")
        for i in range(70):
            time.sleep(1)
            if i % 10 == 0:
                print(f"  {i}/70 seconds elapsed...")

        # Check if transaction timed out
        if regular_tx["transaction_id"] in pool.committed_transactions:
            print("✅ SUCCESS: Regular transaction timed out and was committed")
        else:
            print("❌ FAILURE: Regular transaction did NOT timeout")

        # Test 1B: Attack transaction timeout (180 seconds)
        print("\n[1B] Testing attack transaction timeout (180 seconds)...")

        attack_tx = {
            "transaction_id": f"tx_manual_attack_{int(time.time())}",
            "sender_asn": 12,
            "ip_prefix": "198.51.100.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": True
        }

        print(f"Broadcasting attack transaction: {attack_tx['transaction_id']}")
        pool.broadcast_transaction(attack_tx)

        print("Waiting 70 seconds (should NOT timeout yet)...")
        for i in range(70):
            time.sleep(1)
            if i % 10 == 0:
                print(f"  {i}/70 seconds elapsed...")

        # Check that attack did NOT timeout yet
        if attack_tx["transaction_id"] not in pool.committed_transactions:
            print("✅ SUCCESS: Attack transaction did NOT timeout at 70 seconds (correct)")
        else:
            print("❌ FAILURE: Attack transaction timed out too early")

        print("Waiting another 120 seconds for attack timeout...")
        for i in range(120):
            time.sleep(1)
            if i % 10 == 0:
                print(f"  {i}/120 seconds elapsed...")

        # Check if attack timed out now
        if attack_tx["transaction_id"] in pool.committed_transactions:
            print("✅ SUCCESS: Attack transaction timed out at 180+ seconds")
        else:
            print("❌ FAILURE: Attack transaction did NOT timeout")

        pool.stop()
        print("\n✅ Timeout mechanism test completed")

    except Exception as e:
        print(f"\n❌ ERROR in timeout test: {e}")
        import traceback
        traceback.print_exc()


def test_sampling_logic():
    """
    Manual test for sampling logic.

    Test cases:
    1. Record observation at T=0
    2. Try to record same observation at T=30s (should be skipped)
    3. Try to record different observation at T=30s (should be recorded)
    4. Try to record same observation after 1 hour (should be recorded)
    """
    print("\n" + "="*70)
    print("TEST 2: Sampling Logic (1-hour window)")
    print("="*70)

    try:
        # Initialize P2P pool
        print("Initializing P2P transaction pool...")
        pool = P2PTransactionPool(as_number=1)

        # Test 2A: First observation (should be recorded)
        print("\n[2A] Recording first observation...")
        result1 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        if result1:
            print("✅ SUCCESS: First observation recorded")
        else:
            print("❌ FAILURE: First observation was not recorded")

        # Test 2B: Duplicate observation (should be skipped)
        print("\n[2B] Trying to record duplicate observation (same prefix/AS)...")
        time.sleep(2)  # Small delay

        result2 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        if not result2:
            print("✅ SUCCESS: Duplicate observation was skipped (sampling)")
        else:
            print("❌ FAILURE: Duplicate observation was recorded (should be skipped)")

        # Test 2C: Different observation (should be recorded)
        print("\n[2C] Recording different observation (different prefix)...")
        result3 = pool.add_bgp_observation(
            ip_prefix="198.51.100.0/24",  # Different prefix
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        if result3:
            print("✅ SUCCESS: Different observation recorded")
        else:
            print("❌ FAILURE: Different observation was not recorded")

        # Test 2D: Attack bypass (should always be recorded)
        print("\n[2D] Recording attack (should bypass sampling)...")
        result4 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",  # Same as first
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=True  # Attack bypasses sampling
        )

        if result4:
            print("✅ SUCCESS: Attack observation recorded (bypassed sampling)")
        else:
            print("❌ FAILURE: Attack observation was not recorded")

        print("\n✅ Sampling logic test completed")

        # Note: Testing "after 1 hour" would require waiting 1 hour
        print("\nℹ️  Note: Testing 1-hour expiration requires waiting 1 hour")
        print("   Manually verify by checking last_seen_cache after 1 hour")

    except Exception as e:
        print(f"\n❌ ERROR in sampling test: {e}")
        import traceback
        traceback.print_exc()


def test_vote_deduplication():
    """
    Manual test for vote deduplication.

    Test cases:
    1. Simulate vote from AS3 (should be accepted)
    2. Simulate duplicate vote from AS3 (should be rejected)
    3. Simulate votes from AS5, AS7 (should be accepted)
    """
    print("\n" + "="*70)
    print("TEST 3: Vote Deduplication (Replay Attack Prevention)")
    print("="*70)

    try:
        # Initialize P2P pool
        print("Initializing P2P transaction pool...")
        pool = P2PTransactionPool(as_number=1)

        # Create test transaction
        transaction = {
            "transaction_id": f"tx_dedup_test_{int(time.time())}",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Initialize in pending votes
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [],
            "needed": 3,
            "created_at": datetime.now(),
            "is_attack": False
        }

        # Test 3A: First vote from AS3 (should be accepted)
        print("\n[3A] Simulating vote from AS3...")
        vote1 = {
            "type": "vote_response",
            "transaction_id": transaction["transaction_id"],
            "from_as": 3,
            "vote": "approve",
            "timestamp": datetime.now().isoformat()
        }

        pool._handle_vote_response(vote1)
        vote_count_1 = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        if vote_count_1 == 1:
            print(f"✅ SUCCESS: Vote from AS3 accepted (count={vote_count_1})")
        else:
            print(f"❌ FAILURE: Vote count incorrect (expected 1, got {vote_count_1})")

        # Test 3B: Duplicate vote from AS3 (should be rejected)
        print("\n[3B] Simulating DUPLICATE vote from AS3 (replay attack)...")
        vote2 = {
            "type": "vote_response",
            "transaction_id": transaction["transaction_id"],
            "from_as": 3,  # Same AS voting again
            "vote": "approve",
            "timestamp": datetime.now().isoformat()
        }

        pool._handle_vote_response(vote2)
        vote_count_2 = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        if vote_count_2 == 1:
            print(f"✅ SUCCESS: Duplicate vote rejected (count still {vote_count_2})")
        else:
            print(f"❌ FAILURE: Duplicate vote accepted (count={vote_count_2}, expected 1)")

        # Test 3C: Votes from different nodes (should be accepted)
        print("\n[3C] Simulating votes from AS5 and AS7...")

        for as_num in [5, 7]:
            vote = {
                "type": "vote_response",
                "transaction_id": transaction["transaction_id"],
                "from_as": as_num,
                "vote": "approve",
                "timestamp": datetime.now().isoformat()
            }
            pool._handle_vote_response(vote)

        final_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        if final_vote_count == 3:
            print(f"✅ SUCCESS: Unique votes accepted (total count={final_vote_count})")
        else:
            print(f"❌ FAILURE: Vote count incorrect (expected 3, got {final_vote_count})")

        print("\n✅ Vote deduplication test completed")

    except Exception as e:
        print(f"\n❌ ERROR in deduplication test: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all manual tests"""
    print("\n" + "="*70)
    print("BGP-Sentry Manual Integration Tests")
    print("Timeout, Sampling, and Vote Deduplication")
    print("="*70)

    # Run tests
    test_sampling_logic()
    test_vote_deduplication()

    # Timeout test takes 3+ minutes, ask user
    print("\n" + "="*70)
    response = input("\nRun timeout test? (takes 3+ minutes) [y/N]: ")

    if response.lower() == 'y':
        test_timeout_mechanism()
    else:
        print("⏩ Skipping timeout test")

    print("\n" + "="*70)
    print("All manual tests completed!")
    print("="*70)


if __name__ == "__main__":
    main()
