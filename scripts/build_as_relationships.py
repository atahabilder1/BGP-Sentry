#!/usr/bin/env python3
"""
Build AS relationships file from dataset observation data.

The CAIDA relationship data is embedded in each observation's
'recv_relationship' field (CUSTOMERS, PROVIDERS, PEERS, ORIGIN).
This script extracts it and builds the as_relationships.json
file that the route leak detector needs.

Usage:
    python3 scripts/build_as_relationships.py dataset/caida_50
    → Writes to blockchain_data/state/as_relationships.json
"""

import json
import sys
import os
from collections import defaultdict
from pathlib import Path


def build_relationships(dataset_path: str) -> dict:
    """Extract AS relationships from observation recv_relationship fields."""
    obs_dir = Path(dataset_path) / "observations"
    if not obs_dir.exists():
        print(f"Error: {obs_dir} not found")
        return {}

    relationships = defaultdict(lambda: {"customers": set(), "providers": set(), "peers": set()})

    for f in sorted(obs_dir.glob("AS*.json")):
        with open(f) as fh:
            data = json.load(fh)
        observer = data["asn"]

        for obs in data.get("observations", []):
            rel = obs.get("recv_relationship", "")
            next_hop = obs.get("next_hop_asn")

            if not next_hop or next_hop == observer:
                continue

            if rel == "CUSTOMERS":
                relationships[str(observer)]["customers"].add(next_hop)
                relationships[str(next_hop)]["providers"].add(observer)
            elif rel == "PROVIDERS":
                relationships[str(observer)]["providers"].add(next_hop)
                relationships[str(next_hop)]["customers"].add(observer)
            elif rel == "PEERS":
                relationships[str(observer)]["peers"].add(next_hop)
                relationships[str(next_hop)]["peers"].add(observer)

    # Convert sets to sorted lists for JSON
    result = {}
    for asn, rels in relationships.items():
        result[asn] = {
            "customers": sorted(rels["customers"]),
            "providers": sorted(rels["providers"]),
            "peers": sorted(rels["peers"]),
        }

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/build_as_relationships.py <dataset_path>")
        return 1

    dataset_path = sys.argv[1]
    rels = build_relationships(dataset_path)

    # Write to the location the detector expects
    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "blockchain_data" / "state" / "as_relationships.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(rels, f, indent=2)

    print(f"Built AS relationships: {len(rels)} ASes")
    print(f"Written to: {output_path}")

    # Stats
    total_c = sum(len(r["customers"]) for r in rels.values())
    total_p = sum(len(r["providers"]) for r in rels.values())
    total_pe = sum(len(r["peers"]) for r in rels.values())
    print(f"  Customer links: {total_c}")
    print(f"  Provider links: {total_p}")
    print(f"  Peer links: {total_pe}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
