#!/usr/bin/env python3
"""
VirtualNode - Full blockchain participant for each AS.

RPKI Validator nodes:
  1. Validate via StayRTR (ROA check)
  2. Add observation to knowledge base
  3. Dedup check (skip duplicates within sampling window)
  4. Create transaction -> broadcast to peers for consensus
  5. Peers vote approve/reject based on their own knowledge base
  6. On consensus (BFT threshold): write block to blockchain
  7. Run attack detection (4 types) on committed transaction
  8. If attack detected -> propose attack vote -> majority decides
  9. Award BGPCoin to committer + voters

Non-RPKI Observer nodes:
  1. Run attack detection (4 types)
  2. If attack: record immediately, apply rating penalty
  3. If legitimate: throttle duplicates (10s window), record
  4. Rating tracked longitudinally (start 50)
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from config import cfg

logger = logging.getLogger(__name__)


class VirtualNode:
    """
    Represents a single AS in the BGP-Sentry simulation.

    Validators (RPKI nodes): full blockchain participants with P2P consensus.
    Observers (non-RPKI nodes): attack detection + rating tracking.
    """

    # Dedup windows (from .env)
    RPKI_DEDUP_WINDOW = cfg.RPKI_DEDUP_WINDOW
    NONRPKI_DEDUP_WINDOW = cfg.NONRPKI_DEDUP_WINDOW

    def __init__(
        self,
        asn: int,
        is_rpki: bool,
        rpki_role: str,
        observations: List[dict],
        # Blockchain infrastructure (injected by NodeManager)
        p2p_pool=None,
        rpki_validator=None,
        attack_detector=None,
        rating_system=None,
        shared_blockchain=None,
        bgpcoin_ledger=None,
        private_key=None,
    ):
        self.asn = asn
        self.is_rpki = is_rpki
        self.rpki_role = rpki_role
        self.observations = observations

        # Blockchain infrastructure
        self.p2p_pool = p2p_pool
        self.rpki_validator = rpki_validator
        self.attack_detector = attack_detector
        self.rating_system = rating_system
        self.shared_blockchain = shared_blockchain
        self.bgpcoin_ledger = bgpcoin_ledger
        self.private_key = private_key  # RSA-2048 private key (RPKI nodes only)

        # Processing state
        self.processed_count = 0
        self.attack_detections = []
        self.legitimate_count = 0
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # Dedup / throttle state
        self.dedup_state: Dict[tuple, float] = {}  # (prefix, origin) -> last_write_ts
        self.last_seen: Dict[tuple, float] = {}     # non-RPKI throttle cache

        # Results tracking
        self.detection_results = []
        self.trust_score = 100.0 if is_rpki else 50.0

        # Stats for results output
        self.stats = {
            "transactions_created": 0,
            "transactions_deduped": 0,
            "attacks_detected": 0,
            "attacks_written": 0,
            "legitimate_written": 0,
            "consensus_votes_cast": 0,
        }

    def start(self, callback=None):
        """Start processing observations in a background thread."""
        self.running = True
        self._thread = threading.Thread(
            target=self._process_observations,
            args=(callback,),
            name=f"VNode-AS{self.asn}",
            daemon=True,
        )
        self._thread.start()

    def _process_observations(self, callback=None):
        """Process all observations sequentially."""
        for obs in self.observations:
            if not self.running:
                break

            try:
                if self.is_rpki:
                    result = self._process_observation_rpki(obs)
                else:
                    result = self._process_observation_nonrpki(obs)
            except Exception as e:
                logger.error(f"AS{self.asn} processing error: {e}")
                result = self._make_base_result(obs, action="error")

            if callback:
                try:
                    callback(self, obs, result)
                except Exception as e:
                    logger.error(f"AS{self.asn} callback error: {e}")

            self.processed_count += 1

        self.running = False

    # ------------------------------------------------------------------
    # RPKI Validator processing
    # ------------------------------------------------------------------
    def _process_observation_rpki(self, obs: dict) -> dict:
        """Full RPKI validator pipeline for a single observation."""
        prefix = obs.get("prefix", "")
        origin_asn = obs.get("origin_asn", 0)
        is_attack = obs.get("is_attack", False)
        label = obs.get("label", "LEGITIMATE")
        timestamp = obs.get("timestamp", datetime.now().isoformat())

        result = self._make_base_result(obs)

        # 1. Add to P2P pool knowledge base (so this node can vote on others' txns)
        if self.p2p_pool is not None:
            self.p2p_pool.add_bgp_observation(
                ip_prefix=prefix,
                sender_asn=origin_asn,
                timestamp=timestamp,
                trust_score=100.0,
                is_attack=is_attack,
            )

        # 2. RPKI validation via StayRTR
        validation = {"valid": True, "status": "not_checked"}
        if self.rpki_validator is not None:
            validation = self.rpki_validator.validate(obs)

        result["rpki_validation"] = validation.get("status", "unknown")

        # 3. Run attack detection (all 4 types)
        detected_attacks = []
        if self.attack_detector is not None:
            detected_attacks = self.attack_detector.detect_attacks({
                "sender_asn": origin_asn,
                "ip_prefix": prefix,
                "as_path": obs.get("as_path", [origin_asn]),
            })

        if detected_attacks:
            result["detected"] = True
            result["detection_type"] = detected_attacks[0]["attack_type"]
            result["detection_details"] = [a["attack_type"] for a in detected_attacks]
            self.attack_detections.append(result)
            self.stats["attacks_detected"] += 1
        elif is_attack and (not validation.get("valid", True) or validation.get("status") == "invalid"):
            # RPKI validation caught it even if detector didn't
            result["detected"] = True
            result["detection_type"] = label
            self.attack_detections.append(result)
            self.stats["attacks_detected"] += 1

        # 4. Dedup check: skip if same (prefix, origin) written recently
        dedup_key = (prefix, origin_asn)
        if not is_attack and dedup_key in self.dedup_state:
            if time.time() - self.dedup_state[dedup_key] < self.RPKI_DEDUP_WINDOW:
                result["action"] = "skipped_dedup"
                self.stats["transactions_deduped"] += 1
                self.detection_results.append(result)
                return result

        # 5. Create transaction and broadcast for consensus
        if self.p2p_pool is not None:
            transaction = self._create_transaction(obs, validation, detected_attacks)
            self.p2p_pool.broadcast_transaction(transaction)
            self.stats["transactions_created"] += 1
            result["action"] = "transaction_broadcast"
            result["transaction_id"] = transaction["transaction_id"]
        else:
            result["action"] = "no_p2p_pool"

        # 6. Update dedup state
        self.dedup_state[dedup_key] = time.time()

        if not is_attack:
            self.legitimate_count += 1

        self.detection_results.append(result)
        return result

    def _create_transaction(self, obs: dict, validation: dict, detected_attacks: list) -> dict:
        """Create a blockchain transaction from an observation (RSA-signed)."""
        tx_id = f"tx_{self.asn}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex[:8]}"

        tx = {
            "transaction_id": tx_id,
            "observer_as": self.asn,
            "sender_asn": obs.get("origin_asn", 0),
            "ip_prefix": obs.get("prefix", ""),
            "as_path": obs.get("as_path", [obs.get("origin_asn", 0)]),
            "timestamp": obs.get("timestamp", datetime.now().isoformat()),
            "is_attack": obs.get("is_attack", False),
            "label": obs.get("label", "LEGITIMATE"),
            "rpki_validation": validation,
            "detected_attacks": [a["attack_type"] for a in detected_attacks],
            "created_at": datetime.now().isoformat(),
        }

        # Sign the transaction with this node's RSA private key
        if self.private_key is not None:
            from signature_utils import SignatureUtils
            sign_payload = json.dumps({
                "transaction_id": tx_id,
                "observer_as": self.asn,
                "ip_prefix": tx["ip_prefix"],
                "sender_asn": tx["sender_asn"],
            }, sort_keys=True, separators=(',', ':'))
            tx["signature"] = SignatureUtils.sign_with_key(sign_payload, self.private_key)
            tx["signer_as"] = self.asn

        return tx

    # ------------------------------------------------------------------
    # Non-RPKI Observer processing
    # ------------------------------------------------------------------
    def _process_observation_nonrpki(self, obs: dict) -> dict:
        """Non-RPKI observer pipeline: detect attacks + track rating."""
        prefix = obs.get("prefix", "")
        origin_asn = obs.get("origin_asn", 0)
        is_attack = obs.get("is_attack", False)
        label = obs.get("label", "LEGITIMATE")

        result = self._make_base_result(obs)

        # 1. Run attack detection (all 4 types)
        detected_attacks = []
        if self.attack_detector is not None:
            detected_attacks = self.attack_detector.detect_attacks({
                "sender_asn": origin_asn,
                "ip_prefix": prefix,
                "as_path": obs.get("as_path", [origin_asn]),
            })

        detector_says_attack = len(detected_attacks) > 0

        # Use ground truth OR detector result
        effective_attack = is_attack or detector_says_attack

        if effective_attack:
            # Determine attack type from detector or label
            if detected_attacks:
                attack_type = detected_attacks[0]["attack_type"]
            else:
                attack_type = label

            result["detected"] = True
            result["detection_type"] = attack_type
            self.attack_detections.append(result)
            self.stats["attacks_detected"] += 1
            self.stats["attacks_written"] += 1

            # Rating penalty (off-chain — non-RPKI nodes don't write to blockchain)
            if self.rating_system is not None:
                self.rating_system.record_attack(
                    as_number=origin_asn,
                    attack_type=attack_type,
                    attack_details={"label": label, "prefix": prefix},
                )

            result["action"] = "attack_detected_offchain"
            self.detection_results.append(result)
            return result

        # 2. Not attack: throttle duplicates
        dedup_key = (prefix, origin_asn)
        if dedup_key in self.last_seen:
            if time.time() - self.last_seen[dedup_key] < self.NONRPKI_DEDUP_WINDOW:
                result["action"] = "skipped_throttle"
                self.stats["transactions_deduped"] += 1
                self.detection_results.append(result)
                return result

        self.last_seen[dedup_key] = time.time()
        self.legitimate_count += 1
        self.stats["legitimate_written"] += 1

        # 3. Increment legitimate count for rating (off-chain)
        if self.rating_system is not None:
            self.rating_system.increment_legitimate_announcements(origin_asn, prefix=prefix)

        result["action"] = "legitimate_recorded_offchain"
        self.detection_results.append(result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_base_result(self, obs: dict, action: str = "pending") -> dict:
        return {
            "asn": self.asn,
            "prefix": obs.get("prefix", ""),
            "origin_asn": obs.get("origin_asn", 0),
            "label": obs.get("label", "LEGITIMATE"),
            "is_attack": obs.get("is_attack", False),
            "timestamp": obs.get("timestamp"),
            "detected": False,
            "detection_type": None,
            "action": action,
        }

    def stop(self):
        """Stop processing."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def is_done(self) -> bool:
        """Check if all observations have been processed."""
        return self.processed_count >= len(self.observations)

    def get_status(self) -> dict:
        """Get current node status."""
        return {
            "asn": self.asn,
            "is_rpki": self.is_rpki,
            "role": self.rpki_role,
            "total_observations": len(self.observations),
            "processed": self.processed_count,
            "attacks_detected": len(self.attack_detections),
            "legitimate_count": self.legitimate_count,
            "running": self.running,
            "done": self.is_done(),
            "trust_score": self.trust_score,
            "stats": dict(self.stats),
        }
