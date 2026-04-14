#!/usr/bin/env python3
"""
Fix dataset announcement frequency — remove unrealistic re-announcements.

Problem: BGPy's Weibull sampler causes each (prefix, origin) pair to be
observed ~600 times per node, when in real BGP it would be observed ONCE
(announcement arrives, stays in routing table, no re-announcement).

Fix: For each observer AS, keep only the FIRST observation of each
(prefix, origin) pair. This preserves:
  - Natural propagation delay (different nodes see it at different times)
  - All unique (prefix, origin) events
  - All attack types (first occurrence per observer)
  - Realistic per-node observation count

Usage:
    python3 scripts/fix_dataset_frequency.py dataset/caida_50
    python3 scripts/fix_dataset_frequency.py all
"""

import json
import os
import sys
from pathlib import Path


def fix_dataset(dataset_path):
    """Remove duplicate (prefix, origin) observations per observer."""
    obs_dir = Path(dataset_path) / "observations"
    if not obs_dir.exists():
        print(f"Error: {obs_dir} not found")
        return

    dataset_name = Path(dataset_path).name
    total_before = 0
    total_after = 0
    total_attacks_before = 0
    total_attacks_after = 0

    for f in sorted(obs_dir.glob("AS*.json")):
        with open(f) as fh:
            data = json.load(fh)

        observations = data.get("observations", [])
        total_before += len(observations)
        total_attacks_before += sum(1 for o in observations if o.get("is_attack"))

        # Sort by timestamp to keep the FIRST occurrence
        sorted_obs = sorted(observations, key=lambda o: o.get("timestamp", 0))

        # Keep only first (prefix, origin) per observer
        seen = set()
        filtered = []
        for obs in sorted_obs:
            key = (obs.get("prefix"), obs.get("origin_asn"))
            if key not in seen:
                seen.add(key)
                filtered.append(obs)

        total_after += len(filtered)
        total_attacks_after += sum(1 for o in filtered if o.get("is_attack"))

        # Update the file
        data["observations"] = filtered
        data["total_observations"] = len(filtered)

        # Update sub-counts
        data["attack_observations"] = sum(1 for o in filtered if o.get("is_attack"))
        data["legitimate_observations"] = sum(1 for o in filtered if not o.get("is_attack"))
        data["best_route_observations"] = sum(1 for o in filtered if o.get("is_best", False))
        data["alternative_route_observations"] = len(filtered) - data["best_route_observations"]

        with open(f, "w") as fh:
            json.dump(data, fh, indent=2)

    reduction = (1 - total_after / max(total_before, 1)) * 100
    print(f"{dataset_name}:")
    print(f"  Before: {total_before:>12,} observations ({total_attacks_before:,} attacks)")
    print(f"  After:  {total_after:>12,} observations ({total_attacks_after:,} attacks)")
    print(f"  Reduction: {reduction:.1f}%")
    print(f"  Per-node avg: {total_before // 48:,} → {total_after // 48:,}")

    # Update ground truth attack count to match
    gt_path = Path(dataset_path) / "ground_truth" / "ground_truth.json"
    if gt_path.exists():
        gt = json.load(open(gt_path))
        gt["total_attacks"] = total_attacks_after

        # Recount by type from filtered observations
        from collections import Counter
        attack_types = Counter()
        for f in sorted(obs_dir.glob("AS*.json")):
            data = json.load(open(f))
            for obs in data.get("observations", []):
                if obs.get("is_attack"):
                    attack_types[obs.get("label", "UNKNOWN")] += 1
        gt["attack_types"] = dict(attack_types)

        with open(gt_path, "w") as fh:
            json.dump(gt, fh, indent=2)
        print(f"  Ground truth updated: {total_attacks_after} attacks")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fix_dataset_frequency.py <dataset_path|all>")
        return 1

    if sys.argv[1] == "all":
        project_root = Path(__file__).resolve().parent.parent
        dataset_dir = project_root / "dataset"
        for name in ["caida_50", "caida_100", "caida_200", "caida_350", "caida_650", "caida_1250"]:
            path = dataset_dir / name
            if path.exists():
                fix_dataset(str(path))
    else:
        fix_dataset(sys.argv[1])

    return 0


if __name__ == "__main__":
    sys.exit(main())
