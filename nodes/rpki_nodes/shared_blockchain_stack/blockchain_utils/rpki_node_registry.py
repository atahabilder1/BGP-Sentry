#!/usr/bin/env python3
"""
=============================================================================
RPKI Node Registry - Centralized RPKI Node Identification
=============================================================================

Purpose: Maintain authoritative list of RPKI validator nodes and provide
         functions to check if an AS is RPKI or non-RPKI.

Problem: Currently no centralized way to check if AS is RPKI or not.
         RPKI node list is hardcoded in multiple places.

Solution: Single source of truth for RPKI node identification.

Author: BGP-Sentry Team
=============================================================================
"""

from typing import List, Set

class RPKINodeRegistry:
    """
    Central registry of RPKI validator nodes.

    Provides authoritative list of RPKI nodes and validation functions.
    """

    # AUTHORITATIVE LIST: All RPKI validator nodes in the network
    RPKI_NODES: Set[int] = {1, 3, 5, 7, 9, 11, 13, 15, 17}

    # Total count
    TOTAL_RPKI_NODES = len(RPKI_NODES)

    # Base port for P2P communication
    BASE_PORT = 8000

    @classmethod
    def is_rpki_node(cls, as_number: int) -> bool:
        """
        Check if given AS number is an RPKI validator node.

        Args:
            as_number: AS number to check

        Returns:
            True if AS is RPKI validator, False if non-RPKI

        Examples:
            >>> RPKINodeRegistry.is_rpki_node(1)
            True
            >>> RPKINodeRegistry.is_rpki_node(100)
            False
        """
        return as_number in cls.RPKI_NODES

    @classmethod
    def is_non_rpki(cls, as_number: int) -> bool:
        """
        Check if given AS number is a non-RPKI autonomous system.

        Args:
            as_number: AS number to check

        Returns:
            True if AS is non-RPKI, False if RPKI validator

        Examples:
            >>> RPKINodeRegistry.is_non_rpki(100)
            True
            >>> RPKINodeRegistry.is_non_rpki(1)
            False
        """
        return as_number not in cls.RPKI_NODES

    @classmethod
    def get_all_rpki_nodes(cls) -> List[int]:
        """
        Get list of all RPKI validator AS numbers.

        Returns:
            Sorted list of RPKI AS numbers
        """
        return sorted(list(cls.RPKI_NODES))

    @classmethod
    def get_peer_nodes(cls, my_as_number: int) -> dict:
        """
        Get peer RPKI nodes (excluding self).

        Args:
            my_as_number: This node's AS number

        Returns:
            Dict mapping AS number to (host, port) tuple
        """
        peers = {}
        for as_num in cls.RPKI_NODES:
            if as_num != my_as_number:
                port = cls.BASE_PORT + as_num
                peers[as_num] = ("localhost", port)
        return peers

    @classmethod
    def get_node_count(cls) -> int:
        """Get total number of RPKI validator nodes."""
        return cls.TOTAL_RPKI_NODES

    @classmethod
    def should_apply_rating(cls, as_number: int) -> bool:
        """
        Check if rating system should be applied to this AS.

        RPKI nodes: Use behavioral analysis (monthly)
        Non-RPKI nodes: Use rating system (instant + monthly)

        Args:
            as_number: AS number to check

        Returns:
            True if rating system should apply (non-RPKI), False otherwise
        """
        return cls.is_non_rpki(as_number)

    @classmethod
    def get_node_type(cls, as_number: int) -> str:
        """
        Get human-readable node type.

        Args:
            as_number: AS number to check

        Returns:
            "RPKI_VALIDATOR" or "NON_RPKI"
        """
        return "RPKI_VALIDATOR" if cls.is_rpki_node(as_number) else "NON_RPKI"

    @classmethod
    def validate_as_number(cls, as_number: int) -> dict:
        """
        Comprehensive validation of AS number.

        Args:
            as_number: AS number to validate

        Returns:
            Dict with validation results:
            {
                "as_number": int,
                "is_rpki": bool,
                "node_type": str,
                "should_rate": bool,
                "is_peer": bool,
                "port": int (if RPKI)
            }
        """
        is_rpki = cls.is_rpki_node(as_number)

        return {
            "as_number": as_number,
            "is_rpki": is_rpki,
            "node_type": cls.get_node_type(as_number),
            "should_rate": not is_rpki,  # Rate non-RPKI only
            "is_peer": is_rpki,  # RPKI nodes are peers
            "port": cls.BASE_PORT + as_number if is_rpki else None
        }

    @classmethod
    def get_registry_info(cls) -> dict:
        """
        Get complete registry information.

        Returns:
            Dict with registry details
        """
        return {
            "total_rpki_nodes": cls.TOTAL_RPKI_NODES,
            "rpki_nodes": cls.get_all_rpki_nodes(),
            "base_port": cls.BASE_PORT,
            "description": "BGP-Sentry RPKI Validator Registry"
        }


# Convenience functions (module-level)
def is_rpki(as_number: int) -> bool:
    """
    Quick check if AS is RPKI validator.

    Args:
        as_number: AS number to check

    Returns:
        True if RPKI validator
    """
    return RPKINodeRegistry.is_rpki_node(as_number)


def is_non_rpki(as_number: int) -> bool:
    """
    Quick check if AS is non-RPKI.

    Args:
        as_number: AS number to check

    Returns:
        True if non-RPKI
    """
    return RPKINodeRegistry.is_non_rpki(as_number)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("RPKI NODE REGISTRY - TEST")
    print("=" * 80)
    print()

    # Show registry info
    info = RPKINodeRegistry.get_registry_info()
    print(f"📋 Registry Information:")
    print(f"   Total RPKI nodes: {info['total_rpki_nodes']}")
    print(f"   RPKI nodes: {info['rpki_nodes']}")
    print(f"   Base port: {info['base_port']}")
    print()

    # Test RPKI nodes
    print("🧪 Testing RPKI Nodes:")
    print("-" * 40)
    for as_num in [1, 3, 5, 7, 9]:
        result = RPKINodeRegistry.validate_as_number(as_num)
        print(f"AS{as_num}:")
        print(f"  Type: {result['node_type']}")
        print(f"  Is RPKI: {result['is_rpki']}")
        print(f"  Should rate: {result['should_rate']}")
        print(f"  Port: {result['port']}")
        print()

    # Test non-RPKI nodes
    print("🧪 Testing Non-RPKI Nodes:")
    print("-" * 40)
    for as_num in [100, 200, 666, 15169]:
        result = RPKINodeRegistry.validate_as_number(as_num)
        print(f"AS{as_num}:")
        print(f"  Type: {result['node_type']}")
        print(f"  Is RPKI: {result['is_rpki']}")
        print(f"  Should rate: {result['should_rate']}")
        print()

    # Test convenience functions
    print("🧪 Testing Convenience Functions:")
    print("-" * 40)
    print(f"is_rpki(1): {is_rpki(1)}")
    print(f"is_rpki(100): {is_rpki(100)}")
    print(f"is_non_rpki(1): {is_non_rpki(1)}")
    print(f"is_non_rpki(666): {is_non_rpki(666)}")
    print()

    # Get peer nodes for AS1
    print("🧪 Getting Peer Nodes for AS1:")
    print("-" * 40)
    peers = RPKINodeRegistry.get_peer_nodes(1)
    for as_num, (host, port) in sorted(peers.items()):
        print(f"  AS{as_num}: {host}:{port}")
    print()

    print("✅ All tests complete!")
