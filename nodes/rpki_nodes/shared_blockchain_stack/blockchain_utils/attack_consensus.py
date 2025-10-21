#!/usr/bin/env python3
"""
=============================================================================
Attack Consensus System - Majority Voting for Attack Detection
=============================================================================

Purpose: Enable nodes to collectively decide if BGP announcement is an attack

Voting Process:
1. Node detects potential attack using AttackDetector
2. Broadcasts attack proposal to all peers
3. Each peer runs their own AttackDetector and votes YES/NO
4. Majority voting decides final verdict (minimum 3 votes, like transactions)
5. Confidence score calculated: 0-1 scale based on agreement level
6. Attack verdict recorded to blockchain with voter details
7. BGPCOIN rewards distributed
8. Non-RPKI ratings updated instantly

Example Flow:
─────────────
AS01 detects potential IP prefix hijacking:
  - Prefix: 8.8.8.0/24
  - Announced by: AS666
  - ROA shows: AS15169 (Google)

AS01 broadcasts attack proposal to all peers
  ↓
Voting:
  AS01: YES (detected hijacking)
  AS03: YES (confirmed via ROA)
  AS05: YES (confirmed)
  AS07: NO  (thinks legitimate)
  AS09: YES (confirmed)
  AS11: YES (confirmed)
  AS13: NO  (disagrees)
  AS15: YES (confirmed)
  AS17: NO  (disagrees)
  ↓
Result: 6 YES, 3 NO (66.7% agreement)
Verdict: ATTACK CONFIRMED (majority reached)
Confidence: 0.67
  ↓
Actions:
1. Record attack verdict to blockchain/attack_verdicts.jsonl
2. Update AS666 rating: 50 → 30 (-20 penalty)
3. Award BGPCOIN:
   - AS01 (detector): +10 BGPCOIN
   - Correct voters (6 nodes): +2 BGPCOIN each
   - Incorrect voters (3 nodes): 0 BGPCOIN

Author: BGP-Sentry Team
=============================================================================
"""

import json
import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class AttackConsensus:
    """
    Manages attack detection consensus voting.

    Uses majority voting to determine if BGP announcement is an attack.
    Records verdicts to blockchain with confidence scores.
    """

    def __init__(self, as_number, attack_detector, rating_system,
                 bgpcoin_ledger, p2p_pool, blockchain_dir):
        """
        Initialize attack consensus system.

        Args:
            as_number: This node's AS number
            attack_detector: AttackDetector instance
            rating_system: NonRPKIRatingSystem instance
            bgpcoin_ledger: BGPCoinLedger instance
            p2p_pool: P2PTransactionPool instance
            blockchain_dir: Path to blockchain directory
        """
        self.as_number = as_number
        self.attack_detector = attack_detector
        self.rating_system = rating_system
        self.ledger = bgpcoin_ledger
        self.p2p_pool = p2p_pool

        # Attack verdict storage
        self.blockchain_dir = Path(blockchain_dir)
        self.attack_verdicts_file = self.blockchain_dir / "attack_verdicts.jsonl"

        # Active attack proposals
        self.active_proposals = {}  # proposal_id -> proposal_data
        self.vote_tracking = {}     # proposal_id -> {votes, tallies}

        # Consensus thresholds
        self.min_votes = 3  # Same as transaction consensus

        # BGPCOIN rewards
        self.rewards = {
            "attack_detection": 10,      # Detector gets 10 BGPCOIN
            "correct_vote": 2,           # Each correct voter gets 2 BGPCOIN
            "false_accusation": -20      # Penalty for false detection
        }

        # Thread safety
        self.lock = threading.Lock()

        print(f"🛡️  Attack Consensus System initialized")
        print(f"   Min votes required: {self.min_votes}")
        print(f"   Verdicts file: {self.attack_verdicts_file}")

    def analyze_and_propose_attack(self, announcement: Dict, transaction_id: str):
        """
        Analyze announcement for attacks and propose if detected.

        Args:
            announcement: BGP announcement to analyze
            transaction_id: Associated transaction ID
        """
        try:
            # Run attack detection
            detected_attacks = self.attack_detector.detect_attacks(announcement)

            if not detected_attacks:
                # No attacks detected, nothing to propose
                return

            # Create attack proposal for each detected attack
            for attack in detected_attacks:
                proposal_id = self._create_attack_proposal(
                    announcement=announcement,
                    transaction_id=transaction_id,
                    attack_details=attack
                )

                # Broadcast proposal to all peers
                self._broadcast_attack_proposal(proposal_id)

        except Exception as e:
            print(f"Error analyzing announcement for attacks: {e}")

    def _create_attack_proposal(self, announcement: Dict, transaction_id: str,
                                attack_details: Dict) -> str:
        """
        Create attack proposal for voting.

        Args:
            announcement: BGP announcement
            transaction_id: Associated transaction
            attack_details: Attack detection results

        Returns:
            proposal_id
        """
        proposal_id = f"attack_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        proposal = {
            "proposal_id": proposal_id,
            "proposer_as": self.as_number,
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id,
            "announcement": announcement,
            "attack_details": attack_details,
            "status": "voting"
        }

        with self.lock:
            self.active_proposals[proposal_id] = proposal
            self.vote_tracking[proposal_id] = {
                "votes": {},  # as_number -> YES/NO
                "yes_count": 1,  # Proposer automatically votes YES
                "no_count": 0,
                "total_votes": 1
            }

            # Proposer automatically votes YES
            self.vote_tracking[proposal_id]["votes"][self.as_number] = {
                "vote": "YES",
                "timestamp": datetime.now().isoformat(),
                "confidence": 1.0
            }

        attack_type = attack_details.get("attack_type", "unknown")
        attacker = attack_details.get("attacker_as") or attack_details.get("leaker_as")

        print(f"🚨 Attack Proposal Created: {proposal_id}")
        print(f"   Type: {attack_type}")
        print(f"   Suspected Attacker: AS{attacker}")
        print(f"   Transaction: {transaction_id}")

        return proposal_id

    def _broadcast_attack_proposal(self, proposal_id: str):
        """
        Broadcast attack proposal to all peer nodes.

        Args:
            proposal_id: Proposal to broadcast
        """
        try:
            proposal = self.active_proposals[proposal_id]

            # Broadcast via P2P network
            for peer_as, (host, port) in self.p2p_pool.peer_nodes.items():
                self._send_attack_proposal_to_node(peer_as, host, port, proposal)

            print(f"📡 Broadcasted attack proposal to {len(self.p2p_pool.peer_nodes)} nodes")

        except Exception as e:
            print(f"Error broadcasting attack proposal: {e}")

    def _send_attack_proposal_to_node(self, peer_as: int, host: str, port: int,
                                     proposal: Dict):
        """Send attack proposal to specific node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            message = {
                "type": "attack_proposal",
                "from_as": self.as_number,
                "proposal": proposal,
                "timestamp": datetime.now().isoformat()
            }

            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()

        except Exception as e:
            print(f"Failed to send attack proposal to AS{peer_as}: {e}")

    def handle_attack_proposal(self, message: Dict):
        """
        Handle incoming attack proposal from peer.

        Args:
            message: Attack proposal message
        """
        try:
            proposal = message["proposal"]
            from_as = message["from_as"]
            proposal_id = proposal["proposal_id"]

            attack_type = proposal["attack_details"].get("attack_type", "unknown")

            print(f"📨 Received attack proposal from AS{from_as}: {proposal_id}")
            print(f"   Type: {attack_type}")

            # Add to active proposals
            with self.lock:
                if proposal_id not in self.active_proposals:
                    self.active_proposals[proposal_id] = proposal
                    self.vote_tracking[proposal_id] = {
                        "votes": {},
                        "yes_count": 0,
                        "no_count": 0,
                        "total_votes": 0
                    }

            # Analyze and vote
            self._analyze_and_vote(proposal)

        except Exception as e:
            print(f"Error handling attack proposal: {e}")

    def _analyze_and_vote(self, proposal: Dict):
        """
        Analyze announcement and cast vote on attack proposal.

        Args:
            proposal: Attack proposal to vote on
        """
        try:
            proposal_id = proposal["proposal_id"]
            announcement = proposal["announcement"]

            # Run our own attack detection
            detected_attacks = self.attack_detector.detect_attacks(announcement)

            # Check if we detect same attack type
            proposal_attack_type = proposal["attack_details"]["attack_type"]

            vote = "NO"  # Default: no attack detected
            for attack in detected_attacks:
                if attack["attack_type"] == proposal_attack_type:
                    vote = "YES"
                    break

            # Cast vote
            self.vote_on_attack(proposal_id, vote)

        except Exception as e:
            print(f"Error analyzing and voting on attack: {e}")
            # Vote NO if error
            self.vote_on_attack(proposal["proposal_id"], "NO")

    def vote_on_attack(self, proposal_id: str, vote: str) -> bool:
        """
        Cast vote on attack proposal.

        Args:
            proposal_id: Proposal ID
            vote: "YES" or "NO"

        Returns:
            True if vote recorded
        """
        try:
            if proposal_id not in self.active_proposals:
                print(f"❌ Unknown attack proposal: {proposal_id}")
                return False

            # Record vote
            with self.lock:
                tracking = self.vote_tracking[proposal_id]

                # Check if already voted
                if self.as_number in tracking["votes"]:
                    return False  # Already voted

                tracking["votes"][self.as_number] = {
                    "vote": vote,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 1.0
                }

                if vote == "YES":
                    tracking["yes_count"] += 1
                else:
                    tracking["no_count"] += 1

                tracking["total_votes"] += 1

            print(f"🗳️  AS{self.as_number} voted {vote} on attack {proposal_id}")

            # Broadcast vote to peers
            self._broadcast_attack_vote(proposal_id, vote)

            # Check if consensus reached
            self._check_attack_consensus(proposal_id)

            return True

        except Exception as e:
            print(f"Error voting on attack: {e}")
            return False

    def _broadcast_attack_vote(self, proposal_id: str, vote: str):
        """Broadcast attack vote to all peers"""
        try:
            for peer_as, (host, port) in self.p2p_pool.peer_nodes.items():
                self._send_attack_vote_to_node(peer_as, host, port, proposal_id, vote)

        except Exception as e:
            print(f"Error broadcasting attack vote: {e}")

    def _send_attack_vote_to_node(self, peer_as: int, host: str, port: int,
                                  proposal_id: str, vote: str):
        """Send attack vote to specific node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            message = {
                "type": "attack_vote",
                "from_as": self.as_number,
                "proposal_id": proposal_id,
                "vote": vote,
                "timestamp": datetime.now().isoformat()
            }

            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()

        except Exception as e:
            pass  # Silent fail

    def handle_attack_vote(self, message: Dict):
        """Handle incoming attack vote from peer"""
        try:
            proposal_id = message["proposal_id"]
            voter_as = message["from_as"]
            vote = message["vote"]

            if proposal_id in self.active_proposals:
                with self.lock:
                    tracking = self.vote_tracking[proposal_id]

                    # Check if already voted
                    if voter_as in tracking["votes"]:
                        return

                    tracking["votes"][voter_as] = {
                        "vote": vote,
                        "timestamp": message["timestamp"],
                        "confidence": 1.0
                    }

                    if vote == "YES":
                        tracking["yes_count"] += 1
                    else:
                        tracking["no_count"] += 1

                    tracking["total_votes"] += 1

                print(f"📨 Received {vote} vote from AS{voter_as} on attack {proposal_id}")

                # Check consensus
                self._check_attack_consensus(proposal_id)

        except Exception as e:
            print(f"Error handling attack vote: {e}")

    def _check_attack_consensus(self, proposal_id: str):
        """
        Check if attack proposal reached consensus (majority voting).

        Args:
            proposal_id: Proposal to check
        """
        try:
            tracking = self.vote_tracking[proposal_id]
            proposal = self.active_proposals[proposal_id]

            # Need minimum votes (same as transaction consensus)
            if tracking["total_votes"] < self.min_votes:
                return  # Not enough votes yet

            # Majority voting
            yes_votes = tracking["yes_count"]
            no_votes = tracking["no_count"]
            total = tracking["total_votes"]

            # Calculate confidence score (0-1)
            if yes_votes > no_votes:
                verdict = "ATTACK_CONFIRMED"
                confidence = yes_votes / total
            elif no_votes > yes_votes:
                verdict = "NOT_ATTACK"
                confidence = no_votes / total
            else:
                verdict = "DISPUTED"
                confidence = 0.5

            print(f"📊 Attack Consensus Check:")
            print(f"   Votes: {yes_votes} YES, {no_votes} NO ({total} total)")
            print(f"   Verdict: {verdict}")
            print(f"   Confidence: {confidence:.2f}")

            # Execute verdict
            if proposal["status"] == "voting":
                self._execute_attack_verdict(proposal_id, verdict, confidence)

        except Exception as e:
            print(f"Error checking attack consensus: {e}")

    def _execute_attack_verdict(self, proposal_id: str, verdict: str, confidence: float):
        """
        Execute attack verdict and update ratings.

        Args:
            proposal_id: Proposal ID
            verdict: ATTACK_CONFIRMED, NOT_ATTACK, or DISPUTED
            confidence: Confidence score (0-1)
        """
        try:
            proposal = self.active_proposals[proposal_id]
            tracking = self.vote_tracking[proposal_id]
            attack_details = proposal["attack_details"]

            # Get attacker AS
            attacker_as = attack_details.get("attacker_as") or attack_details.get("leaker_as")
            attack_type = attack_details.get("attack_type")

            # Create verdict record
            verdict_record = {
                "verdict_id": f"verdict_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "proposal_id": proposal_id,
                "transaction_id": proposal["transaction_id"],
                "timestamp": datetime.now().isoformat(),
                "verdict": verdict,
                "confidence": confidence,
                "attack_type": attack_type,
                "attacker_as": attacker_as,
                "votes": {
                    "yes_count": tracking["yes_count"],
                    "no_count": tracking["no_count"],
                    "total": tracking["total_votes"],
                    "voters": tracking["votes"]
                },
                "attack_details": attack_details
            }

            # Save verdict to blockchain
            self._save_verdict_to_blockchain(verdict_record)

            # Update ratings and distribute rewards
            if verdict == "ATTACK_CONFIRMED":
                self._handle_confirmed_attack(proposal, verdict_record, tracking)
            elif verdict == "NOT_ATTACK":
                self._handle_rejected_attack(proposal, verdict_record, tracking)
            else:  # DISPUTED
                self._handle_disputed_attack(proposal, verdict_record, tracking)

            # Mark proposal as executed
            proposal["status"] = "executed"
            proposal["verdict"] = verdict
            proposal["confidence"] = confidence

            print(f"✅ Attack verdict executed: {verdict} (confidence: {confidence:.2f})")

        except Exception as e:
            print(f"Error executing attack verdict: {e}")

    def _save_verdict_to_blockchain(self, verdict_record: Dict):
        """
        Save attack verdict to blockchain file.

        Args:
            verdict_record: Verdict details
        """
        try:
            # Append to attack_verdicts.jsonl
            with open(self.attack_verdicts_file, 'a') as f:
                f.write(json.dumps(verdict_record) + '\n')

            print(f"💾 Verdict saved to blockchain: {verdict_record['verdict_id']}")

        except Exception as e:
            print(f"Error saving verdict to blockchain: {e}")

    def _handle_confirmed_attack(self, proposal: Dict, verdict: Dict, tracking: Dict):
        """
        Handle confirmed attack verdict.

        Actions:
        1. Update non-RPKI AS rating (penalty)
        2. Award BGPCOIN to detector
        3. Award BGPCOIN to correct voters (YES voters)

        Args:
            proposal: Attack proposal
            verdict: Verdict record
            tracking: Vote tracking data
        """
        try:
            attacker_as = verdict["attacker_as"]
            attack_type = verdict["attack_type"]

            print(f"⚠️  ATTACK CONFIRMED!")
            print(f"   Attacker: AS{attacker_as}")
            print(f"   Type: {attack_type}")

            # 1. Update non-RPKI rating (instant penalty)
            rating_update = self.rating_system.record_attack(
                as_number=attacker_as,
                attack_type=attack_type,
                attack_details=verdict["attack_details"]
            )

            # 2. Award BGPCOIN to detector
            detector_as = proposal["proposer_as"]
            detector_reward = self.ledger.award_special_reward(
                as_number=detector_as,
                amount=self.rewards["attack_detection"],
                reason="attack_detection",
                details={
                    "attack_type": attack_type,
                    "verdict_id": verdict["verdict_id"]
                }
            )

            print(f"💰 Detector AS{detector_as} awarded {self.rewards['attack_detection']} BGPCOIN")

            # 3. Award BGPCOIN to correct voters (YES voters)
            yes_voters = [
                as_num for as_num, vote_data in tracking["votes"].items()
                if vote_data["vote"] == "YES"
            ]

            for voter_as in yes_voters:
                if voter_as != detector_as:  # Don't double-reward detector
                    self.ledger.award_special_reward(
                        as_number=voter_as,
                        amount=self.rewards["correct_vote"],
                        reason="correct_attack_vote",
                        details={"verdict_id": verdict["verdict_id"]}
                    )

            print(f"💰 {len(yes_voters)-1} correct voters awarded {self.rewards['correct_vote']} BGPCOIN each")

        except Exception as e:
            print(f"Error handling confirmed attack: {e}")

    def _handle_rejected_attack(self, proposal: Dict, verdict: Dict, tracking: Dict):
        """
        Handle rejected attack verdict (false accusation).

        Actions:
        1. Penalize false detector
        2. Award BGPCOIN to correct voters (NO voters)

        Args:
            proposal: Attack proposal
            verdict: Verdict record
            tracking: Vote tracking data
        """
        try:
            print(f"✅ Attack proposal REJECTED (false accusation)")

            # 1. Penalize false detector
            detector_as = proposal["proposer_as"]
            self.ledger.apply_penalty(
                as_number=detector_as,
                amount=abs(self.rewards["false_accusation"]),
                reason="false_attack_accusation",
                details={"verdict_id": verdict["verdict_id"]}
            )

            print(f"⚠️  Detector AS{detector_as} penalized {abs(self.rewards['false_accusation'])} BGPCOIN")

            # 2. Award BGPCOIN to correct voters (NO voters)
            no_voters = [
                as_num for as_num, vote_data in tracking["votes"].items()
                if vote_data["vote"] == "NO"
            ]

            for voter_as in no_voters:
                self.ledger.award_special_reward(
                    as_number=voter_as,
                    amount=self.rewards["correct_vote"],
                    reason="correct_attack_vote",
                    details={"verdict_id": verdict["verdict_id"]}
                )

            print(f"💰 {len(no_voters)} correct voters awarded {self.rewards['correct_vote']} BGPCOIN each")

        except Exception as e:
            print(f"Error handling rejected attack: {e}")

    def _handle_disputed_attack(self, proposal: Dict, verdict: Dict, tracking: Dict):
        """
        Handle disputed attack verdict (tie).

        No rewards or penalties.

        Args:
            proposal: Attack proposal
            verdict: Verdict record
            tracking: Vote tracking data
        """
        print(f"⚖️  Attack verdict DISPUTED (no consensus)")
        print(f"   No ratings changed, no rewards distributed")


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("ATTACK CONSENSUS SYSTEM - TEST")
    print("=" * 80)
    print()

    print("✅ Attack consensus system ready")
    print("   - Majority voting for attack verification")
    print("   - Confidence scoring (0-1 scale)")
    print("   - BGPCOIN rewards for accurate detection")
    print("   - Instant non-RPKI rating updates")
