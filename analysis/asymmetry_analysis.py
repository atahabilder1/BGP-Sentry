#!/usr/bin/env python3
"""
Quantify BGP observation asymmetry across vantage points.

For each unique (prefix, origin_asn) pair, measures how many of the total
observers actually see it — producing a distribution of "visibility fraction"
that quantifies the inherent asymmetry in BGP.

Also measures:
  - Path length variation (std dev of AS path lengths across observers)
  - Best-route disagreement (fraction of observers selecting it as best)
  - Attack visibility asymmetry (how many observers see each attack)
"""

import json
import os
import sys
import glob
from collections import defaultdict
import statistics

def load_observations(obs_dir, max_files=None):
    """Load all per-AS observation files."""
    files = sorted(glob.glob(os.path.join(obs_dir, "AS*.json")))
    if max_files:
        files = files[:max_files]

    all_obs = []
    as_count = 0
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        as_count += 1
        for obs in data.get("observations", []):
            obs["_file_asn"] = data["asn"]
            all_obs.append(obs)

    return all_obs, as_count


def analyze_asymmetry(obs_dir):
    print(f"Loading observations from: {obs_dir}")
    all_obs, total_ases = load_observations(obs_dir)
    print(f"  Total ASes (observers): {total_ases}")
    print(f"  Total observations: {len(all_obs):,}")

    # --- 1. Prefix visibility: how many observers see each (prefix, origin)? ---
    prefix_observers = defaultdict(set)       # (prefix, origin) -> set of observer ASNs
    prefix_paths = defaultdict(list)          # (prefix, origin) -> list of path lengths
    prefix_best = defaultdict(lambda: [0, 0]) # (prefix, origin) -> [best_count, total_count]
    attack_observers = defaultdict(set)       # (prefix, origin, attack_type) -> set of observers

    for obs in all_obs:
        key = (obs["prefix"], obs["origin_asn"])
        observer = obs.get("observed_by_asn") or obs["_file_asn"]
        prefix_observers[key].add(observer)
        prefix_paths[key].append(obs.get("as_path_length", 0))
        prefix_best[key][1] += 1
        if obs.get("is_best", False):
            prefix_best[key][0] += 1

        if obs.get("is_attack", False):
            akey = (obs["prefix"], obs["origin_asn"], obs.get("label", "UNKNOWN"))
            attack_observers[akey].add(observer)

    total_prefixes = len(prefix_observers)
    print(f"  Unique (prefix, origin) pairs: {total_prefixes:,}")

    # --- Visibility distribution ---
    visibility_fractions = []
    observer_counts = []
    for key, observers in prefix_observers.items():
        frac = len(observers) / total_ases
        visibility_fractions.append(frac)
        observer_counts.append(len(observers))

    print(f"\n{'='*60}")
    print("1. PREFIX VISIBILITY ASYMMETRY")
    print(f"{'='*60}")
    print(f"  Mean visibility fraction:   {statistics.mean(visibility_fractions):.3f}")
    print(f"  Median visibility fraction: {statistics.median(visibility_fractions):.3f}")
    print(f"  Std dev:                    {statistics.stdev(visibility_fractions):.3f}")
    print(f"  Min observers per prefix:   {min(observer_counts)}")
    print(f"  Max observers per prefix:   {max(observer_counts)}")

    # Histogram buckets
    buckets = [(0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 0.9), (0.9, 1.01)]
    print(f"\n  Visibility distribution:")
    for lo, hi in buckets:
        count = sum(1 for f in visibility_fractions if lo <= f < hi)
        pct = count / total_prefixes * 100
        label = f"  [{lo:.0%}-{hi:.0%})" if hi < 1.01 else f"  [{lo:.0%}-100%]"
        print(f"    {label:18s}: {count:6d} prefixes ({pct:5.1f}%)")

    # --- 2. Path length variation ---
    print(f"\n{'='*60}")
    print("2. PATH LENGTH VARIATION")
    print(f"{'='*60}")
    path_stddevs = []
    for key, lengths in prefix_paths.items():
        if len(lengths) >= 2:
            path_stddevs.append(statistics.stdev(lengths))

    if path_stddevs:
        print(f"  Mean path-length std dev:   {statistics.mean(path_stddevs):.2f} hops")
        print(f"  Median path-length std dev: {statistics.median(path_stddevs):.2f} hops")
        print(f"  Max path-length std dev:    {max(path_stddevs):.2f} hops")
        nonzero = sum(1 for s in path_stddevs if s > 0)
        print(f"  Prefixes with path variation: {nonzero}/{len(path_stddevs)} ({nonzero/len(path_stddevs)*100:.1f}%)")

    # --- 3. Best-route disagreement ---
    print(f"\n{'='*60}")
    print("3. BEST-ROUTE DISAGREEMENT")
    print(f"{'='*60}")
    best_fracs = []
    for key, (best_c, total_c) in prefix_best.items():
        if total_c > 0:
            best_fracs.append(best_c / total_c)

    print(f"  Mean best-route fraction:   {statistics.mean(best_fracs):.3f}")
    print(f"  Median best-route fraction: {statistics.median(best_fracs):.3f}")
    disagree = sum(1 for f in best_fracs if 0 < f < 1)
    print(f"  Prefixes with disagreement: {disagree}/{len(best_fracs)} ({disagree/len(best_fracs)*100:.1f}%)")

    # --- 4. Attack visibility asymmetry ---
    print(f"\n{'='*60}")
    print("4. ATTACK VISIBILITY ASYMMETRY")
    print(f"{'='*60}")
    if attack_observers:
        attack_vis = []
        for akey, observers in attack_observers.items():
            attack_vis.append(len(observers) / total_ases)

        print(f"  Total unique attacks: {len(attack_observers)}")
        print(f"  Mean attack visibility:   {statistics.mean(attack_vis):.3f}")
        print(f"  Median attack visibility: {statistics.median(attack_vis):.3f}")
        print(f"  Min attack visibility:    {min(attack_vis):.3f} ({int(min(attack_vis)*total_ases)} observers)")
        print(f"  Max attack visibility:    {max(attack_vis):.3f} ({int(max(attack_vis)*total_ases)} observers)")

        # Per attack type
        by_type = defaultdict(list)
        for (pfx, orig, atype), observers in attack_observers.items():
            by_type[atype].append(len(observers) / total_ases)

        print(f"\n  Per attack type:")
        for atype, fracs in sorted(by_type.items()):
            print(f"    {atype:25s}: mean vis={statistics.mean(fracs):.3f}, "
                  f"median={statistics.median(fracs):.3f}, count={len(fracs)}")
    else:
        print("  No attacks found in dataset.")

    # --- Return data for plotting ---
    return {
        "total_ases": total_ases,
        "visibility_fractions": visibility_fractions,
        "observer_counts": observer_counts,
        "path_stddevs": path_stddevs,
        "best_fracs": best_fracs,
        "attack_observers": {str(k): len(v) for k, v in attack_observers.items()},
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to scale 200
        base = os.path.join(os.path.dirname(__file__),
                            "..", "dataset", "bfsTopology")
        # Pick the largest available scale
        for scale in ["caida_bfs_174_200", "caida_bfs_174_150", "caida_bfs_174_100", "caida_bfs_174_50"]:
            obs_dir = os.path.join(base, scale, "observations")
            if os.path.isdir(obs_dir):
                break
        else:
            print("No dataset found. Pass observations dir as argument.")
            sys.exit(1)
    else:
        obs_dir = sys.argv[1]

    results = analyze_asymmetry(obs_dir)
