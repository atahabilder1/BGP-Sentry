#!/usr/bin/env python3
"""Quick benchmark for remaining multipliers 7x-10x."""
import sys, os, json, time, subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

def set_speed(mult):
    lines = ENV_FILE.read_text().splitlines()
    new = []
    for line in lines:
        if line.strip().startswith("SIMULATION_SPEED_MULTIPLIER="):
            new.append(f"SIMULATION_SPEED_MULTIPLIER={mult}")
        else:
            new.append(line)
    ENV_FILE.write_text("\n".join(new) + "\n")

def log(msg):
    print(msg, flush=True)

python = str(PROJECT_ROOT / "venv" / "bin" / "python3")

for mult in [7.0, 8.0, 9.0, 10.0]:
    log(f"\n--- Running at {mult}x ---")
    set_speed(mult)
    wall_timeout = int(1700 / mult) + 120
    start = time.time()
    try:
        r = subprocess.run(
            [python, str(PROJECT_ROOT / "main_experiment.py"), "--dataset", "caida_100", "--duration", "1800"],
            capture_output=True, text=True, timeout=wall_timeout
        )
        wall = time.time() - start
    except subprocess.TimeoutExpired:
        wall = time.time() - start
        log(f"  TIMEOUT after {wall:.0f}s — blockchain can't keep up at {mult}x!")
        continue

    # Read results
    results_base = PROJECT_ROOT / "results" / "caida_100"
    latest = sorted(results_base.iterdir(), key=lambda p: p.name)[-1]
    summary = json.loads((latest / "summary.json").read_text())
    perf = summary.get("performance", {})
    node_sum = summary.get("node_summary", {})
    total_processed = node_sum.get("total_observations_processed", 0)
    total_tps = round(total_processed / wall, 1) if wall > 0 else 0
    per_node_tps = round(total_tps / 100, 2)

    log(f"  Wall time: {wall:.1f}s")
    log(f"  Processed: {total_processed}")
    log(f"  Total TPS: {total_tps}, Per-node: {per_node_tps}")
    log(f"  Precision: {perf.get('precision', 0)}, Recall: {perf.get('recall', 0)}, F1: {perf.get('f1_score', 0)}")

# Restore 1x
set_speed(1.0)
log("\nDone. Speed restored to 1.0x")
