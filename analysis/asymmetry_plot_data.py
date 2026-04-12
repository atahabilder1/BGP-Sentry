#!/usr/bin/env python3
"""
Generate asymmetry plot data across all dataset scales.

Produces:
1. Per-(prefix,origin): fraction of observers that see it (legitimate vs attack)
2. Per-attack-type visibility distribution
3. Path diversity metrics
4. Cross-scale comparison

Output: CSV files for pgfplots and summary statistics.
"""

import json
import os
import sys
import glob
import csv
from collections import defaultdict
import statistics

DATASET_BASE = os.path.join(os.path.dirname(__file__), "..", "dataset", "bfsTopology")
SCALES = [50, 100, 150, 200, 400, 800, 1200]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "menuscript", "IEEEtran", "data")


def analyze_scale(scale):
    obs_dir = os.path.join(DATASET_BASE, f"caida_bfs_174_{scale}", "observations")
    if not os.path.isdir(obs_dir):
        print(f"  Scale {scale}: directory not found, skipping")
        return None

    files = sorted(glob.glob(os.path.join(obs_dir, "AS*.json")))
    total_ases = len(files)
    print(f"  Scale {scale}: {total_ases} ASes, loading...", end=" ", flush=True)

    # Per (prefix, origin) tracking
    prefix_observers = defaultdict(set)          # (pfx, orig) -> observers
    prefix_is_attack = defaultdict(set)          # (pfx, orig) -> set of attack labels (empty if legit)
    prefix_paths = defaultdict(lambda: defaultdict(list))  # (pfx, orig) -> {observer: [path_lengths]}
    prefix_as_paths = defaultdict(lambda: set()) # (pfx, orig) -> set of unique AS paths

    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        observer = data["asn"]
        for obs in data.get("observations", []):
            key = (obs["prefix"], obs["origin_asn"])
            prefix_observers[key].add(observer)

            # Track unique AS paths (as tuples for hashing)
            as_path = obs.get("as_path", [])
            if as_path:
                prefix_as_paths[key].add(tuple(as_path))

            path_len = obs.get("as_path_length", 0)
            prefix_paths[key][observer].append(path_len)

            if obs.get("is_attack", False):
                prefix_is_attack[key].add(obs.get("label", "ATTACK"))

    print(f"{len(prefix_observers)} unique (prefix,origin) pairs")

    # Compute metrics
    results = {
        "scale": scale,
        "total_ases": total_ases,
        "legitimate": [],    # list of visibility fractions for legit prefixes
        "attack": {},        # attack_type -> list of visibility fractions
        "all_visibility": [],  # (visibility_frac, is_attack, attack_type, num_unique_paths)
        "path_diversity": [], # (num_unique_paths, visibility_frac, is_attack)
    }

    for key, observers in prefix_observers.items():
        vis_frac = len(observers) / total_ases
        attack_types = prefix_is_attack.get(key, set())
        num_unique_paths = len(prefix_as_paths.get(key, set()))

        if attack_types:
            for atype in attack_types:
                results["attack"].setdefault(atype, []).append(vis_frac)
                results["all_visibility"].append((vis_frac, True, atype, num_unique_paths))
        else:
            results["legitimate"].append(vis_frac)
            results["all_visibility"].append((vis_frac, False, "LEGITIMATE", num_unique_paths))

        results["path_diversity"].append((num_unique_paths, vis_frac, bool(attack_types)))

    return results


def write_csv_files(all_results):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # === 1. Cross-scale summary (for grouped bar chart) ===
    with open(os.path.join(OUTPUT_DIR, "asymmetry_cross_scale.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scale", "category", "mean_visibility", "median_visibility",
                     "std_visibility", "min_visibility", "count"])
        for r in all_results:
            s = r["scale"]
            # Legitimate
            if r["legitimate"]:
                w.writerow([s, "LEGITIMATE",
                            f"{statistics.mean(r['legitimate']):.4f}",
                            f"{statistics.median(r['legitimate']):.4f}",
                            f"{statistics.stdev(r['legitimate']):.4f}" if len(r['legitimate']) > 1 else "0",
                            f"{min(r['legitimate']):.4f}",
                            len(r["legitimate"])])
            # Per attack type
            for atype, fracs in sorted(r["attack"].items()):
                w.writerow([s, atype,
                            f"{statistics.mean(fracs):.4f}",
                            f"{statistics.median(fracs):.4f}",
                            f"{statistics.stdev(fracs):.4f}" if len(fracs) > 1 else "0",
                            f"{min(fracs):.4f}",
                            len(fracs)])

    # === 2. Visibility CDF data (for the main figure, use scale 400) ===
    for r in all_results:
        s = r["scale"]
        fname = os.path.join(OUTPUT_DIR, f"visibility_cdf_{s}.csv")
        with open(fname, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["visibility_fraction", "is_attack", "category"])
            for vis, is_atk, atype, _ in sorted(r["all_visibility"]):
                w.writerow([f"{vis:.4f}", int(is_atk), atype])

    # === 3. Path diversity data ===
    for r in all_results:
        s = r["scale"]
        fname = os.path.join(OUTPUT_DIR, f"path_diversity_{s}.csv")
        with open(fname, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["num_unique_paths", "visibility_fraction", "is_attack"])
            for npaths, vis, is_atk in sorted(r["path_diversity"], reverse=True):
                w.writerow([npaths, f"{vis:.4f}", int(is_atk)])

    print(f"\nCSV files written to: {OUTPUT_DIR}")


def print_summary(all_results):
    print(f"\n{'='*70}")
    print("CROSS-SCALE ASYMMETRY SUMMARY")
    print(f"{'='*70}")

    # Header
    categories = ["LEGITIMATE", "PREFIX_HIJACK", "SUBPREFIX_HIJACK", "BOGON_INJECTION", "ROUTE_FLAPPING"]
    print(f"\n{'Scale':>6}", end="")
    for cat in categories:
        short = cat[:10]
        print(f" | {short:>12}", end="")
    print()
    print("-" * 80)

    for r in all_results:
        print(f"{r['scale']:>6}", end="")
        # Legitimate
        if r["legitimate"]:
            mean_v = statistics.mean(r["legitimate"])
            print(f" | {mean_v:>11.1%}", end="")
        else:
            print(f" | {'N/A':>12}", end="")
        # Attacks
        for atype in categories[1:]:
            fracs = r["attack"].get(atype, [])
            if fracs:
                mean_v = statistics.mean(fracs)
                print(f" | {mean_v:>11.1%}", end="")
            else:
                print(f" | {'N/A':>12}", end="")
        print()

    # Path diversity summary
    print(f"\n{'='*70}")
    print("PATH DIVERSITY (unique AS paths per prefix)")
    print(f"{'='*70}")
    for r in all_results:
        paths_legit = [p for p, _, is_atk in r["path_diversity"] if not is_atk]
        paths_attack = [p for p, _, is_atk in r["path_diversity"] if is_atk]
        print(f"  Scale {r['scale']:>5}: "
              f"Legit mean={statistics.mean(paths_legit):.1f} paths, "
              f"max={max(paths_legit)}, "
              f"Attack mean={statistics.mean(paths_attack):.1f} paths, "
              f"max={max(paths_attack)}" if paths_attack else "")


if __name__ == "__main__":
    all_results = []
    for scale in SCALES:
        r = analyze_scale(scale)
        if r:
            all_results.append(r)

    if not all_results:
        print("No datasets found!")
        sys.exit(1)

    write_csv_files(all_results)
    print_summary(all_results)
