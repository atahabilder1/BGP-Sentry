#!/usr/bin/env python3
"""
NodeManager - Creates and manages all virtual nodes with full blockchain infrastructure.

Orchestrates the lifecycle of VirtualNode instances:
  1. Creates shared infrastructure (message bus, ledger, rating system, blockchain)
  2. Creates one VirtualNode per AS with appropriate blockchain components
  3. Starts P2P servers for RPKI nodes, then starts all node processing threads
  4. Monitors progress and collects results
"""

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

    Creates shared blockchain infrastructure and wires it into each VirtualNode.
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

        # ----- Shared infrastructure -----
        self.message_bus = None
        self.primary_blockchain = None      # Canonical chain (disk-backed)
        self.shared_ledger = None
        self.rating_system = None
        self.attack_detector = None
        self.rpki_validator = None

        # Per-node infrastructure
        self.node_blockchains: Dict[int, object] = {}   # asn -> BlockchainInterface (in-memory replicas)
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
        all_obs = data_loader.get_all_observations()
        all_timestamps = [
            obs.get("timestamp", 0)
            for obs_list in all_obs.values()
            for obs in obs_list
            if obs.get("timestamp")
        ]
        self.bgp_ts_min = min(all_timestamps, default=0.0)
        self.bgp_ts_max = max(all_timestamps, default=0.0)
        self.simulation_clock.set_epoch(self.bgp_ts_min)

        self._create_nodes()

    def _init_infrastructure(self):
        """Initialize shared blockchain infrastructure used by all nodes."""
        from message_bus import InMemoryMessageBus
        from blockchain_interface import BlockchainInterface
        from bgpcoin_ledger import BGPCoinLedger
        from nonrpki_rating import NonRPKIRatingSystem
        from attack_detector import AttackDetector

        # 1. Message bus (singleton)
        InMemoryMessageBus.reset()  # Clean slate for this experiment
        self.message_bus = InMemoryMessageBus.get_instance()

        # 2. Primary blockchain (canonical chain, disk-backed)
        blockchain_dir = self.project_root / "blockchain_data" / "chain"
        blockchain_dir.mkdir(parents=True, exist_ok=True)
        self.primary_blockchain = BlockchainInterface(str(blockchain_dir))

        # 3. BGPCoin ledger (shared economy)
        state_dir = blockchain_dir.parent / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
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
            # Try alternative import path
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

        logger.info(
            "Blockchain infrastructure initialized: "
            f"blockchain={blockchain_dir}, "
            f"ledger={state_dir}, "
            f"message_bus=InMemory"
        )

    def _generate_node_keys(self):
        """Generate Ed25519 key pairs for all RPKI validator nodes."""
        from signature_utils import SignatureUtils
        from blockchain_interface import BlockchainInterface

        rpki_asns = [asn for asn in self.data_loader.get_all_asns() if self.data_loader.is_rpki(asn)]

        # Get genesis block from primary chain (so all replicas share same genesis hash)
        genesis_block = self.primary_blockchain.blockchain_data["blocks"][0]

        for asn in rpki_asns:
            # Generate Ed25519 key pair
            private_key, public_key, public_pem = SignatureUtils.generate_key_pair()
            self.node_keys[asn] = (private_key, public_key)
            self.public_key_registry[asn] = public_key
            self.public_key_pems[asn] = public_pem

            # Create per-node blockchain replica (in-memory, same genesis)
            node_chain = BlockchainInterface(in_memory=True, genesis_block=genesis_block)
            self.node_blockchains[asn] = node_chain

        logger.info(
            f"Generated Ed25519 key pairs for {len(rpki_asns)} RPKI nodes, "
            f"created {len(self.node_blockchains)} per-node blockchain replicas"
        )

    def _create_nodes(self):
        """Create a VirtualNode for every AS in the dataset."""
        from p2p_transaction_pool import P2PTransactionPool

        for asn in self.data_loader.get_all_asns():
            is_rpki = self.data_loader.is_rpki(asn)
            role = self.data_loader.get_role(asn)
            observations = self.data_loader.get_observations_for_asn(asn)

            # RPKI nodes get a P2PTransactionPool for consensus
            p2p_pool = None
            private_key = None
            if is_rpki:
                private_key = self.node_keys[asn][0] if asn in self.node_keys else None
                node_chain = self.node_blockchains.get(asn)

                p2p_pool = P2PTransactionPool(
                    as_number=asn,
                    use_memory_bus=True,
                    blockchain_interface=self.primary_blockchain,
                    bgpcoin_ledger=self.shared_ledger,
                    private_key=private_key,
                    public_key_registry=self.public_key_registry,
                    node_blockchain=node_chain,
                )

            node = VirtualNode(
                asn=asn,
                is_rpki=is_rpki,
                rpki_role=role,
                observations=observations,
                p2p_pool=p2p_pool,
                rpki_validator=self.rpki_validator if is_rpki else None,
                attack_detector=self.attack_detector,
                rating_system=self.rating_system if not is_rpki else None,
                shared_blockchain=self.primary_blockchain if is_rpki else None,
                bgpcoin_ledger=self.shared_ledger if is_rpki else None,
                private_key=private_key,
                clock=self.simulation_clock,
            )
            self.nodes[asn] = node

        logger.info(
            f"NodeManager created {len(self.nodes)} virtual nodes "
            f"({self.data_loader.rpki_count} RPKI, {self.data_loader.non_rpki_count} non-RPKI)"
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

    def stop_all(self):
        """Stop all virtual nodes and P2P pools."""
        for node in self.nodes.values():
            node.stop()
            if node.p2p_pool is not None:
                node.p2p_pool.stop()

        # Clean up message bus
        if self.message_bus is not None:
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
        """Get blockchain statistics including per-node replica verification."""
        if self.primary_blockchain is None:
            return {}
        info = self.primary_blockchain.get_blockchain_info()
        integrity = self.primary_blockchain.verify_blockchain_integrity()

        # Verify per-node blockchain replicas
        replica_results = {}
        replicas_valid = 0
        for asn, chain in self.node_blockchains.items():
            node_integrity = chain.verify_blockchain_integrity()
            node_blocks = len(chain.blockchain_data["blocks"])
            is_valid = node_integrity.get("valid", False)
            if is_valid:
                replicas_valid += 1
            replica_results[str(asn)] = {
                "blocks": node_blocks,
                "valid": is_valid,
            }

        return {
            "blockchain_info": info,
            "integrity": integrity,
            "node_replicas": {
                "total_nodes": len(self.node_blockchains),
                "all_valid": replicas_valid == len(self.node_blockchains),
                "valid_count": replicas_valid,
            },
        }

    def get_crypto_summary(self) -> dict:
        """Get cryptographic key and signing summary."""
        return {
            "key_algorithm": "Ed25519",
            "signature_scheme": "RSA-PSS with SHA-256",
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
        """Aggregate consensus decision stats across all RPKI nodes."""
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
        Persist RSA key pairs to disk for each RPKI node.

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
