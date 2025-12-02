#!/usr/bin/env python3
"""
=============================================================================
Test Suite for P2P Transaction Pool - Timeout & Sampling
=============================================================================

Tests for:
1. Transaction timeout mechanism (60s regular, 180s attack)
2. Sampling logic (1-hour window for regular announcements)
3. Vote deduplication (prevent replay attacks)

Author: BGP-Sentry Team
=============================================================================
"""

import unittest
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"))

from p2p_transaction_pool import P2PTransactionPool


class TestTimeoutMechanism(unittest.TestCase):
    """Test transaction timeout handling"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = Path.cwd()

        # Mock minimal dependencies
        self._mock_dependencies()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def _mock_dependencies(self):
        """Mock external dependencies for testing"""
        # This would mock BlockchainInterface, BGPCoinLedger, etc.
        pass

    def test_regular_transaction_timeout_60_seconds(self):
        """
        Test that regular transactions timeout after 60 seconds.

        Expected behavior:
        - Transaction created at T=0
        - No consensus reached
        - At T=60s, transaction written as SINGLE_WITNESS
        """
        # Create transaction pool
        pool = P2PTransactionPool(as_number=1)

        # Create regular transaction
        transaction = {
            "transaction_id": "tx_test_regular_timeout",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Add to pending votes manually (simulate broadcast without actual P2P)
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [],  # No votes received
            "needed": 3,
            "created_at": datetime.now() - timedelta(seconds=65),  # 65 seconds ago
            "is_attack": False
        }

        # Simulate timeout check
        pool._cleanup_timed_out_transactions()

        # Verify transaction was committed with SINGLE_WITNESS status
        # (Would check blockchain here in integration test)
        self.assertIn(transaction["transaction_id"], pool.committed_transactions)

    def test_attack_transaction_timeout_180_seconds(self):
        """
        Test that attack transactions timeout after 180 seconds.

        Expected behavior:
        - Attack transaction created at T=0
        - No consensus reached
        - At T=180s, transaction written as SINGLE_WITNESS
        - At T=60s, should NOT timeout (attack has longer timeout)
        """
        pool = P2PTransactionPool(as_number=1)

        # Create attack transaction
        transaction = {
            "transaction_id": "tx_test_attack_timeout",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": True
        }

        # Add to pending votes 65 seconds ago (should NOT timeout for attack)
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [],
            "needed": 3,
            "created_at": datetime.now() - timedelta(seconds=65),
            "is_attack": True
        }

        # Simulate timeout check at 65 seconds
        pool._cleanup_timed_out_transactions()

        # Should NOT be committed yet (attack timeout is 180s)
        self.assertNotIn(transaction["transaction_id"], pool.committed_transactions)

        # Now simulate 185 seconds elapsed
        pool.pending_votes[transaction["transaction_id"]]["created_at"] = datetime.now() - timedelta(seconds=185)

        # Simulate timeout check at 185 seconds
        pool._cleanup_timed_out_transactions()

        # Should NOW be committed
        self.assertIn(transaction["transaction_id"], pool.committed_transactions)

    def test_insufficient_consensus_status(self):
        """
        Test that transactions with 1-2 votes get INSUFFICIENT_CONSENSUS status.

        Expected behavior:
        - Transaction receives 2 approve votes (threshold is 3)
        - Times out after 60 seconds
        - Written with INSUFFICIENT_CONSENSUS status
        """
        pool = P2PTransactionPool(as_number=1)

        transaction = {
            "transaction_id": "tx_test_insufficient",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Add with 2 approve votes (not enough for consensus)
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [
                {"from_as": 3, "vote": "approve", "timestamp": datetime.now().isoformat()},
                {"from_as": 5, "vote": "approve", "timestamp": datetime.now().isoformat()}
            ],
            "needed": 3,
            "created_at": datetime.now() - timedelta(seconds=65),
            "is_attack": False
        }

        # Simulate timeout
        pool._cleanup_timed_out_transactions()

        # Verify INSUFFICIENT_CONSENSUS status
        # (Would check blockchain transaction metadata here)
        self.assertIn(transaction["transaction_id"], pool.committed_transactions)


class TestSamplingLogic(unittest.TestCase):
    """Test 1-hour sampling window for regular announcements"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self._mock_dependencies()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def _mock_dependencies(self):
        """Mock external dependencies"""
        pass

    def test_sampling_skip_within_1_hour(self):
        """
        Test that regular announcements seen within 1 hour are skipped.

        Expected behavior:
        - Same (prefix, AS) announcement at T=0
        - Same announcement at T=30min should be skipped (sampling)
        - Different announcement at T=30min should be recorded
        """
        pool = P2PTransactionPool(as_number=1)

        # First observation (should be recorded)
        result1 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        self.assertTrue(result1, "First observation should be recorded")

        # Second observation same prefix/AS within 1 hour (should be skipped)
        result2 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        self.assertFalse(result2, "Duplicate observation within 1 hour should be skipped")

        # Different prefix (should be recorded)
        result3 = pool.add_bgp_observation(
            ip_prefix="198.51.100.0/24",  # Different prefix
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        self.assertTrue(result3, "Different prefix should be recorded")

    def test_sampling_record_after_1_hour(self):
        """
        Test that announcements seen after 1 hour are recorded.

        Expected behavior:
        - Same (prefix, AS) at T=0
        - Same announcement at T=61min should be recorded (outside sampling window)
        """
        pool = P2PTransactionPool(as_number=1)

        ip_prefix = "203.0.113.0/24"
        sender_asn = 12

        # Manually set last_seen cache to 61 minutes ago
        cache_key = (ip_prefix, sender_asn)
        pool.last_seen_cache[cache_key] = (datetime.now() - timedelta(minutes=61)).timestamp()

        # Try to add observation (should succeed, outside 1-hour window)
        result = pool.add_bgp_observation(
            ip_prefix=ip_prefix,
            sender_asn=sender_asn,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=False
        )

        self.assertTrue(result, "Observation after 1 hour should be recorded")

    def test_attack_bypass_sampling(self):
        """
        Test that attack announcements bypass sampling.

        Expected behavior:
        - Attack at T=0 (recorded)
        - Same attack at T=5min (should be recorded, attacks bypass sampling)
        """
        pool = P2PTransactionPool(as_number=1)

        # First attack
        result1 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=True
        )

        self.assertTrue(result1, "First attack should be recorded")

        # Second attack same prefix/AS (should ALSO be recorded, attacks bypass sampling)
        result2 = pool.add_bgp_observation(
            ip_prefix="203.0.113.0/24",
            sender_asn=12,
            timestamp=datetime.now().isoformat(),
            trust_score=50.0,
            is_attack=True
        )

        self.assertTrue(result2, "Duplicate attack should be recorded (bypass sampling)")


class TestVoteDeduplication(unittest.TestCase):
    """Test vote deduplication to prevent replay attacks"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self._mock_dependencies()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def _mock_dependencies(self):
        """Mock external dependencies"""
        pass

    def test_reject_duplicate_vote_from_same_as(self):
        """
        Test that duplicate votes from same AS are rejected.

        Expected behavior:
        - AS3 votes "approve" at T=0 (accepted)
        - AS3 votes "approve" at T=1s (rejected, duplicate)
        - Vote count should remain 1
        """
        pool = P2PTransactionPool(as_number=1)

        transaction = {
            "transaction_id": "tx_test_dedup",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Initialize pending votes
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [
                {"from_as": 3, "vote": "approve", "timestamp": datetime.now().isoformat()}
            ],
            "needed": 3,
            "created_at": datetime.now(),
            "is_attack": False
        }

        # Simulate duplicate vote from AS3
        duplicate_vote_message = {
            "type": "vote_response",
            "transaction_id": transaction["transaction_id"],
            "from_as": 3,  # Same AS voting again
            "vote": "approve",
            "timestamp": datetime.now().isoformat()
        }

        initial_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        # Handle duplicate vote
        pool._handle_vote_response(duplicate_vote_message)

        final_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        # Vote count should NOT increase (duplicate rejected)
        self.assertEqual(initial_vote_count, final_vote_count,
                        "Duplicate vote should be rejected")

    def test_reject_vote_overflow(self):
        """
        Test that votes exceeding total nodes (9) are rejected.

        Expected behavior:
        - 9 votes received (max allowed)
        - 10th vote attempt rejected (overflow protection)
        """
        pool = P2PTransactionPool(as_number=1)

        transaction = {
            "transaction_id": "tx_test_overflow",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Initialize with 9 votes (all nodes)
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [
                {"from_as": i, "vote": "approve", "timestamp": datetime.now().isoformat()}
                for i in [1, 3, 5, 7, 9, 11, 13, 15, 17]  # All 9 nodes
            ],
            "needed": 3,
            "created_at": datetime.now(),
            "is_attack": False
        }

        # Simulate 10th vote (should be rejected)
        overflow_vote_message = {
            "type": "vote_response",
            "transaction_id": transaction["transaction_id"],
            "from_as": 19,  # Hypothetical 10th node
            "vote": "approve",
            "timestamp": datetime.now().isoformat()
        }

        initial_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        # Handle overflow vote
        pool._handle_vote_response(overflow_vote_message)

        final_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        # Vote count should NOT increase (overflow rejected)
        self.assertEqual(initial_vote_count, final_vote_count,
                        "Overflow vote should be rejected")
        self.assertEqual(final_vote_count, 9, "Maximum 9 votes allowed")

    def test_accept_unique_votes_from_different_nodes(self):
        """
        Test that unique votes from different nodes are accepted.

        Expected behavior:
        - AS3 votes (accepted)
        - AS5 votes (accepted, different node)
        - AS7 votes (accepted, different node)
        - Total: 3 votes
        """
        pool = P2PTransactionPool(as_number=1)

        transaction = {
            "transaction_id": "tx_test_unique",
            "sender_asn": 12,
            "ip_prefix": "203.0.113.0/24",
            "timestamp": datetime.now().isoformat(),
            "is_attack": False
        }

        # Initialize empty
        pool.pending_votes[transaction["transaction_id"]] = {
            "transaction": transaction,
            "votes": [],
            "needed": 3,
            "created_at": datetime.now(),
            "is_attack": False
        }

        # Add 3 unique votes
        for as_num in [3, 5, 7]:
            vote_message = {
                "type": "vote_response",
                "transaction_id": transaction["transaction_id"],
                "from_as": as_num,
                "vote": "approve",
                "timestamp": datetime.now().isoformat()
            }
            pool._handle_vote_response(vote_message)

        final_vote_count = len(pool.pending_votes[transaction["transaction_id"]]["votes"])

        self.assertEqual(final_vote_count, 3, "All 3 unique votes should be accepted")


class TestCachePersistence(unittest.TestCase):
    """Test last_seen cache persistence across restarts"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def test_cache_save_and_load(self):
        """
        Test that last_seen cache is saved and loaded correctly.

        Expected behavior:
        - Pool1: Record observation
        - Pool1: Save cache to disk
        - Pool2: Load cache from disk
        - Pool2: Should skip duplicate observation
        """
        # This would test the actual file persistence
        # Requires mocking the blockchain path
        pass


# Test runner
if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
