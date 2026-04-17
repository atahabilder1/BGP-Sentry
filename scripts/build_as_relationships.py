#!/usr/bin/env python3
"""
Build AS relationships file using the authoritative CAIDA AS-relationship
dataset via BGPy's CAIDAASGraphConstructor.

This is the source of truth — CAIDA's inferred relationships are
unambiguous (each AS pair has exactly one relationship: customer, provider,
or peer). Earlier versions of this script tried to infer relationships
from BGPy's per-observation `recv_relationship` field, which is route-
specific and varies across observations for the same AS pair.

Usage:
    python3 scripts/build_as_relationships.py dataset/caida_50
    → Writes to blockchain_data/state/as_relationships.json
    → Contains only the ASes actually present in the dataset
"""

import json
import os
import sys
import contextlib
from pathlib import Path

# Make BGPy importable
sys.path.insert(0, "/data/anik/bgpy_pkg")


def build_relationships(dataset_path: str) -> dict:
    """Extract canonical CAIDA AS-relationships for the ASes in the dataset."""
    dataset_path = Path(dataset_path)
    classification_file = dataset_path / "as_classification.json"
    if not classification_file.exists():
        print(f"Error: {classification_file} not found")
        return {}

    # Load the set of ASes present in this dataset
    classification = json.load(open(classification_file))
    dataset_asns = {
        int(k) for k in classification.keys()
        if k.isdigit() or (k.startswith("AS") and k[2:].isdigit())
    }
    # as_classification.json has scalar metadata keys too — extract just the ASN keys
    dataset_asns = set()
    obs_dir = dataset_path / "observations"
    if obs_dir.exists():
        for f in obs_dir.glob("AS*.json"):
            # Filename is AS<digits>.json
            stem = f.stem  # e.g., "AS10075"
            if stem.startswith("AS"):
                try:
                    dataset_asns.add(int(stem[2:]))
                except ValueError:
                    continue

    if not dataset_asns:
        print(f"Error: no ASes found in {obs_dir}")
        return {}

    print(f"Dataset contains {len(dataset_asns)} ASes")
    print(f"Loading CAIDA AS-graph (this may take a minute)...")

    # Load the full CAIDA AS graph via BGPy
    with contextlib.redirect_stdout(open(os.devnull, "w")):
        from bgpy.as_graphs import CAIDAASGraphConstructor
        as_graph = CAIDAASGraphConstructor().run()

    print(f"Loaded {len(as_graph.as_dict)} ASes from CAIDA")

    # For each AS in our dataset, extract relationships restricted to other
    # dataset ASes (relationships to ASes outside the subgraph are irrelevant
    # because they never appear in AS-paths).
    result = {}
    for asn in dataset_asns:
        as_obj = as_graph.as_dict.get(asn)
        if as_obj is None:
            result[str(asn)] = {"customers": [], "providers": [], "peers": []}
            continue

        customers = sorted(
            a.asn for a in getattr(as_obj, "customers", [])
            if a.asn in dataset_asns
        )
        providers = sorted(
            a.asn for a in getattr(as_obj, "providers", [])
            if a.asn in dataset_asns
        )
        peers = sorted(
            a.asn for a in getattr(as_obj, "peers", [])
            if a.asn in dataset_asns
        )

        result[str(asn)] = {
            "customers": customers,
            "providers": providers,
            "peers": peers,
        }

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/build_as_relationships.py <dataset_path>")
        return 1

    dataset_path = sys.argv[1]
    rels = build_relationships(dataset_path)
    if not rels:
        return 1

    # Write to the location the detector expects
    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "blockchain_data" / "state" / "as_relationships.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(rels, f, indent=2)

    print(f"\nBuilt AS relationships: {len(rels)} ASes")
    print(f"Written to: {output_path}")

    # Stats
    total_c = sum(len(r["customers"]) for r in rels.values())
    total_p = sum(len(r["providers"]) for r in rels.values())
    total_pe = sum(len(r["peers"]) for r in rels.values())

    # Consistency check
    conflicts = 0
    for r in rels.values():
        c = set(r["customers"])
        p = set(r["providers"])
        pe = set(r["peers"])
        conflicts += len(c & p) + len(c & pe) + len(p & pe)

    # Mirror check: customer count should equal provider count (every customer
    # relationship on one side is a provider relationship on the other).
    # Peer count should be even (every peer link is counted twice).
    print(f"  Customer links: {total_c}")
    print(f"  Provider links: {total_p}   (should equal customer links)")
    print(f"  Peer links: {total_pe}       (should be even)")
    print(f"  Ambiguous entries: {conflicts}   (should be 0)")

    # ASes with no relationships inside the subgraph
    orphans = sum(1 for r in rels.values() if not any(r.values()))
    if orphans:
        print(f"  Isolated ASes (no neighbors in subgraph): {orphans}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
