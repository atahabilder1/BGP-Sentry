#!/usr/bin/env python3
"""
tab_system_performance.py — produces results/tables/tab_system_performance.tex

Reads each primary scalability run (results/primary/caida_<N>/) and builds
a LaTeX table with three sections:
  (1) Detection — per-attack F1 score
  (2) Blockchain & Consensus — TX created, confirmed %, blocks, fork rate
  (3) P2P & Throughput — messages, delivery rate, network + per-node TPS

Any missing run columns are shown as "--".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.result_loader import load_run, tps_network, tps_per_node  # noqa: E402
from _common.latex_table import write_latex_table, fmt_int, fmt_float, fmt_pct  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "results" / "primary"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "tables" / "tab_system_performance.tex"
DEFAULT_DATASETS = ["caida_100", "caida_200", "caida_350", "caida_650", "caida_1250"]


def fmt_count_large(n: int | None) -> str:
    """Format large counts with K/M suffixes like the paper."""
    if n is None:
        return "--"
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{int(n)}"


def fmt_tps(x: float | None) -> str:
    return "--" if x is None else (f"{x:.2f}" if x >= 1 else f"{x:.3f}")


def _pct(numer: int, denom: int) -> float:
    return 100.0 * numer / denom if denom else 0.0


def build_table(datasets: list[str], runs_root: Path, output: Path) -> None:
    loaded: dict[str, dict] = {}
    for name in datasets:
        d = runs_root / name
        if not (d / ".done").exists():
            print(f"[WARN] run not completed: {d}")
            loaded[name] = {}
            continue
        loaded[name] = load_run(d)

    columns = datasets  # preserve order even if some are missing

    header_row = ["\\textbf{Metric}"] + [
        f"\\textbf{{{name.split('_')[-1]}}}$^*$" for name in columns
    ]

    def col(r: dict, key: str, fmt) -> str:
        if not r:
            return "--"
        val = r.get(key)
        return fmt(val) if val is not None else "--"

    body_rows: list[list[str]] = []
    section_headers: dict[int, str] = {}

    # ── Detection F1 by attack type ──
    # Per-attack F1 is in r['per_type_metrics'] (may be empty if not computed)
    attack_rows = [
        ("PREFIX_HIJACK", "Prefix Hijack"),
        ("SUBPREFIX_HIJACK", "Subprefix Hijack"),
        ("BOGON_INJECTION", "Bogon Injection"),
        ("ROUTE_FLAPPING", "Route Flapping"),
        ("FORGED_ORIGIN_PREFIX_HIJACK", "Forged Origin"),
        ("ACCIDENTAL_ROUTE_LEAK", "Route Leak"),
    ]
    section_headers[len(body_rows)] = "Detection (F1 score)"
    for key, label in attack_rows:
        row = [f"\\quad {label}"]
        for name in columns:
            r = loaded[name]
            f1 = "--"
            if r and r.get("per_type_metrics"):
                m = r["per_type_metrics"].get(key)
                if isinstance(m, dict):
                    f1 = fmt_float(m.get("f1", m.get("f1_score")), 2)
            row.append(f1)
        body_rows.append(row)

    # ── Blockchain & Consensus ──
    section_headers[len(body_rows)] = "Blockchain \\& Consensus"
    # TX Created (unique)
    body_rows.append(
        ["TX Created"]
        + [col(loaded[n], "total_tx_created", fmt_count_large) for n in columns]
    )
    # Committed (unique)
    body_rows.append(
        ["TX Committed"]
        + [col(loaded[n], "total_committed", fmt_count_large) for n in columns]
    )
    # Confirmed % — from consensus_status dict
    conf_pct_row = ["Confirmed (\\%)"]
    for n in columns:
        r = loaded[n]
        if not r:
            conf_pct_row.append("--")
            continue
        statuses = r.get("consensus_status", {}) or {}
        total = sum(v for v in statuses.values() if isinstance(v, (int, float)))
        conf = statuses.get("CONFIRMED", 0)
        conf_pct_row.append(fmt_pct(_pct(conf, total), 1))
    body_rows.append(conf_pct_row)

    # Single-witness %
    sw_pct_row = ["Single-witness (\\%)"]
    for n in columns:
        r = loaded[n]
        if not r:
            sw_pct_row.append("--")
            continue
        statuses = r.get("consensus_status", {}) or {}
        total = sum(v for v in statuses.values() if isinstance(v, (int, float)))
        sw = statuses.get("SINGLE_WITNESS", 0)
        sw_pct_row.append(fmt_pct(_pct(sw, total), 1))
    body_rows.append(sw_pct_row)

    # Total blocks
    body_rows.append(
        ["Total blocks"]
        + [col(loaded[n], "total_blocks", fmt_count_large) for n in columns]
    )
    # Fork resolution rate
    fr_row = ["Fork resolution (\\%)"]
    for n in columns:
        r = loaded[n]
        if not r:
            fr_row.append("--")
            continue
        det = r.get("total_forks_detected", 0) or 0
        res = r.get("total_forks_resolved", 0) or 0
        fr_row.append(fmt_pct(_pct(res, det) if det else 100.0, 1))
    body_rows.append(fr_row)

    # Valid chains %
    vc_row = ["Valid chains (\\%)"]
    for n in columns:
        r = loaded[n]
        if not r:
            vc_row.append("--")
            continue
        tot = r.get("blk_total_nodes", 0) or 0
        vc = r.get("valid_chains", 0) or 0
        vc_row.append(fmt_pct(_pct(vc, tot) if tot else 100.0, 1))
    body_rows.append(vc_row)

    # ── P2P & Throughput ──
    section_headers[len(body_rows)] = "P2P \\& Throughput"
    body_rows.append(
        ["P2P Messages"]
        + [col(loaded[n], "p2p_sent", fmt_count_large) for n in columns]
    )
    dr_row = ["Delivery rate (\\%)"]
    for n in columns:
        r = loaded[n]
        if not r:
            dr_row.append("--")
            continue
        sent = r.get("p2p_sent", 0) or 0
        deliv = r.get("p2p_delivered", 0) or 0
        dr_row.append(fmt_pct(_pct(deliv, sent) if sent else 100.0, 1))
    body_rows.append(dr_row)

    # Network TPS
    body_rows.append(
        ["Network TPS"]
        + [fmt_tps(tps_network(loaded[n])) if loaded[n] else "--" for n in columns]
    )
    # Per-node TPS
    body_rows.append(
        ["Per-node TPS"]
        + [fmt_tps(tps_per_node(loaded[n])) if loaded[n] else "--" for n in columns]
    )

    col_spec = "l" + "r" * len(columns)

    write_latex_table(
        path=output,
        caption=(
            "System performance across scales. "
            "Detection F1 per attack type, blockchain commit and consensus "
            "statistics, and P2P throughput, measured on the primary "
            "scalability runs with the default consensus configuration "
            "($\\tau{=}3$, $\\sqrt{N}$ broadcast, 1-hop discovery, 15\\,s timeout)."
        ),
        label="tab:system_performance",
        column_spec=col_spec,
        header_row=header_row,
        body_rows=body_rows,
        section_headers=section_headers,
        notes=[
            "$^*$Column headers = nominal dataset size (actual ${\\pm}5\\%$)."
        ],
    )

    # Console summary
    print(f"\n[tab_system_performance] wrote {output}\n")
    print(f"{'Dataset':<14} {'TX':>8} {'Conf%':>7} {'Forks/Res':>14} {'P2P':>8} {'NetTPS':>8}")
    print("-" * 65)
    for n in columns:
        r = loaded[n]
        if not r:
            print(f"{n:<14}  (no run)")
            continue
        statuses = r.get("consensus_status", {}) or {}
        total = sum(v for v in statuses.values() if isinstance(v, (int, float)))
        conf = statuses.get("CONFIRMED", 0)
        conf_pct = _pct(conf, total)
        print(
            f"{n:<14} "
            f"{fmt_count_large(r['total_tx_created']):>8} "
            f"{conf_pct:>6.1f}% "
            f"{r['total_forks_resolved']}/{r['total_forks_detected']:>6} "
            f"{fmt_count_large(r['p2p_sent']):>8} "
            f"{tps_network(r):>7.2f}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    p.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    build_table(args.datasets, args.runs_root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
