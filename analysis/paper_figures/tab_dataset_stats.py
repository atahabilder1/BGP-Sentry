#!/usr/bin/env python3
"""
tab_dataset_stats.py — produces results/tables/tab_dataset_stats.tex

Reads each dataset's as_classification.json and ground_truth.json, computes
topology + attack-breakdown statistics, and writes a LaTeX table suitable
for inclusion via \\input{results/tables/tab_dataset_stats} in main.tex.

This script does NOT require any simulation output — it only reads the
generated dataset manifests. Always safe to re-run.

Usage:
    python3 tab_dataset_stats.py
    python3 tab_dataset_stats.py --datasets caida_100 caida_200 caida_350 caida_650 caida_1250
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make _common importable when the script is invoked directly
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.latex_table import write_latex_table, fmt_int, fmt_float, fmt_pct  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASETS = ["caida_100", "caida_200", "caida_350", "caida_650", "caida_1250"]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "tables" / "tab_dataset_stats.tex"

ATTACK_TYPES_ORDERED = [
    ("PREFIX_HIJACK", "Prefix hijack"),
    ("SUBPREFIX_HIJACK", "Subprefix hijack"),
    ("BOGON_INJECTION", "Bogon injection"),
    ("ROUTE_FLAPPING", "Route flapping"),
    ("FORGED_ORIGIN_PREFIX_HIJACK", "Forged origin"),
    ("ACCIDENTAL_ROUTE_LEAK", "Route leak"),
]


def load_dataset_stats(dataset_dir: Path) -> dict:
    """Extract all numbers needed for one column of the stats table.

    Observation counts are cached in `<dataset_dir>/.stats_cache.json`.
    On the first run the script walks every observations/AS*.json, which
    takes ~3 minutes for the full 5-dataset set. Subsequent runs are
    near-instant from the cache. Delete the cache file to force a rescan.
    """
    cls = json.loads((dataset_dir / "as_classification.json").read_text())
    gt = json.loads((dataset_dir / "ground_truth" / "ground_truth.json").read_text())

    total_ases = cls["total_ases"]
    rpki_count = cls["rpki_count"]
    non_rpki_count = cls["non_rpki_count"]
    rpki_pct = 100.0 * rpki_count / total_ases
    non_rpki_pct = 100.0 * non_rpki_count / total_ases

    # Cached observation count (first run walks every file, then caches)
    cache_file = dataset_dir / ".stats_cache.json"
    if cache_file.exists():
        cache = json.loads(cache_file.read_text())
        total_obs = cache["total_observations"]
    else:
        obs_dir = dataset_dir / "observations"
        total_obs = 0
        n_files = 0
        for f in obs_dir.glob("AS*.json"):
            data = json.loads(f.read_text())
            total_obs += data.get("total_observations", 0)
            n_files += 1
        cache_file.write_text(json.dumps({
            "total_observations": total_obs,
            "observation_files": n_files,
        }, indent=2))
        print(f"  cached stats for {dataset_dir.name}: "
              f"{total_obs:,} anns across {n_files} files")

    total_attacks = gt["total_attacks"]
    attack_pct = 100.0 * total_attacks / total_obs if total_obs else 0.0
    legit_pct = 100.0 - attack_pct

    # Per-attack-type breakdown as % of total observations
    attack_counts = gt.get("attack_types", {})
    per_type_pct = {
        t_key: 100.0 * attack_counts.get(t_key, 0) / total_obs if total_obs else 0.0
        for t_key, _ in ATTACK_TYPES_ORDERED
    }

    return {
        "total_ases": total_ases,
        "rpki_count": rpki_count,
        "rpki_pct": rpki_pct,
        "non_rpki_count": non_rpki_count,
        "non_rpki_pct": non_rpki_pct,
        "total_obs": total_obs,
        "total_attacks": total_attacks,
        "attack_pct": attack_pct,
        "legit_pct": legit_pct,
        "per_type_pct": per_type_pct,
    }


def build_table(datasets: list[str], dataset_root: Path, output: Path) -> None:
    stats = {}
    for name in datasets:
        d = dataset_root / name
        if not d.is_dir():
            print(f"[WARN] dataset dir missing: {d}")
            continue
        stats[name] = load_dataset_stats(d)

    if not stats:
        sys.exit("No datasets found — aborting")

    columns = list(stats.keys())
    ncols = 1 + len(columns)

    # Column headers: "Metric" + nominal size labels
    # Use the trailing number in the dataset name as the display label
    header_row = ["\\textbf{Metric}"] + [
        f"\\textbf{{{name.split('_')[-1]}}}$^*$" for name in columns
    ]

    body_rows: list[list[str]] = []
    section_headers: dict[int, str] = {}

    # ── Topology section ──
    section_headers[len(body_rows)] = "Topology"
    body_rows.append(
        ["Total ASes"] + [fmt_int(stats[n]["total_ases"]) for n in columns]
    )
    body_rows.append(
        ["RPKI ASes (\\%)"] + [fmt_pct(stats[n]["rpki_pct"]) for n in columns]
    )
    body_rows.append(
        ["Non-RPKI ASes (\\%)"] + [fmt_pct(stats[n]["non_rpki_pct"]) for n in columns]
    )

    # ── Observations section ──
    section_headers[len(body_rows)] = "Observations"
    body_rows.append(
        ["Total announcements"] + [fmt_int(stats[n]["total_obs"]) for n in columns]
    )
    body_rows.append(
        ["Legitimate (\\%)"] + [fmt_pct(stats[n]["legit_pct"]) for n in columns]
    )
    body_rows.append(
        ["Attack (\\%)"] + [fmt_pct(stats[n]["attack_pct"]) for n in columns]
    )

    # ── Attack breakdown section ──
    section_headers[len(body_rows)] = "Attack breakdown (\\% of total)"
    for t_key, t_label in ATTACK_TYPES_ORDERED:
        body_rows.append(
            [f"\\quad {t_label}"]
            + [fmt_float(stats[n]["per_type_pct"][t_key], 3) for n in columns]
        )

    col_spec = "l" + "r" * len(columns)

    write_latex_table(
        path=output,
        caption=(
            "Dataset statistics across the five CAIDA-anchored subgraph sizes. "
            "Topology numbers from \\texttt{as\\_classification.json}; "
            "observation and attack counts aggregated across all per-AS "
            "observation files. RPKI ratios are label-normalized to the "
            "global 36.3\\% AS-level signing rate "
            "(rpki-client 2022-06 snapshot)."
        ),
        label="tab:dataset_stats",
        column_spec=col_spec,
        header_row=header_row,
        body_rows=body_rows,
        section_headers=section_headers,
        notes=[
            "$^*$Column headers denote the nominal subgraph size; "
            "the actual connected subgraph contains ~5\\% more ASes due "
            "to bridge reconnection. See \\texttt{DATASET\\_METHODOLOGY.md}."
        ],
    )

    # Also print a console summary so the user sees the numbers immediately
    print(f"\n[tab_dataset_stats] wrote {output}\n")
    print(f"{'Dataset':<14} {'N':>6} {'RPKI%':>8} {'Anns':>12} {'Atk%':>8}")
    print("-" * 52)
    for n in columns:
        s = stats[n]
        print(
            f"{n:<14} {s['total_ases']:>6} {s['rpki_pct']:>7.2f}% "
            f"{s['total_obs']:>12,} {s['attack_pct']:>7.3f}%"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help="Dataset directory names (under <project>/dataset/)",
    )
    p.add_argument(
        "--dataset-root",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Root of dataset directories",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output .tex file path",
    )
    args = p.parse_args()

    build_table(args.datasets, args.dataset_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
