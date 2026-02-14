#!/usr/bin/env python3
"""
=============================================================================
RPKI Node Registry - Data-Driven RPKI Node Identification
=============================================================================

Purpose: Maintain authoritative list of RPKI validator nodes and provide
         functions to check if an AS is RPKI or non-RPKI.

Data source: Loaded from as_classification.json (produced by CAIDA dataset
             generator). Falls back to legacy hardcoded set for backward
             compatibility when no dataset is loaded.

Author: BGP-Sentry Team
=============================================================================
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

from config import cfg

logger = logging.getLogger(__name__)

# Legacy hardcoded set (backward compatibility for old 9-node topology)
_LEGACY_RPKI_NODES: Set[int] = {1, 3, 5, 7, 9, 11, 13, 15, 17}


class RPKINodeRegistry:
    """
    Central registry of RPKI validator nodes.

    Call RPKINodeRegistry.initialize(dataset_path) at startup to load
    real AS classification from a CAIDA dataset.  If never initialized,
    falls back to the legacy 9-node set.
    """

    # Populated by initialize()
    RPKI_NODES: Set[int] = set()
    NON_RPKI_NODES: Set[int] = set()
    ALL_NODES: Set[int] = set()
    VALIDATORS: Set[int] = set()   # RPKI ASes with blockchain_validator role
    OBSERVERS: Set[int] = set()    # non-RPKI ASes with observer role
    ROLES: Dict[int, str] = {}     # ASN -> role string

    TOTAL_RPKI_NODES: int = 0
    TOTAL_NON_RPKI_NODES: int = 0
    TOTAL_NODES: int = 0

    _initialized: bool = False
    _dataset_path: str = ""

    # Base port for P2P communication (from .env)
    BASE_PORT = cfg.P2P_BASE_PORT

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    @classmethod
    def initialize(cls, dataset_path: str) -> None:
        """
        Load RPKI / non-RPKI classification from a CAIDA dataset directory.

        Args:
            dataset_path: Path to dataset directory containing as_classification.json
        """
        classification_file = Path(dataset_path) / "as_classification.json"
        if not classification_file.exists():
            raise FileNotFoundError(f"as_classification.json not found in {dataset_path}")

        with open(classification_file, "r") as f:
            data = json.load(f)

        cls.RPKI_NODES = set(data.get("rpki_asns", []))
        cls.NON_RPKI_NODES = set(data.get("non_rpki_asns", []))
        cls.ALL_NODES = cls.RPKI_NODES | cls.NON_RPKI_NODES

        # Roles
        rpki_role = data.get("rpki_role", {})
        cls.ROLES = {int(k): v for k, v in rpki_role.items()}
        cls.VALIDATORS = {asn for asn, role in cls.ROLES.items() if role == "blockchain_validator"}
        cls.OBSERVERS = {asn for asn, role in cls.ROLES.items() if role == "observer"}

        # Counts
        cls.TOTAL_RPKI_NODES = len(cls.RPKI_NODES)
        cls.TOTAL_NON_RPKI_NODES = len(cls.NON_RPKI_NODES)
        cls.TOTAL_NODES = len(cls.ALL_NODES)

        cls._initialized = True
        cls._dataset_path = str(dataset_path)

        logger.info(
            f"RPKINodeRegistry initialized from {dataset_path}: "
            f"{cls.TOTAL_RPKI_NODES} RPKI, {cls.TOTAL_NON_RPKI_NODES} non-RPKI, "
            f"{len(cls.VALIDATORS)} validators, {len(cls.OBSERVERS)} observers"
        )

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Fall back to legacy hardcoded set if initialize() was never called."""
        if not cls._initialized:
            cls.RPKI_NODES = set(_LEGACY_RPKI_NODES)
            cls.NON_RPKI_NODES = {2, 4, 6, 8, 10, 12, 14, 16, 18}
            cls.ALL_NODES = cls.RPKI_NODES | cls.NON_RPKI_NODES
            cls.VALIDATORS = set(cls.RPKI_NODES)
            cls.OBSERVERS = set(cls.NON_RPKI_NODES)
            cls.ROLES = {asn: "blockchain_validator" for asn in cls.RPKI_NODES}
            cls.ROLES.update({asn: "observer" for asn in cls.NON_RPKI_NODES})
            cls.TOTAL_RPKI_NODES = len(cls.RPKI_NODES)
            cls.TOTAL_NON_RPKI_NODES = len(cls.NON_RPKI_NODES)
            cls.TOTAL_NODES = len(cls.ALL_NODES)
            cls._initialized = True
            logger.warning("RPKINodeRegistry using legacy hardcoded set (no dataset loaded)")

    # ------------------------------------------------------------------
    # Query methods (API unchanged from original)
    # ------------------------------------------------------------------
    @classmethod
    def is_rpki_node(cls, as_number: int) -> bool:
        """Check if given AS number is an RPKI validator node."""
        cls._ensure_initialized()
        return as_number in cls.RPKI_NODES

    @classmethod
    def is_non_rpki(cls, as_number: int) -> bool:
        """Check if given AS number is a non-RPKI autonomous system."""
        cls._ensure_initialized()
        return as_number not in cls.RPKI_NODES

    @classmethod
    def get_all_rpki_nodes(cls) -> List[int]:
        """Get sorted list of all RPKI validator AS numbers."""
        cls._ensure_initialized()
        return sorted(cls.RPKI_NODES)

    @classmethod
    def get_all_non_rpki_nodes(cls) -> List[int]:
        """Get sorted list of all non-RPKI AS numbers."""
        cls._ensure_initialized()
        return sorted(cls.NON_RPKI_NODES)

    @classmethod
    def get_all_nodes(cls) -> List[int]:
        """Get sorted list of all AS numbers (RPKI + non-RPKI)."""
        cls._ensure_initialized()
        return sorted(cls.ALL_NODES)

    @classmethod
    def get_peer_nodes(cls, my_as_number: int) -> dict:
        """
        Get peer RPKI nodes (excluding self).

        Returns:
            Dict mapping AS number to (host, port) tuple
        """
        cls._ensure_initialized()
        peers = {}
        for as_num in cls.RPKI_NODES:
            if as_num != my_as_number:
                port = cls.BASE_PORT + as_num
                peers[as_num] = ("localhost", port)
        return peers

    @classmethod
    def get_node_count(cls) -> int:
        """Get total number of RPKI validator nodes."""
        cls._ensure_initialized()
        return cls.TOTAL_RPKI_NODES

    @classmethod
    def get_role(cls, as_number: int) -> str:
        """Get the blockchain role for an AS ('blockchain_validator' or 'observer')."""
        cls._ensure_initialized()
        return cls.ROLES.get(as_number, "unknown")

    @classmethod
    def should_apply_rating(cls, as_number: int) -> bool:
        """
        Check if rating system should be applied to this AS.
        Non-RPKI nodes use the rating system.
        """
        return cls.is_non_rpki(as_number)

    @classmethod
    def get_node_type(cls, as_number: int) -> str:
        """Get human-readable node type."""
        return "RPKI_VALIDATOR" if cls.is_rpki_node(as_number) else "NON_RPKI"

    @classmethod
    def validate_as_number(cls, as_number: int) -> dict:
        """Comprehensive validation of AS number."""
        cls._ensure_initialized()
        is_rpki = cls.is_rpki_node(as_number)
        return {
            "as_number": as_number,
            "is_rpki": is_rpki,
            "node_type": cls.get_node_type(as_number),
            "role": cls.get_role(as_number),
            "should_rate": not is_rpki,
            "is_peer": is_rpki,
            "port": cls.BASE_PORT + as_number if is_rpki else None
        }

    @classmethod
    def get_registry_info(cls) -> dict:
        """Get complete registry information."""
        cls._ensure_initialized()
        return {
            "total_rpki_nodes": cls.TOTAL_RPKI_NODES,
            "total_non_rpki_nodes": cls.TOTAL_NON_RPKI_NODES,
            "total_nodes": cls.TOTAL_NODES,
            "rpki_nodes": cls.get_all_rpki_nodes(),
            "base_port": cls.BASE_PORT,
            "dataset_path": cls._dataset_path,
            "description": "BGP-Sentry RPKI Validator Registry"
        }

    @classmethod
    def get_consensus_threshold(cls) -> int:
        """
        Calculate dynamic consensus threshold.

        BFT minimum is 3 signatures. For large networks we cap at 5 to keep
        the simulation practical while still demonstrating consensus.
        Formula: max(3, min(N // 3 + 1, 5))

        For caida_100 (58 RPKI): max(3, min(20, 5)) = 5
        For caida_1000 (366 RPKI): max(3, min(123, 5)) = 5
        """
        cls._ensure_initialized()
        return max(cfg.CONSENSUS_MIN_SIGNATURES,
                   min(cls.TOTAL_RPKI_NODES // 3 + 1, cfg.CONSENSUS_CAP_SIGNATURES))


# Convenience functions (module-level)
def is_rpki(as_number: int) -> bool:
    """Quick check if AS is RPKI validator."""
    return RPKINodeRegistry.is_rpki_node(as_number)


def is_non_rpki(as_number: int) -> bool:
    """Quick check if AS is non-RPKI."""
    return RPKINodeRegistry.is_non_rpki(as_number)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
        RPKINodeRegistry.initialize(dataset_path)
    else:
        print("Usage: python rpki_node_registry.py <dataset_path>")
        print("Running with legacy defaults...\n")

    info = RPKINodeRegistry.get_registry_info()
    print(f"Registry Information:")
    print(f"  Total RPKI nodes: {info['total_rpki_nodes']}")
    print(f"  Total non-RPKI nodes: {info['total_non_rpki_nodes']}")
    print(f"  Total nodes: {info['total_nodes']}")
    print(f"  Consensus threshold: {RPKINodeRegistry.get_consensus_threshold()}")
    print(f"  Dataset: {info['dataset_path'] or 'legacy'}")
