#!/usr/bin/env python3
"""
fig_consensus_breakdown.py — produces results/figures/fig_consensus_breakdown.pdf

Stacked bar chart showing what fraction of transactions reach each PoP
consensus status (CONFIRMED / INSUFFICIENT_CONSENSUS / SINGLE_WITNESS) at
each dataset scale. One bar per dataset (caida_100..caida_1250).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.result_loader import load_run  # noqa: E402
from _common.plot_style import setup_ieee_column, CONSENSUS_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "results" / "primary"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "figures" / "fig_consensus_breakdown.pdf"
DEFAULT_DATASETS = ["caida_100", "caida_200", "caida_350", "caida_650", "caida_1250"]


def build_figure(datasets: list[str], runs_root: Path, output: Path) -> None:
    setup_ieee_column()
    import matplotlib.pyplot as plt
    import numpy as np

    statuses = ["CONFIRMED", "INSUFFICIENT_CONSENSUS", "SINGLE_WITNESS"]
    pretty = {
        "CONFIRMED": "Confirmed ($\\geq$3 sigs)",
        "INSUFFICIENT_CONSENSUS": "Insufficient (1–2 sigs)",
        "SINGLE_WITNESS": "Single witness (0 sigs)",
    }

    labels: list[str] = []
    data: dict[str, list[float]] = {s: [] for s in statuses}
    missing: list[str] = []
    for name in datasets:
        d = runs_root / name
        if not (d / ".done").exists():
            missing.append(name)
            continue
        r = load_run(d)
        cs = r.get("consensus_status", {}) or {}
        total = sum(v for v in cs.values() if isinstance(v, (int, float)))
        if total == 0:
            missing.append(name)
            continue
        labels.append(name.split("_")[-1])  # "100", "200", etc.
        for s in statuses:
            data[s].append(100.0 * cs.get(s, 0) / total)

    if not labels:
        sys.exit("No completed runs found — aborting")

    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))

    for s in statuses:
        vals = np.array(data[s])
        ax.bar(
            x, vals, bottom=bottom,
            label=pretty[s],
            color=CONSENSUS_COLORS[s],
            edgecolor="white",
            linewidth=0.3,
            width=0.65,
        )
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Topology size (ASes)")
    ax.set_ylabel("Transactions (\\%)")
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.22),
              ncol=3, frameon=False, fontsize=6)
    ax.yaxis.grid(True, linewidth=0.3, color="0.9")
    ax.xaxis.grid(False)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)

    print(f"[fig_consensus_breakdown] wrote {output}")
    if missing:
        print(f"  (missing: {', '.join(missing)})")
    for i, name in enumerate(labels):
        print(
            f"  {name:>6} ASes: "
            f"CONF={data['CONFIRMED'][i]:.1f}%  "
            f"INSUFF={data['INSUFFICIENT_CONSENSUS'][i]:.1f}%  "
            f"SW={data['SINGLE_WITNESS'][i]:.1f}%"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    p.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    build_figure(args.datasets, args.runs_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
