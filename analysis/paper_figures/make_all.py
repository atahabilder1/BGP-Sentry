#!/usr/bin/env python3
"""
make_all.py — re-render every paper figure and table from existing results

Runs every tab_*.py and fig_*.py in this directory in order. Each sub-script
is independently runnable and self-contained, so a failure in one does not
abort the others.

Usage:
    python3 make_all.py
    python3 make_all.py --only tab_dataset_stats fig_consensus_breakdown
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

# Order matters only for readability of console output
SCRIPTS = [
    "tab_dataset_stats.py",
    "tab_system_performance.py",
    "tab_posthoc_results.py",
    "tab_discovery_depth.py",
    "fig_consensus_breakdown.py",
    "fig_per_attack_metrics.py",
    "fig_trust_recovery.py",
    "fig_ecdf_error.py",
    "fig_consensus_ablation.py",
]


def run_script(path: Path) -> tuple[bool, float, str]:
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.time() - start
        ok = result.returncode == 0
        output = (result.stdout + result.stderr).strip()
        return ok, elapsed, output
    except Exception as e:
        return False, time.time() - start, str(e)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--only",
        nargs="+",
        default=None,
        help="Only run these script names (without .py)",
    )
    args = p.parse_args()

    scripts = SCRIPTS
    if args.only:
        wanted = {f"{name}.py" for name in args.only}
        scripts = [s for s in SCRIPTS if s in wanted]

    print("=" * 70)
    print(f"make_all.py — rendering {len(scripts)} scripts")
    print("=" * 70)

    results: list[tuple[str, bool, float]] = []
    for name in scripts:
        path = THIS_DIR / name
        if not path.exists():
            print(f"[SKIP] {name} (not found)")
            continue
        print(f"\n── {name} ──")
        ok, elapsed, output = run_script(path)
        status = "OK" if ok else "FAIL"
        print(output)
        print(f"[{status}] {name} ({elapsed:.1f}s)")
        results.append((name, ok, elapsed))

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    ok_count = sum(1 for _, ok, _ in results if ok)
    fail_count = len(results) - ok_count
    for name, ok, elapsed in results:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name:<35} {elapsed:>6.1f}s")
    print(f"\n{ok_count} succeeded, {fail_count} failed")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
