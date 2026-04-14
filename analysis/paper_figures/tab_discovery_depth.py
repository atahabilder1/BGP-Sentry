#!/usr/bin/env python3
"""
tab_discovery_depth.py — produces results/tables/tab_discovery_depth.tex

Peer-discovery depth ablation table (§5b Table 4 in the paper). Reads
results/ablation/discovery/depth_<N>/ runs and builds a table with
Confirmed %, Insufficient %, Single-witness % per depth.

NOTE: Peer-discovery depth is not yet plumbed through .env. Until that
is wired up, all discovery runs effectively use the 1-hop default and
this table will show identical rows. See 05_ablation_discovery.sh header.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.result_loader import load_runs  # noqa: E402
from _common.latex_table import write_latex_table, fmt_pct  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ABLATION_ROOT = PROJECT_ROOT / "results" / "ablation" / "discovery"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "tables" / "tab_discovery_depth.tex"

DEPTH_LABELS = {
    "0": "0-hop (random)",
    "1": "1-hop (default)",
    "2": "2-hop",
    "3": "3-hop",
}


def _status_pct(run: dict, key: str) -> float:
    statuses = run.get("consensus_status", {}) or {}
    total = sum(v for v in statuses.values() if isinstance(v, (int, float)))
    return 100.0 * statuses.get(key, 0) / total if total else 0.0


def _depth_key(run_name: str) -> str | None:
    m = re.match(r"depth_(\d+)$", run_name)
    return m.group(1) if m else None


def build_table(ablation_root: Path, output: Path) -> None:
    runs = load_runs(ablation_root)

    header_row = [
        "\\textbf{Depth}",
        "\\textbf{Confirmed (\\%)}",
        "\\textbf{Insufficient (\\%)}",
        "\\textbf{Single-witness (\\%)}",
    ]

    body_rows: list[list[str]] = []
    for run_name, run in sorted(runs.items()):
        depth = _depth_key(run_name)
        if depth is None:
            continue
        label = DEPTH_LABELS.get(depth, f"{depth}-hop")
        if depth == "1":
            label = f"\\textbf{{{label}}}"
        body_rows.append([
            label,
            fmt_pct(_status_pct(run, "CONFIRMED")),
            fmt_pct(_status_pct(run, "INSUFFICIENT_CONSENSUS")),
            fmt_pct(_status_pct(run, "SINGLE_WITNESS")),
        ])

    if not body_rows:
        body_rows.append(["(no runs)", "--", "--", "--"])

    write_latex_table(
        path=output,
        caption=(
            "Peer-discovery depth ablation (caida\\_200, $\\sqrt{N}$ broadcast, "
            "$\\tau{=}3$, 15\\,s timeout). P2P cost is constant across depths."
        ),
        label="tab:discovery_depth",
        column_spec="lrrr",
        header_row=header_row,
        body_rows=body_rows,
    )

    print(f"[tab_discovery_depth] wrote {output}")
    for row in body_rows:
        print(f"  {' | '.join(row)}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ablation-root", type=Path, default=DEFAULT_ABLATION_ROOT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    build_table(args.ablation_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
