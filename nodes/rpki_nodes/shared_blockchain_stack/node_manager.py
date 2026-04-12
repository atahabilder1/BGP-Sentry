#!/usr/bin/env python3
"""
NodeManager - Creates and manages all virtual nodes with full blockchain infrastructure.

Orchestrates the lifecycle of VirtualNode instances:
  1. Creates infrastructure (message bus, ledger, rating system)
  2. Creates one VirtualNode per AS with its own independent blockchain
  3. Starts P2P servers for RPKI nodes, then starts all node processing threads
  4. Monitors progress and collects results

Each RPKI node maintains its own blockchain — there is no shared/primary chain.
Forks are expected and tracked when replicated blocks conflict with local state.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ensure blockchain_utils is importable
_blockchain_utils = Path(__file__).resolve().parent / "blockchain_utils"
if str(_blockchain_utils) not in sys.path:
    sys.path.insert(0, str(_blockchain_utils))

try:
    from .data_loader import DatasetLoader
    from .virtual_node import VirtualNode
except ImportError:
    from data_loader import DatasetLoader
    from virtual_node import VirtualNode

from simulation_helpers.timing.shared_clock import SimulationClock


class NodeManager:
    """
    Manages the full set of virtual nodes for a BGP-Sentry experiment.

    Creates per-node blockchain infrastructure and wires it into each VirtualNode.
    Each RPKI node maintains its own independent blockchain (no shared chain).
    """

    def __init__(self, data_loader: DatasetLoader, project_root: str = None):
        self.data_loader = data_loader
        self.nodes: Dict[int, VirtualNode] = {}
        self._observation_callback: Optional[Callable] = None

        # Resolve project root
        if project_root is None:
            # Walk up from this file to find the project root
            project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
        self.project_root = Path(project_root)

        # ----- Infrastructure -----
        self.message_bus = None
        self.shared_ledger = None
        self.rating_system = None
        self.attack_detector = None
        self.rpki_validator = None
        self.prefix_ownership_state = None

        # Per-node infrastructure — each RPKI node owns its own blockchain
        self.node_blockchains: Dict[int, object] = {}   # asn -> BlockchainInterface (independent chain)
        self.node_keys: Dict[int, tuple] = {}            # asn -> (private_key, public_key)
        self.public_key_registry: Dict[int, object] = {} # asn -> public_key object
        self.public_key_pems: Dict[int, str] = {}        # asn -> PEM string (for results output)

        self._init_infrastructure()
        self._generate_node_keys()

        # Create shared simulation clock
        from config import cfg as _cfg
        self.simulation_clock = SimulationClock(
            speed_multiplier=_cfg.SIMULATION_SPEED_MULTIPLIER
        )
        # Find earliest and latest BGP timestamps across all observations
        # Filter out timestamps < 1e9 (year ~2001) — these are bogus values
        # from BGPy's default timestamp=0 + convergence jitter
        all_obs = data_loader.get_all_observations()
        all_timestamps = [
            obs.get("timestamp", 0)
            for obs_list in all_obs.values()
            for obs in obs_list
            if obs.get("timestamp", 0) > 1_000_000_000
        ]
        self.bgp_ts_min = min(all_timestamps, default=0.0)
        self.bgp_ts_max = max(all_timestamps, default=0.0)
        self.simulation_clock.set_epoch(self.bgp_ts_min)

        self._create_nodes()

    def _init_infrastructure(self):
        """Initialize infrastructure (no shared blockchain — each node gets its own)."""
        from config import cfg as _cfg
        from bgpcoin_ledger import BGPCoinLedger
        from nonrpki_rating import NonRPKIRatingSystem
        from attack_detector import AttackDetector

        # 1. Message bus (singleton) — async or threaded
        if _cfg.USE_ASYNC:
            from message_bus_async import AsyncMessageBus
            AsyncMessageBus.reset()
            self.message_bus = AsyncMessageBus.get_instance()
        else:
            from message_bus import InMemoryMessageBus
            InMemoryMessageBus.reset()
            self.message_bus = InMemoryMessageBus.get_instance()

        # 2. State directory for ledger, ratings, etc.
        state_dir = self.project_root / "blockchain_data" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        # 3. BGPCoin ledger (shared economy)
        self.shared_ledger = BGPCoinLedger(ledger_path=str(state_dir))

        # 4. Non-RPKI rating system (shared)
        self.rating_system = NonRPKIRatingSystem(rating_path=str(state_dir))

        # 5. Attack detector (shared — stateless except for flap tracking)
        roa_path = str(state_dir / "roa_database.json")
        rel_path = str(state_dir / "as_relationships.json")
        self.attack_detector = AttackDetector(
            roa_database_path=roa_path,
            as_relationships_path=rel_path,
        )

        # 6. RPKI validator (shared, uses VRP file)
        try:
            from rpki_validator import RPKIValidator
            vrp_path = str(self.project_root / "stayrtr" / "vrp_generated.json")
            self.rpki_validator = RPKIValidator(vrp_path=vrp_path)
        except Exception as e:
            logger.warning(f"RPKIValidator not available: {e}")
            try:
                rpki_validator_path = (
                    self.project_root / "nodes" / "rpki_nodes"
                    / "bgp_attack_detection" / "validators"
                )
                sys.path.insert(0, str(rpki_validator_path))
                from rpki_validator import RPKIValidator
                vrp_path = str(self.project_root / "stayrtr" / "vrp_generated.json")
                self.rpki_validator = RPKIValidator(vrp_path=vrp_path)
            except Exception as e2:
                logger.warning(f"RPKIValidator fallback also failed: {e2}")
                self.rpki_validator = None

        # 7. Prefix Ownership State (blockchain-derived ROA replacement)
        from prefix_ownership_state import PrefixOwnershipState
        self.prefix_ownership_state = PrefixOwnershipState()
        vrp_path = str(self.project_root / "stayrtr" / "vrp_generated.json")
        self.prefix_ownership_state.bootstrap_from_vrp(vrp_path)

        logger.info(
            "Infrastructure initialized: "
            f"state={state_dir}, "
            f"message_bus=InMemory (no shared blockchain)"
        )

    def _generate_node_keys(self):
        """Generate Ed25519 key pairs and independent blockchains for all RPKI nodes.

        Each RPKI node gets its own BlockchainInterface (in-memory).
        All nodes share the same genesis block so their chains start from
        a common root, but after that each node's chain diverges
        independently — forks are expected and tracked.
        """
        from signature_utils import SignatureUtils
        from blockchain_interface import BlockchainInterface

        rpki_asns = [asn for asn in self.data_loader.get_all_asns() if self.data_loader.is_rpki(asn)]

        # Create a shared genesis block (all nodes start from the same root)
        genesis_chain = BlockchainInterface(in_memory=True)
        genesis_block = genesis_chain.blockchain_data["blocks"][0]

        for asn in rpki_asns:
            # Generate Ed25519 key pair
            private_key, public_key, public_pem = SignatureUtils.generate_key_pair()
            self.node_keys[asn] = (private_key, public_key)
            self.public_key_registry[asn] = public_key
            self.public_key_pems[asn] = public_pem

            # Create independent per-node blockchain (same genesis, own chain)
            node_chain = BlockchainInterface(in_memory=True, genesis_block=genesis_block)
            self.node_blockchains[asn] = node_chain

        logger.info(
            f"Generated Ed25519 key pairs for {len(rpki_asns)} RPKI nodes, "
            f"created {len(self.node_blockchains)} independent per-node blockchains"
        )

    def _create_nodes(self):
        """Create a VirtualNode for every AS in the dataset.

        Each RPKI node receives its own independent BlockchainInterface
        (no shared/primary chain).  The node's P2PTransactionPool writes
        directly to this chain, and forks are detected when replicated
        blocks from peers conflict with the local tip.
        """
        from config import cfg as _cfg
        self._use_async = _cfg.USE_ASYNC

        if self._use_async:
            from p2p_transaction_pool_async import AsyncP2PTransactionPool as PoolClass
        else:
            from p2p_transaction_pool import P2PTransactionPool as PoolClass

        for asn in self.data_loader.get_all_asns():
            is_rpki = self.data_loader.is_rpki(asn)
            role = self.data_loader.get_role(asn)
            observations = self.data_loader.get_observations_for_asn(asn)

            # RPKI nodes get a P2PTransactionPool for consensus
            p2p_pool = None
            private_key = None
            if is_rpki:
                private_key = self.node_keys[asn][0] if asn in self.node_keys else None
                # Each node's own independent blockchain
                node_chain = self.node_blockchains.get(asn)

                if self._use_async:
                    p2p_pool = PoolClass(
                        as_number=asn,
                        blockchain_interface=node_chain,
                        bgpcoin_ledger=self.shared_ledger,
                        private_key=private_key,
                        public_key_registry=self.public_key_registry,
                        prefix_ownership_state=self.prefix_ownership_state,
                    )
                else:
                    p2p_pool = PoolClass(
                        as_number=asn,
                        use_memory_bus=True,
                        blockchain_interface=node_chain,
                        bgpcoin_ledger=self.shared_ledger,
                        private_key=private_key,
                        public_key_registry=self.public_key_registry,
                        prefix_ownership_state=self.prefix_ownership_state,
                    )

            node = VirtualNode(
                asn=asn,
                is_rpki=is_rpki,
                rpki_role=role,
                observations=observations,
                p2p_pool=p2p_pool,
                rpki_validator=self.rpki_validator if is_rpki else None,
                attack_detector=self.attack_detector,
                rating_system=None,
                bgpcoin_ledger=self.shared_ledger if is_rpki else None,
                private_key=private_key,
                clock=self.simulation_clock,
                prefix_ownership_state=self.prefix_ownership_state if is_rpki else None,
            )
            self.nodes[asn] = node

        mode = "ASYNC" if self._use_async else "THREADED"
        logger.info(
            f"NodeManager created {len(self.nodes)} virtual nodes "
            f"({self.data_loader.rpki_count} RPKI, {self.data_loader.non_rpki_count} non-RPKI) "
            f"[mode={mode}]"
        )

    def set_observation_callback(self, callback: Callable):
        """Set a callback invoked for each processed observation."""
        self._observation_callback = callback

    def start_all(self):
        """Start all virtual nodes.

        1. Start P2P servers for RPKI nodes (registers them with message bus)
        2. Start processing threads for all nodes
        """
        # Phase 1: Start P2P servers for all RPKI nodes
        rpki_count = 0
        for node in self.nodes.values():
            if node.is_rpki and node.p2p_pool is not None:
                node.p2p_pool.start_p2p_server(
                    attack_detector=self.attack_detector,
                    rating_system=self.rating_system,
                )
                rpki_count += 1

        logger.info(f"Started P2P servers for {rpki_count} RPKI nodes")

        # Phase 2: Start all node processing threads
        logger.info(f"Starting {len(self.nodes)} virtual nodes...")
        for node in self.nodes.values():
            node.start(callback=self._observation_callback)

        # Phase 3: Start simulation clock (unblocks all node threads)
        self.simulation_clock.start()
        logger.info(
            f"Simulation clock started (speed={self.simulation_clock.speed_multiplier}x)"
        )

    # ------------------------------------------------------------------
    # Async mode (USE_ASYNC=true)
    # ------------------------------------------------------------------
    async def start_all_async(self):
        """Async version: start P2P servers and node processing as coroutines."""
        # Phase 1: Start async P2P servers
        rpki_count = 0
        for node in self.nodes.values():
            if node.is_rpki and node.p2p_pool is not None:
                await node.p2p_pool.start_p2p_server(
                    attack_detector=self.attack_detector,
                    rating_system=self.rating_system,
                )
                rpki_count += 1
        logger.info(f"Started async P2P servers for {rpki_count} RPKI nodes")

        # Phase 2: Start all nodes as async tasks
        logger.info(f"Starting {len(self.nodes)} virtual nodes (async)...")
        self._node_tasks = []
        for node in self.nodes.values():
            task = asyncio.create_task(
                node.run_async(callback=self._observation_callback)
            )
            self._node_tasks.append(task)

        # Phase 3: Start simulation clock
        self.simulation_clock.start_async()
        logger.info(
            f"Simulation clock started (speed={self.simulation_clock.speed_multiplier}x, async)"
        )

    async def wait_for_completion_async(self, timeout: float = 600,
                                        poll_interval: float = 2.0):
        """Async version: wait for all nodes to finish."""
        start = time.time()
        while time.time() - start < timeout:
            done = sum(1 for n in self.nodes.values() if n.is_done())
            total = len(self.nodes)
            if done == total:
                logger.info(f"All {total} nodes completed processing (async)")
                return True
            elapsed = time.time() - start
            logger.info(f"Progress: {done}/{total} nodes done ({elapsed:.0f}s elapsed)")
            await asyncio.sleep(poll_interval)
        logger.warning(f"Timed out waiting for nodes ({timeout}s)")
        return False

    def stop_all(self):
        """Stop all virtual nodes and P2P pools."""
        for node in self.nodes.values():
            node.stop()
            if node.p2p_pool is not None:
                node.p2p_pool.stop()

        # Clean up message bus
        if self.message_bus is not None:
            if getattr(self, '_use_async', False):
                from message_bus_async import AsyncMessageBus
                AsyncMessageBus.reset()
            else:
                from message_bus import InMemoryMessageBus
                InMemoryMessageBus.reset()

        logger.info("All virtual nodes stopped")

    def wait_for_completion(self, timeout: float = 600, poll_interval: float = 2.0):
        """Block until all nodes finish processing or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            done = sum(1 for n in self.nodes.values() if n.is_done())
            total = len(self.nodes)

            if done == total:
                logger.info(f"All {total} nodes completed processing")
                return True

            elapsed = time.time() - start
            logger.info(f"Progress: {done}/{total} nodes done ({elapsed:.0f}s elapsed)")
            time.sleep(poll_interval)

        logger.warning(f"Timed out waiting for nodes ({timeout}s)")
        return False

    # ------------------------------------------------------------------
    # Results collection
    # ------------------------------------------------------------------
    def get_all_detection_results(self) -> List[dict]:
        """Collect detection results from all nodes."""
        results = []
        for node in self.nodes.values():
            results.extend(node.detection_results)
        return results

    def get_all_attack_detections(self) -> List[dict]:
        """Collect attack detections from all nodes."""
        detections = []
        for node in self.nodes.values():
            detections.extend(node.attack_detections)
        return detections

    def get_node_statuses(self) -> List[dict]:
        """Get status of all nodes."""
        return [node.get_status() for node in sorted(self.nodes.values(), key=lambda n: n.asn)]

    def get_summary(self) -> dict:
        """Get aggregate summary of all nodes."""
        total = len(self.nodes)
        done = sum(1 for n in self.nodes.values() if n.is_done())
        rpki_nodes = sum(1 for n in self.nodes.values() if n.is_rpki)
        total_processed = sum(n.processed_count for n in self.nodes.values())
        total_attacks_detected = sum(len(n.attack_detections) for n in self.nodes.values())
        total_legitimate = sum(n.legitimate_count for n in self.nodes.values())

        return {
            "total_nodes": total,
            "rpki_nodes": rpki_nodes,
            "non_rpki_nodes": total - rpki_nodes,
            "nodes_done": done,
            "total_observations_processed": total_processed,
            "attacks_detected": total_attacks_detected,
            "legitimate_processed": total_legitimate,
        }

    # ------------------------------------------------------------------
    # Blockchain stats (new)
    # ------------------------------------------------------------------
    def get_blockchain_stats(self) -> dict:
        """Get blockchain statistics from all independent per-node chains.

        Each RPKI node maintains its own blockchain.  This method
        aggregates integrity checks, block/transaction counts, and fork
        statistics across all node chains.
        """
        if not self.node_blockchains:
            return {}

        per_node = {}
        valid_count = 0
        total_blocks_all = []
        total_txns_all = []
        total_forks = 0

        total_forks_resolved = 0
        total_merge_blocks = 0

        for asn, chain in self.node_blockchains.items():
            integrity = chain.verify_blockchain_integrity()
            num_blocks = len(chain.blockchain_data["blocks"])
            num_txns = sum(
                len(b.get("transactions", []))
                for b in chain.blockchain_data["blocks"]
            )
            is_valid = integrity.get("valid", False)
            if is_valid:
                valid_count += 1
            total_blocks_all.append(num_blocks)
            total_txns_all.append(num_txns)

            fork_stats = chain.get_fork_stats()
            total_forks += fork_stats["total_forks_detected"]
            forks_resolved = fork_stats.get("forks_resolved", 0)
            total_forks_resolved += forks_resolved

            # Count merge blocks
            merge_blocks = sum(
                1 for b in chain.blockchain_data["blocks"]
                if b.get("metadata", {}).get("block_type") == "fork_merge"
            )
            total_merge_blocks += merge_blocks

            per_node[str(asn)] = {
                "blocks": num_blocks,
                "transactions": num_txns,
                "valid": is_valid,
                "forks_detected": fork_stats["total_forks_detected"],
                "forks_resolved": forks_resolved,
                "merge_blocks": merge_blocks,
            }

        return {
            "architecture": "per-node independent blockchains",
            "total_nodes": len(self.node_blockchains),
            "valid_chains": valid_count,
            "all_valid": valid_count == len(self.node_blockchains),
            "blocks_per_node": {
                "min": min(total_blocks_all) if total_blocks_all else 0,
                "max": max(total_blocks_all) if total_blocks_all else 0,
                "mean": sum(total_blocks_all) / len(total_blocks_all) if total_blocks_all else 0,
            },
            "transactions_per_node": {
                "min": min(total_txns_all) if total_txns_all else 0,
                "max": max(total_txns_all) if total_txns_all else 0,
                "mean": sum(total_txns_all) / len(total_txns_all) if total_txns_all else 0,
            },
            "total_forks_detected": total_forks,
            "total_forks_resolved": total_forks_resolved,
            "total_merge_blocks": total_merge_blocks,
            "per_node": per_node,
        }

    def get_crypto_summary(self) -> dict:
        """Get cryptographic key and signing summary."""
        return {
            "key_algorithm": "Ed25519",
            "signature_scheme": "Ed25519",
            "total_key_pairs": len(self.node_keys),
            "public_key_registry_size": len(self.public_key_registry),
            "nodes_with_keys": sorted(self.node_keys.keys()),
        }

    def get_bgpcoin_summary(self) -> dict:
        """Get BGPCoin economy stats."""
        if self.shared_ledger is None:
            return {}
        return self.shared_ledger.get_ledger_summary()

    def get_rating_summary(self) -> dict:
        """Get non-RPKI rating distribution."""
        if self.rating_system is None:
            return {}
        return self.rating_system.get_summary()

    def get_all_ratings(self) -> dict:
        """Get all non-RPKI AS ratings."""
        if self.rating_system is None:
            return {}
        return self.rating_system.get_all_ratings()

    def get_consensus_log(self) -> dict:
        """Aggregate consensus decision stats across all RPKI nodes.

        Scans in-memory blockchains for consensus_status breakdown
        (CONFIRMED vs SINGLE_WITNESS vs INSUFFICIENT_CONSENSUS).
        """
        consensus_stats = {
            "total_transactions_created": 0,
            "total_committed": 0,
            "total_pending": 0,
        }

        for node in self.nodes.values():
            if node.is_rpki and node.p2p_pool is not None:
                pool = node.p2p_pool
                consensus_stats["total_committed"] += len(pool.committed_transactions)
                consensus_stats["total_pending"] += len(pool.pending_votes)

            consensus_stats["total_transactions_created"] += node.stats.get("transactions_created", 0)

        # Scan all per-node blockchains for consensus status breakdown
        status_counts = {
            "CONFIRMED": 0,
            "SINGLE_WITNESS": 0,
            "INSUFFICIENT_CONSENSUS": 0,
            "no_status": 0,
        }
        block_type_counts = {
            "transaction": 0,
            "batch": 0,
            "fork_merge": 0,
            "genesis": 0,
            "other": 0,
        }
        # Track unique tx IDs across all chains (many txns appear on multiple chains via fork merge)
        unique_tx_ids = set()
        unique_status = {
            "CONFIRMED": set(),
            "SINGLE_WITNESS": set(),
            "INSUFFICIENT_CONSENSUS": set(),
            "no_status": set(),
        }

        for asn, chain in self.node_blockchains.items():
            for block in chain.blockchain_data.get("blocks", []):
                bt = block.get("metadata", {}).get("block_type", "other")
                block_type_counts[bt] = block_type_counts.get(bt, 0) + 1

                for tx in block.get("transactions", []):
                    tx_id = tx.get("transaction_id", "")
                    unique_tx_ids.add(tx_id)
                    cs = tx.get("consensus_status", "")
                    if cs == "CONFIRMED" or tx.get("consensus_reached") is True:
                        status_counts["CONFIRMED"] += 1
                        unique_status["CONFIRMED"].add(tx_id)
                    elif cs == "SINGLE_WITNESS":
                        status_counts["SINGLE_WITNESS"] += 1
                        unique_status["SINGLE_WITNESS"].add(tx_id)
                    elif cs == "INSUFFICIENT_CONSENSUS":
                        status_counts["INSUFFICIENT_CONSENSUS"] += 1
                        unique_status["INSUFFICIENT_CONSENSUS"].add(tx_id)
                    else:
                        status_counts["no_status"] += 1
                        unique_status["no_status"].add(tx_id)

        consensus_stats["consensus_status_all_chains"] = status_counts
        consensus_stats["consensus_status_unique"] = {
            k: len(v) for k, v in unique_status.items()
        }
        consensus_stats["unique_transactions_across_chains"] = len(unique_tx_ids)
        consensus_stats["block_type_counts"] = block_type_counts

        return consensus_stats

    def get_dedup_stats(self) -> dict:
        """Get deduplication statistics across all nodes."""
        total_deduped = 0
        total_throttled = 0
        for node in self.nodes.values():
            deduped = node.stats.get("transactions_deduped", 0)
            if node.is_rpki:
                total_deduped += deduped
            else:
                total_throttled += deduped

        return {
            "rpki_deduped": total_deduped,
            "nonrpki_throttled": total_throttled,
            "total_skipped": total_deduped + total_throttled,
        }

    def get_attack_verdicts(self) -> List[dict]:
        """Collect attack verdicts from all RPKI nodes' attack consensus systems."""
        verdicts = []
        for node in self.nodes.values():
            if node.is_rpki and node.p2p_pool is not None:
                ac = node.p2p_pool.attack_consensus
                if ac is not None:
                    for pid, proposal in ac.active_proposals.items():
                        tracking = ac.vote_tracking.get(pid, {})
                        verdicts.append({
                            "proposal_id": pid,
                            "proposer_as": proposal.get("proposer_as"),
                            "attack_type": proposal.get("attack_details", {}).get("attack_type"),
                            "status": proposal.get("status"),
                            "verdict": proposal.get("verdict"),
                            "confidence": proposal.get("confidence"),
                            "yes_votes": tracking.get("yes_count", 0),
                            "no_votes": tracking.get("no_count", 0),
                            "total_votes": tracking.get("total_votes", 0),
                        })
        return verdicts

    def get_message_bus_stats(self) -> dict:
        """Get message bus statistics."""
        if self.message_bus is None:
            return {}
        return self.message_bus.get_stats()

    def save_keys_to_disk(self):
        """
        Persist Ed25519 key pairs to disk for each RPKI node.

        Writes:
          - blockchain_data/nodes/as{N}/keys/private_key.pem
          - blockchain_data/public_key_registry.json
        """
        import json
        from cryptography.hazmat.primitives import serialization

        base_dir = self.project_root / "blockchain_data" / "nodes"

        for asn, (private_key, public_key) in self.node_keys.items():
            node_dir = base_dir / f"as{asn}" / "keys"
            node_dir.mkdir(parents=True, exist_ok=True)

            # Write private key PEM
            pem_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            (node_dir / "private_key.pem").write_bytes(pem_bytes)

        # Write public key registry
        registry_path = self.project_root / "blockchain_data" / "public_key_registry.json"
        registry_data = {str(asn): pem for asn, pem in self.public_key_pems.items()}
        with open(registry_path, "w") as f:
            json.dump(registry_data, f, indent=2)

        logger.info(
            f"Saved {len(self.node_keys)} private keys to {base_dir}, "
            f"public key registry to {registry_path}"
        )
