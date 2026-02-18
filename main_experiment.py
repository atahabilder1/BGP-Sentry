#!/usr/bin/env python3
"""
BGP-Sentry Main Experiment Orchestrator
========================================

Runs the BGP-Sentry distributed blockchain simulation using CAIDA datasets.

Usage:
    python3 main_experiment.py --dataset caida_100
    python3 main_experiment.py --dataset caida_100 --duration 300

Author: Anik Tahabilder
"""

import sys
import os
import time
import platform
import signal
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "nodes" / "rpki_nodes" / "shared_blockchain_stack"))
sys.path.insert(0, str(PROJECT_ROOT / "nodes" / "rpki_nodes" / "shared_blockchain_stack" / "blockchain_utils"))

# Import simulation helpers
from simulation_helpers import SharedClockManager, SimulationOrchestrator, create_default_experiment_config

# Import data-driven components
# IMPORTANT: Import via direct module name (not package path) so that the same
# RPKINodeRegistry class is shared with bgpcoin_ledger.py, p2p_transaction_pool.py,
# etc. which also use `from rpki_node_registry import RPKINodeRegistry`.
# If imported via different paths, Python creates separate class objects and
# initialize() only affects one copy.
from rpki_node_registry import RPKINodeRegistry
from data_loader import DatasetLoader
from node_manager import NodeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BGP-Sentry-Main')


def get_system_info():
    """Collect system/hardware information for performance benchmarking."""
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
    }

    # CPU info
    try:
        cpu_count = os.cpu_count()
        info["cpu_count"] = cpu_count
    except Exception:
        pass

    # Memory info (Linux)
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_kb = int(line.split()[1])
                    info["memory_total_gb"] = round(mem_kb / 1024 / 1024, 1)
                    break
    except Exception:
        pass

    # CPU model (Linux)
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    info["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    return info


def resolve_dataset_path(dataset_name):
    """Resolve dataset name to full path."""
    dataset_dir = PROJECT_ROOT / "dataset" / dataset_name
    if dataset_dir.exists():
        return str(dataset_dir)

    # Try as absolute/relative path
    if Path(dataset_name).exists():
        return str(Path(dataset_name).resolve())

    raise FileNotFoundError(
        f"Dataset '{dataset_name}' not found. "
        f"Looked in: {PROJECT_ROOT / 'dataset' / dataset_name}"
    )


class BGPSentryExperiment:
    """
    Main experiment controller that orchestrates the entire BGP-Sentry simulation.

    Startup sequence:
      1. Resolve dataset path
      2. RPKINodeRegistry.initialize(dataset_path)
      3. DatasetLoader loads observations + ground truth
      4. NodeManager creates virtual nodes
      5. Orchestrator runs virtual nodes in-process
      6. Results written to results/<dataset>/<timestamp>/
    """

    def __init__(self, dataset_path, duration=300, clean=True):
        self.dataset_path = dataset_path
        self.duration = duration

        # Clean blockchain state from previous runs
        if clean:
            self._reset_blockchain_state()

        # Initialize registry from dataset
        RPKINodeRegistry.initialize(dataset_path)

        # Load dataset
        self.data_loader = DatasetLoader(dataset_path)
        logger.info(f"Dataset summary: {json.dumps(self.data_loader.summary(), indent=2)}")

        # Create node manager with project root for blockchain data paths
        self.node_manager = NodeManager(self.data_loader, project_root=str(PROJECT_ROOT))

        # Create orchestrator with node manager
        self.orchestrator = SimulationOrchestrator(node_manager=self.node_manager)

        # Results directory
        dataset_name = self.data_loader.dataset_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = PROJECT_ROOT / "results" / dataset_name / timestamp
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Experiment state
        self.experiment_start_time = None
        self.shutdown_requested = False

        # System info for benchmarking
        self.system_info = get_system_info()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _reset_blockchain_state(self):
        """Reset all blockchain data to start fresh for this experiment."""
        import shutil
        bc_dir = PROJECT_ROOT / "blockchain_data"
        if bc_dir.exists():
            shutil.rmtree(bc_dir)
            logger.info("Cleaned blockchain state from previous runs")
        bc_dir.mkdir(parents=True, exist_ok=True)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True

    def run(self):
        """Run the full experiment."""
        logger.info("=" * 70)
        logger.info("BGP-SENTRY EXPERIMENT STARTING")
        logger.info("=" * 70)
        logger.info(f"Dataset: {self.data_loader.dataset_name}")
        logger.info(f"Nodes: {self.data_loader.total_ases} ({self.data_loader.rpki_count} RPKI, {self.data_loader.non_rpki_count} non-RPKI)")
        logger.info(f"Duration limit: {self.duration}s")
        logger.info(f"Results: {self.results_dir}")

        self.experiment_start_time = time.time()

        try:
            # Step 0: Start monitoring dashboard
            from monitoring.dashboard_server import SimulationDashboard
            self._dashboard = SimulationDashboard(
                node_manager=self.node_manager,
                clock=self.node_manager.simulation_clock,
                port=5555,
                system_info=self.system_info,
            )
            self._dashboard.start()

            # Step 1: Generate VRP
            self._generate_vrp()

            # Step 2: Start nodes
            logger.info("Starting all virtual nodes...")
            self.orchestrator.start_all_nodes()

            # Step 3: Wait for processing
            logger.info("Processing observations...")
            completed = self.node_manager.wait_for_completion(
                timeout=self.duration,
                poll_interval=5.0,
            )

            if not completed:
                logger.warning("Processing did not complete within timeout")

            # Step 4: Save monitoring time-series data
            if hasattr(self, '_dashboard'):
                self._dashboard.save_report(self.results_dir)
                self._dashboard.stop()

            # Step 5: Collect and write results
            self._write_results()

            elapsed = time.time() - self.experiment_start_time
            logger.info("=" * 70)
            logger.info(f"EXPERIMENT COMPLETED in {elapsed:.1f}s")
            logger.info(f"Results written to: {self.results_dir}")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.orchestrator.stop_all_nodes()

    def _generate_vrp(self):
        """Generate VRP file from dataset."""
        vrp_path = PROJECT_ROOT / "stayrtr" / "vrp_generated.json"
        vrp_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            generate_script = PROJECT_ROOT / "scripts" / "generate_vrp.py"
            subprocess.run(
                [sys.executable, str(generate_script), self.dataset_path, str(vrp_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"VRP generated: {vrp_path}")
        except Exception as e:
            logger.warning(f"VRP generation failed (non-fatal): {e}")

    def _write_results(self):
        """Write structured results to the results directory."""
        elapsed = time.time() - self.experiment_start_time

        def _safe_write(filename, data):
            """Write JSON file, catching serialization errors."""
            try:
                with open(self.results_dir / filename, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            except Exception as e:
                logger.error(f"Failed to write {filename}: {e}")

        # 1. Detection results
        all_results = self.node_manager.get_all_detection_results()
        _safe_write("detection_results.json", all_results)

        # 2. Trust scores (per-node)
        trust_scores = {}
        for asn, node in self.node_manager.nodes.items():
            trust_scores[str(asn)] = {
                "asn": asn,
                "is_rpki": node.is_rpki,
                "role": node.rpki_role,
                "trust_score": node.trust_score,
                "observations_processed": node.processed_count,
                "attacks_detected": len(node.attack_detections),
                "stats": node.stats,
            }
        _safe_write("trust_scores.json", trust_scores)

        # 3. Performance metrics (compare against ground truth)
        performance = self._compute_performance_metrics()
        _safe_write("performance_metrics.json", performance)

        # 4. Summary
        summary = {
            "dataset": self.data_loader.summary(),
            "node_summary": self.node_manager.get_summary(),
            "performance": performance,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now().isoformat(),
        }
        _safe_write("summary.json", summary)

        # 5. Run config (includes system info for benchmarking)
        run_config = {
            "dataset_path": self.dataset_path,
            "dataset_name": self.data_loader.dataset_name,
            "duration_limit": self.duration,
            "actual_duration": elapsed,
            "system_info": self.system_info,
            "rpki_node_count": self.data_loader.rpki_count,
            "non_rpki_node_count": self.data_loader.non_rpki_count,
            "total_nodes": self.data_loader.total_ases,
            "consensus_threshold": RPKINodeRegistry.get_consensus_threshold(),
            "timestamp": datetime.now().isoformat(),
        }
        _safe_write("run_config.json", run_config)

        # --- NEW: Blockchain infrastructure results ---

        # 6. Blockchain stats (blocks written, transactions, integrity check)
        blockchain_stats = self.node_manager.get_blockchain_stats()
        _safe_write("blockchain_stats.json", blockchain_stats)

        # 7. BGPCoin economy (treasury, distributed, burned, per-node balances)
        bgpcoin_economy = self.node_manager.get_bgpcoin_summary()
        _safe_write("bgpcoin_economy.json", bgpcoin_economy)

        # 8. Non-RPKI ratings (rating for each non-RPKI AS + history)
        nonrpki_ratings = {
            "summary": self.node_manager.get_rating_summary(),
            "ratings": self.node_manager.get_all_ratings(),
        }
        _safe_write("nonrpki_ratings.json", nonrpki_ratings)

        # 9. Consensus log (confirmed, insufficient, single-witness)
        consensus_log = self.node_manager.get_consensus_log()
        _safe_write("consensus_log.json", consensus_log)

        # 10. Attack verdicts (proposals, votes, verdicts, confidence)
        attack_verdicts = self.node_manager.get_attack_verdicts()
        _safe_write("attack_verdicts.json", attack_verdicts)

        # 11. Dedup stats (how many observations were deduplicated/throttled)
        dedup_stats = self.node_manager.get_dedup_stats()
        _safe_write("dedup_stats.json", dedup_stats)

        # 12. Message bus stats
        bus_stats = self.node_manager.get_message_bus_stats()
        _safe_write("message_bus_stats.json", bus_stats)

        # 13. Cryptographic signing summary
        crypto_summary = self.node_manager.get_crypto_summary()
        _safe_write("crypto_summary.json", crypto_summary)

        # 14. Save Ed25519 keys to disk (per-node folders + public key registry)
        try:
            self.node_manager.save_keys_to_disk()
        except Exception as e:
            logger.warning(f"Failed to save keys to disk: {e}")

        # 15. Human-readable README summary of this run
        self._write_result_readme(summary, performance, blockchain_stats,
                                  bgpcoin_economy, nonrpki_ratings,
                                  consensus_log, dedup_stats, bus_stats,
                                  attack_verdicts, run_config, crypto_summary)

        # 16. Generate analysis notebook
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
            from generate_analysis_notebook import generate_notebook
            nb_path = generate_notebook(str(self.results_dir))
            if nb_path:
                logger.info(f"Analysis notebook: {nb_path}")
        except Exception as e:
            logger.warning(f"Failed to generate analysis notebook: {e}")

        logger.info(f"Results written: {self.results_dir} (15 files + notebook + keys)")

    # ------------------------------------------------------------------
    def _write_result_readme(self, summary, performance, blockchain_stats,
                             bgpcoin_economy, nonrpki_ratings, consensus_log,
                             dedup_stats, bus_stats, attack_verdicts, run_config,
                             crypto_summary=None):
        """Generate a comprehensive markdown report for this experiment run."""
        ds = summary.get("dataset", {})
        ns = summary.get("node_summary", {})
        perf = performance or {}
        bc = blockchain_stats or {}
        bc_info = bc.get("blockchain_info", {})
        integrity = bc.get("integrity", {})
        eco = bgpcoin_economy or {}
        cl = consensus_log or {}
        dd = dedup_stats or {}
        bus = bus_stats or {}
        cfg_data = run_config or {}
        ratings_summary = (nonrpki_ratings or {}).get("summary", {})
        all_ratings = (nonrpki_ratings or {}).get("ratings", {})

        # Rating distribution (from summary.by_level)
        rating_dist = ratings_summary.get("by_level", {})
        if not rating_dist:
            for asn_str, info in all_ratings.items():
                category = info.get("rating_level", "unknown")
                rating_dist[category] = rating_dist.get(category, 0) + 1

        # Attack verdict breakdown
        verdict_types = {}
        for v in (attack_verdicts or []):
            atype = v.get("attack_type", "unknown")
            verdict_types[atype] = verdict_types.get(atype, 0) + 1

        elapsed = summary.get("elapsed_seconds", 0)
        sysinfo = cfg_data.get("system_info", {})

        # Compute throughput metrics
        total_processed = ns.get("total_observations_processed", 0)
        total_nodes = ds.get("total_ases", 100)
        rpki_count = ds.get("rpki_count", 0)
        nonrpki_count = ds.get("non_rpki_count", 0)
        network_tps = round(total_processed / elapsed, 1) if elapsed > 0 else 0
        per_node_tps = round(network_tps / max(total_nodes, 1), 3) if network_tps > 0 else 0

        # Read config values
        speed_mult = 1.0
        try:
            from config import cfg as _cfg
            speed_mult = float(_cfg.SIMULATION_SPEED_MULTIPLIER)
        except Exception:
            _cfg = None

        # Derived metrics
        committed = cl.get('total_committed', 0)
        created = cl.get('total_transactions_created', 1)
        commit_rate = 100 * committed / max(created, 1)
        f1 = perf.get('f1_score', 0)
        precision = perf.get('precision', 0)
        recall = perf.get('recall', 0)
        fp = perf.get('false_positives', 0)
        fn = perf.get('false_negatives', 0)
        nodes_done = ns.get('nodes_done', 0)
        total_node_count = ns.get('total_nodes', total_nodes)
        msg_sent = bus.get('sent', 0)
        msg_delivered = bus.get('delivered', 0)
        msg_dropped = bus.get('dropped', 0)
        delivery_rate = 100 * msg_delivered / max(msg_sent, 1)

        lines = []

        # ================================================================
        # HEADER
        # ================================================================
        lines.append(f"# BGP-Sentry Experiment Report")
        lines.append(f"")
        lines.append(f"**Dataset:** `{ds.get('dataset_name', 'unknown')}` | "
                      f"**Date:** {summary.get('timestamp', 'N/A')[:19]} | "
                      f"**Duration:** {elapsed:.1f}s | "
                      f"**Speed:** {speed_mult}x")
        lines.append(f"")

        # ================================================================
        # EXECUTIVE SUMMARY (quick verdict)
        # ================================================================
        lines.append(f"## Executive Summary")
        lines.append(f"")
        # Build quick status indicators
        integrity_ok = integrity.get('valid', False)
        all_nodes_done = (nodes_done == total_node_count)
        zero_drops = (msg_dropped == 0)
        lines.append(f"| Metric | Result | Status |")
        lines.append(f"|--------|--------|--------|")
        lines.append(f"| Detection F1 Score | {f1:.4f} | {'PASS' if f1 >= 0.9 else 'REVIEW' if f1 >= 0.5 else 'LOW'} |")
        lines.append(f"| Precision | {precision:.4f} | {'PASS' if precision >= 0.9 else 'LOW -- false positives: ' + str(fp)} |")
        lines.append(f"| Recall | {recall:.4f} | {'PASS' if recall >= 0.9 else 'MISSED ' + str(fn) + ' attacks'} |")
        lines.append(f"| Network TPS (all nodes combined) | {network_tps} | {'GOOD' if network_tps >= 4.0 else 'SLOW'} |")
        lines.append(f"| Consensus Commit Rate | {commit_rate:.1f}% | {'GOOD' if commit_rate >= 80 else 'LOW -- increase timeout or reduce threshold'} |")
        lines.append(f"| Blockchain Integrity | {'Valid' if integrity_ok else 'INVALID'} | {'PASS' if integrity_ok else 'FAIL'} |")
        lines.append(f"| Message Delivery | {delivery_rate:.1f}% | {'PASS' if zero_drops else str(msg_dropped) + ' DROPPED'} |")
        lines.append(f"| Nodes Completed | {nodes_done}/{total_node_count} | {'PASS' if all_nodes_done else 'INCOMPLETE -- increase duration'} |")
        lines.append(f"")

        # ================================================================
        # CONFIGURATION USED (critical for reproducibility & tuning)
        # ================================================================
        lines.append(f"## Configuration Used")
        lines.append(f"")
        lines.append(f"These are the `.env` parameters that were active for this run. "
                      f"Change these in `.env` and re-run to tune results.")
        lines.append(f"")
        if _cfg is not None:
            lines.append(f"### Consensus & P2P")
            lines.append(f"")
            lines.append(f"| Parameter | Value | Description |")
            lines.append(f"|-----------|-------|-------------|")
            lines.append(f"| `CONSENSUS_MIN_SIGNATURES` | {_cfg.CONSENSUS_MIN_SIGNATURES} | Min votes to commit a block |")
            lines.append(f"| `CONSENSUS_CAP_SIGNATURES` | {_cfg.CONSENSUS_CAP_SIGNATURES} | Upper cap on required votes |")
            lines.append(f"| Effective Threshold | {cfg_data.get('consensus_threshold', 'N/A')} | max(MIN, min(N/3+1, CAP)) |")
            lines.append(f"| `P2P_REGULAR_TIMEOUT` | {_cfg.P2P_REGULAR_TIMEOUT}s | Timeout for regular consensus |")
            lines.append(f"| `P2P_ATTACK_TIMEOUT` | {_cfg.P2P_ATTACK_TIMEOUT}s | Timeout for attack consensus |")
            lines.append(f"| `P2P_MAX_BROADCAST_PEERS` | {_cfg.P2P_MAX_BROADCAST_PEERS} | Peers per vote broadcast |")
            lines.append(f"")
            lines.append(f"### Deduplication & Knowledge")
            lines.append(f"")
            lines.append(f"| Parameter | Value | Description |")
            lines.append(f"|-----------|-------|-------------|")
            lines.append(f"| `RPKI_DEDUP_WINDOW` | {_cfg.RPKI_DEDUP_WINDOW}s | RPKI skip window (attacks bypass) |")
            lines.append(f"| `NONRPKI_DEDUP_WINDOW` | {_cfg.NONRPKI_DEDUP_WINDOW}s | Non-RPKI skip window (attacks bypass) |")
            lines.append(f"| `KNOWLEDGE_WINDOW_SECONDS` | {_cfg.KNOWLEDGE_WINDOW_SECONDS}s | How long nodes remember observations |")
            lines.append(f"")
            lines.append(f"### Attack Detection")
            lines.append(f"")
            lines.append(f"| Parameter | Value | Description |")
            lines.append(f"|-----------|-------|-------------|")
            lines.append(f"| `FLAP_WINDOW_SECONDS` | {_cfg.FLAP_WINDOW_SECONDS}s | Sliding window for route flapping |")
            lines.append(f"| `FLAP_THRESHOLD` | {_cfg.FLAP_THRESHOLD} | State changes to trigger flapping alert |")
            lines.append(f"| `ATTACK_CONSENSUS_MIN_VOTES` | {_cfg.ATTACK_CONSENSUS_MIN_VOTES} | Min votes for attack verdict |")
            lines.append(f"")
            lines.append(f"### Simulation")
            lines.append(f"")
            lines.append(f"| Parameter | Value | Description |")
            lines.append(f"|-----------|-------|-------------|")
            lines.append(f"| `SIMULATION_SPEED_MULTIPLIER` | {_cfg.SIMULATION_SPEED_MULTIPLIER}x | 1.0 = real-time |")
            lines.append(f"| `INGESTION_BUFFER_MAX_SIZE` | {_cfg.INGESTION_BUFFER_MAX_SIZE} | Per-node buffer cap |")
            lines.append(f"")

        # ================================================================
        # DATASET
        # ================================================================
        lines.append(f"## Dataset")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total ASes | {total_nodes} |")
        lines.append(f"| RPKI Validators | {rpki_count} |")
        lines.append(f"| Non-RPKI Observers | {nonrpki_count} |")
        lines.append(f"| Total Observations | {ds.get('total_observations', 0):,} |")
        lines.append(f"| Attack Observations | {ds.get('attack_observations', 0):,} ({100*ds.get('attack_observations',0)/max(ds.get('total_observations',1),1):.1f}%) |")
        lines.append(f"| Legitimate Observations | {ds.get('legitimate_observations', 0):,} |")
        lines.append(f"")

        # ================================================================
        # THROUGHPUT
        # ================================================================
        lines.append(f"## Throughput")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Speed Multiplier | {speed_mult}x |")
        lines.append(f"| Wall-Clock Time | {elapsed:.1f}s |")
        lines.append(f"| Total Observations Processed | {total_processed:,} |")
        lines.append(f"| **Network TPS (all nodes combined)** | **{network_tps}** |")
        lines.append(f"| Per-Node TPS (network TPS / node count) | {per_node_tps} |")
        lines.append(f"| RPKI Validators (consensus participants) | {rpki_count} |")
        lines.append(f"")
        lines.append(f"> **Network TPS** = total observations processed / wall-clock seconds. "
                      f"Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.")
        lines.append(f"")

        # ================================================================
        # NODE PROCESSING
        # ================================================================
        lines.append(f"## Node Processing")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Nodes Completed | {nodes_done} / {total_node_count} |")
        lines.append(f"| Total Observations Processed | {ns.get('total_observations_processed', 0):,} |")
        lines.append(f"| Attacks Detected | {ns.get('attacks_detected', 0):,} |")
        lines.append(f"| Legitimate Processed | {ns.get('legitimate_processed', 0):,} |")
        lines.append(f"")
        if not all_nodes_done:
            lines.append(f"> **WARNING:** {total_node_count - nodes_done} nodes did not finish. "
                          f"Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.")
            lines.append(f"")

        # ================================================================
        # DETECTION PERFORMANCE
        # ================================================================
        lines.append(f"## Detection Performance (vs Ground Truth)")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Ground Truth Attacks (unique) | {perf.get('ground_truth_attacks', 0)} |")
        lines.append(f"| Total Detections (unique) | {perf.get('total_detections', 0)} |")
        lines.append(f"| True Positives | {perf.get('true_positives', 0)} |")
        lines.append(f"| False Positives | {fp} |")
        lines.append(f"| False Negatives | {fn} |")
        lines.append(f"| **Precision** | **{precision:.4f}** |")
        lines.append(f"| **Recall** | **{recall:.4f}** |")
        lines.append(f"| **F1 Score** | **{f1:.4f}** |")
        lines.append(f"")
        if fp > 0:
            lines.append(f"> **{fp} false positives detected.** Most are from route flapping. "
                          f"To reduce: increase `FLAP_THRESHOLD` (currently {_cfg.FLAP_THRESHOLD if _cfg else '?'}) "
                          f"or increase `FLAP_WINDOW_SECONDS`.")
            lines.append(f"")
        if fn > 0:
            lines.append(f"> **{fn} attacks missed (false negatives).** Check if nodes had enough "
                          f"time to process all observations. Try increasing `--duration`.")
            lines.append(f"")

        # ================================================================
        # BLOCKCHAIN
        # ================================================================
        lines.append(f"## Blockchain")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Blocks | {bc_info.get('total_blocks', 0):,} |")
        lines.append(f"| Total Transactions | {bc_info.get('total_transactions', 0):,} |")
        latest = bc_info.get("latest_block", {})
        lines.append(f"| Latest Block # | {latest.get('block_number', 'N/A')} |")
        lines.append(f"| Integrity Valid | {'Yes' if integrity_ok else 'No'} |")
        if not integrity_ok:
            errors = integrity.get("errors", [])
            lines.append(f"| Integrity Errors | {'; '.join(errors[:3])} |")
        replicas = bc.get("node_replicas", {})
        if replicas:
            lines.append(f"| Node Replicas | {replicas.get('total_nodes', 0)} |")
            lines.append(f"| All Replicas Valid | {'Yes' if replicas.get('all_valid') else 'No'} |")
            lines.append(f"| Valid Replicas | {replicas.get('valid_count', 0)}/{replicas.get('total_nodes', 0)} |")
        lines.append(f"")

        # ── Cryptographic Signing ──
        crypto = crypto_summary or {}
        if crypto:
            lines.append(f"## Cryptographic Signing")
            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Key Algorithm | {crypto.get('key_algorithm', 'N/A')} |")
            lines.append(f"| Signature Scheme | {crypto.get('signature_scheme', 'N/A')} |")
            lines.append(f"| Total Key Pairs | {crypto.get('total_key_pairs', 0)} |")
            lines.append(f"")

        # ================================================================
        # CONSENSUS
        # ================================================================
        lines.append(f"## Consensus (Proof of Population)")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Consensus Threshold | {cfg_data.get('consensus_threshold', 'N/A')} signatures |")
        lines.append(f"| Transactions Created | {cl.get('total_transactions_created', 0):,} |")
        lines.append(f"| Committed (consensus reached) | {committed:,} |")
        lines.append(f"| Pending (timed out / not enough votes) | {cl.get('total_pending', 0):,} |")
        lines.append(f"| **Commit Rate** | **{commit_rate:.1f}%** |")
        lines.append(f"")
        if commit_rate < 50:
            lines.append(f"> **Low commit rate ({commit_rate:.1f}%).** Consider: "
                          f"increase `P2P_REGULAR_TIMEOUT` (currently {_cfg.P2P_REGULAR_TIMEOUT if _cfg else '?'}s), "
                          f"increase `P2P_MAX_BROADCAST_PEERS` (currently {_cfg.P2P_MAX_BROADCAST_PEERS if _cfg else '?'}), "
                          f"or lower `CONSENSUS_CAP_SIGNATURES` (currently {_cfg.CONSENSUS_CAP_SIGNATURES if _cfg else '?'}).")
            lines.append(f"")

        # ================================================================
        # BGPCOIN ECONOMY
        # ================================================================
        lines.append(f"## BGPCoin Economy")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Supply | {eco.get('total_supply', 0):,} |")
        lines.append(f"| Treasury Balance | {eco.get('treasury_balance', 0):,.0f} |")
        lines.append(f"| Total Distributed | {eco.get('total_distributed', 0):,.0f} |")
        lines.append(f"| Circulating Supply | {eco.get('circulating_supply', 0):,.0f} |")
        lines.append(f"| Participating Nodes | {eco.get('nodes_count', 0)} |")
        distributed = eco.get('total_distributed', 0)
        supply = eco.get('total_supply', 10_000_000)
        lines.append(f"| Distribution Rate | {100*distributed/max(supply,1):.2f}% of supply |")
        lines.append(f"")

        # ================================================================
        # NON-RPKI TRUST RATINGS
        # ================================================================
        lines.append(f"## Non-RPKI Trust Ratings")
        lines.append(f"")
        if rating_dist:
            cat_labels = [
                ("highly_trusted", "Highly Trusted (90-100)"),
                ("trusted", "Trusted (70-89)"),
                ("neutral", "Neutral (50-69)"),
                ("suspicious", "Suspicious (30-49)"),
                ("malicious", "Malicious (0-29)"),
            ]
            lines.append(f"| Category | Count |")
            lines.append(f"|----------|-------|")
            for key, label in cat_labels:
                count = rating_dist.get(key, 0)
                if count > 0:
                    lines.append(f"| {label} | {count} |")
            lines.append(f"")
        avg = ratings_summary.get('average_score', 'N/A')
        avg_str = f"{avg:.2f}" if isinstance(avg, (int, float)) else str(avg)
        low = ratings_summary.get('lowest_score', ratings_summary.get('min_score', 'N/A'))
        high = ratings_summary.get('highest_score', ratings_summary.get('max_score', 'N/A'))
        lines.append(f"| Stat | Value |")
        lines.append(f"|------|-------|")
        lines.append(f"| Total Rated ASes | {ratings_summary.get('total_ases', ratings_summary.get('total_rated', len(all_ratings)))} |")
        lines.append(f"| Average Score | {avg_str} |")
        lines.append(f"| Lowest Score | {low} |")
        lines.append(f"| Highest Score | {high} |")
        lines.append(f"")

        # ================================================================
        # ATTACK VERDICTS
        # ================================================================
        lines.append(f"## Attack Verdicts")
        lines.append(f"")
        if verdict_types:
            lines.append(f"| Attack Type | Count |")
            lines.append(f"|-------------|-------|")
            for atype, count in sorted(verdict_types.items()):
                lines.append(f"| {atype} | {count} |")
            lines.append(f"")
        else:
            lines.append(f"No attack verdicts recorded in this run.")
            lines.append(f"")

        # ================================================================
        # DEDUPLICATION
        # ================================================================
        rpki_deduped = dd.get('rpki_deduped', 0)
        nonrpki_throttled = dd.get('nonrpki_throttled', 0)
        total_skipped = dd.get('total_skipped', 0)
        total_obs = ds.get('total_observations', 1)
        lines.append(f"## Deduplication")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| RPKI Deduped | {rpki_deduped:,} |")
        lines.append(f"| Non-RPKI Throttled | {nonrpki_throttled:,} |")
        lines.append(f"| Total Skipped | {total_skipped:,} ({100*total_skipped/max(total_obs,1):.1f}% of observations) |")
        lines.append(f"")

        # ================================================================
        # P2P MESSAGE BUS
        # ================================================================
        lines.append(f"## P2P Message Bus")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Messages Sent | {msg_sent:,} |")
        lines.append(f"| Messages Delivered | {msg_delivered:,} |")
        lines.append(f"| Messages Dropped | {msg_dropped:,} |")
        lines.append(f"| Delivery Rate | {delivery_rate:.2f}% |")
        lines.append(f"")

        # ================================================================
        # SYSTEM INFO
        # ================================================================
        if sysinfo:
            lines.append(f"## System Info")
            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| CPU | {sysinfo.get('cpu_model', sysinfo.get('processor', 'N/A'))} |")
            lines.append(f"| Cores | {sysinfo.get('cpu_count', 'N/A')} |")
            lines.append(f"| RAM | {sysinfo.get('memory_total_gb', 'N/A')} GB |")
            lines.append(f"| Platform | {sysinfo.get('platform', 'N/A')} |")
            lines.append(f"| Python | {sysinfo.get('python_version', 'N/A')} |")
            lines.append(f"")

        # ================================================================
        # TUNING RECOMMENDATIONS
        # ================================================================
        lines.append(f"## Tuning Recommendations")
        lines.append(f"")
        recommendations = []
        if fp > 5:
            recommendations.append(
                f"- **Reduce false positives ({fp})**: Increase `FLAP_THRESHOLD` "
                f"(currently {_cfg.FLAP_THRESHOLD if _cfg else '?'}). "
                f"Try 8 or 10 to reduce route flapping false alarms.")
        if fn > 0:
            recommendations.append(
                f"- **Missed {fn} attacks**: Ensure `--duration` is long enough for all "
                f"nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` "
                f"(currently {_cfg.KNOWLEDGE_WINDOW_SECONDS if _cfg else '?'}s).")
        if commit_rate < 80:
            recommendations.append(
                f"- **Low commit rate ({commit_rate:.1f}%)**: Increase `P2P_REGULAR_TIMEOUT` "
                f"(currently {_cfg.P2P_REGULAR_TIMEOUT if _cfg else '?'}s) to give voters more "
                f"time, or increase `P2P_MAX_BROADCAST_PEERS` "
                f"(currently {_cfg.P2P_MAX_BROADCAST_PEERS if _cfg else '?'}) to query more voters.")
        if not all_nodes_done:
            recommendations.append(
                f"- **{total_node_count - nodes_done} nodes incomplete**: Increase "
                f"`--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` "
                f"(currently {speed_mult}x).")
        if network_tps < 4.0 and speed_mult >= 1.0:
            recommendations.append(
                f"- **Low TPS ({network_tps})**: System may be overloaded. "
                f"Reduce `SIMULATION_SPEED_MULTIPLIER` or check CPU load.")
        if not integrity_ok:
            recommendations.append(
                f"- **Blockchain integrity FAILED**: This is a critical error. "
                f"Check `blockchain_stats.json` for details.")
        if msg_dropped > 0:
            recommendations.append(
                f"- **{msg_dropped} messages dropped**: P2P bus may be overloaded. "
                f"Reduce speed or check thread pool size.")
        if not recommendations:
            recommendations.append(
                f"- All metrics look good. No changes needed for this configuration.")
            if speed_mult < 10:
                recommendations.append(
                    f"- **Try increasing speed**: Set `SIMULATION_SPEED_MULTIPLIER={speed_mult + 1.0}` "
                    f"to test higher throughput.")
        for r in recommendations:
            lines.append(r)
        lines.append(f"")

        # ================================================================
        # OUTPUT FILES REFERENCE
        # ================================================================
        lines.append(f"## Output Files in This Folder")
        lines.append(f"")
        lines.append(f"| File | What to Look For |")
        lines.append(f"|------|-----------------|")
        lines.append(f"| `README.md` | This report -- start here |")
        lines.append(f"| `summary.json` | Overall run summary (dataset, nodes, timing) |")
        lines.append(f"| `performance_metrics.json` | Precision, recall, F1 -- compare across runs |")
        lines.append(f"| `detection_results.json` | Every detection decision by every node |")
        lines.append(f"| `blockchain_stats.json` | Block count, integrity check, per-node replicas |")
        lines.append(f"| `consensus_log.json` | Committed vs pending -- shows consensus health |")
        lines.append(f"| `attack_verdicts.json` | Which attacks were confirmed/rejected by vote |")
        lines.append(f"| `bgpcoin_economy.json` | Token distribution -- who earned what |")
        lines.append(f"| `nonrpki_ratings.json` | Per-AS trust scores -- identify bad actors |")
        lines.append(f"| `dedup_stats.json` | How many observations were skipped (efficiency) |")
        lines.append(f"| `message_bus_stats.json` | P2P health -- any dropped messages? |")
        lines.append(f"| `run_config.json` | Full config + hardware info for reproducibility |")
        lines.append(f"| `crypto_summary.json` | Key algorithm and signature scheme used |")
        lines.append(f"")

        lines.append(f"---")
        lines.append(f"*Generated by BGP-Sentry main_experiment.py*")

        readme_path = self.results_dir / "README.md"
        try:
            with open(readme_path, "w") as f:
                f.write("\n".join(lines))
        except Exception as e:
            logger.error(f"Failed to write README.md: {e}")

    def _compute_performance_metrics(self):
        """Compare detections against ground truth to compute precision/recall/F1."""
        gt_attacks = self.data_loader.get_ground_truth_attacks()
        detections = self.node_manager.get_all_attack_detections()

        # Build ground truth set: (prefix, origin_asn, label)
        gt_set = set()
        for atk in gt_attacks:
            key = (atk.get("prefix"), atk.get("origin_asn"), atk.get("label"))
            gt_set.add(key)

        # Build detection set
        detected_set = set()
        for det in detections:
            key = (det.get("prefix"), det.get("origin_asn"), det.get("detection_type"))
            detected_set.add(key)

        # Compute metrics
        true_positives = len(gt_set & detected_set)
        false_positives = len(detected_set - gt_set)
        false_negatives = len(gt_set - detected_set)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "ground_truth_attacks": len(gt_set),
            "total_detections": len(detected_set),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }


def main():
    parser = argparse.ArgumentParser(
        description='BGP-Sentry Distributed Blockchain Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main_experiment.py --dataset caida_100
  python3 main_experiment.py --dataset caida_100 --duration 300
  python3 main_experiment.py --dataset caida_1000 --duration 600
        """
    )
    parser.add_argument(
        '--dataset', required=True,
        help='Dataset name (caida_100, caida_200, caida_500, caida_1000) or path'
    )
    parser.add_argument(
        '--duration', type=int, default=300,
        help='Maximum duration in seconds (default: 300)'
    )
    parser.add_argument(
        '--clean', action='store_true', default=True,
        help='Reset blockchain state before experiment (default: True)'
    )
    parser.add_argument(
        '--no-clean', action='store_false', dest='clean',
        help='Keep existing blockchain state from previous runs'
    )

    args = parser.parse_args()

    # Resolve dataset
    try:
        dataset_path = resolve_dataset_path(args.dataset)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # Run experiment
    experiment = BGPSentryExperiment(
        dataset_path=dataset_path,
        duration=args.duration,
        clean=args.clean,
    )

    success = experiment.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
