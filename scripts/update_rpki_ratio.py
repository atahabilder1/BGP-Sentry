#!/usr/bin/env python3
"""
Update RPKI ratio in dataset to match current real-world deployment (~55%).

Strategy:
  1. Un-demote: restore ASes that were naturally RPKI (demoted during normalization)
  2. Promote by degree: promote highest-degree non-RPKI ASes (transit providers)
     — realistic because large transit providers adopt RPKI first
  3. Verify: ensure no non-RPKI AS has zero RPKI neighbors

Usage:
    python3 scripts/update_rpki_ratio.py dataset/caida_50 0.55
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict


def get_as_degree(dataset_path):
    """Count how many direct neighbors each AS has from observation data."""
    obs_dir = Path(dataset_path) / "observations"
    degree = defaultdict(int)

    for f in sorted(obs_dir.glob("AS*.json")):
        with open(f) as fh:
            data = json.load(fh)
        observer = data["asn"]
        neighbors = set()
        for obs in data.get("observations", []):
            path = obs.get("as_path", [])
            if len(path) >= 2:
                neighbors.add(path[1])
        degree[observer] = len(neighbors)

    return degree


def update_rpki_ratio(dataset_path, target_ratio=0.55):
    """Update as_classification.json to match target RPKI ratio."""
    cls_path = Path(dataset_path) / "as_classification.json"
    with open(cls_path) as f:
        data = json.load(f)

    total = data["total_ases"]
    current_rpki = set(data["rpki_asns"])
    current_non_rpki = set(data["non_rpki_asns"])
    classification = data["classification"]

    target_rpki_count = int(total * target_ratio)
    need_to_promote = target_rpki_count - len(current_rpki)

    if need_to_promote <= 0:
        print(f"Already at or above target: {len(current_rpki)}/{total} = {len(current_rpki)/total*100:.1f}%")
        return

    print(f"Current: {len(current_rpki)} RPKI ({len(current_rpki)/total*100:.1f}%)")
    print(f"Target:  {target_rpki_count} RPKI ({target_ratio*100:.0f}%)")
    print(f"Need to promote: {need_to_promote}")

    # Step 1: Identify candidates for promotion
    # Priority 1: ASes that were naturally RPKI (demoted during normalization)
    # We don't have a direct list of demoted ASes, but rpki_natural_count tells us how many
    # For now, promote by degree (highest degree = transit providers = most realistic RPKI adopters)

    degree = get_as_degree(dataset_path)

    # Sort non-RPKI ASes by degree (highest first = transit providers)
    candidates = sorted(current_non_rpki, key=lambda asn: degree.get(asn, 0), reverse=True)

    promoted = []
    for asn in candidates:
        if len(promoted) >= need_to_promote:
            break
        promoted.append(asn)

    # Apply promotions
    new_rpki = current_rpki | set(promoted)
    new_non_rpki = current_non_rpki - set(promoted)

    # Update classification
    for asn in promoted:
        classification[str(asn)] = "RPKI"
        data["rpki_role"][str(asn)] = "blockchain_validator"

    data["rpki_asns"] = sorted(new_rpki)
    data["non_rpki_asns"] = sorted(new_non_rpki)
    data["rpki_count"] = len(new_rpki)
    data["non_rpki_count"] = len(new_non_rpki)
    data["rpki_target_ratio"] = target_ratio
    data["rpki_normalization"] = (
        f"Updated to {target_ratio*100:.0f}% to match 2025 global IPv4 ROA coverage. "
        f"Promoted {len(promoted)} highest-degree non-RPKI ASes (transit providers adopt first)."
    )

    # Step 2: Verify no non-RPKI AS has zero RPKI neighbors
    obs_dir = Path(dataset_path) / "observations"
    rpki_neighbors_count = defaultdict(int)

    for f in sorted(obs_dir.glob("AS*.json")):
        with open(f) as fh:
            obs_data = json.load(fh)
        observer = obs_data["asn"]
        if observer in new_non_rpki:
            for obs in obs_data.get("observations", []):
                path = obs.get("as_path", [])
                if len(path) >= 2 and path[1] in new_rpki:
                    rpki_neighbors_count[observer] += 1
                    break  # just need at least one

    no_rpki_neighbor = [asn for asn in new_non_rpki if rpki_neighbors_count.get(asn, 0) == 0]

    # Write updated classification
    with open(cls_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResult: {len(new_rpki)} RPKI ({len(new_rpki)/total*100:.1f}%), {len(new_non_rpki)} non-RPKI")
    print(f"Promoted {len(promoted)} ASes (by highest degree)")
    if promoted[:5]:
        print(f"  Top promoted: {promoted[:5]} (degrees: {[degree.get(a,0) for a in promoted[:5]]})")
    if no_rpki_neighbor:
        print(f"⚠️ {len(no_rpki_neighbor)} non-RPKI ASes still have no RPKI neighbor")
    else:
        print(f"✅ All non-RPKI ASes have at least one RPKI neighbor")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/update_rpki_ratio.py <dataset_path> [target_ratio]")
        return 1

    dataset_path = sys.argv[1]
    target_ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.55

    update_rpki_ratio(dataset_path, target_ratio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
