#!/usr/bin/env python3
"""
Consensus-relevant asymmetry analysis.

The key question: When an RPKI observer proposes a transaction for voting,
how many peer RPKI validators can actually corroborate it?

Asymmetry dimensions:
1. TEMPORAL: At vote time, has the peer received this (prefix, origin) yet?
2. PATH: Did the peer receive it via an RPKI-connected path (trusted)?
3. COMBINED: Within a voting window, how many peers have RPKI-validated knowledge?

This directly motivates why BGP-Sentry needs SINGLE_WITNESS / INSUFFICIENT_CONSENSUS
levels — not all valid observations can achieve full consensus.
"""

import json
import os
import sys
import glob
import csv
from collections import defaultdict
import statistics

DATASET_BASE = os.path.join(os.path.dirname(__file__), "..", "dataset", "bfsTopology")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "menuscript", "IEEEtran", "data")


def analyze_consensus_asymmetry(scale, voting_windows=[5, 10, 30, 60]):
    """For each (prefix, origin), simulate: if observer O proposes at time T,
    how many other RPKI observers have seen it within [T - window, T]?
    Also check if the path to the peer goes through RPKI nodes."""

    obs_dir = os.path.join(DATASET_BASE, f"caida_bfs_174_{scale}", "observations")
    gt_dir = os.path.join(DATASET_BASE, f"caida_bfs_174_{scale}", "ground_truth")

    if not os.path.isdir(obs_dir):
        print(f"Scale {scale} not found")
        return None

    # Load classification
    with open(os.path.join(gt_dir, "as_classification.json")) as f:
        classify = json.load(f)

    rpki_set = set(classify["rpki_asns"])
    all_asns = set(classify["rpki_asns"] + classify["non_rpki_asns"])
    print(f"Scale {scale}: {len(rpki_set)} RPKI, {len(all_asns)-len(rpki_set)} non-RPKI")

    # Load all observations indexed by (prefix, origin)
    # For each observer: earliest timestamp and whether path has RPKI connectivity
    # key: (prefix, origin) -> {observer_asn: {timestamp, as_path, has_rpki_next_hop}}
    prefix_obs = defaultdict(dict)

    files = sorted(glob.glob(os.path.join(obs_dir, "AS*.json")))
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        observer = data["asn"]
        for obs in data.get("observations", []):
            if obs.get("is_withdrawal", False):
                continue
            key = (obs["prefix"], obs["origin_asn"])
            ts = obs["timestamp"]
            as_path = obs.get("as_path", [])
            is_attack = obs.get("is_attack", False)
            label = obs.get("label", "LEGITIMATE")

            # Check RPKI connectivity:
            # The next_hop (direct neighbor that relayed) should be RPKI
            next_hop = obs.get("next_hop_asn", None)
            next_hop_rpki = next_hop in rpki_set if next_hop else False

            # Check if the path has at least one RPKI intermediary
            path_has_rpki = any(asn in rpki_set for asn in as_path if asn != observer)

            # Fraction of path that is RPKI
            non_self_path = [asn for asn in as_path if asn != observer]
            rpki_fraction = sum(1 for a in non_self_path if a in rpki_set) / max(len(non_self_path), 1)

            if observer not in prefix_obs[key]:
                prefix_obs[key][observer] = {
                    "timestamp": ts,
                    "next_hop_rpki": next_hop_rpki,
                    "path_has_rpki": path_has_rpki,
                    "rpki_path_fraction": rpki_fraction,
                    "is_attack": is_attack,
                    "label": label,
                    "observer_is_rpki": observer in rpki_set,
                    "as_path_length": len(as_path),
                }
            else:
                # Keep earliest observation
                if ts < prefix_obs[key][observer]["timestamp"]:
                    prefix_obs[key][observer]["timestamp"] = ts

    print(f"  Loaded {len(prefix_obs)} unique (prefix, origin) pairs")

    # === Analysis ===
    total_rpki = len(rpki_set)

    results = {
        "scale": scale,
        "total_rpki": total_rpki,
        "total_ases": len(all_asns),
        # Per (prefix,origin): how many RPKI observers see it at all
        "rpki_visibility": [],
        # Per (prefix,origin): how many RPKI observers have RPKI next-hop
        "rpki_path_visibility": [],
        # Per (prefix,origin): temporal corroboration within windows
        "temporal_corroboration": {w: [] for w in voting_windows},
        # Combined: RPKI observers with RPKI path within window
        "combined_corroboration": {w: [] for w in voting_windows},
        # Attack vs legitimate breakdown
        "by_category": defaultdict(lambda: {
            "rpki_vis": [], "rpki_path_vis": [],
            "temporal": {w: [] for w in voting_windows},
            "combined": {w: [] for w in voting_windows},
        }),
    }

    for key, observers in prefix_obs.items():
        # Determine category
        categories = set()
        for obs_data in observers.values():
            categories.add(obs_data["label"])
        category = "LEGITIMATE"
        for c in categories:
            if c != "LEGITIMATE":
                category = c
                break

        # RPKI observers that see this prefix
        rpki_observers = {asn: d for asn, d in observers.items() if d["observer_is_rpki"]}
        rpki_vis_frac = len(rpki_observers) / total_rpki if total_rpki > 0 else 0
        results["rpki_visibility"].append(rpki_vis_frac)
        results["by_category"][category]["rpki_vis"].append(rpki_vis_frac)

        # RPKI observers with RPKI-connected next hop
        rpki_path_observers = {asn: d for asn, d in rpki_observers.items() if d["next_hop_rpki"]}
        rpki_path_frac = len(rpki_path_observers) / total_rpki if total_rpki > 0 else 0
        results["rpki_path_visibility"].append(rpki_path_frac)
        results["by_category"][category]["rpki_path_vis"].append(rpki_path_frac)

        # Temporal: for each RPKI observer as proposer, how many other RPKI
        # observers have seen it within the voting window?
        if rpki_observers:
            timestamps = sorted([(d["timestamp"], asn) for asn, d in rpki_observers.items()])

            for window in voting_windows:
                corroboration_fracs = []
                combined_fracs = []
                for i, (t_prop, proposer) in enumerate(timestamps):
                    # Other RPKI observers that have seen it before t_prop + window
                    peers_seen = 0
                    peers_rpki_path = 0
                    for j, (t_peer, peer_asn) in enumerate(timestamps):
                        if peer_asn == proposer:
                            continue
                        # Peer must have received it before proposer's vote deadline
                        if t_peer <= t_prop + window:
                            peers_seen += 1
                            if rpki_observers[peer_asn]["next_hop_rpki"]:
                                peers_rpki_path += 1

                    max_peers = total_rpki - 1
                    if max_peers > 0:
                        corroboration_fracs.append(peers_seen / max_peers)
                        combined_fracs.append(peers_rpki_path / max_peers)

                if corroboration_fracs:
                    # Use median proposer's corroboration
                    results["temporal_corroboration"][window].append(
                        statistics.median(corroboration_fracs))
                    results["combined_corroboration"][window].append(
                        statistics.median(combined_fracs))
                    results["by_category"][category]["temporal"][window].append(
                        statistics.median(corroboration_fracs))
                    results["by_category"][category]["combined"][window].append(
                        statistics.median(combined_fracs))

    return results


def print_results(r):
    scale = r["scale"]
    windows = sorted(r["temporal_corroboration"].keys())

    print(f"\n{'='*75}")
    print(f"CONSENSUS ASYMMETRY — Scale {scale} ({r['total_rpki']} RPKI / {r['total_ases']} total)")
    print(f"{'='*75}")

    # Overall
    print(f"\n--- Overall (all prefix,origin pairs) ---")
    vis = r["rpki_visibility"]
    pvis = r["rpki_path_visibility"]
    print(f"  RPKI observer visibility:      mean={statistics.mean(vis):.1%}, median={statistics.median(vis):.1%}")
    print(f"  RPKI path-connected visibility: mean={statistics.mean(pvis):.1%}, median={statistics.median(pvis):.1%}")

    for w in windows:
        tc = r["temporal_corroboration"][w]
        cc = r["combined_corroboration"][w]
        if tc:
            print(f"  Temporal corroboration ({w:>2}s window): mean={statistics.mean(tc):.1%}, median={statistics.median(tc):.1%}")
            print(f"  Combined (RPKI path + {w:>2}s window):  mean={statistics.mean(cc):.1%}, median={statistics.median(cc):.1%}")

    # Per category
    print(f"\n--- Per category ---")
    for cat in ["LEGITIMATE", "PREFIX_HIJACK", "SUBPREFIX_HIJACK", "BOGON_INJECTION", "ROUTE_FLAPPING"]:
        if cat not in r["by_category"]:
            continue
        cd = r["by_category"][cat]
        if not cd["rpki_vis"]:
            continue
        print(f"\n  {cat} (n={len(cd['rpki_vis'])})")
        print(f"    RPKI visibility:      mean={statistics.mean(cd['rpki_vis']):.1%}")
        print(f"    RPKI-path visibility: mean={statistics.mean(cd['rpki_path_vis']):.1%}")
        for w in windows:
            if cd["temporal"][w]:
                print(f"    Temporal ({w:>2}s): mean={statistics.mean(cd['temporal'][w]):.1%}, "
                      f"Combined: mean={statistics.mean(cd['combined'][w]):.1%}")


def write_plot_data(all_results):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # CSV for the bar chart: scale x category x metric
    fname = os.path.join(OUTPUT_DIR, "consensus_asymmetry.csv")
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scale", "category", "rpki_visibility", "rpki_path_visibility",
                     "temporal_5s", "temporal_30s", "combined_5s", "combined_30s"])
        for r in all_results:
            for cat in ["LEGITIMATE", "PREFIX_HIJACK", "SUBPREFIX_HIJACK",
                        "BOGON_INJECTION", "ROUTE_FLAPPING"]:
                cd = r["by_category"].get(cat, None)
                if not cd or not cd["rpki_vis"]:
                    continue
                row = [
                    r["scale"], cat,
                    f"{statistics.mean(cd['rpki_vis']):.4f}",
                    f"{statistics.mean(cd['rpki_path_vis']):.4f}",
                    f"{statistics.mean(cd['temporal'].get(5, [0])):.4f}",
                    f"{statistics.mean(cd['temporal'].get(30, [0])):.4f}",
                    f"{statistics.mean(cd['combined'].get(5, [0])):.4f}",
                    f"{statistics.mean(cd['combined'].get(30, [0])):.4f}",
                ]
                w.writerow(row)

    print(f"\nPlot data written to: {fname}")


if __name__ == "__main__":
    scales = [50, 200, 400]
    if len(sys.argv) > 1:
        scales = [int(s) for s in sys.argv[1:]]

    all_results = []
    for scale in scales:
        r = analyze_consensus_asymmetry(scale, voting_windows=[5, 10, 30, 60])
        if r:
            all_results.append(r)
            print_results(r)

    if all_results:
        write_plot_data(all_results)
