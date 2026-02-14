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

            # Step 4: Collect and write results
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

        # 14. Save RSA keys to disk (per-node folders + public key registry)
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
        """Generate a markdown README summarising this experiment run."""
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
            # Fallback: count from individual ratings
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

        lines = []
        lines.append(f"# BGP-Sentry Experiment Results")
        lines.append(f"")
        lines.append(f"**Dataset:** `{ds.get('dataset_name', 'unknown')}` | "
                      f"**Date:** {summary.get('timestamp', 'N/A')[:19]} | "
                      f"**Duration:** {elapsed:.1f}s")
        lines.append(f"")

        # ── Dataset ──
        lines.append(f"## Dataset")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total ASes | {ds.get('total_ases', 0)} |")
        lines.append(f"| RPKI Validators | {ds.get('rpki_count', 0)} |")
        lines.append(f"| Non-RPKI Observers | {ds.get('non_rpki_count', 0)} |")
        lines.append(f"| Total Observations | {ds.get('total_observations', 0):,} |")
        lines.append(f"| Attack Observations | {ds.get('attack_observations', 0):,} ({100*ds.get('attack_observations',0)/max(ds.get('total_observations',1),1):.1f}%) |")
        lines.append(f"| Legitimate Observations | {ds.get('legitimate_observations', 0):,} |")
        lines.append(f"")

        # ── Node Processing ──
        lines.append(f"## Node Processing")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Nodes Completed (within time limit) | {ns.get('nodes_done', 0)} / {ns.get('total_nodes', 0)} |")
        lines.append(f"| Total Observations Processed | {ns.get('total_observations_processed', 0):,} |")
        lines.append(f"| Attacks Detected | {ns.get('attacks_detected', 0):,} |")
        lines.append(f"| Legitimate Processed | {ns.get('legitimate_processed', 0):,} |")
        lines.append(f"")

        # ── Detection Performance ──
        lines.append(f"## Detection Performance (vs Ground Truth)")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Ground Truth Attacks (unique) | {perf.get('ground_truth_attacks', 0)} |")
        lines.append(f"| Total Detections (unique) | {perf.get('total_detections', 0)} |")
        lines.append(f"| True Positives | {perf.get('true_positives', 0)} |")
        lines.append(f"| False Positives | {perf.get('false_positives', 0)} |")
        lines.append(f"| False Negatives | {perf.get('false_negatives', 0)} |")
        lines.append(f"| **Precision** | **{perf.get('precision', 0):.4f}** |")
        lines.append(f"| **Recall** | **{perf.get('recall', 0):.4f}** |")
        lines.append(f"| **F1 Score** | **{perf.get('f1_score', 0):.4f}** |")
        lines.append(f"")

        # ── Blockchain ──
        lines.append(f"## Blockchain")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Blocks | {bc_info.get('total_blocks', 0):,} |")
        lines.append(f"| Total Transactions | {bc_info.get('total_transactions', 0):,} |")
        latest = bc_info.get("latest_block", {})
        lines.append(f"| Latest Block # | {latest.get('block_number', 'N/A')} |")
        lines.append(f"| Integrity Valid | {'Yes' if integrity.get('valid') else 'No'} |")
        if not integrity.get("valid"):
            errors = integrity.get("errors", [])
            lines.append(f"| Integrity Errors | {'; '.join(errors[:3])} |")

        # Per-node blockchain replicas
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

        # ── Consensus ──
        lines.append(f"## Consensus")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Consensus Threshold | {cfg_data.get('consensus_threshold', 'N/A')} signatures |")
        lines.append(f"| Transactions Created | {cl.get('total_transactions_created', 0):,} |")
        lines.append(f"| Committed (consensus reached) | {cl.get('total_committed', 0):,} |")
        lines.append(f"| Pending (timed out / not enough votes) | {cl.get('total_pending', 0):,} |")
        committed = cl.get('total_committed', 0)
        created = cl.get('total_transactions_created', 1)
        lines.append(f"| **Commit Rate** | **{100*committed/max(created,1):.1f}%** |")
        lines.append(f"")

        # ── BGPCoin Economy ──
        lines.append(f"## BGPCoin Economy")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Supply | {eco.get('total_supply', 0):,} |")
        lines.append(f"| Treasury Balance | {eco.get('treasury_balance', 0):,.0f} |")
        lines.append(f"| Total Distributed | {eco.get('total_distributed', 0):,.0f} |")
        lines.append(f"| Circulating Supply | {eco.get('circulating_supply', 0):,.0f} |")
        lines.append(f"| Participating Nodes | {eco.get('nodes_count', 0)} |")
        lines.append(f"")

        # ── Non-RPKI Ratings ──
        lines.append(f"## Non-RPKI Trust Ratings")
        lines.append(f"")
        if rating_dist:
            cat_labels = [
                ("highly_trusted", "Highly Trusted"),
                ("trusted", "Trusted"),
                ("neutral", "Neutral"),
                ("suspicious", "Suspicious"),
                ("malicious", "Malicious"),
            ]
            lines.append(f"| Category | Count |")
            lines.append(f"|----------|-------|")
            for key, label in cat_labels:
                count = rating_dist.get(key, 0)
                if count > 0:
                    lines.append(f"| {label} | {count} |")
            lines.append(f"")

        lines.append(f"| Stat | Value |")
        lines.append(f"|------|-------|")
        avg = ratings_summary.get('average_score', 'N/A')
        avg_str = f"{avg:.2f}" if isinstance(avg, (int, float)) else str(avg)
        low = ratings_summary.get('lowest_score', ratings_summary.get('min_score', 'N/A'))
        high = ratings_summary.get('highest_score', ratings_summary.get('max_score', 'N/A'))
        lines.append(f"| Total Rated ASes | {ratings_summary.get('total_ases', ratings_summary.get('total_rated', len(all_ratings)))} |")
        lines.append(f"| Average Score | {avg_str} |")
        lines.append(f"| Lowest Score | {low} |")
        lines.append(f"| Highest Score | {high} |")
        lines.append(f"")

        # ── Attack Verdicts ──
        lines.append(f"## Attack Verdicts")
        lines.append(f"")
        if verdict_types:
            lines.append(f"| Attack Type | Count |")
            lines.append(f"|-------------|-------|")
            for atype, count in sorted(verdict_types.items()):
                lines.append(f"| {atype} | {count} |")
            lines.append(f"")

        # ── Deduplication ──
        lines.append(f"## Deduplication")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| RPKI Deduped | {dd.get('rpki_deduped', 0):,} |")
        lines.append(f"| Non-RPKI Throttled | {dd.get('nonrpki_throttled', 0):,} |")
        lines.append(f"| Total Skipped | {dd.get('total_skipped', 0):,} |")
        lines.append(f"")

        # ── P2P Message Bus ──
        lines.append(f"## P2P Message Bus")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Messages Sent | {bus.get('sent', 0):,} |")
        lines.append(f"| Messages Delivered | {bus.get('delivered', 0):,} |")
        lines.append(f"| Messages Dropped | {bus.get('dropped', 0):,} |")
        lines.append(f"")

        # ── System Info ──
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
