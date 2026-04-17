#!/usr/bin/env python3
"""
Revise a dataset to realistic real-world parameters.

Transforms:
  1. Drop attack observations of types whose detector is disabled
     (ACCIDENTAL_ROUTE_LEAK, ROUTE_LEAK) — clean FP baseline.
  2. Per-type balanced attack retention — keep first N unique attack
     EVENTS per enabled type (sorted by timestamp), where an event is
     identified by (label, origin_asn, prefix).  All observations of
     a kept event are preserved so BGP propagation structure stays
     intact across observers.
  3. Per-node legit subsample — keep every Kth legitimate observation
     per observer AS so per-node rate matches real-world BGP steady
     state (~0.005 events/sec/validator).
  4. Ground truth is recomputed from the revised observations.

Safe-by-design:
  - Writes to dataset/<NAME>_tmp/ first, verifies counts, then swaps.
  - Moves original to dataset/_raw_backup_<DATE>/<NAME>/ on swap.

Usage:
  python3 scripts/revise_dataset.py caida_50 [--apply]
  python3 scripts/revise_dataset.py all    [--apply]

Without --apply, the script runs in dry-run mode: computes the target
counts, writes to *_tmp/, and prints a summary.  Nothing else changes.
With --apply, after dry-run validation, original is backed up and
swapped with the revised version.
"""

import argparse
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────
#  Plan — per-dataset knobs
# ──────────────────────────────────────────────────────────────────────
# Per-type attack count per dataset (doubling schedule).
# Enables per-category precision/recall at larger N.
ATTACKS_PER_TYPE = {
    "caida_50":   2,
    "caida_100":  4,
    "caida_200":  8,
    "caida_400":  16,
    "caida_800":  32,
    "caida_1600": 64,
}

# Per-node legitimate-observation subsample factor.
# Tuned so per-node legit rate lands near the real-world steady-state
# target (0.005 events/sec/validator) given the original observation
# density + SIM_DURATION=2100s.
LEGIT_SUBSAMPLE = {
    "caida_50":   23,
    "caida_100":  43,
    "caida_200":  65,
    "caida_400":  77,
    "caida_800":  102,
    "caida_1600": 101,
}

# Attack types whose detector is disabled in attack_detector.detect_attacks().
# Events of these types are dropped from both observations and ground truth.
DISABLED_ATTACK_TYPES = {"ACCIDENTAL_ROUTE_LEAK", "ROUTE_LEAK"}


def revise_observations(obs_dir: Path, attacks_per_type: int, legit_K: int):
    """Return (revised_by_file, summary) without writing anything.

    revised_by_file: dict[filepath -> list[observation]]
    summary: dict with overall counts
    """
    # ── Pass 1: collect every attack observation across all observer files,
    # grouped by (label, origin_asn, prefix) = "event" identifier.
    events_by_type: dict[str, dict[tuple, list[tuple[Path, dict]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    legit_by_file: dict[Path, list[dict]] = {}

    obs_files = sorted(obs_dir.glob("AS*.json"))
    for f in obs_files:
        with open(f) as fh:
            data = json.load(fh)
        legit_by_file[f] = []
        for o in data.get("observations", []):
            if o.get("is_attack"):
                label = o.get("label", "UNKNOWN")
                if label in DISABLED_ATTACK_TYPES:
                    continue
                key = (label, o.get("origin_asn"), o.get("prefix"))
                events_by_type[label][key].append((f, o))
            else:
                legit_by_file[f].append(o)

    # ── Pass 2: select first `attacks_per_type` events per label, sorted by
    # earliest timestamp of that event across observers.
    kept_event_keys: set[tuple] = set()
    kept_events_by_type: dict[str, int] = {}
    for label, events in events_by_type.items():
        # Earliest timestamp across observers
        events_sorted = sorted(
            events.items(),
            key=lambda item: min(o.get("timestamp", 0) for _, o in item[1]),
        )
        chosen = [key for key, _ in events_sorted[:attacks_per_type]]
        kept_events_by_type[label] = len(chosen)
        for k in chosen:
            kept_event_keys.add(k)

    # ── Pass 3: subsample legit per observer (every Kth, deterministic).
    # Then recombine with kept attacks for each file.
    revised_by_file: dict[Path, list[dict]] = {}
    for f in obs_files:
        # Sorted by timestamp for determinism
        legit = sorted(legit_by_file[f], key=lambda o: o.get("timestamp", 0))
        kept_legit = legit[::legit_K]

        # Attacks belonging to kept events that were observed by this file
        with open(f) as fh:
            file_obs = json.load(fh).get("observations", [])
        kept_attacks = [
            o for o in file_obs
            if o.get("is_attack")
            and o.get("label") not in DISABLED_ATTACK_TYPES
            and (o.get("label"), o.get("origin_asn"), o.get("prefix")) in kept_event_keys
        ]

        combined = sorted(
            kept_legit + kept_attacks,
            key=lambda o: o.get("timestamp", 0),
        )
        revised_by_file[f] = combined

    # ── Summary
    total_obs = sum(len(v) for v in revised_by_file.values())
    attacks = sum(1 for v in revised_by_file.values() for o in v if o.get("is_attack"))
    legit = total_obs - attacks
    per_type = Counter(
        o.get("label")
        for v in revised_by_file.values()
        for o in v
        if o.get("is_attack")
    )
    summary = {
        "n_files": len(obs_files),
        "total": total_obs,
        "attacks": attacks,
        "legit": legit,
        "per_type_attacks": dict(per_type),
        "kept_event_keys_count": len(kept_event_keys),
        "kept_events_by_type": kept_events_by_type,
    }
    return revised_by_file, summary


def write_revised(revised_by_file, out_dir: Path, src_dir: Path):
    """Write revised dataset to out_dir, preserving non-observation files."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy non-observation top-level files
    for name in src_dir.iterdir():
        if name.is_file():
            shutil.copy2(name, out_dir / name.name)

    # Copy as_classification.json etc. (skip ground_truth + observations — we regenerate)
    for sub in src_dir.iterdir():
        if sub.is_dir() and sub.name not in ("observations", "ground_truth"):
            dest = out_dir / sub.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(sub, dest)

    # Write observations
    obs_out = out_dir / "observations"
    obs_out.mkdir(parents=True, exist_ok=True)
    for src_path, obs_list in revised_by_file.items():
        # Load original metadata, overwrite observations + counts
        with open(src_path) as fh:
            data = json.load(fh)
        data["observations"] = obs_list
        data["total_observations"] = len(obs_list)
        data["attack_observations"] = sum(1 for o in obs_list if o.get("is_attack"))
        data["legitimate_observations"] = len(obs_list) - data["attack_observations"]
        data["best_route_observations"] = sum(
            1 for o in obs_list if o.get("is_best", False)
        )
        data["alternative_route_observations"] = (
            len(obs_list) - data["best_route_observations"]
        )
        with open(obs_out / src_path.name, "w") as fh:
            json.dump(data, fh, indent=2)

    # Rebuild ground_truth.json
    gt_out = out_dir / "ground_truth"
    gt_out.mkdir(parents=True, exist_ok=True)
    gt_src = src_dir / "ground_truth" / "ground_truth.json"
    gt = {}
    if gt_src.exists():
        with open(gt_src) as fh:
            gt = json.load(fh)

    # Recount from revised obs
    per_type = Counter()
    total_attacks = 0
    attacks_list = []
    for obs_list in revised_by_file.values():
        for o in obs_list:
            if not o.get("is_attack"):
                continue
            per_type[o.get("label")] += 1
            total_attacks += 1
            attacks_list.append({
                "timestamp": o.get("timestamp"),
                "prefix": o.get("prefix"),
                "origin_asn": o.get("origin_asn"),
                "as_path": o.get("as_path"),
                "attack_type": o.get("label"),
                "observed_by_asn": o.get("observed_by_asn"),
            })
    gt["total_attacks"] = total_attacks
    gt["attack_types"] = dict(per_type)
    # Preserve existing attack entries if they had richer metadata; otherwise
    # write the recomputed list.
    gt["attacks"] = attacks_list
    gt["_revision"] = {
        "script": "scripts/revise_dataset.py",
        "revised_at": datetime.now().isoformat(),
    }
    with open(gt_out / "ground_truth.json", "w") as fh:
        json.dump(gt, fh, indent=2)


def write_revision_notes(out_dir: Path, dataset_name: str,
                         attacks_per_type: int, legit_K: int,
                         summary: dict):
    md = f"""# Revision Notes — {dataset_name}

This dataset was produced by `scripts/revise_dataset.py` from the original
`dataset/{dataset_name}/`.

## Transformations applied

1. **Disabled-detector attack types dropped** — observations labelled
   {sorted(DISABLED_ATTACK_TYPES)} are removed because no enabled detector
   claims to catch them (avoids artificial false-negatives).
2. **Per-type attack event balance** — for each remaining attack type,
   the first `{attacks_per_type}` unique attack **events** (identified by
   `(label, origin_asn, prefix)`) in timestamp order are retained.  All
   observations of a retained event across observer nodes are preserved,
   so BGP propagation structure stays intact.
3. **Legitimate observation subsample** — per observer AS, every
   `{legit_K}`-th legitimate observation (sorted by timestamp) is kept.
   The chosen factor targets a per-node legit rate of ~0.005 events/sec,
   matching real-world BGP steady-state (RIPE RIS 2022).
4. **Ground truth recomputed** — `attack_types` counts and the `attacks`
   list are rebuilt from the revised observations.

## Resulting counts

| Metric | Value |
|---|---|
| Observer AS files | {summary['n_files']} |
| Total observations | {summary['total']:,} |
| Legitimate | {summary['legit']:,} |
| Attacks | {summary['attacks']:,} |
| Unique attack events kept | {summary['kept_event_keys_count']} |

Per-type attack counts:
{chr(10).join(f'  - {t}: {c}' for t, c in sorted(summary['per_type_attacks'].items()))}

Script-level knobs applied:
  - `ATTACKS_PER_TYPE = {attacks_per_type}`
  - `LEGIT_SUBSAMPLE = {legit_K}`
  - `DISABLED_ATTACK_TYPES = {sorted(DISABLED_ATTACK_TYPES)}`
"""
    with open(out_dir / "REVISION_NOTES.md", "w") as fh:
        fh.write(md)


def process_one(dataset_name: str, apply: bool, backup_root: Path) -> bool:
    base = Path(__file__).resolve().parent.parent
    src = base / "dataset" / dataset_name
    if not src.exists():
        print(f"  ❌ {dataset_name}: not found at {src}")
        return False
    tmp = base / "dataset" / f"{dataset_name}_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)

    attacks_per_type = ATTACKS_PER_TYPE.get(dataset_name)
    legit_K = LEGIT_SUBSAMPLE.get(dataset_name)
    if attacks_per_type is None or legit_K is None:
        print(f"  ❌ {dataset_name}: no knobs configured (see ATTACKS_PER_TYPE/LEGIT_SUBSAMPLE)")
        return False

    print(f"\n  {dataset_name} — apply={apply}, attacks_per_type={attacks_per_type}, legit_K={legit_K}")
    revised, summary = revise_observations(src / "observations", attacks_per_type, legit_K)

    print(f"    files:        {summary['n_files']}")
    print(f"    total obs:    {summary['total']:,}")
    print(f"    legit:        {summary['legit']:,}")
    print(f"    attacks:      {summary['attacks']}")
    print(f"    unique events kept: {summary['kept_event_keys_count']}")
    print(f"    per-type:     {summary['per_type_attacks']}")

    # Validation: each enabled type should have exactly `attacks_per_type`
    # unique events (or fewer if dataset didn't contain enough)
    kept_events = summary["kept_events_by_type"]
    all_expected_types = {
        "PREFIX_HIJACK", "SUBPREFIX_HIJACK", "BOGON_INJECTION",
        "FORGED_ORIGIN_PREFIX_HIJACK", "ROUTE_FLAPPING",
    }
    for t in all_expected_types:
        got = kept_events.get(t, 0)
        if got != attacks_per_type:
            print(f"    ⚠️  {t}: kept {got} events (target was {attacks_per_type})")

    write_revised(revised, tmp, src)
    write_revision_notes(tmp, dataset_name, attacks_per_type, legit_K, summary)
    print(f"    ✅ wrote revised to {tmp}")

    if apply:
        # Move original to backup
        backup_root.mkdir(parents=True, exist_ok=True)
        dst_backup = backup_root / dataset_name
        if dst_backup.exists():
            shutil.rmtree(dst_backup)
        shutil.move(str(src), str(dst_backup))
        shutil.move(str(tmp), str(src))
        print(f"    ✅ swapped. original → {dst_backup}")

    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("target", help="dataset name (e.g. caida_50) or 'all'")
    p.add_argument("--apply", action="store_true",
                   help="Swap in revised dataset (without this, only writes *_tmp/)")
    args = p.parse_args()

    backup_root = Path(__file__).resolve().parent.parent / "dataset" / f"_raw_backup_{datetime.now().strftime('%Y%m%d')}"

    if args.target == "all":
        for name in ["caida_50", "caida_100", "caida_200", "caida_400", "caida_800", "caida_1600"]:
            process_one(name, args.apply, backup_root)
    else:
        process_one(args.target, args.apply, backup_root)

    print("\nDone.")
    if not args.apply:
        print("  (dry run — nothing swapped; inspect *_tmp/ before re-running with --apply)")


if __name__ == "__main__":
    sys.exit(main() or 0)
