#!/usr/bin/env python3
"""
Build precomputed observer map for consensus optimization.

For each origin AS in the dataset, computes the set of RPKI validators
that will receive (or have received) announcements from that origin.
This lets the proposer target vote requests to peers with guaranteed
first-hand knowledge — eliminating warm-up dependency and reducing
SINGLE_WITNESS consensus outcomes at scale.

This is logically valid for real deployment: the AS-relationship graph
is public (CAIDA), and propagation reach is deterministic under Gao-
Rexford. Every RPKI validator can compute this map locally and refresh
it whenever the topology changes.

For the simulation we extract the map directly from BGPy-generated
observation files (which is equivalent to the Gao-Rexford propagation
result, since BGPy is what produced them).

Usage:
    python3 scripts/build_observer_map.py dataset/caida_200
    → Writes to blockchain_data/state/observer_map.json
"""

import json
import sys
import glob
from collections import defaultdict
from pathlib import Path


def build_observer_map(dataset_path: str) -> dict:
    """Extract origin_asn → set of RPKI validator ASNs that observe it."""
    dataset_path = Path(dataset_path)
    obs_dir = dataset_path / "observations"
    classification_file = dataset_path / "as_classification.json"

    if not obs_dir.exists():
        print(f"Error: {obs_dir} not found")
        return {}

    # Load RPKI classification for this dataset
    rpki_validators = set()
    if classification_file.exists():
        cls = json.load(open(classification_file))
        # as_classification.json has either a flat ASN → record mapping, or a
        # metadata record with rpki_count. We use the observation-file naming:
        # any AS with its own file is a participant; we cross-check RPKI status
        # inside the observation files themselves.
        pass

    # Iterate each observation file; the observation file has `is_rpki_node`
    observer_map = defaultdict(set)

    for f in sorted(obs_dir.glob("AS*.json")):
        data = json.load(open(f))
        observer_asn = data.get("asn")
        is_rpki = data.get("is_rpki_node", False)
        if not observer_asn or not is_rpki:
            # Only RPKI validators count as potential voters.
            continue

        rpki_validators.add(observer_asn)

        # For each announcement this observer saw, record the origin's
        # observer set. We count legitimate observations — attacks are
        # injected specifically and may not reflect normal propagation.
        for obs in data.get("observations", []):
            origin = obs.get("origin_asn")
            if origin is None or origin == observer_asn:
                continue
            observer_map[origin].add(observer_asn)

    # Convert sets to sorted lists for deterministic JSON output
    result = {
        str(origin): sorted(observers)
        for origin, observers in observer_map.items()
    }

    return result, rpki_validators


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/build_observer_map.py <dataset_path>")
        return 1

    dataset_path = sys.argv[1]
    observer_map, rpki_validators = build_observer_map(dataset_path)
    if not observer_map:
        return 1

    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "blockchain_data" / "state" / "observer_map.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(observer_map, f, indent=2)

    # Stats
    total_origins = len(observer_map)
    total_validators = len(rpki_validators)
    observers_per_origin = [len(v) for v in observer_map.values()]
    avg_obs = sum(observers_per_origin) / total_origins if total_origins else 0
    min_obs = min(observers_per_origin) if observers_per_origin else 0
    max_obs = max(observers_per_origin) if observers_per_origin else 0

    # Coverage analysis
    # Tau-reachable: origins with >= 2 observers (can achieve CONFIRMED at tau=2)
    tau = 2
    tau_reachable = sum(1 for n in observers_per_origin if n >= tau)

    print(f"Observer map: {total_origins} origins, {total_validators} RPKI validators")
    print(f"  Observers per origin: min={min_obs}, avg={avg_obs:.1f}, max={max_obs}")
    print(f"  Origins with ≥{tau} observers (CONFIRMED-reachable): "
          f"{tau_reachable} ({100*tau_reachable/total_origins:.1f}%)")
    print(f"Written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
