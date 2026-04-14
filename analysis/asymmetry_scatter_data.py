#!/usr/bin/env python3
"""
Generate scatter plot data: topological reach vs temporal reach
for each (prefix, origin) pair, colored by category.
"""

import json
import os
import glob
from collections import defaultdict
import csv

DATASET_BASE = os.path.join(os.path.dirname(__file__), "..", "dataset", "bfsTopology")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "menuscript", "IEEEtran", "data")

def analyze(scale=400, window=10):
    obs_dir = os.path.join(DATASET_BASE, f"caida_bfs_174_{scale}", "observations")
    gt_dir = os.path.join(DATASET_BASE, f"caida_bfs_174_{scale}", "ground_truth")

    with open(os.path.join(gt_dir, "as_classification.json")) as f:
        classify = json.load(f)

    rpki_set = set(classify["rpki_asns"])
    total_rpki = len(rpki_set)
    print(f"Scale {scale}: {total_rpki} RPKI validators")

    # Collect per (prefix, origin): {observer: earliest_timestamp, ...}
    prefix_data = defaultdict(dict)  # key -> {observer: {ts, label}}

    files = sorted(glob.glob(os.path.join(obs_dir, "AS*.json")))
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        observer = data["asn"]
        if observer not in rpki_set:
            continue  # only RPKI observers
        for obs in data.get("observations", []):
            if obs.get("is_withdrawal", False):
                continue
            key = (obs["prefix"], obs["origin_asn"])
            ts = obs["timestamp"]
            label = obs.get("label", "LEGITIMATE")

            if observer not in prefix_data[key]:
                prefix_data[key][observer] = {"ts": ts, "label": label}
            else:
                if ts < prefix_data[key][observer]["ts"]:
                    prefix_data[key][observer]["ts"] = ts

    print(f"  {len(prefix_data)} unique (prefix, origin) pairs seen by RPKI observers")

    # Compute scatter data
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fname = os.path.join(OUTPUT_DIR, f"scatter_{scale}.csv")

    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["topological_pct", "temporal_pct", "category", "num_observers"])

        for key, observers in prefix_data.items():
            # Topological reach: how many RPKI observers see it at all
            topo_count = len(observers)
            topo_pct = topo_count / total_rpki * 100

            # Determine category
            labels = set(d["label"] for d in observers.values())
            category = "LEGITIMATE"
            for l in labels:
                if l != "LEGITIMATE":
                    category = l
                    break

            # Temporal reach: for each observer as proposer,
            # how many other RPKI observers received it within window?
            timestamps = sorted([(d["ts"], asn) for asn, d in observers.items()])

            # Use median proposer
            temporal_fracs = []
            for i, (t_prop, proposer) in enumerate(timestamps):
                peers_in_window = sum(
                    1 for t_peer, peer in timestamps
                    if peer != proposer and t_peer <= t_prop + window
                )
                max_peers = total_rpki - 1
                temporal_fracs.append(peers_in_window / max_peers * 100)

            # Use median proposer's experience
            temporal_fracs.sort()
            median_temporal = temporal_fracs[len(temporal_fracs) // 2] if temporal_fracs else 0

            w.writerow([f"{topo_pct:.2f}", f"{median_temporal:.2f}", category, topo_count])

    print(f"  Written to {fname}")

    # Print summary
    from collections import Counter
    cats = Counter()
    for key, observers in prefix_data.items():
        labels = set(d["label"] for d in observers.values())
        cat = "LEGITIMATE"
        for l in labels:
            if l != "LEGITIMATE":
                cat = l
                break
        cats[cat] += 1
    print(f"  Categories: {dict(cats)}")


if __name__ == "__main__":
    analyze(400, window=10)
