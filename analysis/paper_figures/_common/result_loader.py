"""Load a single BGP-Sentry simulation run directory into a structured dict.

Every rendering script starts by calling `load_run(path)` on a
results/primary/caida_N/ or results/ablation/*/ directory and getting
back a single dict with flat access to all the metrics it needs.

This keeps the figure scripts from duplicating JSON-file-parsing logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_load(path: Path) -> dict:
    """Load a JSON file, returning {} if missing or malformed."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_run(run_dir: Path | str) -> dict[str, Any]:
    """Load a completed simulation run directory.

    Args:
        run_dir: Path to a results/primary/caida_N/ (or ablation/) dir

    Returns:
        Flat dict with keys for every top-level metric the rendering
        scripts care about. Missing files → defaults (empty dicts, zeros).
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {run_dir}")

    summary = _safe_load(run_dir / "summary.json")
    perf = _safe_load(run_dir / "performance_metrics.json")
    blk = _safe_load(run_dir / "blockchain_stats.json")
    cons = _safe_load(run_dir / "consensus_log.json")
    bus = _safe_load(run_dir / "message_bus_stats.json")
    dedup = _safe_load(run_dir / "dedup_stats.json")
    coin = _safe_load(run_dir / "bgpcoin_economy.json")
    trust = _safe_load(run_dir / "trust_scores.json")
    ratings = _safe_load(run_dir / "nonrpki_ratings.json")
    verdicts = _safe_load(run_dir / "attack_verdicts.json")
    detection = _safe_load(run_dir / "detection_results.json")
    metadata = _safe_load(run_dir / "metadata.json")
    run_config = _safe_load(run_dir / "run_config.json")

    ds = summary.get("dataset", {})
    node_sum = summary.get("node_summary", {})

    return {
        "run_dir": str(run_dir),

        # ── Dataset identity ──
        "dataset_name": ds.get("dataset_name", run_dir.name),
        "total_ases": ds.get("total_ases", 0),
        "rpki_count": ds.get("rpki_count", 0),
        "non_rpki_count": ds.get("non_rpki_count", 0),
        "total_observations": ds.get("total_observations", 0),

        # ── Detection performance ──
        "ground_truth_attacks": perf.get("ground_truth_attacks", 0),
        "total_detections": perf.get("total_detections", 0),
        "true_positives": perf.get("true_positives", 0),
        "false_positives": perf.get("false_positives", 0),
        "false_negatives": perf.get("false_negatives", 0),
        "precision": perf.get("precision", 0.0),
        "recall": perf.get("recall", 0.0),
        "f1_score": perf.get("f1_score", 0.0),
        "per_type_metrics": perf.get("per_attack_type", {}),

        # ── Blockchain ──
        "total_blocks": _sum_dict(blk.get("blocks_per_node", {})),
        "total_forks_detected": blk.get("total_forks_detected", 0),
        "total_forks_resolved": blk.get("total_forks_resolved", 0),
        "valid_chains": blk.get("valid_chains", 0),
        "blk_total_nodes": blk.get("total_nodes", 0),
        "blocks_per_node": blk.get("blocks_per_node", {}),
        "block_type_counts": cons.get("block_type_counts", {}),

        # ── Consensus ──
        "total_tx_created": cons.get("total_transactions_created", 0),
        "total_committed": cons.get("total_committed", 0),
        "consensus_status": cons.get("consensus_status_all_chains", {}),
        "consensus_status_unique": cons.get("consensus_status_unique", {}),
        "unique_transactions": cons.get("unique_transactions_across_chains", 0),

        # ── P2P ──
        "p2p_sent": bus.get("sent", 0),
        "p2p_delivered": bus.get("delivered", 0),
        "p2p_dropped": bus.get("dropped", 0),

        # ── Deduplication ──
        "rpki_deduped": dedup.get("rpki_deduped", 0),
        "nonrpki_throttled": dedup.get("nonrpki_throttled", 0),
        "total_skipped": dedup.get("total_skipped", 0),

        # ── BGPCoin economy ──
        "bgpcoin_distributed": coin.get("total_distributed", 0),
        "bgpcoin_treasury": coin.get("treasury_balance", 0),
        "bgpcoin_circulating": coin.get("circulating_supply", 0),

        # ── Trust ratings (non-RPKI) ──
        "ratings_summary": ratings.get("summary", {}),
        "ratings_all": ratings.get("ratings", {}),
        "trust_scores": trust,
        "attack_verdicts": verdicts,
        "detection_results": detection,

        # ── Runtime / provenance ──
        "elapsed_seconds": summary.get("elapsed_seconds", 0),
        "duration_limit": run_config.get("duration_limit", 0),
        "metadata": metadata,
        "run_config": run_config,
    }


def load_runs(runs_dir: Path | str) -> dict[str, dict]:
    """Load every completed run under `runs_dir` (each subdir = one run).

    Returns {run_name: loaded_dict}. Skips subdirs without a .done marker.
    """
    runs_dir = Path(runs_dir)
    out: dict[str, dict] = {}
    if not runs_dir.is_dir():
        return out
    for sub in sorted(runs_dir.iterdir()):
        if not sub.is_dir():
            continue
        if not (sub / ".done").exists():
            continue
        try:
            out[sub.name] = load_run(sub)
        except Exception as e:
            print(f"[result_loader] skipping {sub}: {e}")
    return out


def tps_network(run: dict) -> float:
    """Network-wide TPS = committed transactions / elapsed seconds."""
    dur = run.get("duration_limit") or run.get("elapsed_seconds") or 1
    return run["total_committed"] / max(dur, 1)


def tps_per_node(run: dict) -> float:
    """Per-validator TPS = network TPS / number of RPKI validators."""
    val = run.get("rpki_count") or run.get("blk_total_nodes") or 1
    return tps_network(run) / max(val, 1)


def _sum_dict(d: dict) -> int:
    """Sum the integer values of a dict (ignoring non-numeric)."""
    total = 0
    for v in d.values():
        try:
            total += int(v)
        except (TypeError, ValueError):
            pass
    return total
