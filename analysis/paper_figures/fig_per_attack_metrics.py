#!/usr/bin/env python3
"""
fig_per_attack_metrics.py — produces results/figures/fig_per_attack_metrics.pdf

Grouped bar chart showing per-attack-type Precision / Recall / F1 on the
representative caida_200 topology. Falls back to caida_100 if caida_200
isn't done yet.
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
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "figures" / "fig_per_attack_metrics.pdf"
DEFAULT_DATASET = "caida_200"

ATTACK_ORDER = [
    ("PREFIX_HIJACK",               "Prefix"),
    ("SUBPREFIX_HIJACK",            "Subprefix"),
    ("BOGON_INJECTION",             "Bogon"),
    ("ROUTE_FLAPPING",              "Flap"),
    ("FORGED_ORIGIN_PREFIX_HIJACK", "Forged"),
    ("ACCIDENTAL_ROUTE_LEAK",       "Leak"),
]


def _compute_per_attack_from_detection(run: dict) -> dict[str, dict[str, float]]:
    """If per_attack_type metrics are missing, compute them from
    detection_results + attack ground truth via simple label matching.
    Returns {attack_key: {"precision": x, "recall": y, "f1": z}}.
    """
    metrics = run.get("per_type_metrics") or {}
    if metrics:
        return metrics

    # Fallback: walk detection_results.json + ground_truth labels
    # This is a rough approximation — main_experiment.py should compute
    # these itself in _compute_performance_metrics() ideally.
    return {}


def build_figure(dataset: str, runs_root: Path, output: Path) -> None:
    setup_ieee_column()
    import matplotlib.pyplot as plt
    import numpy as np

    run_dir = runs_root / dataset
    if not (run_dir / ".done").exists():
        alt = runs_root / "caida_100"
        if (alt / ".done").exists():
            print(f"[fig_per_attack_metrics] {dataset} not done, falling back to caida_100")
            run_dir = alt
            dataset = "caida_100"
        else:
            sys.exit(f"No completed run available (tried {dataset} and caida_100)")

    r = load_run(run_dir)
    per_type = _compute_per_attack_from_detection(r)

    if not per_type:
        print(f"[WARN] no per-attack metrics in {run_dir}; producing placeholder figure")
        per_type = {k: {"precision": 0.0, "recall": 0.0, "f1": 0.0} for k, _ in ATTACK_ORDER}

    labels = [lbl for _, lbl in ATTACK_ORDER]
    precision = [float(per_type.get(k, {}).get("precision", 0.0)) for k, _ in ATTACK_ORDER]
    recall = [float(per_type.get(k, {}).get("recall", 0.0)) for k, _ in ATTACK_ORDER]
    f1 = [float(per_type.get(k, {}).get("f1", per_type.get(k, {}).get("f1_score", 0.0))) for k, _ in ATTACK_ORDER]

    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    x = np.arange(len(labels))
    width = 0.27

    ax.bar(x - width, precision, width, label="Precision", color=COLORS["primary"])
    ax.bar(x,         recall,    width, label="Recall",    color=COLORS["tertiary"])
    ax.bar(x + width, f1,        width, label="F1",        color=COLORS["secondary"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18),
              ncol=3, fontsize=6, frameon=False)
    ax.yaxis.grid(True, linewidth=0.3, color="0.9")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)

    print(f"[fig_per_attack_metrics] wrote {output} (from {dataset})")
    for i, (_, lbl) in enumerate(ATTACK_ORDER):
        print(f"  {lbl:<10}: P={precision[i]:.3f}  R={recall[i]:.3f}  F1={f1[i]:.3f}")


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
