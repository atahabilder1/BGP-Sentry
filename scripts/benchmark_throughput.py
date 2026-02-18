#!/usr/bin/env python3
"""
BGP-Sentry Throughput Benchmark
================================

Runs the experiment at increasing speed multipliers to find maximum
throughput and measure how performance degrades under load.

Produces a benchmark report with TPS, lag, accuracy, and timing at each level.

Usage:
    python3 scripts/benchmark_throughput.py --dataset caida_100
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def set_speed_multiplier(multiplier: float):
    """Update SIMULATION_SPEED_MULTIPLIER in .env."""
    lines = ENV_FILE.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("SIMULATION_SPEED_MULTIPLIER="):
            new_lines.append(f"SIMULATION_SPEED_MULTIPLIER={multiplier}")
        else:
            new_lines.append(line)
    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def run_experiment(dataset: str, duration: int = 1800, wall_timeout: int = 600) -> dict:
    """Run one experiment and return the summary."""
    python = str(PROJECT_ROOT / "venv" / "bin" / "python3")
    cmd = [python, str(PROJECT_ROOT / "main_experiment.py"),
           "--dataset", dataset, "--duration", str(duration)]

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=wall_timeout)
    wall_time = time.time() - start

    # Find the latest results directory
    results_base = PROJECT_ROOT / "results" / dataset
    if not results_base.exists():
        return {"error": "No results directory found", "wall_time": wall_time}

    latest = sorted(results_base.iterdir(), key=lambda p: p.name)[-1]

    summary_file = latest / "summary.json"
    if not summary_file.exists():
        return {"error": "No summary.json found", "wall_time": wall_time}

    summary = json.loads(summary_file.read_text())
    summary["actual_wall_time"] = wall_time

    # Get blockchain stats if available
    blockchain_file = latest / "blockchain_stats.json"
    if blockchain_file.exists():
        summary["blockchain"] = json.loads(blockchain_file.read_text())

    # Get monitoring timeseries if available
    monitoring_file = latest / "monitoring_timeseries.json"
    if monitoring_file.exists():
        monitoring = json.loads(monitoring_file.read_text())
        if monitoring.get("snapshots"):
            # Get peak and average TPS from timeseries
            tps_values = [s.get("avg_tps", 0) for s in monitoring["snapshots"] if s.get("avg_tps", 0) > 0]
            if tps_values:
                summary["peak_tps"] = max(tps_values)
                summary["avg_tps"] = sum(tps_values) / len(tps_values)

            # Get lag info
            lag_values = [s.get("avg_lag", 0) for s in monitoring["snapshots"] if "avg_lag" in s]
            if lag_values:
                summary["avg_lag"] = sum(lag_values) / len(lag_values)
                summary["max_lag"] = max(lag_values)

    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BGP-Sentry throughput benchmark")
    parser.add_argument("--dataset", default="caida_100", help="Dataset to use")
    parser.add_argument("--duration", type=int, default=300, help="Max wall-clock seconds per run")
    args = parser.parse_args()

    # Speed multipliers to test
    multipliers = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    def log(msg):
        print(msg, flush=True)

    log("=" * 70)
    log("BGP-Sentry Throughput Benchmark")
    log(f"Dataset: {args.dataset}")
    log(f"Multipliers: {multipliers}")
    log("=" * 70)

    results = []

    for mult in multipliers:
        log(f"\n{'─' * 70}")
        log(f"Running at {mult}x speed...")
        log(f"{'─' * 70}")

        set_speed_multiplier(mult)

        # Wall timeout: at 1x the 28-min dataset needs ~1800s + overhead.
        # At higher multipliers it finishes faster.
        # Formula: (1700 / multiplier) + 60s overhead
        wall_timeout = int(1700 / mult) + 60

        try:
            summary = run_experiment(args.dataset, duration=args.duration, wall_timeout=wall_timeout)
        except subprocess.TimeoutExpired:
            log(f"  TIMEOUT at {mult}x (wall limit {wall_timeout}s) — blockchain can't keep up!")
            summary = {"error": "timeout", "multiplier": mult}
        except Exception as e:
            log(f"  ERROR at {mult}x: {e}")
            summary = {"error": str(e), "multiplier": mult}

        # Extract key metrics
        perf = summary.get("performance", {})
        node_sum = summary.get("node_summary", {})

        entry = {
            "multiplier": mult,
            "wall_time_seconds": round(summary.get("actual_wall_time", summary.get("elapsed_seconds", 0)), 2),
            "total_processed": node_sum.get("total_observations_processed", 0),
            "attacks_detected": node_sum.get("attacks_detected", 0),
            "precision": perf.get("precision", 0),
            "recall": perf.get("recall", 0),
            "f1_score": perf.get("f1_score", 0),
            "true_positives": perf.get("true_positives", 0),
            "false_positives": perf.get("false_positives", 0),
            "false_negatives": perf.get("false_negatives", 0),
            "peak_tps": round(summary.get("peak_tps", 0), 2),
            "avg_tps": round(summary.get("avg_tps", 0), 2),
            "avg_lag": round(summary.get("avg_lag", 0), 2),
            "max_lag": round(summary.get("max_lag", 0), 2),
        }

        # Calculate effective TPS from wall time
        if entry["wall_time_seconds"] > 0 and entry["total_processed"] > 0:
            entry["effective_total_tps"] = round(entry["total_processed"] / entry["wall_time_seconds"], 1)
            entry["effective_per_node_tps"] = round(entry["effective_total_tps"] / 100, 2)
        else:
            entry["effective_total_tps"] = 0
            entry["effective_per_node_tps"] = 0

        results.append(entry)

        log(f"  Wall time: {entry['wall_time_seconds']}s")
        log(f"  Processed: {entry['total_processed']}")
        log(f"  Effective TPS: {entry['effective_total_tps']} total, {entry['effective_per_node_tps']}/node")
        log(f"  Precision: {entry['precision']}, Recall: {entry['recall']}, F1: {entry['f1_score']}")
        log(f"  Avg lag: {entry['avg_lag']}s, Max lag: {entry['max_lag']}s")

    # Restore real-time speed
    set_speed_multiplier(1.0)

    # Save benchmark results
    benchmark_file = PROJECT_ROOT / "results" / f"benchmark_{args.dataset}.json"
    benchmark_file.parent.mkdir(parents=True, exist_ok=True)
    with open(benchmark_file, "w") as f:
        json.dump({
            "dataset": args.dataset,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        }, f, indent=2)

    log(f"\n{'=' * 70}")
    log("BENCHMARK RESULTS")
    log(f"{'=' * 70}")
    log(f"\n{'Multiplier':>10} {'Wall(s)':>8} {'Total TPS':>10} {'Per-Node':>10} {'Precision':>10} {'Recall':>8} {'F1':>6} {'Max Lag':>8}")
    log(f"{'─' * 10} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 6} {'─' * 8}")
    for r in results:
        log(f"{r['multiplier']:>10.0f}x {r['wall_time_seconds']:>7.1f}s {r['effective_total_tps']:>10.1f} {r['effective_per_node_tps']:>10.2f} {r['precision']:>10.3f} {r['recall']:>8.3f} {r['f1_score']:>6.3f} {r['max_lag']:>7.1f}s")

    log(f"\nResults saved to: {benchmark_file}")


if __name__ == "__main__":
    main()
