#!/usr/bin/env python3
"""
=============================================================================
Relevant Neighbor Cache - BGP Topology Intelligence
=============================================================================

Purpose: Map non-RPKI ASes to their first-hop RPKI neighbors based on
         observed BGP announcements.

Problem: Broadcasting vote requests to ALL 9 RPKI nodes is communication-heavy.

Solution: Build knowledge base mapping:
          non_RPKI_AS → [RPKI_neighbors_who_observe_it]

Example:
--------
AS100 (non-RPKI) announces 10.0.0.0/8
  - RPKI AS1 observes it (direct neighbor)
  - RPKI AS3 observes it (direct neighbor)
  - RPKI AS5 does NOT observe it (not neighbor)

Cache stores:
{
  "AS100": [1, 3]  ← Only ask AS1 and AS3 for votes about AS100
}

Benefits:
- Reduces vote requests from 9 to ~2-3 (typical AS peering)
- Faster consensus (less network overhead)
- More accurate (only nodes with direct knowledge vote)

Author: BGP-Sentry Team
=============================================================================
"""

import json
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional

# Import RPKI Node Registry
sys.path.insert(0, str(Path(__file__).parent.parent / "blockchain_utils"))
from rpki_node_registry import RPKINodeRegistry

class RelevantNeighborCache:
    """
    Maintains mapping of non-RPKI ASes to their RPKI neighbors.

    This cache is built from actual BGP observations:
    - When RPKI node observes announcement from non-RPKI AS
    - Records: "I am a first-hop neighbor of this AS"
    - Shares knowledge with other RPKI nodes
    """

    def __init__(self, cache_path: str, my_as_number: int):
        """
        Initialize relevant neighbor cache.

        Args:
            cache_path: Path to store cache file (network_stack folder)
            my_as_number: This RPKI node's AS number
        """
        self.cache_dir = Path(cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "relevant_neighbor_cache.json"
        self.my_as_number = my_as_number

        # Thread safety
        self.lock = threading.RLock()

        # Cache data structure
        self.cache_data = {
            "version": "1.0",
            "my_as_number": my_as_number,
            "last_updated": datetime.now().isoformat(),
            "non_rpki_to_rpki_neighbors": {},  # AS number -> [RPKI AS list]
            "observation_count": {},  # AS number -> count (confidence)
            "rpki_nodes": RPKINodeRegistry.get_all_rpki_nodes()  # All RPKI nodes from registry
        }

        # Load existing cache (runtime-accumulated observations)
        self._load_cache()

        # Also load precomputed observer map, if available. This gives every
        # proposer knowledge from transaction zero — avoiding the warm-up
        # dependency and the cold-start problem of the runtime cache.
        # In real deployment this map is derived from the public CAIDA graph
        # via deterministic Gao-Rexford propagation analysis; here we load
        # it from disk after being built by scripts/build_observer_map.py.
        self._load_precomputed_observer_map()

        print(f"📡 Relevant Neighbor Cache initialized for AS{my_as_number}")
        print(f"   Cache file: {self.cache_file}")
        print(f"   Non-RPKI ASes tracked: {len(self.cache_data['non_rpki_to_rpki_neighbors'])}")

    def _load_cache(self):
        """Load cache from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    loaded = json.load(f)
                    self.cache_data.update(loaded)
                print(f"📂 Loaded neighbor cache: {len(self.cache_data['non_rpki_to_rpki_neighbors'])} ASes")
            else:
                print(f"📂 Creating new neighbor cache")
        except Exception as e:
            print(f"Error loading cache: {e}")

    def _load_precomputed_observer_map(self):
        """Load precomputed observer map from blockchain_data/state/.

        The map is produced by scripts/build_observer_map.py before the
        experiment starts. It tells every proposer, for any origin AS,
        which RPKI validators are expected to have observed that origin's
        announcements — based on the topology alone, not runtime state.

        Merging this into the runtime cache means:
          - On first observation we already know who to ask (no warm-up gap).
          - Runtime observations can still refine the map (add newly-seen
            validators) but cannot remove precomputed entries.
        """
        try:
            # Search up the directory tree for blockchain_data/state
            # (we're under nodes/rpki_nodes/shared_blockchain_stack/network_stack)
            here = Path(__file__).resolve()
            project_root = None
            for parent in here.parents:
                candidate = parent / "blockchain_data" / "state" / "observer_map.json"
                if candidate.exists():
                    project_root = parent
                    break

            if project_root is None:
                print(f"📡 No precomputed observer map found (will learn at runtime)")
                return

            map_file = project_root / "blockchain_data" / "state" / "observer_map.json"
            with open(map_file, "r") as f:
                precomputed = json.load(f)

            with self.lock:
                merged_count = 0
                for as_str, observers in precomputed.items():
                    if as_str not in self.cache_data["non_rpki_to_rpki_neighbors"]:
                        self.cache_data["non_rpki_to_rpki_neighbors"][as_str] = []
                        self.cache_data["observation_count"][as_str] = 0

                    # Merge: union of existing + precomputed, exclude self
                    existing = set(self.cache_data["non_rpki_to_rpki_neighbors"][as_str])
                    precomp = set(observers) - {self.my_as_number}
                    merged = sorted(existing | precomp)

                    if merged != sorted(existing):
                        self.cache_data["non_rpki_to_rpki_neighbors"][as_str] = merged
                        merged_count += 1

            print(f"📡 Precomputed observer map loaded: {len(precomputed)} origins, "
                  f"{merged_count} entries updated")
        except Exception as e:
            print(f"Error loading precomputed observer map: {e}")

    def _save_cache(self):
        """Save cache to disk (atomic write)"""
        try:
            with self.lock:
                self.cache_data["last_updated"] = datetime.now().isoformat()

                # Atomic write
                temp_file = self.cache_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.cache_data, f, indent=2)
                temp_file.replace(self.cache_file)

        except Exception as e:
            print(f"Error saving cache: {e}")

    def record_observation(self, origin_as: int, observed_by_rpki_as: int = None):
        """
        Record that an AS (RPKI or non-RPKI) was observed by an RPKI node.

        Builds the mapping: origin_AS -> [RPKI neighbors that have seen it]
        This allows targeted peer selection when voting — ask peers who
        are likely to have knowledge about this origin AS.

        Args:
            origin_as: AS number that made the announcement (any AS)
            observed_by_rpki_as: RPKI AS that observed it (defaults to self)
        """
        if observed_by_rpki_as is None:
            observed_by_rpki_as = self.my_as_number

        # Don't record self-observation (a node observing itself)
        if origin_as == observed_by_rpki_as:
            return

        try:
            with self.lock:
                as_str = str(origin_as)

                # Initialize if new AS
                if as_str not in self.cache_data["non_rpki_to_rpki_neighbors"]:
                    self.cache_data["non_rpki_to_rpki_neighbors"][as_str] = []
                    self.cache_data["observation_count"][as_str] = 0

                # Add RPKI observer if not already recorded
                if observed_by_rpki_as not in self.cache_data["non_rpki_to_rpki_neighbors"][as_str]:
                    self.cache_data["non_rpki_to_rpki_neighbors"][as_str].append(observed_by_rpki_as)
                    self.cache_data["non_rpki_to_rpki_neighbors"][as_str].sort()

                # Increment observation count (confidence metric)
                self.cache_data["observation_count"][as_str] += 1

                # Save periodically (every 10 observations)
                if self.cache_data["observation_count"][as_str] % 10 == 0:
                    self._save_cache()

        except Exception as e:
            print(f"Error recording observation: {e}")

    def get_relevant_neighbors(self, origin_as: int) -> List[int]:
        """
        Get list of RPKI nodes that are relevant for voting on this AS.

        Returns RPKI nodes that have observed announcements from this AS
        (works for both RPKI and non-RPKI origin ASes).
        Falls back to all RPKI nodes if no cache entry exists.

        Args:
            origin_as: AS number (RPKI or non-RPKI)

        Returns:
            List of RPKI AS numbers to ask for votes
        """
        try:
            with self.lock:
                as_str = str(origin_as)

                # Check cache
                if as_str in self.cache_data["non_rpki_to_rpki_neighbors"]:
                    neighbors = self.cache_data["non_rpki_to_rpki_neighbors"][as_str]

                    if neighbors:
                        return neighbors

                # Cache miss - fall back to all RPKI nodes (except self)
                all_nodes = [n for n in self.cache_data["rpki_nodes"] if n != self.my_as_number]
                return all_nodes

        except Exception as e:
            # Fallback to all nodes on error
            return [n for n in self.cache_data["rpki_nodes"] if n != self.my_as_number]

    def is_relevant_for_as(self, origin_as: int, rpki_as: int) -> bool:
        """
        Check if specific RPKI node is relevant for voting on this AS.

        Args:
            origin_as: AS in question (RPKI or non-RPKI)
            rpki_as: RPKI AS to check

        Returns:
            True if this RPKI node should vote on this AS
        """
        relevant = self.get_relevant_neighbors(origin_as)
        return rpki_as in relevant

    def get_cache_statistics(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total_ases = len(self.cache_data["non_rpki_to_rpki_neighbors"])
            total_observations = sum(self.cache_data["observation_count"].values())

            # Calculate average neighbors per AS
            neighbor_counts = [
                len(neighbors)
                for neighbors in self.cache_data["non_rpki_to_rpki_neighbors"].values()
            ]
            avg_neighbors = sum(neighbor_counts) / len(neighbor_counts) if neighbor_counts else 0

            return {
                "total_non_rpki_ases": total_ases,
                "total_observations": total_observations,
                "average_neighbors_per_as": avg_neighbors,
                "cache_file": str(self.cache_file),
                "last_updated": self.cache_data["last_updated"]
            }

    def import_peer_knowledge(self, peer_cache_data: Dict):
        """
        Import knowledge from another RPKI node's cache.

        This allows RPKI nodes to share their topology knowledge.

        Args:
            peer_cache_data: Cache data from peer node
        """
        try:
            with self.lock:
                peer_mappings = peer_cache_data.get("non_rpki_to_rpki_neighbors", {})

                for as_str, rpki_neighbors in peer_mappings.items():
                    if as_str not in self.cache_data["non_rpki_to_rpki_neighbors"]:
                        self.cache_data["non_rpki_to_rpki_neighbors"][as_str] = []

                    # Merge neighbor lists
                    current = set(self.cache_data["non_rpki_to_rpki_neighbors"][as_str])
                    new_neighbors = set(rpki_neighbors)
                    merged = current.union(new_neighbors)

                    self.cache_data["non_rpki_to_rpki_neighbors"][as_str] = sorted(list(merged))

                self._save_cache()
                print(f"📥 Imported peer knowledge: {len(peer_mappings)} AS mappings")

        except Exception as e:
            print(f"Error importing peer knowledge: {e}")

    def export_knowledge(self) -> Dict:
        """
        Export this node's cache for sharing with peers.

        Returns:
            Cache data dict
        """
        with self.lock:
            return {
                "non_rpki_to_rpki_neighbors": self.cache_data["non_rpki_to_rpki_neighbors"],
                "observation_count": self.cache_data["observation_count"],
                "exporter_as": self.my_as_number,
                "exported_at": datetime.now().isoformat()
            }

    def cleanup_stale_entries(self, days_threshold: int = 30):
        """
        Remove cache entries for ASes not seen in N days.

        Args:
            days_threshold: Days of inactivity before removal
        """
        # This would require tracking last_seen timestamp
        # For now, just save cache
        self._save_cache()
        print(f"💾 Cache saved with {len(self.cache_data['non_rpki_to_rpki_neighbors'])} entries")


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("RELEVANT NEIGHBOR CACHE - TEST")
    print("=" * 80)
    print()

    # Initialize cache for AS1
    cache = RelevantNeighborCache(
        cache_path="/home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/network_stack",
        my_as_number=1
    )

    # Simulate observations
    print("\n🧪 Test 1: Record observations")
    print("-" * 40)
    cache.record_observation(non_rpki_as=100, observed_by_rpki_as=1)
    cache.record_observation(non_rpki_as=100, observed_by_rpki_as=3)
    cache.record_observation(non_rpki_as=100, observed_by_rpki_as=5)

    cache.record_observation(non_rpki_as=200, observed_by_rpki_as=7)
    cache.record_observation(non_rpki_as=200, observed_by_rpki_as=9)

    # Query relevant neighbors
    print("\n🧪 Test 2: Query relevant neighbors")
    print("-" * 40)
    neighbors_100 = cache.get_relevant_neighbors(100)
    print(f"AS100 relevant neighbors: {neighbors_100}")

    neighbors_200 = cache.get_relevant_neighbors(200)
    print(f"AS200 relevant neighbors: {neighbors_200}")

    neighbors_999 = cache.get_relevant_neighbors(999)  # Not in cache
    print(f"AS999 relevant neighbors: {neighbors_999} (fallback to all)")

    # Statistics
    print("\n🧪 Test 3: Cache statistics")
    print("-" * 40)
    stats = cache.get_cache_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ Test complete!")
