#!/usr/bin/env python3
"""
PosthocBlockchainDetector — Cross-chain longitudinal analysis for attack detection.

Reads raw blockchain data dumped after simulation and performs analyses that
exploit the multi-observer blockchain architecture to find attacks that the
five real-time detectors missed.

Key insight: real-time detectors run per-observation with static databases.
They cannot see that three different RPKI validators independently recorded
the same suspicious (prefix, origin_asn) as SINGLE_WITNESS. This module can.

Usage:
    python3 analysis/posthoc_blockchain_detection.py results/caida_100/20260410_101937/
"""

import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class PosthocBlockchainDetector:
    """Cross-chain longitudinal analysis of blockchain data for attack detection."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.bc_dir = self.results_dir / "blockchain_data"

        if not self.bc_dir.exists():
            raise FileNotFoundError(
                f"No blockchain_data/ directory in {results_dir}. "
                f"Re-run the experiment to generate blockchain dumps."
            )

        # Raw data
        self.chain_transactions: Dict[int, List[dict]] = {}
        self.unique_transactions: Dict[str, dict] = {}

        # Indices
        self.prefix_origin_index: Dict[Tuple[str, int], List[dict]] = defaultdict(list)
        self.observer_index: Dict[int, List[dict]] = defaultdict(list)
        self.chain_presence: Dict[str, Set[int]] = defaultdict(set)

        # Ground truth
        self.ground_truth: Dict[Tuple[str, int], dict] = {}
        self.all_attacks: Set[Tuple[str, int]] = set()
        self.realtime_detected: Set[Tuple[str, int]] = set()

        # Load
        self._load_all_chains()
        self._build_indices()
        self._load_ground_truth()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_all_chains(self):
        """Load all per-node blockchain.json files and extract transactions."""
        total_tx = 0
        for chain_file in sorted(self.bc_dir.glob("AS*/blockchain.json")):
            try:
                with open(chain_file) as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load {chain_file}: {e}")
                continue

            asn = data.get("asn")
            if asn is None:
                # Parse from directory name
                asn = int(chain_file.parent.name.replace("AS", ""))

            chain_txs = []
            for block in data.get("blocks", []):
                block_type = block.get("metadata", {}).get("block_type", "")
                if block_type == "genesis":
                    continue

                for tx in block.get("transactions", []):
                    tx_id = tx.get("transaction_id")
                    if not tx_id:
                        continue

                    # Track which chain has this tx
                    self.chain_presence[tx_id].add(asn)
                    chain_txs.append(tx)
                    total_tx += 1

                    # Store canonical copy (first seen)
                    if tx_id not in self.unique_transactions:
                        self.unique_transactions[tx_id] = tx

            self.chain_transactions[asn] = chain_txs

        logger.info(
            f"Loaded {len(self.chain_transactions)} chains, "
            f"{len(self.unique_transactions)} unique transactions, "
            f"{total_tx} total (across chains)"
        )

    def _build_indices(self):
        """Build lookup indices from unique transactions."""
        for tx in self.unique_transactions.values():
            prefix = tx.get("ip_prefix")
            origin = tx.get("sender_asn")
            observer = tx.get("observer_as")

            if prefix and origin is not None:
                self.prefix_origin_index[(prefix, origin)].append(tx)

            if observer is not None:
                self.observer_index[observer].append(tx)

    def _load_ground_truth(self):
        """Load ground truth from detection_results.json."""
        det_path = self.results_dir / "detection_results.json"
        if not det_path.exists():
            logger.warning("detection_results.json not found, ground truth unavailable")
            return

        try:
            with open(det_path) as f:
                results = json.load(f)
        except Exception:
            return

        for det in results:
            prefix = det.get("prefix")
            origin = det.get("origin_asn")
            if not prefix or origin is None:
                continue

            key = (prefix, origin)
            is_attack = det.get("is_attack", False)
            label = det.get("label", "UNKNOWN")

            if key not in self.ground_truth:
                self.ground_truth[key] = {
                    "is_attack": is_attack,
                    "label": label,
                }

            if is_attack:
                self.all_attacks.add(key)

            if det.get("detected", False):
                self.realtime_detected.add(key)

    # ------------------------------------------------------------------
    # Analysis 1: SINGLE_WITNESS Accumulation
    # ------------------------------------------------------------------

    def single_witness_accumulation(self, threshold: int = 3) -> Dict:
        """Find (prefix, origin) pairs with SINGLE_WITNESS on multiple independent chains."""
        upgraded = []
        partial_count = 0
        isolated_count = 0

        for (prefix, origin), txs in self.prefix_origin_index.items():
            # Get SINGLE_WITNESS transactions with distinct observers
            sw_observers = set()
            for tx in txs:
                if tx.get("consensus_status") == "SINGLE_WITNESS":
                    obs = tx.get("observer_as")
                    if obs is not None:
                        sw_observers.add(obs)

            if not sw_observers:
                continue

            gt = self.ground_truth.get((prefix, origin), {})
            is_attack = gt.get("is_attack", False)
            label = gt.get("label", "UNKNOWN")
            rt_detected = (prefix, origin) in self.realtime_detected

            if len(sw_observers) >= threshold:
                upgraded.append({
                    "prefix": prefix,
                    "origin_asn": origin,
                    "independent_observers": len(sw_observers),
                    "observer_list": sorted(sw_observers),
                    "is_attack": is_attack,
                    "label": label,
                    "realtime_detected": rt_detected,
                })
            elif len(sw_observers) > 1:
                partial_count += 1
            else:
                isolated_count += 1

        new_detections = [u for u in upgraded if u["is_attack"] and not u["realtime_detected"]]
        new_fp = [u for u in upgraded if not u["is_attack"]]

        missed_by_realtime = self.all_attacks - self.realtime_detected
        recall_gain = len(new_detections) / max(len(missed_by_realtime), 1)

        return {
            "description": (
                f"SINGLE_WITNESS entries from {threshold}+ independent observers "
                f"for the same (prefix, origin) — accumulated credibility"
            ),
            "threshold": threshold,
            "upgraded_count": len(upgraded),
            "partial_count": partial_count,
            "isolated_count": isolated_count,
            "upgraded_pairs": upgraded[:100],  # Cap output size
            "new_detections": len(new_detections),
            "new_false_positives": len(new_fp),
            "accumulation_precision": len(new_detections) / max(len(upgraded), 1),
            "accumulation_recall_gain": recall_gain,
        }

    # ------------------------------------------------------------------
    # Analysis 2: Cross-Chain Corroboration
    # ------------------------------------------------------------------

    def cross_chain_corroboration(self) -> Dict:
        """Analyze how announcements are corroborated across independent chains."""
        corroboration_hist = Counter()
        disagreements = []
        widely_corroborated = []

        for (prefix, origin), txs in self.prefix_origin_index.items():
            # Count distinct chains that recorded this pair
            chains = set()
            for tx in txs:
                tx_id = tx.get("transaction_id")
                if tx_id:
                    chains.update(self.chain_presence.get(tx_id, set()))

            chain_count = len(chains)
            corroboration_hist[chain_count] += 1

            # Consensus status distribution
            status_dist = Counter(
                tx.get("consensus_status", "no_status") for tx in txs
            )

            gt = self.ground_truth.get((prefix, origin), {})
            is_attack = gt.get("is_attack", False)

            # Flag disagreements
            has_confirmed = status_dist.get("CONFIRMED", 0) > 0
            has_sw = status_dist.get("SINGLE_WITNESS", 0) > 0
            if has_confirmed and has_sw:
                disagreements.append({
                    "prefix": prefix,
                    "origin_asn": origin,
                    "status_distribution": dict(status_dist),
                    "chains_count": chain_count,
                    "is_attack": is_attack,
                })

            # Flag widely corroborated
            if chain_count >= 5:
                dominant_status = status_dist.most_common(1)[0][0]
                widely_corroborated.append({
                    "prefix": prefix,
                    "origin_asn": origin,
                    "chains_count": chain_count,
                    "consensus_status": dominant_status,
                    "is_attack": is_attack,
                })

        attack_disagree = sum(1 for d in disagreements if d["is_attack"])

        return {
            "description": "Cross-chain corroboration analysis",
            "total_unique_pairs": len(self.prefix_origin_index),
            "corroboration_distribution": dict(sorted(corroboration_hist.items())),
            "disagreement_count": len(disagreements),
            "disagreements": disagreements[:50],
            "widely_corroborated_count": len(widely_corroborated),
            "widely_corroborated": widely_corroborated[:50],
            "disagreement_attack_rate": attack_disagree / max(len(disagreements), 1),
        }

    # ------------------------------------------------------------------
    # Analysis 3: Temporal Pattern Detection
    # ------------------------------------------------------------------

    def temporal_pattern_detection(self, burst_threshold: int = 5,
                                    burst_window: int = 60) -> Dict:
        """Detect origin changes and announcement bursts from blockchain timeline."""

        # --- Origin changes ---
        prefix_origins: Dict[str, Dict[int, list]] = defaultdict(lambda: defaultdict(list))
        for (prefix, origin), txs in self.prefix_origin_index.items():
            for tx in txs:
                ts = tx.get("timestamp")
                if ts is not None:
                    prefix_origins[prefix][origin].append(ts)

        origin_changes = []
        for prefix, origins_dict in prefix_origins.items():
            if len(origins_dict) < 2:
                continue

            # Sort origins by earliest timestamp
            origin_times = []
            for origin, timestamps in origins_dict.items():
                try:
                    earliest = min(float(t) if isinstance(t, (int, float)) else 0
                                   for t in timestamps)
                except (ValueError, TypeError):
                    earliest = 0
                origin_times.append((earliest, origin))
            origin_times.sort()

            origins_ordered = [o for _, o in origin_times]

            # Check ground truth for any of these origins
            gt_labels = {}
            for origin in origins_ordered:
                gt = self.ground_truth.get((prefix, origin), {})
                if gt.get("is_attack"):
                    gt_labels[origin] = gt.get("label", "UNKNOWN")

            origin_changes.append({
                "prefix": prefix,
                "origins": origins_ordered,
                "is_attack": bool(gt_labels),
                "attack_origins": gt_labels,
            })

        # --- Announcement bursts ---
        bursts = []
        for (prefix, origin), txs in self.prefix_origin_index.items():
            sw_txs = [tx for tx in txs if tx.get("consensus_status") == "SINGLE_WITNESS"]
            if len(sw_txs) < burst_threshold:
                continue

            # Extract numeric timestamps
            timestamps = []
            for tx in sw_txs:
                ts = tx.get("timestamp")
                try:
                    timestamps.append(float(ts) if isinstance(ts, (int, float, str)) else 0)
                except (ValueError, TypeError):
                    continue

            if len(timestamps) < burst_threshold:
                continue

            timestamps.sort()

            # Sliding window
            for i in range(len(timestamps)):
                window_end = timestamps[i] + burst_window
                count = sum(1 for t in timestamps[i:] if t <= window_end)
                if count >= burst_threshold:
                    gt = self.ground_truth.get((prefix, origin), {})
                    bursts.append({
                        "prefix": prefix,
                        "origin_asn": origin,
                        "burst_count": count,
                        "window_start": timestamps[i],
                        "is_attack": gt.get("is_attack", False),
                        "label": gt.get("label", "UNKNOWN"),
                    })
                    break  # One burst per pair is enough

        true_hijacks = sum(1 for c in origin_changes if c["is_attack"])
        burst_attacks = sum(1 for b in bursts if b["is_attack"])

        return {
            "description": "Temporal pattern detection: origin changes and announcement bursts",
            "origin_changes": {
                "total_prefixes_with_changes": len(origin_changes),
                "true_hijacks": true_hijacks,
                "false_alarms": len(origin_changes) - true_hijacks,
                "changes": origin_changes[:50],
            },
            "announcement_bursts": {
                "total_bursts": len(bursts),
                "burst_attack_rate": burst_attacks / max(len(bursts), 1),
                "bursts": bursts[:50],
            },
        }

    # ------------------------------------------------------------------
    # Analysis 4: Longitudinal Trust Scoring
    # ------------------------------------------------------------------

    def longitudinal_trust_scoring(self) -> Dict:
        """Score each origin AS by its CONFIRMED vs SINGLE_WITNESS ratio."""
        as_stats: Dict[int, Dict] = defaultdict(lambda: {
            "confirmed": 0, "insufficient": 0, "single_witness": 0,
            "no_status": 0, "total": 0,
            "attack_types": set(),
        })

        for tx in self.unique_transactions.values():
            origin = tx.get("sender_asn")
            if origin is None:
                continue

            status = tx.get("consensus_status", "no_status")
            stats = as_stats[origin]
            stats["total"] += 1

            if status == "CONFIRMED":
                stats["confirmed"] += 1
            elif status == "INSUFFICIENT_CONSENSUS":
                stats["insufficient"] += 1
            elif status == "SINGLE_WITNESS":
                stats["single_witness"] += 1
            else:
                stats["no_status"] += 1

            # Track attack types from ground truth
            prefix = tx.get("ip_prefix")
            if prefix:
                gt = self.ground_truth.get((prefix, origin), {})
                if gt.get("is_attack"):
                    stats["attack_types"].add(gt.get("label", "UNKNOWN"))

        # Compute per-AS trust scores
        per_as = {}
        suspicious = []
        for asn, stats in as_stats.items():
            total = stats["total"]
            sw_ratio = stats["single_witness"] / max(total, 1)
            is_attacker = bool(stats["attack_types"])

            entry = {
                "total_announcements": total,
                "confirmed": stats["confirmed"],
                "insufficient": stats["insufficient"],
                "single_witness": stats["single_witness"],
                "sw_ratio": round(sw_ratio, 4),
                "is_attacker": is_attacker,
                "attack_types": sorted(stats["attack_types"]),
            }
            per_as[str(asn)] = entry

            if sw_ratio > 0.5 and total >= 3:
                suspicious.append({"asn": asn, **entry})

        suspicious.sort(key=lambda x: x["sw_ratio"], reverse=True)
        susp_attackers = sum(1 for s in suspicious if s["is_attacker"])

        return {
            "description": "Longitudinal trust scoring by SINGLE_WITNESS ratio",
            "total_origin_ases": len(per_as),
            "suspicious_ases_count": len(suspicious),
            "suspicious_precision": susp_attackers / max(len(suspicious), 1),
            "suspicious_ases": suspicious[:20],
            "per_as_trust": per_as,
        }

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def full_report(self) -> Dict:
        """Run all analyses and produce aggregate report."""
        sw_accum = self.single_witness_accumulation()
        corroboration = self.cross_chain_corroboration()
        temporal = self.temporal_pattern_detection()
        trust = self.longitudinal_trust_scoring()

        # Aggregate: collect all new detections
        new_detection_pairs = set()

        for u in sw_accum.get("upgraded_pairs", []):
            if u["is_attack"] and not u["realtime_detected"]:
                new_detection_pairs.add((u["prefix"], u["origin_asn"]))

        for c in temporal.get("origin_changes", {}).get("changes", []):
            if c["is_attack"]:
                for origin, label in c.get("attack_origins", {}).items():
                    key = (c["prefix"], origin)
                    if key not in self.realtime_detected:
                        new_detection_pairs.add(key)

        total_attacks = len(self.all_attacks)
        rt_detected = len(self.all_attacks & self.realtime_detected)
        posthoc_additional = len(new_detection_pairs)
        combined = rt_detected + posthoc_additional

        return {
            "single_witness_accumulation": sw_accum,
            "cross_chain_corroboration": corroboration,
            "temporal_patterns": temporal,
            "longitudinal_trust": trust,
            "aggregate_impact": {
                "total_attacks_in_dataset": total_attacks,
                "realtime_detected": rt_detected,
                "realtime_recall": rt_detected / max(total_attacks, 1),
                "posthoc_additional": posthoc_additional,
                "combined_detected": combined,
                "combined_recall": combined / max(total_attacks, 1),
                "recall_improvement": posthoc_additional / max(total_attacks, 1),
            },
            "data_summary": {
                "chains_loaded": len(self.chain_transactions),
                "unique_transactions": len(self.unique_transactions),
                "unique_prefix_origin_pairs": len(self.prefix_origin_index),
                "ground_truth_attacks": total_attacks,
            },
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analysis/posthoc_blockchain_detection.py <results_dir>")
        return 1

    results_dir = sys.argv[1]
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        detector = PosthocBlockchainDetector(results_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    report = detector.full_report()

    output_path = Path(results_dir) / "posthoc_blockchain_detection.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    agg = report["aggregate_impact"]
    data = report["data_summary"]
    sw = report["single_witness_accumulation"]
    temporal = report["temporal_patterns"]

    print(f"\n{'=' * 60}")
    print(f"POST-HOC BLOCKCHAIN DETECTION REPORT")
    print(f"{'=' * 60}")
    print(f"Chains: {data['chains_loaded']}")
    print(f"Unique transactions: {data['unique_transactions']:,}")
    print(f"Unique (prefix, origin) pairs: {data['unique_prefix_origin_pairs']:,}")
    print(f"")
    print(f"SINGLE_WITNESS accumulation:")
    print(f"  Upgraded (3+ observers): {sw['upgraded_count']}")
    print(f"  New detections: {sw['new_detections']}")
    print(f"  Precision: {sw['accumulation_precision']:.4f}")
    print(f"")
    print(f"Temporal patterns:")
    print(f"  Origin changes: {temporal['origin_changes']['total_prefixes_with_changes']}")
    print(f"  Announcement bursts: {temporal['announcement_bursts']['total_bursts']}")
    print(f"")
    print(f"AGGREGATE IMPACT:")
    print(f"  Total attacks: {agg['total_attacks_in_dataset']}")
    print(f"  Real-time detected: {agg['realtime_detected']} "
          f"(recall={agg['realtime_recall']:.4f})")
    print(f"  Post-hoc additional: {agg['posthoc_additional']}")
    print(f"  Combined: {agg['combined_detected']} "
          f"(recall={agg['combined_recall']:.4f})")
    print(f"  Recall improvement: +{agg['recall_improvement']:.4f}")
    print(f"\nReport saved: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
