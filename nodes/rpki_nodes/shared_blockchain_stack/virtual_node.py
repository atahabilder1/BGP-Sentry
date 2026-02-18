#!/usr/bin/env python3
"""
VirtualNode - Full blockchain participant for each AS.

RPKI Validator nodes (merger + signer model):
  1. Check if announcement is skippable (same prefix/origin seen recently)
     - Attack: NEVER skip, always process
     - Legitimate duplicate within RPKI_DEDUP_WINDOW: skip entirely
  2. Validate via StayRTR (ROA check)
  3. Add observation to knowledge base
  4. Create transaction -> broadcast to peers for consensus
  5. Peers (signers) vote approve/reject based on their own knowledge base
  6. Merger collects signatures; on PoP threshold (3+): write block to blockchain
  7. Run attack detection (4 types) on committed transaction
  8. If attack detected -> propose attack vote -> majority decides
  9. Award BGPCoin to committer + voters

Non-RPKI Observer nodes:
  1. Check if announcement is skippable (within NONRPKI_DEDUP_WINDOW)
     - Attack: NEVER skip
  2. Run attack detection (4 types)
  3. If attack: record immediately, apply rating penalty
  4. If legitimate: record, track rating
"""

import collections
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

    # Dedup / skip windows (from .env) [seconds]
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
        clock=None,
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
        self.private_key = private_key  # Ed25519 private key (RPKI nodes only)
        self._clock = clock  # SimulationClock (optional)

        # Processing state
        self.processed_count = 0
        self.attack_detections = []
        self.legitimate_count = 0
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # Dedup / skip state — tracks last-processed time per (prefix, origin)
        # If same (prefix, origin) arrives within skip window and is NOT an
        # attack, the node skips it entirely (no validation, no consensus,
        # no blockchain write).  Attacks always bypass this check.
        self.dedup_state: Dict[tuple, float] = {}  # RPKI: (prefix, origin) -> last_ts
        self.last_seen: Dict[tuple, float] = {}     # non-RPKI: (prefix, origin) -> last_ts

        # Results tracking
        self.detection_results = []
        self.trust_score = 100.0 if is_rpki else 50.0

        # Live buffer reference (set during processing, read by dashboard)
        self._buffer: Optional['_PriorityBuffer'] = None

        # Stats for results output
        self.stats = {
            "transactions_created": 0,
            "transactions_deduped": 0,
            "attacks_detected": 0,
            "attacks_written": 0,
            "legitimate_written": 0,
            "consensus_votes_cast": 0,
            "buffer_sampled": 0,
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
        """Process observations in real-time according to BGP timestamps."""
        # Sort by timestamp to ensure correct replay order
        sorted_obs = sorted(self.observations, key=lambda o: o.get("timestamp", 0))

        # Build ingestion buffer — drains at clock pace
        buffer = _PriorityBuffer(max_size=cfg.INGESTION_BUFFER_MAX_SIZE)
        self._buffer = buffer  # expose for dashboard monitoring

        for obs in sorted_obs:
            if not self.running:
                break

            # Wait for real time to catch up to this observation's timestamp
            bgp_ts = obs.get("timestamp", 0)
            if self._clock is not None:
                self._clock.wait_until(bgp_ts)

            is_attack = obs.get("is_attack", False)

            if is_attack:
                # ATTACKS: always process immediately, bypass buffer
                self._process_single(obs, callback)
            else:
                # NORMAL: add to buffer
                if not buffer.try_add(obs):
                    # Buffer full — sample: drop this observation
                    self.stats["buffer_sampled"] += 1
                    self.processed_count += 1
                    continue
                # Drain buffer: process all buffered observations
                while not buffer.empty():
                    buffered_obs = buffer.pop()
                    self._process_single(buffered_obs, callback)

        # Drain any remaining buffered observations
        while not buffer.empty():
            self._process_single(buffer.pop(), callback)

        self.running = False

    def _process_single(self, obs, callback=None):
        """Process a single observation through the appropriate pipeline."""
        self._last_bgp_ts = obs.get("timestamp", 0)
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

    # ------------------------------------------------------------------
    # RPKI Validator processing (merger + signer model)
    # ------------------------------------------------------------------
    def _process_observation_rpki(self, obs: dict) -> dict:
        """
        Full RPKI validator pipeline for a single observation.

        SKIP-EARLY: If this (prefix, origin) was processed within the last
        RPKI_DEDUP_WINDOW seconds AND is not an attack, skip the entire
        pipeline (no validation, no knowledge base, no consensus, no
        blockchain write).  This avoids wasting consensus round-trips on
        duplicate legitimate announcements.
        """
        prefix = obs.get("prefix", "")
        origin_asn = obs.get("origin_asn", 0)
        is_attack = obs.get("is_attack", False)
        label = obs.get("label", "LEGITIMATE")
        timestamp = obs.get("timestamp", datetime.now().isoformat())

        result = self._make_base_result(obs)

        # ── STEP 0: Early skip for non-attack duplicates ──
        # Attacks ALWAYS proceed.  Legitimate duplicates within the skip
        # window are dropped before any expensive work happens.
        dedup_key = (prefix, origin_asn)
        if not is_attack and dedup_key in self.dedup_state:
            elapsed = time.time() - self.dedup_state[dedup_key]
            if elapsed < self.RPKI_DEDUP_WINDOW:
                result["action"] = "skipped_dedup"
                self.stats["transactions_deduped"] += 1
                self.detection_results.append(result)
                return result

        # ── STEP 1: Add to P2P pool knowledge base ──
        # So this node can vote on other nodes' transactions about the
        # same prefix.
        if self.p2p_pool is not None:
            self.p2p_pool.add_bgp_observation(
                ip_prefix=prefix,
                sender_asn=origin_asn,
                timestamp=timestamp,
                trust_score=100.0,
                is_attack=is_attack,
            )

        # ── STEP 2: RPKI validation via StayRTR ──
        validation = {"valid": True, "status": "not_checked"}
        if self.rpki_validator is not None:
            validation = self.rpki_validator.validate(obs)

        result["rpki_validation"] = validation.get("status", "unknown")

        # ── STEP 3: Attack detection (all 4 types) ──
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

        # ── STEP 4: Create transaction and broadcast for consensus ──
        # This node acts as MERGER: collects signatures from SIGNER peers.
        # Signers vote approve/reject based on their knowledge base.
        # On 3+ approve signatures → block is committed to blockchain.
        #
        # PIPELINED: broadcast runs in a background thread so this node
        # can immediately proceed to the next observation.  Consensus
        # votes arrive asynchronously and the commit happens whenever
        # the threshold is reached (or timeout fires).
        if self.p2p_pool is not None:
            transaction = self._create_transaction(obs, validation, detected_attacks)
            threading.Thread(
                target=self.p2p_pool.broadcast_transaction,
                args=(transaction,),
                daemon=True,
            ).start()
            self.stats["transactions_created"] += 1
            result["action"] = "transaction_broadcast"
            result["transaction_id"] = transaction["transaction_id"]
        else:
            result["action"] = "no_p2p_pool"

        # ── STEP 5: Update dedup state ──
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
        """
        Non-RPKI observer pipeline: detect attacks + track rating.

        SKIP-EARLY: If this (prefix, origin) was seen within the last
        NONRPKI_DEDUP_WINDOW seconds AND is not an attack, skip entirely.
        Attacks always proceed to detection and rating.
        """
        prefix = obs.get("prefix", "")
        origin_asn = obs.get("origin_asn", 0)
        is_attack = obs.get("is_attack", False)
        label = obs.get("label", "LEGITIMATE")

        result = self._make_base_result(obs)

        # ── STEP 0: Early skip for non-attack duplicates ──
        dedup_key = (prefix, origin_asn)
        if not is_attack and dedup_key in self.last_seen:
            elapsed = time.time() - self.last_seen[dedup_key]
            if elapsed < self.NONRPKI_DEDUP_WINDOW:
                result["action"] = "skipped_throttle"
                self.stats["transactions_deduped"] += 1
                self.detection_results.append(result)
                return result

        # ── STEP 1: Attack detection (all 4 types) ──
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

            # Rating updates are handled exclusively by RPKI consensus to
            # avoid duplicate penalties (non-RPKI nodes are passive observers).

            result["action"] = "attack_detected_offchain"
            self.detection_results.append(result)
            return result

        # ── STEP 2: Record legitimate announcement ──
        self.last_seen[dedup_key] = time.time()
        self.legitimate_count += 1
        self.stats["legitimate_written"] += 1

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
        buf = self._buffer
        buf_queued = len(buf._queue) if buf is not None else 0
        buf_max = buf.max_size if buf is not None else 0
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
            "last_bgp_timestamp": getattr(self, "_last_bgp_ts", None),
            "buffer_queued": buf_queued,
            "buffer_max": buf_max,
        }


class _PriorityBuffer:
    """Fixed-size buffer for normal BGP announcements.

    Attacks bypass this buffer entirely.

    Sampling strategy:
      - Below 60% capacity: accept all non-attack observations.
      - 60-100% capacity: probabilistic sampling — the closer to full,
        the higher the drop probability.  At 60% the drop chance is 0%,
        ramping linearly to 100% at max_size.
      - At 100%: always drop (hard cap).

    This keeps the buffer from ever completely filling while ensuring
    attack observations are never dropped (they bypass the buffer).
    """

    SAMPLE_THRESHOLD = 0.6  # start sampling at 60% full

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._queue: collections.deque = collections.deque()
        self._rng = __import__('random').Random()

    def try_add(self, obs) -> bool:
        """Add observation to buffer. Returns False if sampled out."""
        fill = len(self._queue) / self.max_size if self.max_size > 0 else 1.0

        if fill >= 1.0:
            # Hard cap — buffer full
            return False

        if fill >= self.SAMPLE_THRESHOLD:
            # Linear ramp: 0% drop at threshold, 100% drop at max_size
            drop_prob = (fill - self.SAMPLE_THRESHOLD) / (1.0 - self.SAMPLE_THRESHOLD)
            if self._rng.random() < drop_prob:
                return False

        self._queue.append(obs)
        return True

    def pop(self):
        return self._queue.popleft()

    def empty(self) -> bool:
        return len(self._queue) == 0
