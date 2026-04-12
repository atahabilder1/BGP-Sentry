#!/usr/bin/env python3
"""
AsyncAttackConsensus - Async version of attack detection majority voting.

Same logic as AttackConsensus but uses AsyncMessageBus and asyncio.Lock
instead of threading primitives.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from rpki_node_registry import RPKINodeRegistry
from config import cfg

logger = logging.getLogger(__name__)


class AsyncAttackConsensus:
    """Async attack detection consensus voting."""

    def __init__(self, as_number, attack_detector, rating_system,
                 bgpcoin_ledger, p2p_pool, blockchain_dir):
        self.as_number = as_number
        self.attack_detector = attack_detector
        self.rating_system = rating_system
        self.ledger = bgpcoin_ledger
        self.p2p_pool = p2p_pool

        if blockchain_dir is not None:
            self.blockchain_dir = Path(blockchain_dir)
            self.attack_verdicts_file = self.blockchain_dir / "attack_verdicts.jsonl"
        else:
            self.blockchain_dir = None
            self.attack_verdicts_file = None

        self.active_proposals: Dict[str, dict] = {}
        self.vote_tracking: Dict[str, dict] = {}

        self.min_votes = cfg.ATTACK_CONSENSUS_MIN_VOTES
        self.rewards = {
            "attack_detection": cfg.ATTACK_CONSENSUS_REWARD_DETECTION,
            "correct_vote": cfg.ATTACK_CONSENSUS_REWARD_CORRECT_VOTE,
            "false_accusation": cfg.ATTACK_CONSENSUS_PENALTY_FALSE_ACCUSATION,
        }

        self.lock = asyncio.Lock()
        logger.info(f"AsyncAttackConsensus initialized (AS{as_number})")

    async def analyze_and_propose_attack(self, announcement: Dict,
                                         transaction_id: str):
        """Analyze announcement and propose attack if detected."""
        try:
            detected_attacks = self.attack_detector.detect_attacks(announcement)
            if not detected_attacks:
                return
            for attack in detected_attacks:
                proposal_id = self._create_attack_proposal(
                    announcement, transaction_id, attack
                )
                await self._broadcast_attack_proposal(proposal_id)
        except Exception as e:
            logger.error(f"Error analyzing announcement: {e}")

    def _create_attack_proposal(self, announcement, transaction_id,
                                attack_details) -> str:
        """Create attack proposal for voting."""
        proposal_id = f"attack_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        proposal = {
            "proposal_id": proposal_id,
            "proposer_as": self.as_number,
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id,
            "announcement": announcement,
            "attack_details": attack_details,
            "status": "voting",
        }
        self.active_proposals[proposal_id] = proposal
        self.vote_tracking[proposal_id] = {
            "votes": {},
            "yes_count": 1,
            "no_count": 0,
            "total_votes": 1,
        }
        self.vote_tracking[proposal_id]["votes"][self.as_number] = {
            "vote": "YES",
            "timestamp": datetime.now().isoformat(),
            "confidence": 1.0,
        }
        return proposal_id

    async def _broadcast_attack_proposal(self, proposal_id: str):
        """Broadcast attack proposal via async message bus."""
        try:
            proposal = self.active_proposals[proposal_id]
            message = {
                "type": "attack_proposal",
                "from_as": self.as_number,
                "proposal": proposal,
                "timestamp": datetime.now().isoformat(),
            }
            from message_bus_async import AsyncMessageBus
            bus = AsyncMessageBus.get_instance()
            await bus.broadcast(
                self.as_number, message,
                targets=list(self.p2p_pool.peer_nodes.keys()),
            )
        except Exception as e:
            logger.error(f"Error broadcasting attack proposal: {e}")

    async def handle_attack_proposal(self, message: Dict):
        """Handle incoming attack proposal from peer."""
        try:
            proposal = message["proposal"]
            proposal_id = proposal["proposal_id"]

            async with self.lock:
                if proposal_id not in self.active_proposals:
                    self.active_proposals[proposal_id] = proposal
                    self.vote_tracking[proposal_id] = {
                        "votes": {},
                        "yes_count": 0,
                        "no_count": 0,
                        "total_votes": 0,
                    }

            await self._analyze_and_vote(proposal)
        except Exception as e:
            logger.error(f"Error handling attack proposal: {e}")

    async def _analyze_and_vote(self, proposal: Dict):
        """Analyze announcement and cast vote."""
        try:
            proposal_id = proposal["proposal_id"]
            announcement = proposal["announcement"]
            detected_attacks = self.attack_detector.detect_attacks(announcement)
            proposal_attack_type = proposal["attack_details"]["attack_type"]

            vote = "NO"
            for attack in detected_attacks:
                if attack["attack_type"] == proposal_attack_type:
                    vote = "YES"
                    break

            await self.vote_on_attack(proposal_id, vote)
        except Exception as e:
            logger.error(f"Error analyzing attack: {e}")
            await self.vote_on_attack(proposal["proposal_id"], "NO")

    async def vote_on_attack(self, proposal_id: str, vote: str) -> bool:
        """Cast vote on attack proposal."""
        try:
            if proposal_id not in self.active_proposals:
                return False

            async with self.lock:
                tracking = self.vote_tracking[proposal_id]
                if self.as_number in tracking["votes"]:
                    return False

                tracking["votes"][self.as_number] = {
                    "vote": vote,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 1.0,
                }
                if vote == "YES":
                    tracking["yes_count"] += 1
                else:
                    tracking["no_count"] += 1
                tracking["total_votes"] += 1

            await self._broadcast_attack_vote(proposal_id, vote)
            self._check_attack_consensus(proposal_id)
            return True
        except Exception as e:
            logger.error(f"Error voting on attack: {e}")
            return False

    async def _broadcast_attack_vote(self, proposal_id: str, vote: str):
        """Broadcast attack vote via async message bus."""
        try:
            message = {
                "type": "attack_vote",
                "from_as": self.as_number,
                "proposal_id": proposal_id,
                "vote": vote,
                "timestamp": datetime.now().isoformat(),
            }
            from message_bus_async import AsyncMessageBus
            bus = AsyncMessageBus.get_instance()
            await bus.broadcast(
                self.as_number, message,
                targets=list(self.p2p_pool.peer_nodes.keys()),
            )
        except Exception as e:
            logger.error(f"Error broadcasting attack vote: {e}")

    async def handle_attack_vote(self, message: Dict):
        """Handle incoming attack vote from peer."""
        try:
            proposal_id = message["proposal_id"]
            voter_as = message["from_as"]
            vote = message["vote"]

            if proposal_id not in self.active_proposals:
                return

            async with self.lock:
                tracking = self.vote_tracking[proposal_id]
                if voter_as in tracking["votes"]:
                    return
                tracking["votes"][voter_as] = {
                    "vote": vote,
                    "timestamp": message["timestamp"],
                    "confidence": 1.0,
                }
                if vote == "YES":
                    tracking["yes_count"] += 1
                else:
                    tracking["no_count"] += 1
                tracking["total_votes"] += 1

            self._check_attack_consensus(proposal_id)
        except Exception as e:
            logger.error(f"Error handling attack vote: {e}")

    def _check_attack_consensus(self, proposal_id: str):
        """Check if attack proposal reached consensus."""
        try:
            tracking = self.vote_tracking[proposal_id]
            proposal = self.active_proposals[proposal_id]

            if tracking["total_votes"] < self.min_votes:
                return
            if proposal["status"] != "voting":
                return

            yes_votes = tracking["yes_count"]
            no_votes = tracking["no_count"]
            total = tracking["total_votes"]

            if yes_votes > no_votes:
                verdict = "ATTACK_CONFIRMED"
                confidence = yes_votes / total
            elif no_votes > yes_votes:
                verdict = "NOT_ATTACK"
                confidence = no_votes / total
            else:
                verdict = "DISPUTED"
                confidence = 0.5

            proposal["status"] = "executing"
            self._execute_attack_verdict(proposal_id, verdict, confidence)
        except Exception as e:
            logger.error(f"Error checking attack consensus: {e}")

    def _execute_attack_verdict(self, proposal_id, verdict, confidence):
        """Execute verdict — update ratings and distribute rewards."""
        try:
            proposal = self.active_proposals[proposal_id]
            tracking = self.vote_tracking[proposal_id]
            attack_details = proposal["attack_details"]
            attacker_as = attack_details.get("attacker_as") or attack_details.get("leaker_as")
            attack_type = attack_details.get("attack_type")

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
                    "voters": tracking["votes"],
                },
                "attack_details": attack_details,
            }

            # Save to blockchain
            blockchain_tx = dict(verdict_record)
            blockchain_tx["transaction_id"] = verdict_record["verdict_id"]
            blockchain_tx["record_type"] = "attack_verdict"
            self.p2p_pool.blockchain.add_transaction_to_blockchain(
                blockchain_tx, block_type="attack_verdict"
            )

            # Secondary index
            try:
                if self.attack_verdicts_file is not None:
                    with open(self.attack_verdicts_file, 'a') as f:
                        f.write(json.dumps(verdict_record) + '\n')
            except Exception:
                pass

            if verdict == "ATTACK_CONFIRMED":
                self._handle_confirmed_attack(proposal, verdict_record, tracking)
            elif verdict == "NOT_ATTACK":
                self._handle_rejected_attack(proposal, verdict_record, tracking)

            proposal["status"] = "executed"
            proposal["verdict"] = verdict
            proposal["confidence"] = confidence

        except Exception as e:
            logger.error(f"Error executing attack verdict: {e}")

    def _handle_confirmed_attack(self, proposal, verdict, tracking):
        """Handle confirmed attack — penalize attacker, reward voters."""
        try:
            attacker_as = verdict["attacker_as"]
            attack_type = verdict["attack_type"]

            if RPKINodeRegistry.should_apply_rating(attacker_as):
                self.rating_system.record_attack(
                    as_number=attacker_as,
                    attack_type=attack_type,
                    attack_details=verdict["attack_details"],
                )

            detector_as = proposal["proposer_as"]
            self.ledger.award_special_reward(
                as_number=detector_as,
                amount=self.rewards["attack_detection"],
                reason="attack_detection",
                details={"verdict_id": verdict["verdict_id"]},
            )

            yes_voters = [
                as_num for as_num, vote_data in tracking["votes"].items()
                if vote_data["vote"] == "YES"
            ]
            for voter_as in yes_voters:
                if voter_as != detector_as:
                    self.ledger.award_special_reward(
                        as_number=voter_as,
                        amount=self.rewards["correct_vote"],
                        reason="correct_attack_vote",
                        details={"verdict_id": verdict["verdict_id"]},
                    )
        except Exception as e:
            logger.error(f"Error handling confirmed attack: {e}")

    def _handle_rejected_attack(self, proposal, verdict, tracking):
        """Handle rejected attack — penalize false accuser."""
        try:
            detector_as = proposal["proposer_as"]
            self.ledger.apply_penalty(
                as_number=detector_as,
                amount=abs(self.rewards["false_accusation"]),
                reason="false_attack_accusation",
                details={"verdict_id": verdict["verdict_id"]},
            )
            no_voters = [
                as_num for as_num, vote_data in tracking["votes"].items()
                if vote_data["vote"] == "NO"
            ]
            for voter_as in no_voters:
                self.ledger.award_special_reward(
                    as_number=voter_as,
                    amount=self.rewards["correct_vote"],
                    reason="correct_attack_vote",
                    details={"verdict_id": verdict["verdict_id"]},
                )
        except Exception as e:
            logger.error(f"Error handling rejected attack: {e}")
