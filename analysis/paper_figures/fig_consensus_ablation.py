#!/usr/bin/env python3
"""
fig_consensus_ablation.py — produces results/figures/fig_consensus_ablation.pdf

Four-panel consensus mechanism ablation (§5b in the paper):
  (a) RPKI adoption ratio ↓  — placeholder until RPKI ratio ablation is wired up
  (b) Broadcast size        — reads results/ablation/broadcast/
  (c) Threshold τ           — reads results/ablation/tau/
  (d) Timeout               — reads results/ablation/timeout/

For each panel:
  - Solid green line = Confirmed % (reliability)
  - Dashed orange line = associated cost metric (messages, Byz tolerance, wall time)
  - Vertical dashed line marks the default value
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.result_loader import load_runs  # noqa: E402
from _common.plot_style import setup_ieee_column, COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ABLATION_ROOT = PROJECT_ROOT / "results" / "ablation"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "figures" / "fig_consensus_ablation.pdf"


def _extract_numeric_key(run_name: str) -> float | None:
    """'tau_3' → 3.0, 'broadcast_14' → 14.0, 'timeout_15' → 15.0."""
    m = re.search(r"(\d+(?:\.\d+)?)$", run_name)
    return float(m.group(1)) if m else None


def _confirmed_pct(run: dict) -> float:
    statuses = run.get("consensus_status", {}) or {}
    total = sum(v for v in statuses.values() if isinstance(v, (int, float)))
    if total == 0:
        return 0.0
    return 100.0 * (statuses.get("CONFIRMED", 0) / total)


def _sweep(ablation_root: Path, name: str) -> list[tuple[float, dict]]:
    runs = load_runs(ablation_root / name)
    pts: list[tuple[float, dict]] = []
    for run_name, run in runs.items():
        k = _extract_numeric_key(run_name)
        if k is not None:
            pts.append((k, run))
    pts.sort(key=lambda x: x[0])
    return pts


def _plot_panel(ax, sweep, x_label: str, title: str,
                cost_key: str = "p2p_sent", cost_label: str = "P2P msgs",
                default_x: float | None = None, log_cost: bool = False) -> None:
    if not sweep:
        ax.text(0.5, 0.5, "(no runs yet)", ha="center", va="center",
                transform=ax.transAxes, fontsize=7, color="0.5")
        ax.set_title(title, fontsize=8, loc="left")
        return

    xs = [x for x, _ in sweep]
    conf = [_confirmed_pct(r) for _, r in sweep]

    ax.plot(xs, conf, color=COLORS["tertiary"], linewidth=1.4,
            marker="o", markersize=3, label="Confirmed \\%")
    ax.set_xlabel(x_label)
    ax.set_ylabel("Confirmed \\%", color=COLORS["tertiary"])
    ax.set_ylim(0, 105)
    ax.tick_params(axis="y", labelcolor=COLORS["tertiary"])
    ax.yaxis.grid(True, linewidth=0.3, color="0.9")

    # Right axis: cost metric
    ax2 = ax.twinx()
    costs = [r.get(cost_key, 0) for _, r in sweep]
    ax2.plot(xs, costs, color=COLORS["secondary"], linewidth=1.2,
             linestyle="--", marker="s", markersize=3, label=cost_label)
    ax2.set_ylabel(cost_label, color=COLORS["secondary"])
    ax2.tick_params(axis="y", labelcolor=COLORS["secondary"])
    if log_cost:
        ax2.set_yscale("log")

    if default_x is not None:
        ax.axvline(default_x, color="0.6", linestyle=":", linewidth=0.6, zorder=0)

    ax.set_title(title, fontsize=8, loc="left")


def build_figure(ablation_root: Path, output: Path) -> None:
    setup_ieee_column()
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.5))

    # (a) RPKI adoption ratio — currently no sweep, placeholder
    rpki_sweep = _sweep(ablation_root, "rpki")
    _plot_panel(
        axes[0, 0], rpki_sweep,
        x_label="RPKI adoption ratio",
        title="(a) RPKI adoption",
        cost_key="p2p_sent", cost_label="P2P msgs",
        default_x=0.363,
    )

    # (b) Broadcast size
    bcast_sweep = _sweep(ablation_root, "broadcast")
    _plot_panel(
        axes[0, 1], bcast_sweep,
        x_label="Broadcast peers",
        title="(b) Broadcast size",
        cost_key="p2p_sent", cost_label="P2P msgs",
        default_x=14, log_cost=True,
    )

    # (c) Threshold τ
    tau_sweep = _sweep(ablation_root, "tau")
    _plot_panel(
        axes[1, 0], tau_sweep,
        x_label="Consensus threshold $\\tau$",
        title="(c) Threshold",
        cost_key="p2p_sent", cost_label="P2P msgs",
        default_x=3,
    )

    # (d) Timeout
    to_sweep = _sweep(ablation_root, "timeout")
    _plot_panel(
        axes[1, 1], to_sweep,
        x_label="Timeout (s)",
        title="(d) Timeout",
        cost_key="elapsed_seconds", cost_label="Wall time (s)",
        default_x=15,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)

    print(f"[fig_consensus_ablation] wrote {output}")
    print(f"  rpki sweep:      {len(rpki_sweep)} points")
    print(f"  broadcast sweep: {len(bcast_sweep)} points")
    print(f"  tau sweep:       {len(tau_sweep)} points")
    print(f"  timeout sweep:   {len(to_sweep)} points")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ablation-root", type=Path, default=DEFAULT_ABLATION_ROOT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    build_figure(args.ablation_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
