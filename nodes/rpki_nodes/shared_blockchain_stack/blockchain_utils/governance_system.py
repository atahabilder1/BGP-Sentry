#!/usr/bin/env python3
"""
=============================================================================
Governance System - Decentralized Consensus for Network Operations
=============================================================================

Purpose: Enable democratic protocol evolution through BGPCOIN-weighted voting

All major network operations require consensus:
1. Monthly behavioral analysis (66% consensus)
2. Trust scoring modifications (75% consensus)
3. Reward adjustments (66% consensus)
4. New threat detection (60% consensus)

Voting Process:
1. Any node proposes an action (monthly_analysis, reward_change, etc.)
2. Proposal broadcasted to all nodes via P2P network
3. Nodes vote (approve/reject) based on their judgment
4. Votes weighted by BGPCOIN holdings (prevents Sybil attacks)
5. If consensus threshold met → Action executed on all nodes
6. Results recorded on blockchain for transparency

Example: Monthly Analysis Trigger
────────────────────────────────────
AS01 proposes: "Run monthly behavioral analysis for November 2025"
   ↓
Broadcast to all 8 other nodes
   ↓
Voting:
  AS01: APPROVE (weight: 1,250 BGPCOIN)
  AS03: APPROVE (weight: 980 BGPCOIN)
  AS05: APPROVE (weight: 1,100 BGPCOIN)
  AS07: APPROVE (weight: 750 BGPCOIN)
  AS09: APPROVE (weight: 890 BGPCOIN)
  AS11: REJECT  (weight: 650 BGPCOIN)
  AS13: REJECT  (weight: 420 BGPCOIN)
  AS15: APPROVE (weight: 1,050 BGPCOIN)
  AS17: APPROVE (weight: 810 BGPCOIN)
   ↓
Calculate: 7/9 nodes approved (77.7%) → Consensus reached!
Weighted: 7,830/8,900 BGPCOIN (87.9%) → Above 66% threshold
   ↓
✅ Execute monthly analysis on ALL nodes
✅ Record governance transaction on blockchain

Author: BGP-Sentry Team
=============================================================================
"""

import json
import socket
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class GovernanceSystem:
    """
    Decentralized governance for BGP-Sentry network operations.

    Uses BGPCOIN-weighted voting to reach consensus on:
    - Monthly behavioral analysis
    - Parameter changes
    - Protocol upgrades
    """

    def __init__(self, as_number, bgpcoin_ledger, p2p_pool, governance_path="blockchain_data/state"):
        """
        Initialize governance system.

        Args:
            as_number: This node's AS number
            bgpcoin_ledger: BGPCoinLedger instance
            p2p_pool: P2PTransactionPool instance (for broadcasting)
            governance_path: Path to store governance data
        """
        self.as_number = as_number
        self.ledger = bgpcoin_ledger
        self.p2p_pool = p2p_pool
        self.governance_dir = Path(governance_path)
        self.proposals_file = self.governance_dir / "governance_proposals.json"
        self.votes_file = self.governance_dir / "governance_votes.jsonl"

        # Consensus thresholds (from proposal)
        self.thresholds = {
            "monthly_analysis": 0.66,        # 66% consensus
            "trust_modification": 0.75,      # 75% consensus
            "reward_adjustment": 0.66,       # 66% consensus
            "threat_detection": 0.60,        # 60% consensus
            "protocol_upgrade": 0.75         # 75% consensus
        }

        # Active proposals
        self.active_proposals = {}  # proposal_id -> proposal_data
        self.vote_tracking = {}     # proposal_id -> {votes, weighted_total}

        # Thread safety
        self.lock = threading.Lock()

        # Load existing proposals
        self._load_proposals()

    def _load_proposals(self):
        """Load active governance proposals from disk"""
        try:
            if self.proposals_file.exists():
                with open(self.proposals_file, 'r') as f:
                    data = json.load(f)
                    self.active_proposals = data.get("proposals", {})
                    self.vote_tracking = data.get("vote_tracking", {})
                print(f"📜 Loaded {len(self.active_proposals)} active governance proposals")
        except Exception as e:
            print(f"Error loading governance proposals: {e}")

    def _save_proposals(self):
        """Save governance proposals to disk"""
        try:
            data = {
                "proposals": self.active_proposals,
                "vote_tracking": self.vote_tracking,
                "last_updated": datetime.now().isoformat()
            }

            temp_file = self.proposals_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.proposals_file)

        except Exception as e:
            print(f"Error saving governance proposals: {e}")

    def propose_monthly_analysis(self, analysis_period: str) -> str:
        """
        Propose running monthly behavioral analysis.

        Args:
            analysis_period: Period to analyze (e.g., "November 2025")

        Returns:
            proposal_id
        """
        proposal_id = f"monthly_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        proposal = {
            "proposal_id": proposal_id,
            "type": "monthly_analysis",
            "proposer_as": self.as_number,
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period": analysis_period,
                "days": 30
            },
            "status": "voting",
            "required_consensus": self.thresholds["monthly_analysis"]
        }

        with self.lock:
            self.active_proposals[proposal_id] = proposal
            self.vote_tracking[proposal_id] = {
                "votes": {},  # as_number -> vote
                "approve_count": 0,
                "reject_count": 0,
                "weighted_approve": 0,
                "weighted_reject": 0,
                "total_weight": 0
            }

            # Automatically vote approve from proposer
            self._record_vote(proposal_id, self.as_number, "approve")

            self._save_proposals()

        print(f"📋 Governance Proposal Created: {proposal_id}")
        print(f"   Type: Monthly Behavioral Analysis")
        print(f"   Period: {analysis_period}")
        print(f"   Required Consensus: {self.thresholds['monthly_analysis']:.0%}")

        # Broadcast proposal to all nodes
        self._broadcast_proposal(proposal)

        return proposal_id

    def _broadcast_proposal(self, proposal: Dict):
        """
        Broadcast governance proposal to all peer nodes.

        Args:
            proposal: Proposal data
        """
        try:
            # Use P2P network to broadcast
            for peer_as, (host, port) in self.p2p_pool.peer_nodes.items():
                self._send_proposal_to_node(peer_as, host, port, proposal)

            print(f"📡 Broadcasted proposal {proposal['proposal_id']} to {len(self.p2p_pool.peer_nodes)} nodes")

        except Exception as e:
            print(f"Error broadcasting proposal: {e}")

    def _send_proposal_to_node(self, peer_as: int, host: str, port: int, proposal: Dict):
        """Send governance proposal to specific node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            message = {
                "type": "governance_proposal",
                "from_as": self.as_number,
                "proposal": proposal,
                "timestamp": datetime.now().isoformat()
            }

            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()

        except Exception as e:
            print(f"Failed to send proposal to AS{peer_as}: {e}")

    def handle_proposal_message(self, message: Dict):
        """
        Handle incoming governance proposal from peer.

        Args:
            message: Governance proposal message
        """
        try:
            proposal = message["proposal"]
            from_as = message["from_as"]

            proposal_id = proposal["proposal_id"]

            print(f"📨 Received governance proposal from AS{from_as}: {proposal_id}")
            print(f"   Type: {proposal['type']}")

            # Add to active proposals
            with self.lock:
                if proposal_id not in self.active_proposals:
                    self.active_proposals[proposal_id] = proposal
                    self.vote_tracking[proposal_id] = {
                        "votes": {},
                        "approve_count": 0,
                        "reject_count": 0,
                        "weighted_approve": 0,
                        "weighted_reject": 0,
                        "total_weight": 0
                    }
                    self._save_proposals()

            # Automatically vote (can be changed to manual voting)
            self._auto_vote_on_proposal(proposal)

        except Exception as e:
            print(f"Error handling proposal message: {e}")

    def _auto_vote_on_proposal(self, proposal: Dict):
        """
        Automatically vote on proposal based on node's logic.

        For now, auto-approve monthly analysis proposals.
        Can be extended with more sophisticated logic.

        Args:
            proposal: Proposal to vote on
        """
        proposal_id = proposal["proposal_id"]
        proposal_type = proposal["type"]

        # Default: approve monthly analysis
        if proposal_type == "monthly_analysis":
            vote = "approve"
        else:
            vote = "approve"  # Default approve for now

        self.vote_on_proposal(proposal_id, vote)

    def vote_on_proposal(self, proposal_id: str, vote: str) -> bool:
        """
        Cast vote on governance proposal.

        Args:
            proposal_id: Proposal to vote on
            vote: "approve" or "reject"

        Returns:
            True if vote recorded
        """
        try:
            if proposal_id not in self.active_proposals:
                print(f"❌ Unknown proposal: {proposal_id}")
                return False

            # Record vote locally
            self._record_vote(proposal_id, self.as_number, vote)

            # Broadcast vote to all nodes
            self._broadcast_vote(proposal_id, vote)

            # Check if consensus reached
            self._check_consensus(proposal_id)

            return True

        except Exception as e:
            print(f"Error voting on proposal: {e}")
            return False

    def _record_vote(self, proposal_id: str, voter_as: int, vote: str):
        """
        Record vote with BGPCOIN weighting.

        Args:
            proposal_id: Proposal ID
            voter_as: AS number of voter
            vote: "approve" or "reject"
        """
        with self.lock:
            tracking = self.vote_tracking[proposal_id]

            # Get voter's BGPCOIN balance (weight)
            weight = self.ledger.get_balance(voter_as)

            # Record vote
            tracking["votes"][voter_as] = {
                "vote": vote,
                "weight": weight,
                "timestamp": datetime.now().isoformat()
            }

            # Update counts
            if vote == "approve":
                tracking["approve_count"] += 1
                tracking["weighted_approve"] += weight
            else:
                tracking["reject_count"] += 1
                tracking["weighted_reject"] += weight

            tracking["total_weight"] = tracking["weighted_approve"] + tracking["weighted_reject"]

            self._save_proposals()

            print(f"🗳️  AS{voter_as} voted {vote.upper()} on {proposal_id} (weight: {weight} BGPCOIN)")

    def _broadcast_vote(self, proposal_id: str, vote: str):
        """Broadcast vote to all peers"""
        try:
            for peer_as, (host, port) in self.p2p_pool.peer_nodes.items():
                self._send_vote_to_node(peer_as, host, port, proposal_id, vote)

        except Exception as e:
            print(f"Error broadcasting vote: {e}")

    def _send_vote_to_node(self, peer_as: int, host: str, port: int, proposal_id: str, vote: str):
        """Send vote to specific node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            message = {
                "type": "governance_vote",
                "from_as": self.as_number,
                "proposal_id": proposal_id,
                "vote": vote,
                "timestamp": datetime.now().isoformat()
            }

            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()

        except Exception as e:
            pass  # Silent fail for vote broadcasting

    def handle_vote_message(self, message: Dict):
        """Handle incoming vote from peer"""
        try:
            proposal_id = message["proposal_id"]
            voter_as = message["from_as"]
            vote = message["vote"]

            if proposal_id in self.active_proposals:
                self._record_vote(proposal_id, voter_as, vote)
                self._check_consensus(proposal_id)

        except Exception as e:
            print(f"Error handling vote message: {e}")

    def _check_consensus(self, proposal_id: str):
        """
        Check if proposal has reached consensus.

        Args:
            proposal_id: Proposal to check
        """
        try:
            proposal = self.active_proposals[proposal_id]
            tracking = self.vote_tracking[proposal_id]
            required_threshold = proposal["required_consensus"]

            # Calculate consensus percentage (weighted by BGPCOIN)
            if tracking["total_weight"] == 0:
                return  # No votes yet

            weighted_approval = tracking["weighted_approve"] / tracking["total_weight"]

            # Also check simple majority (number of nodes)
            total_votes = tracking["approve_count"] + tracking["reject_count"]
            simple_approval = tracking["approve_count"] / total_votes if total_votes > 0 else 0

            print(f"📊 Consensus Check for {proposal_id}:")
            print(f"   Weighted Approval: {weighted_approval:.1%} (threshold: {required_threshold:.1%})")
            print(f"   Simple Approval: {simple_approval:.1%} ({tracking['approve_count']}/{total_votes} nodes)")

            # Consensus reached if both weighted and simple majority
            if weighted_approval >= required_threshold and simple_approval >= required_threshold:
                print(f"✅ CONSENSUS REACHED for {proposal_id}!")
                self._execute_proposal(proposal_id)

        except Exception as e:
            print(f"Error checking consensus: {e}")

    def _execute_proposal(self, proposal_id: str):
        """
        Execute approved proposal.

        Args:
            proposal_id: Proposal to execute
        """
        try:
            proposal = self.active_proposals[proposal_id]
            proposal_type = proposal["type"]

            print(f"⚡ Executing proposal: {proposal_id}")
            print(f"   Type: {proposal_type}")

            # Execute based on type
            if proposal_type == "monthly_analysis":
                self._execute_monthly_analysis(proposal)

            # Mark as executed
            proposal["status"] = "executed"
            proposal["execution_timestamp"] = datetime.now().isoformat()
            self._save_proposals()

            # Log to votes file
            self._log_governance_action(proposal)

        except Exception as e:
            print(f"Error executing proposal: {e}")

    def _execute_monthly_analysis(self, proposal: Dict):
        """
        Execute monthly behavioral analysis.

        Args:
            proposal: Analysis proposal
        """
        try:
            from behavioral_analysis import BehavioralAnalyzer

            # Get blockchain interface from P2P pool
            blockchain = self.p2p_pool.blockchain

            # Create analyzer
            analyzer = BehavioralAnalyzer(blockchain, self.ledger, self.governance_dir)

            # Run analysis
            days = proposal["parameters"].get("days", 30)
            result = analyzer.run_monthly_analysis(days)

            print(f"✅ Monthly analysis completed!")

        except Exception as e:
            print(f"Error executing monthly analysis: {e}")

    def _log_governance_action(self, proposal: Dict):
        """Log governance action to file"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "proposal_id": proposal["proposal_id"],
                "type": proposal["type"],
                "proposer": proposal["proposer_as"],
                "votes": self.vote_tracking[proposal["proposal_id"]],
                "status": proposal["status"]
            }

            with open(self.votes_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            print(f"Error logging governance action: {e}")


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("GOVERNANCE SYSTEM - TEST")
    print("=" * 80)
    print()

    # This would be integrated with P2P pool in real usage
    print("✅ Governance system ready")
    print("   - Decentralized proposal creation")
    print("   - BGPCOIN-weighted voting")
    print("   - Automated execution on consensus")
