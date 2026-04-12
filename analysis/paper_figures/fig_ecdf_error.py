#!/usr/bin/env python3
"""
fig_ecdf_error.py — produces results/figures/fig_ecdf_error.pdf

Two-panel figure (§4 in the paper):
  (a) Pipeline volumes across dataset sizes: total observations received,
      unique observations after dedup, transactions written to blockchain.
  (b) ECDF of absolute rating error for non-RPKI ASes: BGP-Sentry
      produces a trust score; the "error" is |score - expected|, where
      expected = 50 (Neutral) for clean ASes and 0 for ground-truth
      attackers. Compared against an RPKI-only baseline (no observer data).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.result_loader import load_run  # noqa: E402
from _common.plot_style import setup_ieee_column, COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "results" / "primary"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "figures" / "fig_ecdf_error.pdf"
DEFAULT_DATASETS = ["caida_100", "caida_200", "caida_350", "caida_650", "caida_1250"]


def _expected_score(asn: int, attackers: set[int]) -> float:
    return 0.0 if asn in attackers else 50.0


def _compute_rating_errors(run: dict) -> tuple[list[float], list[float]]:
    """Return (bgpsentry_errors, rpki_baseline_errors) lists.

    BGP-Sentry error = |actual_score - expected_score|.
    RPKI baseline score = 50 (Neutral) for every non-RPKI AS → error = |50 - expected|.
    """
    ratings = run.get("ratings_all", {}) or {}
    verdicts = run.get("attack_verdicts", {}) or {}

    # Extract ground-truth attacker AS set from verdicts (if present)
    attackers: set[int] = set()
    if isinstance(verdicts, dict):
        for v in verdicts.values():
            if not isinstance(v, dict):
                continue
            asn = v.get("attacker_asn") or v.get("origin_asn")
            if asn is not None:
                try:
                    attackers.add(int(asn))
                except (TypeError, ValueError):
                    pass
    elif isinstance(verdicts, list):
        for v in verdicts:
            if isinstance(v, dict):
                asn = v.get("attacker_asn") or v.get("origin_asn")
                if asn is not None:
                    try:
                        attackers.add(int(asn))
                    except (TypeError, ValueError):
                        pass

    bgpsentry_err: list[float] = []
    baseline_err: list[float] = []
    for asn_str, rating in ratings.items():
        try:
            asn = int(asn_str)
        except (TypeError, ValueError):
            continue
        if not isinstance(rating, dict):
            continue
        score = rating.get("current_score", rating.get("score", 50))
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        expected = _expected_score(asn, attackers)
        bgpsentry_err.append(abs(score - expected))
        baseline_err.append(abs(50.0 - expected))  # RPKI-only always 50

    return bgpsentry_err, baseline_err


def build_figure(datasets: list[str], runs_root: Path, output: Path) -> None:
    setup_ieee_column()
    import matplotlib.pyplot as plt
    import numpy as np

    # ── Panel (a): pipeline volumes across sizes ──
    labels: list[str] = []
    total_obs: list[int] = []
    unique_obs: list[int] = []
    tx_written: list[int] = []
    for name in datasets:
        d = runs_root / name
        if not (d / ".done").exists():
            continue
        r = load_run(d)
        labels.append(name.split("_")[-1])
        total_obs.append(r.get("total_observations", 0) or 0)
        # "unique" = total - deduped (approx)
        unique_obs.append(max(0, (r.get("total_observations", 0) or 0)
                              - (r.get("total_skipped", 0) or 0)))
        tx_written.append(r.get("total_committed", 0) or 0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.3))

    if labels:
        x = np.arange(len(labels))
        width = 0.27
        ax1.bar(x - width, total_obs,  width, label="Received",   color=COLORS["primary"])
        ax1.bar(x,         unique_obs, width, label="Unique",     color=COLORS["secondary"])
        ax1.bar(x + width, tx_written, width, label="On-chain",   color=COLORS["tertiary"])
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.set_xlabel("Topology size (ASes)")
        ax1.set_ylabel("Observations / TX (log)")
        ax1.set_yscale("log")
        ax1.legend(loc="upper left", fontsize=6, ncol=1, frameon=False)
        ax1.set_title("(a) Pipeline volume", fontsize=8, loc="left")
        ax1.yaxis.grid(True, linewidth=0.3, color="0.9", which="both")
    else:
        ax1.text(0.5, 0.5, "(no data)", ha="center", va="center", transform=ax1.transAxes)
        ax1.set_title("(a) Pipeline volume", fontsize=8, loc="left")

    # ── Panel (b): ECDF on caida_200 (or caida_100 fallback) ──
    target = runs_root / "caida_200"
    if not (target / ".done").exists():
        target = runs_root / "caida_100"
    bg_err: list[float] = []
    bl_err: list[float] = []
    if (target / ".done").exists():
        r = load_run(target)
        bg_err, bl_err = _compute_rating_errors(r)

    if bg_err and bl_err:
        bg_sorted = np.sort(bg_err)
        bl_sorted = np.sort(bl_err)
        y_bg = np.arange(1, len(bg_sorted) + 1) / len(bg_sorted)
        y_bl = np.arange(1, len(bl_sorted) + 1) / len(bl_sorted)

        ax2.plot(bg_sorted, y_bg, color=COLORS["primary"],
                 linewidth=1.4, label="BGP-Sentry")
        ax2.plot(bl_sorted, y_bl, color=COLORS["muted"],
                 linewidth=1.0, linestyle="--", label="RPKI-only baseline")
        ax2.set_xlabel("Absolute rating error")
        ax2.set_ylabel("CDF")
        ax2.set_xlim(0, 60)
        ax2.set_ylim(0, 1.02)
        ax2.legend(loc="lower right", fontsize=6, frameon=False)
        ax2.yaxis.grid(True, linewidth=0.3, color="0.9")
        ax2.set_title(f"(b) Rating error ECDF ({target.name})", fontsize=8, loc="left")
    else:
        ax2.text(0.5, 0.5, "(no rating data yet)",
                 ha="center", va="center", transform=ax2.transAxes)
        ax2.set_title("(b) Rating error ECDF", fontsize=8, loc="left")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)

    print(f"[fig_ecdf_error] wrote {output}")
    if labels:
        print(f"  panel (a): {len(labels)} datasets — {labels}")
    if bg_err:
        import numpy as np
        print(f"  panel (b): {len(bg_err)} non-RPKI ratings, "
              f"median BGP-Sentry error={np.median(bg_err):.2f}, "
              f"median baseline={np.median(bl_err):.2f}")


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
