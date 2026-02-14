#!/usr/bin/env python3
"""
PosthocAnalyzer - Post-experiment analysis of BGP-Sentry results.

Usage:
    python3 analysis/posthoc_analysis.py results/caida_100/20260213_120000/

Produces:
  - Longitudinal non-RPKI behavior analysis
  - Attack detection accuracy by type
  - Consensus voting efficiency
  - BGPCoin distribution analysis
  - Blockchain growth analysis
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional


class PosthocAnalyzer:
    """Load and analyze results from a completed BGP-Sentry experiment."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        # Load all result files
        self.detection_results = self._load("detection_results.json", [])
        self.trust_scores = self._load("trust_scores.json", {})
        self.performance = self._load("performance_metrics.json", {})
        self.summary = self._load("summary.json", {})
        self.run_config = self._load("run_config.json", {})
        self.blockchain_stats = self._load("blockchain_stats.json", {})
        self.bgpcoin_economy = self._load("bgpcoin_economy.json", {})
        self.nonrpki_ratings = self._load("nonrpki_ratings.json", {})
        self.consensus_log = self._load("consensus_log.json", {})
        self.attack_verdicts = self._load("attack_verdicts.json", [])
        self.dedup_stats = self._load("dedup_stats.json", {})

    def _load(self, filename: str, default):
        """Load a JSON file from the results directory."""
        path = self.results_dir / filename
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def longitudinal_nonrpki_behavior(self) -> Dict:
        """Track how non-RPKI AS ratings changed over time."""
        ratings = self.nonrpki_ratings.get("ratings", {})
        result = {
            "total_nonrpki_ases": len(ratings),
            "per_as": {},
        }

        for as_str, rating_info in ratings.items():
            history = rating_info.get("history", [])
            result["per_as"][as_str] = {
                "final_score": rating_info.get("trust_score", 50),
                "initial_score": rating_info.get("initial_score", 50),
                "attacks_detected": rating_info.get("attacks_detected", 0),
                "legitimate_announcements": rating_info.get("legitimate_announcements", 0),
                "rating_level": rating_info.get("rating_level", "neutral"),
                "history_length": len(history),
                "score_delta": rating_info.get("trust_score", 50) - rating_info.get("initial_score", 50),
            }

        # Aggregate statistics
        if ratings:
            scores = [r.get("trust_score", 50) for r in ratings.values()]
            result["aggregate"] = {
                "min_score": min(scores),
                "max_score": max(scores),
                "avg_score": sum(scores) / len(scores),
                "median_score": sorted(scores)[len(scores) // 2],
                "ases_with_attacks": sum(1 for r in ratings.values() if r.get("attacks_detected", 0) > 0),
                "ases_degraded": sum(1 for r in ratings.values() if r.get("trust_score", 50) < 50),
            }

        return result

    def attack_detection_accuracy(self) -> Dict:
        """Compare detected attacks vs ground truth per attack type."""
        # Group detections by type
        detected_by_type = defaultdict(set)
        ground_truth_by_type = defaultdict(set)

        for det in self.detection_results:
            if det.get("detected"):
                dtype = det.get("detection_type", "UNKNOWN")
                key = (det.get("prefix"), det.get("origin_asn"))
                detected_by_type[dtype].add(key)

            if det.get("is_attack"):
                label = det.get("label", "UNKNOWN")
                key = (det.get("prefix"), det.get("origin_asn"))
                ground_truth_by_type[label].add(key)

        # Per-type accuracy
        all_types = set(detected_by_type.keys()) | set(ground_truth_by_type.keys())
        per_type = {}

        for attack_type in all_types:
            gt = ground_truth_by_type.get(attack_type, set())
            det = detected_by_type.get(attack_type, set())
            tp = len(gt & det)
            fp = len(det - gt)
            fn = len(gt - det)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            per_type[attack_type] = {
                "ground_truth_count": len(gt),
                "detected_count": len(det),
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
            }

        return {
            "overall": self.performance,
            "per_attack_type": per_type,
        }

    def consensus_efficiency(self) -> Dict:
        """Analyze consensus voting patterns."""
        verdicts = self.attack_verdicts if isinstance(self.attack_verdicts, list) else []

        if not verdicts:
            return {
                "total_proposals": 0,
                "consensus_log": self.consensus_log,
            }

        total_votes = sum(v.get("total_votes", 0) for v in verdicts)
        avg_votes = total_votes / len(verdicts) if verdicts else 0

        status_counts = Counter(v.get("status", "unknown") for v in verdicts)
        verdict_counts = Counter(v.get("verdict", "unknown") for v in verdicts)

        return {
            "total_proposals": len(verdicts),
            "avg_votes_per_proposal": round(avg_votes, 2),
            "status_distribution": dict(status_counts),
            "verdict_distribution": dict(verdict_counts),
            "consensus_log": self.consensus_log,
        }

    def bgpcoin_distribution(self) -> Dict:
        """Analyze token economy health."""
        economy = self.bgpcoin_economy
        if not economy:
            return {"status": "no_data"}

        total_distributed = economy.get("total_distributed", 0)
        total_supply = economy.get("total_supply", 10_000_000)
        treasury = economy.get("treasury_balance", total_supply)
        circulating = economy.get("circulating_supply", 0)

        return {
            "total_supply": total_supply,
            "treasury_balance": treasury,
            "total_distributed": total_distributed,
            "total_burned": economy.get("total_burned", 0),
            "total_recycled": economy.get("total_recycled", 0),
            "circulating_supply": circulating,
            "distribution_rate": round(total_distributed / total_supply * 100, 4) if total_supply > 0 else 0,
            "treasury_remaining_pct": round(treasury / total_supply * 100, 2) if total_supply > 0 else 0,
        }

    def blockchain_growth(self) -> Dict:
        """Analyze blockchain growth rate and transaction composition."""
        bc = self.blockchain_stats
        if not bc:
            return {"status": "no_data"}

        info = bc.get("blockchain_info", {})
        integrity = bc.get("integrity", {})

        total_blocks = info.get("total_blocks", 0)
        total_txns = info.get("total_transactions", 0)
        elapsed = self.summary.get("elapsed_seconds", 1)

        # Count attack vs legitimate in detection results
        attack_count = sum(1 for d in self.detection_results if d.get("is_attack"))
        legit_count = sum(1 for d in self.detection_results if not d.get("is_attack"))

        return {
            "total_blocks": total_blocks,
            "total_transactions": total_txns,
            "blocks_per_second": round(total_blocks / elapsed, 4) if elapsed > 0 else 0,
            "transactions_per_block": round(total_txns / max(total_blocks, 1), 2),
            "attack_observations": attack_count,
            "legitimate_observations": legit_count,
            "attack_ratio": round(attack_count / max(attack_count + legit_count, 1), 4),
            "integrity_check": integrity,
            "dedup_stats": self.dedup_stats,
        }

    def full_report(self) -> Dict:
        """Generate complete post-hoc analysis report."""
        return {
            "experiment_info": {
                "dataset": self.run_config.get("dataset_name"),
                "duration": self.run_config.get("actual_duration"),
                "total_nodes": self.run_config.get("total_nodes"),
                "rpki_nodes": self.run_config.get("rpki_node_count"),
                "non_rpki_nodes": self.run_config.get("non_rpki_node_count"),
            },
            "longitudinal_nonrpki": self.longitudinal_nonrpki_behavior(),
            "attack_accuracy": self.attack_detection_accuracy(),
            "consensus_efficiency": self.consensus_efficiency(),
            "bgpcoin_distribution": self.bgpcoin_distribution(),
            "blockchain_growth": self.blockchain_growth(),
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analysis/posthoc_analysis.py <results_dir>")
        print("Example: python3 analysis/posthoc_analysis.py results/caida_100/20260213_120000/")
        return 1

    results_dir = sys.argv[1]
    analyzer = PosthocAnalyzer(results_dir)
    report = analyzer.full_report()

    # Write report
    output_path = Path(results_dir) / "posthoc_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Post-hoc analysis report written to: {output_path}")

    # Print summary
    perf = report.get("attack_accuracy", {}).get("overall", {})
    print(f"\nPerformance: P={perf.get('precision', 0):.4f} R={perf.get('recall', 0):.4f} F1={perf.get('f1_score', 0):.4f}")

    bc = report.get("blockchain_growth", {})
    print(f"Blockchain: {bc.get('total_blocks', 0)} blocks, {bc.get('total_transactions', 0)} transactions")

    coin = report.get("bgpcoin_distribution", {})
    print(f"BGPCoin: {coin.get('total_distributed', 0)} distributed, {coin.get('treasury_remaining_pct', 100)}% treasury remaining")

    nonrpki = report.get("longitudinal_nonrpki", {}).get("aggregate", {})
    print(f"Non-RPKI ratings: avg={nonrpki.get('avg_score', 0):.1f}, degraded={nonrpki.get('ases_degraded', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
