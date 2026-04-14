#!/usr/bin/env python3
"""
AsyncP2PTransactionPool - Pure asyncio replacement for P2PTransactionPool.

Eliminates all threading:
  - threading.Lock   -> asyncio.Lock
  - threading.Event  -> asyncio.Event
  - threading.Thread -> asyncio.create_task
  - time.sleep       -> asyncio.sleep

Same consensus logic, same vote model (approve / no_knowledge / reject),
same blockchain write path.  Only the concurrency model changes.

At 400 nodes the threaded version spawns 2,400+ threads (6 per node)
which causes GIL contention and CPU starvation.  This version runs
all 400 nodes as lightweight coroutines on a single event loop.
"""

import asyncio
import json
import logging
import math
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from blockchain_interface import BlockchainInterface
from bgpcoin_ledger import BGPCoinLedger
from rpki_node_registry import RPKINodeRegistry
from config import cfg

sys.path.insert(0, str(Path(__file__).parent.parent / "network_stack"))
from relevant_neighbor_cache import RelevantNeighborCache


class AsyncP2PTransactionPool:
    """
    Async peer-to-peer transaction pool with consensus voting.

    Drop-in replacement for P2PTransactionPool.  Same public API
    but all methods are coroutines and background work runs as
    asyncio tasks instead of daemon threads.
    """

    MAX_BROADCAST_PEERS = cfg.P2P_MAX_BROADCAST_PEERS

    def __init__(self, as_number, base_port=8000,
                 blockchain_interface=None, bgpcoin_ledger=None,
                 private_key=None, public_key_registry=None,
                 prefix_ownership_state=None):
        self.as_number = as_number
        self.my_port = base_port + as_number

        # Per-node cryptographic keys (Ed25519)
        self.private_key = private_key
        self.public_key_registry = public_key_registry or {}
        self.prefix_ownership_state = prefix_ownership_state

        # Peer RPKI nodes
        self.peer_nodes = RPKINodeRegistry.get_peer_nodes(self.as_number)

        # Blockchain interface
        if blockchain_interface is not None:
            self.blockchain = blockchain_interface
        else:
            as_formatted = f"as{self.as_number:02d}"
            blockchain_path = f"nodes/rpki_nodes/{as_formatted}/blockchain_node/blockchain_data/chain"
            self.blockchain = BlockchainInterface(blockchain_path)

        # Async concurrency primitives (replace threading.Lock / Event)
        self.lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._new_tx_event = asyncio.Event()

        self.running = False
        self.draining = False  # True = stop creating new txns, but keep consensus alive
        self.logger = logging.getLogger(f"AsyncP2P-AS{self.as_number}")

        # Transaction voting tracking
        self.pending_votes: Dict[str, dict] = {}
        self.committed_transactions: Dict[str, float] = {}

        # Network-wide dedup: track (prefix, origin) pairs that already have
        # a pending vote_request from another node. Prevents redundant TXs.
        self._pending_event_keys: set = set()  # (prefix, origin) → already proposed
        self.total_nodes = RPKINodeRegistry.get_node_count()
        self.consensus_threshold = RPKINodeRegistry.get_consensus_threshold()

        # Knowledge base
        self.knowledge_base: list = []
        self.knowledge_window_seconds = cfg.KNOWLEDGE_WINDOW_SECONDS
        self.cleanup_interval = cfg.KNOWLEDGE_CLEANUP_INTERVAL

        # Timeouts
        self.REGULAR_TIMEOUT = cfg.P2P_REGULAR_TIMEOUT
        self.ATTACK_TIMEOUT = cfg.P2P_ATTACK_TIMEOUT

        # Sampling
        self.SAMPLING_WINDOW_SECONDS = cfg.SAMPLING_WINDOW_SECONDS
        self.last_seen_cache: dict = {}

        # No file persistence for in-memory simulation
        self.knowledge_base_file = None
        self.last_seen_cache_file = None

        # BGPCoin
        if bgpcoin_ledger is not None:
            self.bgpcoin_ledger = bgpcoin_ledger
        else:
            self.bgpcoin_ledger = BGPCoinLedger(ledger_path=self.blockchain.state_dir)

        self.first_commit_tracker: dict = {}

        # Governance & attack consensus (initialized in start_p2p_server)
        self.governance = None
        self.attack_consensus = None

        # Neighbor cache
        network_stack_path = Path(__file__).parent.parent / "network_stack"
        self.neighbor_cache = RelevantNeighborCache(
            cache_path=str(network_stack_path),
            my_as_number=self.as_number,
        )

        # Batching
        self.batch_size = cfg.BATCH_SIZE
        self.batch_timeout = cfg.BATCH_TIMEOUT
        self._batch_queue: list = []
        self._batch_event = asyncio.Event()

        # Background task handles (for cleanup on stop)
        self._background_tasks: list = []

    async def start_p2p_server(self, attack_detector=None, rating_system=None):
        """Register with async message bus and start background tasks."""
        self.running = True

        # Register with async message bus
        from message_bus_async import AsyncMessageBus
        bus = AsyncMessageBus.get_instance()
        bus.register(self.as_number, self._handle_bus_message)
        self.logger.info(f"Async P2P server registered (AS{self.as_number})")

        # Initialize governance
        from governance_system import GovernanceSystem
        self.governance = GovernanceSystem(
            as_number=self.as_number,
            bgpcoin_ledger=self.bgpcoin_ledger,
            p2p_pool=self,
            governance_path=self.blockchain.state_dir,
        )

        # Initialize attack consensus (async version)
        if attack_detector is None:
            from attack_detector import AttackDetector
            attack_detector = AttackDetector(
                roa_database_path=str(self.blockchain.state_dir / "roa_database.json"),
                as_relationships_path=str(self.blockchain.state_dir / "as_relationships.json"),
            )
        if rating_system is None:
            from nonrpki_rating import NonRPKIRatingSystem
            rating_system = NonRPKIRatingSystem(rating_path=str(self.blockchain.state_dir))

        from attack_consensus_async import AsyncAttackConsensus
        self.attack_consensus = AsyncAttackConsensus(
            as_number=self.as_number,
            attack_detector=attack_detector,
            rating_system=rating_system,
            bgpcoin_ledger=self.bgpcoin_ledger,
            p2p_pool=self,
            blockchain_dir=self.blockchain.blockchain_dir,
        )

        # Start background coroutines (replace 6 daemon threads)
        self._background_tasks = [
            asyncio.create_task(self._cleanup_old_observations()),
            asyncio.create_task(self._cleanup_timed_out_transactions()),
            asyncio.create_task(self._cleanup_old_committed_transactions()),
            asyncio.create_task(self._cleanup_last_seen_cache_loop()),
        ]
        if self.batch_size > 1:
            self._background_tasks.append(
                asyncio.create_task(self._batch_flush_loop())
            )
            self.logger.info(
                f"Batching enabled: size={self.batch_size}, timeout={self.batch_timeout}s"
            )

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------
    async def _handle_bus_message(self, message: dict):
        """Handle incoming message from AsyncMessageBus.

        During drain mode, vote responses and block replications are still
        processed so that in-flight consensus rounds complete naturally.
        Only new vote *requests* (which would start new rounds) are rejected.
        """
        if not self.running:
            return  # Pool fully stopped — discard everything
        try:
            msg_type = message["type"]
            if msg_type == "vote_request":
                if self.draining:
                    return  # Don't start new consensus rounds during drain
                await self._handle_vote_request(message)
            elif msg_type == "vote_response":
                await self._handle_vote_response(message)
            elif msg_type == "block_replicate":
                self._handle_block_replicate(message)
            elif msg_type == "governance_proposal":
                if self.governance:
                    self.governance.handle_proposal_message(message)
            elif msg_type == "governance_vote":
                if self.governance:
                    self.governance.handle_vote_message(message)
            elif msg_type == "attack_proposal":
                if self.attack_consensus:
                    await self.attack_consensus.handle_attack_proposal(message)
            elif msg_type == "attack_vote":
                if self.attack_consensus:
                    await self.attack_consensus.handle_attack_vote(message)
        except Exception as e:
            self.logger.error(f"Error handling bus message: {e}")

    async def _handle_vote_request(self, message: dict):
        """Handle incoming vote request — validate and respond."""
        transaction = message["transaction"]
        from_as = message["from_as"]

        # Record that this (prefix, origin) is already being proposed by another node
        # This prevents us from creating a redundant TX for the same event
        event_key = (transaction.get("ip_prefix"), transaction.get("sender_asn"))
        self._pending_event_keys.add(event_key)

        vote = await self._validate_transaction(transaction)
        await self._send_vote_to_node(from_as, transaction["transaction_id"], vote)

    async def _handle_vote_response(self, message: dict):
        """Handle incoming vote response and check consensus."""
        tx_id = message["transaction_id"]
        vote = message["vote"]
        from_as = message["from_as"]

        should_commit = False

        async with self.lock:
            if tx_id not in self.pending_votes:
                return
            if tx_id in self.committed_transactions:
                return

            existing_voters = [v["from_as"] for v in self.pending_votes[tx_id]["votes"]]
            if from_as in existing_voters:
                return  # Duplicate vote
            if len(existing_voters) >= self.total_nodes:
                return  # Overflow

            self.pending_votes[tx_id]["votes"].append({
                "from_as": from_as,
                "vote": vote,
                "timestamp": message.get("timestamp"),
            })

            votes = self.pending_votes[tx_id]["votes"]
            approve_votes = sum(1 for v in votes if v["vote"] == "approve")

            if approve_votes >= self.consensus_threshold:
                self.committed_transactions[tx_id] = datetime.now().timestamp()
                should_commit = True

                evt = self.pending_votes[tx_id].get("consensus_event")
                if evt is not None:
                    evt.set()

        if should_commit:
            await self._commit_to_blockchain(tx_id)

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------
    async def broadcast_transaction(self, transaction: dict):
        """Broadcast transaction to peers for consensus voting."""
        tx_id = transaction["transaction_id"]
        sender_asn = transaction.get("sender_asn")
        ip_prefix = transaction.get("ip_prefix")

        # Network-wide dedup: if another node already proposed a TX for this
        # (prefix, origin), don't create a redundant TX. Our vote was already
        # cast when we received their vote_request.
        event_key = (ip_prefix, sender_asn)
        if event_key in self._pending_event_keys:
            self.logger.debug(f"Skipping redundant TX for {ip_prefix}/AS{sender_asn} — already proposed by peer")
            return

        # Mark this event as proposed (by us)
        self._pending_event_keys.add(event_key)

        # Capacity check + register must be atomic to prevent races
        oldest_to_evict = None
        async with self.lock:
            if len(self.pending_votes) >= cfg.PENDING_VOTES_MAX_CAPACITY:
                oldest_to_evict = min(
                    self.pending_votes,
                    key=lambda k: self.pending_votes[k]["created_at"]
                )

        # Force-timeout outside lock (it acquires lock internally)
        if oldest_to_evict:
            self.logger.warning(
                f"pending_votes at capacity ({cfg.PENDING_VOTES_MAX_CAPACITY}), "
                f"force-timing-out oldest: {oldest_to_evict}"
            )
            await self._handle_timed_out_transaction(oldest_to_evict)

        self.pending_votes[tx_id] = {
            "transaction": transaction,
            "votes": [],
            "needed": self.consensus_threshold,
            "created_at": datetime.now(),
            "is_attack": transaction.get("is_attack", False),
            "consensus_event": asyncio.Event(),
        }

        # Adaptive peer selection: scale with network size
        # Goal: maximize chance of getting "approve" votes by asking
        # peers most likely to have knowledge, while scaling sublinearly.
        #
        # Broadcast size: max(MIN_SIGNATURES * 2, sqrt(N))
        #   - At  33 nodes: max(6, 5.7)  =  6 peers
        #   - At 104 nodes: max(6, 10.2) = 10 peers
        #   - At 254 nodes: max(6, 15.9) = 16 peers
        #   - At 500 nodes: max(6, 22.4) = 22 peers
        #
        # Priority: relevant neighbors first (topology-aware),
        # then fill remaining slots with random peers for diversity.
        n_peers = len(self.peer_nodes)
        broadcast_size = max(
            self.consensus_threshold * 2,
            int(math.sqrt(n_peers)),
        )
        broadcast_size = min(broadcast_size, n_peers)  # never exceed total

        # Layer 1: relevant neighbors (most likely to have knowledge)
        relevant_neighbors = self.neighbor_cache.get_relevant_neighbors(sender_asn)
        relevant_peers = {
            peer_as: (host, port)
            for peer_as, (host, port) in self.peer_nodes.items()
            if peer_as in relevant_neighbors
        }

        # If too many relevant neighbors, sample down
        if len(relevant_peers) > broadcast_size:
            relevant_peers = dict(random.sample(list(relevant_peers.items()), broadcast_size))

        # Layer 2: fill remaining slots with random non-relevant peers
        target_peers = dict(relevant_peers)
        remaining_slots = broadcast_size - len(target_peers)
        if remaining_slots > 0:
            other_peers = [
                (peer_as, addr) for peer_as, addr in self.peer_nodes.items()
                if peer_as not in target_peers
            ]
            if other_peers:
                fill = random.sample(other_peers, min(remaining_slots, len(other_peers)))
                target_peers.update(dict(fill))

        # Send vote requests
        for peer_as, (host, port) in target_peers.items():
            await self._send_vote_request_to_node(peer_as, host, port, transaction)

        self.logger.debug(f"Broadcast {tx_id} to {len(target_peers)} peers")
        self._new_tx_event.set()

    async def _send_vote_request_to_node(self, peer_as, host, port, transaction):
        """Send vote request via async message bus."""
        message = {
            "type": "vote_request",
            "from_as": self.as_number,
            "transaction": transaction,
            "timestamp": datetime.now().isoformat(),
        }
        from message_bus_async import AsyncMessageBus
        await AsyncMessageBus.get_instance().send(self.as_number, peer_as, message)

    async def _send_vote_to_node(self, target_as, transaction_id, vote):
        """Send vote response via async message bus."""
        if target_as not in self.peer_nodes:
            return
        message = {
            "type": "vote_response",
            "from_as": self.as_number,
            "transaction_id": transaction_id,
            "vote": vote,
            "timestamp": datetime.now().isoformat(),
            "signature": self._sign_vote(transaction_id, vote),
        }
        from message_bus_async import AsyncMessageBus
        await AsyncMessageBus.get_instance().send(self.as_number, target_as, message)

    # ------------------------------------------------------------------
    # Block replication
    # ------------------------------------------------------------------
    def _handle_block_replicate(self, message: dict):
        """Handle replicated block from a peer."""
        block = message.get("block")
        if block is not None:
            self.blockchain.append_replicated_block(block)

    async def _replicate_block_to_peers(self, block):
        """Broadcast committed block to gossip subset."""
        if block is None:
            return
        from message_bus_async import AsyncMessageBus
        bus = AsyncMessageBus.get_instance()
        message = {
            "type": "block_replicate",
            "from_as": self.as_number,
            "block": block,
        }
        all_peers = [n for n in self.peer_nodes if n != self.as_number]
        gossip_size = max(3, int(math.sqrt(len(all_peers))))
        targets = random.sample(all_peers, min(gossip_size, len(all_peers)))
        await bus.broadcast(self.as_number, message, targets=targets)

    # ------------------------------------------------------------------
    # Vote signing
    # ------------------------------------------------------------------
    def _sign_vote(self, transaction_id, vote):
        """Sign a consensus vote with Ed25519 private key."""
        if self.private_key is None:
            return None
        from signature_utils import SignatureUtils
        payload = json.dumps({
            "transaction_id": transaction_id,
            "voter_as": self.as_number,
            "vote": vote,
        }, sort_keys=True, separators=(',', ':'))
        return SignatureUtils.sign_with_key(payload, self.private_key)

    # ------------------------------------------------------------------
    # Knowledge base & validation
    # ------------------------------------------------------------------
    def add_bgp_observation(self, ip_prefix, sender_asn, timestamp,
                            trust_score, is_attack=False):
        """Add BGP observation to knowledge base (sync — called from node pipeline)."""
        if not is_attack:
            if self._check_recent_announcement_in_cache(ip_prefix, sender_asn):
                return False

        # Capacity check
        if len(self.knowledge_base) >= cfg.KNOWLEDGE_BASE_MAX_SIZE:
            trim_count = len(self.knowledge_base) - cfg.KNOWLEDGE_BASE_MAX_SIZE + 1
            self.knowledge_base = self.knowledge_base[trim_count:]

        observation = {
            "ip_prefix": ip_prefix,
            "sender_asn": sender_asn,
            "timestamp": timestamp,
            "trust_score": trust_score,
            "observed_at": datetime.now().isoformat(),
            "is_attack": is_attack,
        }
        self.knowledge_base.append(observation)

        self.neighbor_cache.record_observation(
            origin_as=sender_asn,
            observed_by_rpki_as=self.as_number,
        )
        return True

    def _check_recent_announcement_in_cache(self, ip_prefix, sender_asn):
        """Check if same announcement was seen within sampling window."""
        cache_key = (ip_prefix, sender_asn)
        current_time = datetime.now().timestamp()
        cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS
        if cache_key in self.last_seen_cache:
            if self.last_seen_cache[cache_key] > cutoff_time:
                return True
        return False

    def _update_last_seen_cache(self, ip_prefix, sender_asn):
        """Update last seen timestamp."""
        if len(self.last_seen_cache) >= cfg.LAST_SEEN_CACHE_MAX_SIZE:
            evict_count = max(1, cfg.LAST_SEEN_CACHE_MAX_SIZE // 10)
            sorted_keys = sorted(self.last_seen_cache, key=self.last_seen_cache.get)
            for k in sorted_keys[:evict_count]:
                del self.last_seen_cache[k]
        self.last_seen_cache[(ip_prefix, sender_asn)] = datetime.now().timestamp()

    @staticmethod
    def _parse_timestamp(ts) -> datetime:
        """Parse timestamp (int/float/ISO string)."""
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                from dateutil import parser
                return parser.parse(ts)
        return datetime.now()

    def _check_knowledge_base(self, transaction) -> str:
        """Multi-source vote decision: KB → Blockchain State → no_knowledge.

        Same logic as sync version — three independent approve sources.
        """
        ip_prefix = transaction.get("ip_prefix")
        sender_asn = transaction.get("sender_asn")
        tx_timestamp = transaction.get("timestamp")

        if not all([ip_prefix, sender_asn, tx_timestamp]):
            return "no_knowledge"

        tx_time = self._parse_timestamp(tx_timestamp)
        knowledge_snapshot = list(self.knowledge_base)

        # ── Source 1: Knowledge Base ──
        prefix_seen_different_origin = False
        for obs in knowledge_snapshot:
            if obs["ip_prefix"] != ip_prefix:
                continue
            obs_time = self._parse_timestamp(obs["timestamp"])
            time_diff = abs((tx_time - obs_time).total_seconds())
            if time_diff > self.knowledge_window_seconds:
                continue

            if obs["sender_asn"] == sender_asn:
                return "approve"  # KB confirms

            prefix_seen_different_origin = True

        # ── Source 2: Blockchain State (ROA bootstrap + consensus history) ──
        if self.prefix_ownership_state is not None:
            ownership = self.prefix_ownership_state.get_ownership(ip_prefix)
            if ownership is not None:
                if ownership["established_origin"] == sender_asn:
                    return "approve"  # Blockchain state confirms
                else:
                    prefix_seen_different_origin = True

        if prefix_seen_different_origin:
            return "reject"
        return "no_knowledge"

    async def _validate_transaction(self, transaction):
        """Validate transaction against knowledge base."""
        try:
            vote = self._check_knowledge_base(transaction)
            return vote
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return "no_knowledge"

    # ------------------------------------------------------------------
    # Commit path
    # ------------------------------------------------------------------
    async def _commit_to_blockchain(self, transaction_id):
        """Commit approved transaction to blockchain."""
        try:
            if transaction_id not in self.pending_votes:
                return

            vote_data = self.pending_votes[transaction_id]
            transaction = vote_data["transaction"]
            # Snapshot votes — do NOT share the mutable list with vote_data,
            # otherwise late-arriving votes would mutate the block's content
            # after its hash has been computed, causing chain invalidity.
            transaction["signatures"] = list(vote_data["votes"])
            transaction["consensus_reached"] = True
            transaction["consensus_status"] = "CONFIRMED"
            transaction["signature_count"] = len(transaction["signatures"])

            if self.batch_size > 1:
                self._batch_queue.append((transaction, vote_data, transaction_id))
                self._batch_event.set()
                del self.pending_votes[transaction_id]
                return

            await self._write_single_transaction(transaction, vote_data, transaction_id)

        except Exception as e:
            self.logger.error(f"Error committing transaction: {e}")

    async def _write_single_transaction(self, transaction, vote_data, transaction_id):
        """Write a single transaction as its own block."""
        success = self.blockchain.add_transaction_to_blockchain(transaction)
        if success:
            self.logger.info(
                f"⛓️  Transaction {transaction_id} committed with "
                f"{len(vote_data['votes'])} signatures"
            )
            committed_block = self.blockchain.get_last_block()
            if committed_block:
                await self._replicate_block_to_peers(committed_block)

            if not transaction.get('is_attack', False):
                self._update_last_seen_cache(
                    transaction.get('ip_prefix'),
                    transaction.get('sender_asn'),
                )

            self._award_bgpcoin_rewards(transaction_id, vote_data)

            # Update prefix ownership state (CONFIRMED = strengthens mapping)
            if self.prefix_ownership_state is not None:
                self.prefix_ownership_state.update_from_confirmed(
                    prefix=transaction.get("ip_prefix", ""),
                    origin_asn=transaction.get("sender_asn", 0),
                    timestamp=transaction.get("timestamp", 0),
                )

            # Trigger attack detection
            asyncio.create_task(
                self._trigger_attack_detection(transaction, transaction_id)
            )

            if transaction_id in self.pending_votes:
                del self.pending_votes[transaction_id]
        else:
            self.logger.error(f"Failed to write transaction {transaction_id} to blockchain")
            # Remove from committed so timeout handler can retry
            async with self.lock:
                self.committed_transactions.pop(transaction_id, None)

    # ------------------------------------------------------------------
    # Timeout handling
    # ------------------------------------------------------------------
    async def _handle_timed_out_transaction(self, transaction_id):
        """Handle timed-out transaction with partial consensus."""
        try:
            async with self.lock:
                if transaction_id not in self.pending_votes:
                    return
                if transaction_id in self.committed_transactions:
                    return

                vote_data = self.pending_votes.get(transaction_id)
                if not vote_data:
                    return

                all_votes = vote_data["votes"]
                approve_count = sum(1 for v in all_votes if v["vote"] == "approve")

                if approve_count >= self.consensus_threshold:
                    consensus_status = "CONFIRMED"
                elif approve_count >= 1:
                    consensus_status = "INSUFFICIENT_CONSENSUS"
                else:
                    consensus_status = "SINGLE_WITNESS"

                self.committed_transactions[transaction_id] = datetime.now().timestamp()

            self._commit_unconfirmed_transaction(
                transaction_id, consensus_status, approve_count
            )

        except Exception as e:
            self.logger.error(f"Error handling timed-out transaction: {e}")

    def _commit_unconfirmed_transaction(self, transaction_id, consensus_status,
                                        approve_count):
        """Commit transaction with partial consensus status (sync for force-commit)."""
        try:
            if transaction_id not in self.pending_votes:
                return

            vote_data = self.pending_votes[transaction_id]
            transaction = vote_data["transaction"]

            # Snapshot votes — same mutable-reference fix as _commit_to_blockchain
            transaction["signatures"] = list(vote_data["votes"])
            transaction["consensus_status"] = consensus_status
            transaction["consensus_reached"] = (consensus_status == "CONFIRMED")
            transaction["signature_count"] = len(transaction["signatures"])
            transaction["approve_count"] = approve_count
            transaction["timeout_commit"] = True

            success = self.blockchain.add_transaction_to_blockchain(transaction)
            if success:
                self.logger.info(
                    f"⛓️  Transaction {transaction_id} committed "
                    f"status={consensus_status} ({approve_count} approve, timeout)"
                )
                if not transaction.get('is_attack', False) and approve_count > 0:
                    self._update_last_seen_cache(
                        transaction.get('ip_prefix'),
                        transaction.get('sender_asn'),
                    )
                if approve_count > 0 and consensus_status in [
                    "CONFIRMED", "INSUFFICIENT_CONSENSUS"
                ]:
                    self._award_bgpcoin_rewards(transaction_id, vote_data)
                # Update prefix ownership (only CONFIRMED)
                if consensus_status == "CONFIRMED" and self.prefix_ownership_state is not None:
                    self.prefix_ownership_state.update_from_confirmed(
                        prefix=transaction.get("ip_prefix", ""),
                        origin_asn=transaction.get("sender_asn", 0),
                        timestamp=transaction.get("timestamp", 0),
                    )
                del self.pending_votes[transaction_id]
            else:
                self.logger.error(f"Failed to write timed-out transaction {transaction_id} to blockchain")
                # Remove from committed so timeout handler can retry
                self.committed_transactions.pop(transaction_id, None)

        except Exception as e:
            self.logger.error(f"Error committing unconfirmed transaction: {e}")

    # ------------------------------------------------------------------
    # Batching
    # ------------------------------------------------------------------
    async def _batch_flush_loop(self):
        """Background coroutine that flushes batch queue periodically."""
        while self.running:
            try:
                await asyncio.wait_for(
                    self._batch_event.wait(), timeout=self.batch_timeout
                )
            except asyncio.TimeoutError:
                pass
            self._batch_event.clear()

            if not self._batch_queue:
                continue
            batch = list(self._batch_queue)
            self._batch_queue.clear()
            await self._flush_batch(batch)

    async def _flush_batch(self, batch):
        """Write batch of transactions as a single block."""
        if not batch:
            return
        transactions = [item[0] for item in batch]
        success = self.blockchain.add_multiple_transactions(transactions)
        if success:
            self.logger.info(
                f"⛓️  Batch committed: {len(transactions)} transactions"
            )
            committed_block = self.blockchain.get_last_block()
            if committed_block:
                await self._replicate_block_to_peers(committed_block)
            for transaction, vote_data, transaction_id in batch:
                if not transaction.get('is_attack', False):
                    self._update_last_seen_cache(
                        transaction.get('ip_prefix'),
                        transaction.get('sender_asn'),
                    )
                self._award_bgpcoin_rewards(transaction_id, vote_data)
                asyncio.create_task(
                    self._trigger_attack_detection(transaction, transaction_id)
                )

    # ------------------------------------------------------------------
    # Background cleanup coroutines (replace 6 daemon threads)
    # ------------------------------------------------------------------
    async def _cleanup_old_observations(self):
        """Periodically remove expired observations from knowledge base."""
        await asyncio.sleep(self.cleanup_interval)
        while self.running:
            try:
                current_time = datetime.now()
                initial_count = len(self.knowledge_base)
                self.knowledge_base = [
                    obs for obs in self.knowledge_base
                    if (current_time - self._parse_timestamp(obs["observed_at"])
                        ).total_seconds() <= self.knowledge_window_seconds
                ]
                removed = initial_count - len(self.knowledge_base)
                if removed > 0:
                    self.logger.debug(f"Cleaned {removed} old observations")
            except Exception as e:
                self.logger.error(f"Error cleaning knowledge base: {e}")
            await asyncio.sleep(self.cleanup_interval)

    async def _cleanup_timed_out_transactions(self):
        """Check for timed-out pending transactions."""
        await asyncio.sleep(1)
        while self.running:
            try:
                sleep_secs = 2.0
                if self.pending_votes:
                    now = datetime.now()
                    soonest = None
                    for vote_data in self.pending_votes.values():
                        created_at = vote_data.get("created_at")
                        if not created_at:
                            continue
                        is_attack = vote_data.get("is_attack", False)
                        if self.draining:
                            timeout_dur = 1.0
                        else:
                            timeout_dur = self.ATTACK_TIMEOUT if is_attack else self.REGULAR_TIMEOUT
                        remaining = timeout_dur - (now - created_at).total_seconds()
                        if soonest is None or remaining < soonest:
                            soonest = remaining
                    if soonest is not None:
                        sleep_secs = max(0.05, soonest + 0.05)
                else:
                    sleep_secs = 5.0

                try:
                    await asyncio.wait_for(
                        self._new_tx_event.wait(), timeout=sleep_secs
                    )
                except asyncio.TimeoutError:
                    pass
                self._new_tx_event.clear()

                current_time = datetime.now()
                timed_out = []
                for tx_id, vote_data in list(self.pending_votes.items()):
                    if tx_id in self.committed_transactions:
                        continue
                    created_at = vote_data.get("created_at")
                    if not created_at:
                        continue
                    is_attack = vote_data.get("is_attack", False)
                    if self.draining:
                        timeout_duration = 1.0
                    else:
                        timeout_duration = self.ATTACK_TIMEOUT if is_attack else self.REGULAR_TIMEOUT
                    elapsed = (current_time - created_at).total_seconds()
                    if elapsed >= timeout_duration:
                        timed_out.append(tx_id)

                for tx_id in timed_out:
                    await self._handle_timed_out_transaction(tx_id)

            except Exception as e:
                self.logger.error(f"Error in timeout cleanup: {e}")

    async def _cleanup_old_committed_transactions(self):
        """Periodically evict old committed transaction IDs."""
        await asyncio.sleep(15)
        while self.running:
            try:
                await asyncio.sleep(cfg.COMMITTED_TX_CLEANUP_INTERVAL)
                current_time = datetime.now().timestamp()
                cutoff = current_time - cfg.COMMITTED_TX_CLEANUP_INTERVAL

                before = len(self.committed_transactions)
                self.committed_transactions = {
                    tx_id: ts for tx_id, ts in self.committed_transactions.items()
                    if ts > cutoff
                }
                removed = before - len(self.committed_transactions)

                if len(self.committed_transactions) > cfg.COMMITTED_TX_MAX_SIZE:
                    sorted_items = sorted(
                        self.committed_transactions.items(), key=lambda x: x[1]
                    )
                    keep = sorted_items[-cfg.COMMITTED_TX_MAX_SIZE:]
                    self.committed_transactions = dict(keep)
                    removed += len(sorted_items) - len(keep)

                active_tx_ids = set(self.committed_transactions) | set(self.pending_votes)
                fc_before = len(self.first_commit_tracker)
                self.first_commit_tracker = {
                    tx_id: v for tx_id, v in self.first_commit_tracker.items()
                    if tx_id in active_tx_ids
                }

            except Exception as e:
                self.logger.error(f"Error in committed-tx cleanup: {e}")

    async def _cleanup_last_seen_cache_loop(self):
        """Periodically clean last_seen_cache."""
        await asyncio.sleep(10)
        while self.running:
            try:
                await asyncio.sleep(3600)
                current_time = datetime.now().timestamp()
                cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS
                self.last_seen_cache = {
                    key: ts for key, ts in self.last_seen_cache.items()
                    if ts > cutoff_time
                }
            except Exception as e:
                self.logger.error(f"Error cleaning last_seen cache: {e}")

    # ------------------------------------------------------------------
    # BGPCoin rewards
    # ------------------------------------------------------------------
    def _award_bgpcoin_rewards(self, transaction_id: str, vote_data: dict):
        """Award BGPCOIN tokens for block commit."""
        try:
            is_first = transaction_id not in self.first_commit_tracker
            if is_first:
                self.first_commit_tracker[transaction_id] = self.as_number

            voter_as_list = [
                v["from_as"] for v in vote_data["votes"]
                if v["vote"] == "approve"
            ]
            self.bgpcoin_ledger.award_block_commit_reward(
                committer_as=self.as_number,
                voter_as_list=voter_as_list,
                is_first=is_first,
            )
        except Exception as e:
            self.logger.error(f"Error awarding BGPCOIN: {e}")

    # ------------------------------------------------------------------
    # Attack detection
    # ------------------------------------------------------------------
    async def _trigger_attack_detection(self, transaction: dict,
                                        transaction_id: str):
        """Trigger attack detection for committed transaction."""
        try:
            if not self.attack_consensus:
                return
            announcement = {
                "sender_asn": transaction.get("sender_asn"),
                "ip_prefix": transaction.get("ip_prefix"),
                "as_path": transaction.get("as_path", [transaction.get("sender_asn")]),
                "timestamp": transaction.get("timestamp"),
            }
            if not announcement["sender_asn"] or not announcement["ip_prefix"]:
                return
            await self.attack_consensus.analyze_and_propose_attack(
                announcement, transaction_id
            )
        except Exception as e:
            self.logger.error(f"Error triggering attack detection: {e}")

    # ------------------------------------------------------------------
    # Compatibility methods (used by NodeManager for results collection)
    # ------------------------------------------------------------------
    def get_pending_transactions(self):
        """Get list of pending transactions."""
        pending = []
        committed_keys = set(self.committed_transactions.keys())
        for tx_id, vote_data in self.pending_votes.items():
            if tx_id not in committed_keys:
                tx = vote_data.get("transaction", {})
                if tx:
                    pending.append(tx)
        return pending

    # ------------------------------------------------------------------
    # Drain helpers
    # ------------------------------------------------------------------
    def get_pending_count(self):
        """Return the number of transactions still awaiting consensus."""
        return len(self.pending_votes)

    def begin_drain(self):
        """Enter drain mode: stop accepting new vote requests but keep
        processing vote responses and block replications so that every
        in-flight consensus round can complete naturally."""
        self.draining = True
        self.logger.info(
            f"Drain mode ON — {self.get_pending_count()} pending transactions "
            f"will be resolved by the timeout handler"
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def stop(self):
        """Stop async P2P pool."""
        self.running = False
        self._shutdown_event.set()
        for task in self._background_tasks:
            task.cancel()
        from message_bus_async import AsyncMessageBus
        AsyncMessageBus.get_instance().unregister(self.as_number)
