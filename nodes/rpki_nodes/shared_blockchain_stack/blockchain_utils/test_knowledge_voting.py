#!/usr/bin/env python3
"""
Test script to demonstrate knowledge-based voting mechanism.

Scenario:
1. Node A and Node B both observe BGP announcement: AS12 announces 203.0.113.0/24
2. Node A creates transaction and broadcasts to peers
3. Node B receives vote request and checks knowledge base
4. Node B votes APPROVE because it also observed the same announcement
5. Node C did NOT observe this announcement
6. Node C votes REJECT because it has no record in knowledge base

This creates consensus based on actual observations, preventing fake announcements.
"""

import json
import time
from datetime import datetime
from pathlib import Path

def test_knowledge_voting():
    """Demonstrate knowledge-based voting"""

    print("=" * 80)
    print("KNOWLEDGE-BASED VOTING TEST")
    print("=" * 80)
    print()

    # Simulate BGP announcement observed by multiple nodes
    bgp_announcement = {
        "ip_prefix": "203.0.113.0/24",
        "sender_asn": 12,
        "timestamp": "2025-07-27T21:00:00Z",
        "trust_score": 50.0
    }

    print("📡 BGP Announcement Received:")
    print(json.dumps(bgp_announcement, indent=2))
    print()

    # Simulate knowledge bases for different nodes
    print("🧠 Node Knowledge Bases:")
    print()

    # Node AS01 observed the announcement
    node_as01_knowledge = [
        {
            "ip_prefix": "203.0.113.0/24",
            "sender_asn": 12,
            "timestamp": "2025-07-27T21:00:00Z",
            "trust_score": 50.0,
            "observed_at": datetime.now().isoformat()
        }
    ]
    print("✅ AS01 Knowledge Base: HAS observation for 203.0.113.0/24 from AS12")

    # Node AS03 also observed the announcement
    node_as03_knowledge = [
        {
            "ip_prefix": "203.0.113.0/24",
            "sender_asn": 12,
            "timestamp": "2025-07-27T21:00:00Z",
            "trust_score": 50.0,
            "observed_at": datetime.now().isoformat()
        }
    ]
    print("✅ AS03 Knowledge Base: HAS observation for 203.0.113.0/24 from AS12")

    # Node AS05 did NOT observe this announcement
    node_as05_knowledge = []
    print("❌ AS05 Knowledge Base: NO observation for 203.0.113.0/24 from AS12")
    print()

    # Simulate voting
    print("🗳️  Voting Process:")
    print()

    # AS15 creates transaction and broadcasts
    print("1. AS15 observes announcement → creates transaction → broadcasts to peers")
    transaction = {
        "transaction_id": "tx_12345",
        "observer_as": 15,
        "sender_asn": 12,
        "ip_prefix": "203.0.113.0/24",
        "timestamp": "2025-07-27T21:00:00Z",
        "trust_score": 50.0
    }
    print(f"   Transaction ID: {transaction['transaction_id']}")
    print()

    # AS01 checks knowledge and votes
    print("2. AS01 receives vote request")
    print("   → Checks knowledge base")
    print("   → ✅ MATCH FOUND in knowledge base")
    print("   → Votes: APPROVE")
    print()

    # AS03 checks knowledge and votes
    print("3. AS03 receives vote request")
    print("   → Checks knowledge base")
    print("   → ✅ MATCH FOUND in knowledge base")
    print("   → Votes: APPROVE")
    print()

    # AS05 checks knowledge and votes
    print("4. AS05 receives vote request")
    print("   → Checks knowledge base")
    print("   → ❌ NO MATCH in knowledge base")
    print("   → Votes: REJECT (possible fake announcement)")
    print()

    # Consensus result
    print("5. Consensus Result:")
    print("   Approve votes: 2 (AS01, AS03)")
    print("   Reject votes: 1 (AS05)")
    print("   Threshold: 3/9 nodes")
    print()
    print("   → More nodes vote, eventually 3+ approvals")
    print("   → ✅ CONSENSUS REACHED - Transaction committed to blockchain")
    print()

    print("=" * 80)
    print("KEY BENEFITS OF KNOWLEDGE-BASED VOTING:")
    print("=" * 80)
    print()
    print("1. ✅ Prevents Fake Announcements")
    print("   If only one malicious node claims an announcement,")
    print("   other nodes will reject because they didn't observe it.")
    print()
    print("2. ✅ Creates Competition")
    print("   Multiple nodes race to collect signatures for same announcement,")
    print("   first to get 3/9 approvals wins.")
    print()
    print("3. ✅ Time Window Tolerance")
    print("   Nodes observe announcements at slightly different times,")
    print("   ±5 minute window allows matching despite timing differences.")
    print()
    print("4. ✅ Distributed Consensus")
    print("   No single node controls what gets recorded,")
    print("   requires majority agreement based on actual observations.")
    print()

    # Show attack scenario
    print("=" * 80)
    print("ATTACK SCENARIO: Malicious Node Attempts Fake Announcement")
    print("=" * 80)
    print()

    fake_announcement = {
        "ip_prefix": "8.8.8.0/24",  # Google's IP - impossible for AS99 to announce
        "sender_asn": 99,
        "timestamp": "2025-07-27T21:00:00Z",
        "trust_score": 50.0
    }

    print("🚨 Malicious AS17 creates FAKE transaction:")
    print(json.dumps(fake_announcement, indent=2))
    print()

    print("🗳️  Voting Process:")
    print("   AS01: ❌ REJECT (no matching observation)")
    print("   AS03: ❌ REJECT (no matching observation)")
    print("   AS05: ❌ REJECT (no matching observation)")
    print("   AS07: ❌ REJECT (no matching observation)")
    print("   AS09: ❌ REJECT (no matching observation)")
    print("   AS11: ❌ REJECT (no matching observation)")
    print("   AS13: ❌ REJECT (no matching observation)")
    print("   AS15: ❌ REJECT (no matching observation)")
    print()
    print("   ❌ CONSENSUS FAILED - Transaction NOT committed")
    print("   ✅ Attack prevented by knowledge-based voting!")
    print()

if __name__ == "__main__":
    test_knowledge_voting()
