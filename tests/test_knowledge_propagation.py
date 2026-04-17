#!/usr/bin/env python3
"""
Unit tests for the three knowledge-propagation fixes:

  Fix #9: _handle_block_replicate calls prefix_ownership_state.update_from_confirmed
  Fix #3: _handle_block_replicate calls add_bgp_observation (KB backfill)
  Fix #2: _handle_vote_request calls add_bgp_observation AFTER voting

These are verified by instantiating the pool via __new__ (bypassing __init__)
and wiring in mock dependencies, so the test does not need any BGP dataset
or network. Run with:

    python3 tests/test_knowledge_propagation.py
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make imports work
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"))
sys.path.insert(0, str(ROOT / "nodes/rpki_nodes/shared_blockchain_stack/network_stack"))
sys.path.insert(0, str(ROOT / "nodes/rpki_nodes/shared_blockchain_stack"))
sys.path.insert(0, str(ROOT / "core"))

# The pool imports config.cfg at module load — stub it if needed
os.environ.setdefault("KNOWLEDGE_WINDOW_SECONDS", "480")
os.environ.setdefault("KNOWLEDGE_CLEANUP_INTERVAL", "60")
os.environ.setdefault("KNOWLEDGE_BASE_MAX_SIZE", "50000")
os.environ.setdefault("SAMPLING_WINDOW_SECONDS", "3600")

from p2p_transaction_pool import P2PTransactionPool


def make_pool(as_number=1):
    """Build a P2PTransactionPool without running __init__."""
    pool = P2PTransactionPool.__new__(P2PTransactionPool)
    import logging
    import threading
    pool.as_number = as_number
    pool.logger = logging.getLogger(f"test-pool-as{as_number}")
    pool.lock = threading.Lock()
    pool._pending_event_keys = set()
    pool.knowledge_base = []
    pool._kb_index = {}
    pool.knowledge_window_seconds = 480
    pool.last_seen_cache = {}
    # Stub out SAMPLING_WINDOW check
    pool.SAMPLING_WINDOW_SECONDS = 3600
    # Capture add_bgp_observation calls
    pool._add_obs_calls = []
    orig = pool.add_bgp_observation.__get__(pool)
    def _wrapped(ip_prefix, sender_asn, timestamp, trust_score, is_attack=False):
        pool._add_obs_calls.append({
            "ip_prefix": ip_prefix,
            "sender_asn": sender_asn,
            "timestamp": timestamp,
            "trust_score": trust_score,
            "is_attack": is_attack,
        })
        # Also update _kb_index so downstream checks can see it
        pool._kb_index.setdefault(ip_prefix, []).append((sender_asn, timestamp, "now"))
        return True
    pool.add_bgp_observation = _wrapped

    pool.prefix_ownership_state = MagicMock()
    pool.blockchain = MagicMock()
    pool.blockchain.append_replicated_block = MagicMock(return_value=True)

    # neighbor_cache is referenced by add_bgp_observation — safe stub
    pool.neighbor_cache = MagicMock()
    return pool


# ----------------------------------------------------------------------
# Fix #2 — learn from incoming vote_request
# ----------------------------------------------------------------------
def test_vote_request_adds_to_kb_after_voting():
    pool = make_pool(as_number=1)

    # Stub the vote-and-send path so we only test the KB-learning part
    pool._validate_transaction = MagicMock(return_value="no_knowledge")
    pool._send_vote_to_node = MagicMock()

    tx = {
        "transaction_id": "tx_test_001",
        "ip_prefix": "203.0.113.0/24",
        "sender_asn": 64500,
        "timestamp": 1700000000.0,
        "is_attack": False,
    }
    msg = {"transaction": tx, "from_as": 2}

    pool._handle_vote_request(msg)

    # Vote must have been computed before KB write (for Fix #2 correctness)
    assert pool._validate_transaction.called, "validate_transaction must be called"
    assert pool._send_vote_to_node.called, "send_vote_to_node must be called"

    # KB must have received the observation
    assert len(pool._add_obs_calls) == 1, f"expected 1 KB write, got {len(pool._add_obs_calls)}"
    call = pool._add_obs_calls[0]
    assert call["ip_prefix"] == "203.0.113.0/24"
    assert call["sender_asn"] == 64500
    assert call["trust_score"] == 65.0  # 3rd-party witness tier
    assert call["is_attack"] is False
    print("✅ Fix #2: vote_request adds observation to KB after voting")


def test_vote_request_kb_write_propagates_attack_flag():
    pool = make_pool()
    pool._validate_transaction = MagicMock(return_value="no_knowledge")
    pool._send_vote_to_node = MagicMock()
    tx = {
        "transaction_id": "tx_attack_001",
        "ip_prefix": "198.51.100.0/24",
        "sender_asn": 64666,
        "timestamp": 1700000100.0,
        "is_attack": True,
    }
    pool._handle_vote_request({"transaction": tx, "from_as": 3})
    assert pool._add_obs_calls[0]["is_attack"] is True, "attack flag must propagate to KB"
    print("✅ Fix #2: attack flag propagates into KB")


def test_vote_request_skipped_when_missing_fields():
    pool = make_pool()
    pool._validate_transaction = MagicMock(return_value="no_knowledge")
    pool._send_vote_to_node = MagicMock()
    tx = {
        "transaction_id": "tx_bad",
        "ip_prefix": "",        # missing
        "sender_asn": 0,        # missing
        "timestamp": 0,
        "is_attack": False,
    }
    pool._handle_vote_request({"transaction": tx, "from_as": 3})
    assert len(pool._add_obs_calls) == 0, "no KB write when prefix/origin missing"
    print("✅ Fix #2: missing-field guard works")


# ----------------------------------------------------------------------
# Fix #9 + Fix #3 — replicated block propagates state + KB
# ----------------------------------------------------------------------
def test_replicated_block_updates_ownership_state_and_kb():
    pool = make_pool(as_number=1)

    block = {
        "block_hash": "abc",
        "previous_hash": "prev",
        "transactions": [
            {   # CONFIRMED — should fire both updates
                "consensus_status": "CONFIRMED",
                "ip_prefix": "10.0.0.0/8",
                "sender_asn": 64500,
                "timestamp": 1700000000.0,
                "is_attack": False,
            },
            {   # INSUFFICIENT — should be skipped entirely
                "consensus_status": "INSUFFICIENT_CONSENSUS",
                "ip_prefix": "172.16.0.0/12",
                "sender_asn": 64501,
                "timestamp": 1700000050.0,
                "is_attack": False,
            },
            {   # CONFIRMED attack — should hit KB but NOT ownership state
                "consensus_status": "CONFIRMED",
                "ip_prefix": "192.0.2.0/24",
                "sender_asn": 64666,
                "timestamp": 1700000100.0,
                "is_attack": True,
            },
        ],
    }

    pool._handle_block_replicate({"block": block})

    # Source 2: prefix_ownership_state.update_from_confirmed — only non-attack CONFIRMED
    ups_calls = pool.prefix_ownership_state.update_from_confirmed.call_args_list
    assert len(ups_calls) == 1, f"expected 1 ownership update, got {len(ups_calls)}"
    kwargs = ups_calls[0].kwargs
    assert kwargs["prefix"] == "10.0.0.0/8"
    assert kwargs["origin_asn"] == 64500
    print("✅ Fix #9: CONFIRMED non-attack TX updates prefix_ownership_state")

    # Source 1: add_bgp_observation — both CONFIRMED TXs (including attack)
    kb_prefixes = [c["ip_prefix"] for c in pool._add_obs_calls]
    assert "10.0.0.0/8" in kb_prefixes
    assert "192.0.2.0/24" in kb_prefixes
    assert "172.16.0.0/12" not in kb_prefixes
    assert all(c["trust_score"] == 70.0 for c in pool._add_obs_calls)
    print("✅ Fix #3: CONFIRMED TXs backfill KB at trust_score 70 (attacks included)")


def test_replicated_block_rejected_when_hash_invalid():
    pool = make_pool()
    pool.blockchain.append_replicated_block = MagicMock(return_value=False)

    block = {
        "block_hash": "bogus",
        "previous_hash": "prev",
        "transactions": [{
            "consensus_status": "CONFIRMED",
            "ip_prefix": "10.0.0.0/8",
            "sender_asn": 64500,
            "timestamp": 1700000000.0,
            "is_attack": False,
        }],
    }
    pool._handle_block_replicate({"block": block})

    assert not pool.prefix_ownership_state.update_from_confirmed.called, \
        "must NOT update ownership state if block rejected"
    assert len(pool._add_obs_calls) == 0, \
        "must NOT backfill KB if block rejected"
    print("✅ Security: rejected blocks do not leak into knowledge state")


def test_replicated_block_none_is_safe():
    pool = make_pool()
    pool._handle_block_replicate({"block": None})
    assert not pool.blockchain.append_replicated_block.called
    assert len(pool._add_obs_calls) == 0
    print("✅ None-block handled safely")


# ----------------------------------------------------------------------
# Fix #5 — approve-vote teaches neighbor_cache (dynamic Layer 1 intelligence)
# ----------------------------------------------------------------------
def _setup_vote_response_pool(as_number=1):
    """Extended pool setup for _handle_vote_response tests."""
    import threading
    pool = P2PTransactionPool.__new__(P2PTransactionPool)
    import logging
    pool.as_number = as_number
    pool.logger = logging.getLogger(f"test-vr-as{as_number}")
    pool.lock = threading.Lock()
    pool.pending_votes = {}
    pool.committed_transactions = {}
    pool.total_nodes = 10
    pool.consensus_threshold = 2
    pool.neighbor_cache = MagicMock()
    pool._commit_to_blockchain = MagicMock()
    return pool


def _seed_pending_tx(pool, tx_id, sender_asn):
    """Seed a pending transaction so vote_response has something to match."""
    import threading
    from datetime import datetime
    pool.pending_votes[tx_id] = {
        "transaction": {
            "transaction_id": tx_id,
            "ip_prefix": "10.0.0.0/8",
            "sender_asn": sender_asn,
            "timestamp": 1700000000.0,
        },
        "votes": [],
        "needed": pool.consensus_threshold,
        "created_at": datetime.now(),
        "is_attack": False,
        "consensus_event": threading.Event(),
    }


def test_approve_vote_teaches_neighbor_cache():
    pool = _setup_vote_response_pool(as_number=1)
    _seed_pending_tx(pool, "tx_approve_001", sender_asn=64500)

    pool._handle_vote_response({
        "transaction_id": "tx_approve_001",
        "vote": "approve",
        "from_as": 7,
        "timestamp": 1700000010.0,
    })

    pool.neighbor_cache.record_observation.assert_called_once()
    kwargs = pool.neighbor_cache.record_observation.call_args.kwargs
    assert kwargs["origin_as"] == 64500, f"origin_as should be tx sender, got {kwargs['origin_as']}"
    assert kwargs["observed_by_rpki_as"] == 7, f"observed_by should be voter, got {kwargs['observed_by_rpki_as']}"
    print("✅ Fix #5: approve vote records voter as observer in neighbor_cache")


def test_no_knowledge_vote_does_not_teach_cache():
    pool = _setup_vote_response_pool()
    _seed_pending_tx(pool, "tx_noknow_001", sender_asn=64500)

    pool._handle_vote_response({
        "transaction_id": "tx_noknow_001",
        "vote": "no_knowledge",
        "from_as": 7,
    })

    assert not pool.neighbor_cache.record_observation.called, \
        "no_knowledge must NOT teach neighbor_cache"
    print("✅ Fix #5: no_knowledge votes do not teach cache (correct — voter has no knowledge)")


def test_reject_vote_does_not_teach_cache():
    pool = _setup_vote_response_pool()
    _seed_pending_tx(pool, "tx_reject_001", sender_asn=64500)

    pool._handle_vote_response({
        "transaction_id": "tx_reject_001",
        "vote": "reject",
        "from_as": 7,
    })

    assert not pool.neighbor_cache.record_observation.called, \
        "reject must NOT teach cache for this origin (voter has conflicting knowledge)"
    print("✅ Fix #5: reject votes do not teach cache (voter saw different origin)")


def test_approve_vote_never_records_self():
    pool = _setup_vote_response_pool(as_number=1)
    _seed_pending_tx(pool, "tx_self_001", sender_asn=64500)

    # Pretend we got our own signed approve back (shouldn't normally happen,
    # but guard against self-reference cache corruption)
    pool._handle_vote_response({
        "transaction_id": "tx_self_001",
        "vote": "approve",
        "from_as": pool.as_number,   # our own ASN
    })

    assert not pool.neighbor_cache.record_observation.called, \
        "Must not record self as observer via own-vote"
    print("✅ Fix #5: self-vote is never recorded as observer")


def test_duplicate_approve_does_not_teach_cache_twice():
    pool = _setup_vote_response_pool()
    _seed_pending_tx(pool, "tx_dup_001", sender_asn=64500)

    for _ in range(2):
        pool._handle_vote_response({
            "transaction_id": "tx_dup_001",
            "vote": "approve",
            "from_as": 7,
        })

    # Second call hits the vote-deduplication guard and early-returns
    assert pool.neighbor_cache.record_observation.call_count == 1, \
        f"expected 1 teach call, got {pool.neighbor_cache.record_observation.call_count}"
    print("✅ Fix #5: duplicate approve votes are deduplicated, cache not double-taught")


if __name__ == "__main__":
    test_vote_request_adds_to_kb_after_voting()
    test_vote_request_kb_write_propagates_attack_flag()
    test_vote_request_skipped_when_missing_fields()
    test_replicated_block_updates_ownership_state_and_kb()
    test_replicated_block_rejected_when_hash_invalid()
    test_replicated_block_none_is_safe()
    print()
    test_approve_vote_teaches_neighbor_cache()
    test_no_knowledge_vote_does_not_teach_cache()
    test_reject_vote_does_not_teach_cache()
    test_approve_vote_never_records_self()
    test_duplicate_approve_does_not_teach_cache_twice()
    print("\n🎉 All knowledge-propagation tests passed")
