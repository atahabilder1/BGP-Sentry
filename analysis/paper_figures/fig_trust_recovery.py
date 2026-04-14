#!/usr/bin/env python3
"""
fig_trust_recovery.py — produces results/figures/fig_trust_recovery.pdf

Trust score trajectories over time for three representative non-RPKI AS
profiles (attacker / honest / reformed) on caida_200, validating the
reactive + adaptive trust engine design (§5 Fig. 4 in the paper).

Reads per-AS rating history from the nonrpki_ratings.json produced by
main_experiment.py. If history data is missing, falls back to a demo
curve so the figure is never empty.
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
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "figures" / "fig_trust_recovery.pdf"
DEFAULT_DATASET = "caida_200"


def extract_trajectories(ratings_all: dict) -> dict[str, list[tuple[float, float]]]:
    """Pick 3 AS trajectories: persistent attacker, honest, reformed.

    Each rating entry typically has:
        {"asn": X, "current_score": 50, "history": [(timestamp, score), ...]}
    """
    if not ratings_all:
        return {}

    candidates = []
    for asn_str, rating in ratings_all.items():
        if not isinstance(rating, dict):
            continue
        history = rating.get("history") or rating.get("rating_history")
        if not isinstance(history, list) or len(history) < 2:
            continue
        # Normalize each point to (time, score) tuples
        norm_hist: list[tuple[float, float]] = []
        for h in history:
            if isinstance(h, dict):
                t = h.get("timestamp") or h.get("t") or h.get("time")
                s = h.get("score") or h.get("rating") or h.get("new_score")
                if t is not None and s is not None:
                    norm_hist.append((float(t), float(s)))
            elif isinstance(h, (list, tuple)) and len(h) >= 2:
                norm_hist.append((float(h[0]), float(h[1])))
        if len(norm_hist) >= 2:
            candidates.append((asn_str, norm_hist))

    if not candidates:
        return {}

    # Classify each by final score and score range
    def classify(traj: list[tuple[float, float]]) -> str:
        scores = [s for _, s in traj]
        final = scores[-1]
        lowest = min(scores)
        if final < 30:
            return "attacker"
        if lowest < 40 < final:
            return "reformed"
        return "honest"

    picked: dict[str, list[tuple[float, float]]] = {}
    for asn_str, traj in candidates:
        cls = classify(traj)
        if cls not in picked:
            picked[cls] = traj
        if len(picked) == 3:
            break
    return picked


def demo_trajectories() -> dict[str, list[tuple[float, float]]]:
    """Fallback: synthetic curves that illustrate the three profiles."""
    return {
        "attacker": [(0, 50), (60, 50), (80, 30), (120, 10), (180, 0), (300, 0)],
        "honest":   [(0, 50), (100, 52), (200, 55), (300, 58)],
        "reformed": [(0, 50), (60, 50), (90, 32), (150, 35), (220, 42), (300, 48)],
    }


def build_figure(dataset: str, runs_root: Path, output: Path) -> None:
    setup_ieee_column()
    import matplotlib.pyplot as plt

    run_dir = runs_root / dataset
    using_demo = False
    if not (run_dir / ".done").exists():
        print(f"[fig_trust_recovery] {dataset} not done; falling back to demo trajectories")
        trajs = demo_trajectories()
        using_demo = True
    else:
        r = load_run(run_dir)
        trajs = extract_trajectories(r.get("ratings_all", {}))
        if not trajs:
            print("[fig_trust_recovery] no rating history found; using demo")
            trajs = demo_trajectories()
            using_demo = True

    fig, ax = plt.subplots(figsize=(3.4, 2.3))

    labels = {
        "attacker": ("Persistent attacker", COLORS["negative"],  "-"),
        "honest":   ("Honest AS",           COLORS["tertiary"],  "-"),
        "reformed": ("Reformed attacker",   COLORS["primary"],   "-"),
    }
    for key, (lbl, color, ls) in labels.items():
        if key not in trajs:
            continue
        traj = trajs[key]
        # Normalize time to start at 0
        t0 = traj[0][0]
        xs = [t - t0 for t, _ in traj]
        ys = [s for _, s in traj]
        ax.plot(xs, ys, color=color, linestyle=ls, label=lbl, linewidth=1.3)

    # Horizontal tier lines
    for score, label in [(90, "Highly trusted"), (70, "Trusted"),
                         (50, "Neutral"), (30, "Suspicious")]:
        ax.axhline(score, color="0.85", linewidth=0.4, linestyle=":", zorder=0)

    ax.set_xlabel("Simulation time (seconds)")
    ax.set_ylabel("Trust score")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, max(300, max((t for traj in trajs.values() for t, _ in traj), default=300)))
    ax.set_yticks([0, 30, 50, 70, 90, 100])
    ax.legend(loc="lower left", fontsize=6, ncol=1)
    if using_demo:
        ax.text(0.98, 0.98, "demo data", transform=ax.transAxes,
                ha="right", va="top", fontsize=5, color="0.5", style="italic")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)

    print(f"[fig_trust_recovery] wrote {output} ({'demo' if using_demo else dataset})")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    build_figure(args.dataset, args.runs_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
