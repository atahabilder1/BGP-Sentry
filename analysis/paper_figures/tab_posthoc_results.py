#!/usr/bin/env python3
"""
tab_posthoc_results.py — produces results/tables/tab_posthoc_results.tex

Post-hoc forensic analysis table (§5 Table 3 in the paper). Reuses the
existing analysis/posthoc_analysis.py script against three primary runs
(caida_100, caida_200, caida_350) and formats the results.

Falls back to placeholder cells if the posthoc script can't be imported
or if a run isn't completed yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from _common.latex_table import write_latex_table, fmt_int  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "results" / "primary"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "tables" / "tab_posthoc_results.tex"
DEFAULT_DATASETS = ["caida_100", "caida_200", "caida_350"]

# Each row: (analysis category, metric label, key in the posthoc output dict)
ROWS = [
    ("Cross-Observer Route Stability", "Prefixes flagged (real-time)", "flagged_prefixes"),
    ("Cross-Observer Route Stability", "Systemic (multi-observer)",    "systemic_flagged"),
    ("Cross-Observer Route Stability", "Localized / FPs filtered",     "localized_filtered"),
    ("Coordinated Attack Detection",   "Coordination clusters",        "coordination_clusters"),
    ("Coordinated Attack Detection",   "Max attackers per cluster",    "max_cluster_size"),
    ("Observer Integrity Auditing",    "Observers audited",            "observers_audited"),
    ("Observer Integrity Auditing",    "Outliers ($>$2$\\sigma$ FP rate)", "observer_outliers"),
    ("Behavioral Pattern Detection",   "ASes with attacks",            "ases_with_attacks"),
    ("Behavioral Pattern Detection",   "Multi-phase attackers",        "multi_phase_attackers"),
    ("Behavioral Pattern Detection",   "Gaming pattern detected",      "gaming_patterns"),
]


def _try_run_posthoc(run_dir: Path) -> dict:
    """Try to run the existing posthoc_analysis.py against a run directory.

    Returns a flat dict of the metrics ROWS needs. Best-effort — returns
    an empty dict on any failure so the table shows '--' instead of
    crashing the render pipeline.
    """
    script = PROJECT_ROOT / "analysis" / "posthoc_analysis.py"
    if not script.exists():
        return {}
    # Insert analysis/ on path and import
    sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
    try:
        import importlib
        posthoc = importlib.import_module("posthoc_analysis")
    except Exception as e:
        print(f"[WARN] couldn't import posthoc_analysis: {e}")
        return {}

    # Best-effort: look for a top-level function that returns metrics
    for fn_name in ("analyze", "run_posthoc_analysis", "main", "analyze_run"):
        fn = getattr(posthoc, fn_name, None)
        if callable(fn):
            try:
                result = fn(str(run_dir))
                if isinstance(result, dict):
                    return result
            except Exception as e:
                print(f"[WARN] posthoc.{fn_name}({run_dir}) failed: {e}")
                break

    # Fallback: check for a cached posthoc_results.json in the run dir
    cached = run_dir / "posthoc_results.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text())
        except Exception:
            pass
    return {}


def build_table(datasets: list[str], runs_root: Path, output: Path) -> None:
    data: dict[str, dict] = {}
    for name in datasets:
        d = runs_root / name
        if (d / ".done").exists():
            data[name] = _try_run_posthoc(d)
        else:
            data[name] = {}

    columns = datasets
    header_row = ["\\textbf{Analysis}"] + [
        f"\\textbf{{{name.split('_')[-1]} ASes}}" for name in columns
    ]

    body_rows: list[list[str]] = []
    section_headers: dict[int, str] = {}
    last_section: str | None = None
    for idx, (section, label, key) in enumerate(ROWS):
        if section != last_section:
            section_headers[len(body_rows)] = section
            last_section = section
        row = [f"\\quad {label}"]
        for name in columns:
            val = data[name].get(key) if data[name] else None
            row.append(fmt_int(val))
        body_rows.append(row)

    write_latex_table(
        path=output,
        caption="Post-hoc forensic analysis results across three CAIDA topologies.",
        label="tab:posthoc_results",
        column_spec="l" + "r" * len(columns),
        header_row=header_row,
        body_rows=body_rows,
        section_headers=section_headers,
    )

    print(f"[tab_posthoc_results] wrote {output}")
    missing = [n for n in columns if not data[n]]
    if missing:
        print(f"  (no posthoc data for: {', '.join(missing)})")


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
