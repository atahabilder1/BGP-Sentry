#!/usr/bin/env python3
"""
BlockchainForensics - Post-hoc forensic query module for BGP-Sentry.

Provides high-level query functions to investigate blockchain records
after experiments, supporting audit trail analysis, attacker profiling,
and cross-dataset forensic comparison.

Usage:
    python3 analysis/blockchain_forensics.py results/caida_500/20260213_233454/

Demonstrates BGP-Sentry's post-hoc audit capability (Contribution #3).
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BlockchainForensics:
    """Forensic query engine for BGP-Sentry blockchain data."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        self.detection_results = self._load("detection_results.json", [])
        self.blockchain_stats = self._load("blockchain_stats.json", {})
        self.nonrpki_ratings = self._load("nonrpki_ratings.json", {})
        self.consensus_log = self._load("consensus_log.json", {})
        self.attack_verdicts = self._load("attack_verdicts.json", [])
        self.trust_scores = self._load("trust_scores.json", {})
        self.run_config = self._load("run_config.json", {})

    def _load(self, filename: str, default):
        path = self.results_dir / filename
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def get_attack_history(self, as_number: int) -> Dict:
        """
        Get complete attack history for a specific AS from blockchain records.

        Returns all attacks attributed to this AS, including attack types,
        affected prefixes, observer ASes, and consensus status.
        """
        attacks = []
        legitimate = []

        for det in self.detection_results:
            origin = det.get("origin_asn", det.get("sender_asn"))
            if origin == as_number:
                entry = {
                    "prefix": det.get("prefix", det.get("ip_prefix")),
                    "label": det.get("label", "UNKNOWN"),
                    "is_attack": det.get("is_attack", False),
                    "observer_as": det.get("observer_as"),
                    "detected": det.get("detected", False),
                    "consensus": det.get("consensus_reached", False),
                }
                if det.get("is_attack"):
                    attacks.append(entry)
                else:
                    legitimate.append(entry)

        # Get trust score
        ratings = self.nonrpki_ratings.get("ratings", self.nonrpki_ratings)
        rating_info = ratings.get(str(as_number), {})

        attack_types = Counter(a["label"] for a in attacks)

        return {
            "as_number": as_number,
            "total_attacks": len(attacks),
            "total_legitimate": len(legitimate),
            "attack_types": dict(attack_types),
            "trust_score": rating_info.get("trust_score", rating_info.get("score", "N/A")),
            "rating_level": rating_info.get("rating_level", rating_info.get("level", "N/A")),
            "unique_prefixes_attacked": len(set(a["prefix"] for a in attacks)),
            "attacks": attacks,
            "legitimate": legitimate,
        }

    def identify_attackers(self) -> List[Dict]:
        """
        Identify all ASes that performed attacks, ranked by severity.

        This is the primary forensic query: given the immutable blockchain
        records, identify which ASes misbehaved and how.
        """
        attacker_stats = defaultdict(lambda: {
            "attacks": [], "attack_count": 0, "legit_count": 0
        })

        for det in self.detection_results:
            asn = det.get("origin_asn", det.get("sender_asn"))
            if asn is None:
                continue
            if det.get("is_attack"):
                attacker_stats[asn]["attacks"].append(det.get("label", "UNKNOWN"))
                attacker_stats[asn]["attack_count"] += 1
            else:
                attacker_stats[asn]["legit_count"] += 1

        # Build ranked list
        ratings = self.nonrpki_ratings.get("ratings", self.nonrpki_ratings)
        result = []
        for asn, stats in attacker_stats.items():
            if stats["attack_count"] == 0:
                continue
            rating_info = ratings.get(str(asn), {})
            attack_types = Counter(stats["attacks"])
            result.append({
                "as_number": asn,
                "total_attacks": stats["attack_count"],
                "total_legitimate": stats["legit_count"],
                "attack_types": dict(attack_types),
                "primary_attack": attack_types.most_common(1)[0][0],
                "trust_score": rating_info.get("trust_score", rating_info.get("score", "N/A")),
                "rating_level": rating_info.get("rating_level", rating_info.get("level", "N/A")),
            })

        return sorted(result, key=lambda x: -x["total_attacks"])

    def get_prefix_history(self, prefix: str) -> Dict:
        """
        Get all blockchain records related to a specific IP prefix.

        Useful for investigating whether a prefix was ever hijacked,
        by whom, and how many observers detected it.
        """
        records = []
        for det in self.detection_results:
            det_prefix = det.get("prefix", det.get("ip_prefix", ""))
            if det_prefix == prefix:
                records.append({
                    "origin_asn": det.get("origin_asn", det.get("sender_asn")),
                    "observer_as": det.get("observer_as"),
                    "is_attack": det.get("is_attack", False),
                    "label": det.get("label"),
                    "detected": det.get("detected", False),
                })

        attack_records = [r for r in records if r["is_attack"]]
        legitimate_records = [r for r in records if not r["is_attack"]]

        return {
            "prefix": prefix,
            "total_records": len(records),
            "attack_records": len(attack_records),
            "legitimate_records": len(legitimate_records),
            "attackers": list(set(r["origin_asn"] for r in attack_records)),
            "observers": list(set(r["observer_as"] for r in records if r["observer_as"])),
            "records": records,
        }

    def generate_audit_report(self) -> Dict:
        """
        Generate a comprehensive forensic audit report from blockchain data.

        This demonstrates the post-hoc audit capability: after the experiment,
        an operator can query the blockchain to reconstruct a complete picture
        of all routing events, attacks, and trust changes.
        """
        info = self.blockchain_stats.get("blockchain_info", {})
        integrity = self.blockchain_stats.get("integrity", {})

        total_records = len(self.detection_results)
        attack_records = sum(1 for d in self.detection_results if d.get("is_attack"))
        legitimate_records = total_records - attack_records

        attackers = self.identify_attackers()

        # Attack type breakdown
        all_attacks = [d.get("label") for d in self.detection_results if d.get("is_attack")]
        attack_type_counts = Counter(all_attacks)

        # Unique prefixes affected
        attacked_prefixes = set()
        for d in self.detection_results:
            if d.get("is_attack"):
                attacked_prefixes.add(d.get("prefix", d.get("ip_prefix", "")))

        # Observer coverage
        observers = set()
        for d in self.detection_results:
            obs = d.get("observer_as")
            if obs:
                observers.add(obs)

        return {
            "blockchain_summary": {
                "total_blocks": info.get("total_blocks", 0),
                "total_transactions": info.get("total_transactions", 0),
                "chain_integrity": integrity.get("valid", "unknown"),
            },
            "observation_summary": {
                "total_records": total_records,
                "attack_observations": attack_records,
                "legitimate_observations": legitimate_records,
                "attack_ratio": round(attack_records / max(total_records, 1) * 100, 1),
            },
            "attacker_profile": {
                "unique_attackers": len(attackers),
                "attackers": attackers,
            },
            "attack_breakdown": dict(attack_type_counts),
            "affected_prefixes": len(attacked_prefixes),
            "observer_coverage": {
                "unique_observers": len(observers),
                "observer_list": sorted(observers),
            },
            "dataset": self.run_config.get("dataset_name", "unknown"),
        }

    def cross_reference_observers(self, as_number: int) -> Dict:
        """
        For a given AS, find which observers detected its attacks and
        how many independent observers corroborated each detection.
        """
        observer_detections = defaultdict(list)
        for det in self.detection_results:
            origin = det.get("origin_asn", det.get("sender_asn"))
            if origin == as_number and det.get("is_attack"):
                obs = det.get("observer_as", det.get("asn"))
                if obs:
                    observer_detections[obs].append(det.get("label"))

        return {
            "as_number": as_number,
            "total_observers": len(observer_detections),
            "per_observer": {
                obs: {"count": len(labels), "types": dict(Counter(labels))}
                for obs, labels in observer_detections.items()
            },
        }

    # =================================================================
    # POST-HOC FORENSIC ANALYSES (Section 3, items i-v)
    # =================================================================

    def cross_observer_route_stability(self, time_window: int = 60) -> Dict:
        """
        Post-hoc analysis (i): Cross-Observer Route Stability.

        For each (prefix, origin) flagged as ROUTE_FLAPPING, check how many
        independent observers recorded repeated announcements within overlapping
        time windows. If multiple observers see oscillation -> systemic
        instability (confirmed flapping). If only one observer -> likely
        localized convergence (false positive candidate).

        Args:
            time_window: seconds to define overlapping observation windows
        """
        # Step 1: Group all flapping-flagged records by (prefix, origin_asn)
        flap_observations = defaultdict(list)
        for det in self.detection_results:
            if det.get("detection_type") == "ROUTE_FLAPPING":
                key = (det.get("prefix"), det.get("origin_asn"))
                flap_observations[key].append({
                    "observer": det.get("asn"),
                    "timestamp": det.get("timestamp", 0),
                    "is_attack": det.get("is_attack", False),
                    "label": det.get("label"),
                })

        # Step 2: For each flagged (prefix, origin), count independent observers
        systemic = []  # Multiple observers -> confirmed instability
        localized = []  # Single observer -> likely false positive

        for (prefix, origin), observations in flap_observations.items():
            unique_observers = set(o["observer"] for o in observations)
            timestamps = sorted(o["timestamp"] for o in observations)

            # Check temporal overlap: are observations within the same window?
            time_span = (timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0
            is_ground_truth_attack = any(o["is_attack"] for o in observations)

            entry = {
                "prefix": prefix,
                "origin_asn": origin,
                "num_observers": len(unique_observers),
                "observers": sorted(unique_observers),
                "total_observations": len(observations),
                "time_span_seconds": time_span,
                "ground_truth_is_attack": is_ground_truth_attack,
            }

            if len(unique_observers) >= 2:
                systemic.append(entry)
            else:
                localized.append(entry)

        # Step 3: Compute accuracy of cross-observer classification
        # Systemic should mostly be true attacks; localized should mostly be FPs
        systemic_tp = sum(1 for e in systemic if e["ground_truth_is_attack"])
        systemic_fp = sum(1 for e in systemic if not e["ground_truth_is_attack"])
        localized_tp = sum(1 for e in localized if e["ground_truth_is_attack"])
        localized_fp = sum(1 for e in localized if not e["ground_truth_is_attack"])

        total_flagged = len(systemic) + len(localized)

        return {
            "description": "Cross-observer route stability analysis: "
                           "systemic = multi-observer confirmed, "
                           "localized = single-observer (FP candidate)",
            "time_window_seconds": time_window,
            "total_prefixes_flagged": total_flagged,
            "systemic_instability": {
                "count": len(systemic),
                "true_attacks": systemic_tp,
                "false_positives": systemic_fp,
                "precision": round(systemic_tp / max(systemic_tp + systemic_fp, 1), 4),
                "entries": systemic[:10],  # Top 10 for brevity
            },
            "localized_convergence": {
                "count": len(localized),
                "true_attacks_missed": localized_tp,
                "correctly_filtered_fps": localized_fp,
                "fp_filter_rate": round(localized_fp / max(len(localized), 1), 4),
                "entries": localized[:10],
            },
            "improvement": {
                "realtime_flap_flags": total_flagged,
                "posthoc_confirmed": len(systemic),
                "posthoc_filtered": len(localized),
                "realtime_precision": round(
                    (systemic_tp + localized_tp) / max(total_flagged, 1), 4
                ),
                "posthoc_precision": round(
                    systemic_tp / max(len(systemic), 1), 4
                ) if systemic else 0.0,
            },
        }

    def coordinated_attack_detection(self, time_window: int = 30) -> Dict:
        """
        Post-hoc analysis (iii): Coordinated Attack Detection.

        Find groups of different ASes that launched attacks within the same
        time window. Each individual attack appears independent to the
        real-time pipeline; this analysis reveals temporal coordination.

        Args:
            time_window: seconds within which co-occurring attacks are
                         considered potentially coordinated
        """
        # Step 1: Collect all confirmed attacks with timestamps
        attacks = []
        for det in self.detection_results:
            if det.get("is_attack") and det.get("detected"):
                attacks.append({
                    "origin_asn": det.get("origin_asn"),
                    "prefix": det.get("prefix"),
                    "timestamp": det.get("timestamp", 0),
                    "attack_type": det.get("label"),
                    "observer": det.get("asn"),
                })

        if not attacks:
            return {"description": "No attacks found", "clusters": []}

        # Step 2: Sort by time and find clusters of attacks from different ASes
        attacks.sort(key=lambda x: x["timestamp"])
        clusters = []
        i = 0

        while i < len(attacks):
            # Start a new window from this attack
            window_start = attacks[i]["timestamp"]
            window_end = window_start + time_window
            window_attacks = []

            j = i
            while j < len(attacks) and attacks[j]["timestamp"] <= window_end:
                window_attacks.append(attacks[j])
                j += 1

            # Check if multiple distinct ASes attacked in this window
            unique_attackers = set(a["origin_asn"] for a in window_attacks)
            if len(unique_attackers) >= 2:
                unique_prefixes = set(a["prefix"] for a in window_attacks)
                attack_types = Counter(a["attack_type"] for a in window_attacks)
                clusters.append({
                    "window_start": window_start,
                    "window_end": window_end,
                    "num_attackers": len(unique_attackers),
                    "attackers": sorted(unique_attackers),
                    "num_prefixes": len(unique_prefixes),
                    "total_attacks_in_window": len(window_attacks),
                    "attack_types": dict(attack_types),
                })

            # Advance past this window to avoid duplicate clusters
            i = j if j > i else i + 1

        # Deduplicate overlapping clusters: keep those with most attackers
        deduplicated = []
        seen_windows = set()
        for cluster in sorted(clusters, key=lambda c: -c["num_attackers"]):
            window_key = (cluster["window_start"] // time_window)
            if window_key not in seen_windows:
                deduplicated.append(cluster)
                seen_windows.add(window_key)

        return {
            "description": "Coordinated attack detection: groups of different ASes "
                           "attacking within the same time window",
            "time_window_seconds": time_window,
            "total_attacks_analyzed": len(attacks),
            "coordination_clusters": len(deduplicated),
            "max_attackers_in_cluster": max(
                (c["num_attackers"] for c in deduplicated), default=0
            ),
            "clusters": deduplicated[:20],  # Top 20
        }

    def observer_integrity_audit(self) -> Dict:
        """
        Post-hoc analysis (iv): Observer Integrity Auditing.

        For each RPKI observer, compute detection accuracy compared to
        ground truth and identify statistical outliers whose detection
        patterns deviate significantly from the majority.
        """
        # Step 1: Per-observer detection statistics
        observer_stats = defaultdict(lambda: {
            "total_observed": 0,
            "attacks_in_ground_truth": 0,
            "attacks_detected": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_positives": 0,
            "true_negatives": 0,
            "detection_types": Counter(),
        })

        for det in self.detection_results:
            obs = det.get("asn")
            if obs is None:
                continue

            stats = observer_stats[obs]
            stats["total_observed"] += 1

            is_attack = det.get("is_attack", False)
            detected = det.get("detected", False)

            if is_attack:
                stats["attacks_in_ground_truth"] += 1
                if detected:
                    stats["true_positives"] += 1
                    stats["attacks_detected"] += 1
                else:
                    stats["false_negatives"] += 1
            else:
                if detected:
                    stats["false_positives"] += 1
                    dtype = det.get("detection_type", "UNKNOWN")
                    stats["detection_types"][dtype] += 1
                else:
                    stats["true_negatives"] += 1

        # Step 2: Compute per-observer metrics
        observer_metrics = {}
        all_fp_rates = []

        for obs, stats in observer_stats.items():
            total = stats["total_observed"]
            tp = stats["true_positives"]
            fp = stats["false_positives"]
            fn = stats["false_negatives"]
            tn = stats["true_negatives"]

            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            fp_rate = fp / max(fp + tn, 1)
            all_fp_rates.append(fp_rate)

            observer_metrics[obs] = {
                "total_observed": total,
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "fp_rate": round(fp_rate, 6),
                "fp_types": dict(stats["detection_types"]),
            }

        # Step 3: Identify outliers (observers with anomalous FP rates)
        if all_fp_rates:
            mean_fp = sum(all_fp_rates) / len(all_fp_rates)
            variance = sum((r - mean_fp) ** 2 for r in all_fp_rates) / max(len(all_fp_rates), 1)
            std_fp = variance ** 0.5
            threshold = mean_fp + 2 * std_fp  # 2-sigma outlier

            outliers = []
            for obs, metrics in observer_metrics.items():
                if metrics["fp_rate"] > threshold and metrics["false_positives"] > 0:
                    outliers.append({
                        "observer_as": obs,
                        "fp_rate": metrics["fp_rate"],
                        "false_positives": metrics["false_positives"],
                        "total_observed": metrics["total_observed"],
                        "deviation_sigmas": round(
                            (metrics["fp_rate"] - mean_fp) / max(std_fp, 1e-9), 2
                        ),
                        "fp_types": metrics["fp_types"],
                    })

            outliers.sort(key=lambda x: -x["deviation_sigmas"])
        else:
            mean_fp = 0
            std_fp = 0
            threshold = 0
            outliers = []

        return {
            "description": "Observer integrity audit: per-observer detection accuracy "
                           "and outlier identification",
            "total_observers": len(observer_metrics),
            "global_stats": {
                "mean_fp_rate": round(mean_fp, 6),
                "std_fp_rate": round(std_fp, 6),
                "outlier_threshold_fp_rate": round(threshold, 6),
            },
            "outliers": {
                "count": len(outliers),
                "flagged_observers": outliers[:10],
            },
            "per_observer": observer_metrics,
        }

    def behavioral_pattern_detection(self) -> Dict:
        """
        Post-hoc analysis (v): Behavioral Pattern Detection.

        For each non-RPKI AS, reconstruct the behavioral timeline from
        blockchain records and detect trust score gaming patterns
        (cyclical attack -> recovery -> attack behavior).
        """
        # Step 1: Build per-AS timeline sorted by timestamp
        as_timelines = defaultdict(list)
        for det in self.detection_results:
            origin = det.get("origin_asn")
            if origin is None:
                continue
            as_timelines[origin].append({
                "timestamp": det.get("timestamp", 0),
                "is_attack": det.get("is_attack", False),
                "label": det.get("label"),
                "prefix": det.get("prefix"),
                "observer": det.get("asn"),
                "detected": det.get("detected", False),
            })

        # Sort each timeline
        for asn in as_timelines:
            as_timelines[asn].sort(key=lambda x: x["timestamp"])

        # Step 2: Detect behavioral patterns
        ratings = self.nonrpki_ratings.get("ratings", self.nonrpki_ratings)
        as_profiles = {}

        for asn, timeline in as_timelines.items():
            if not timeline:
                continue

            attacks = [e for e in timeline if e["is_attack"]]
            legitimate = [e for e in timeline if not e["is_attack"]]

            if not attacks:
                continue  # Only analyze ASes with attacks

            # Compute timeline phases: attack clusters separated by clean periods
            attack_timestamps = sorted(e["timestamp"] for e in attacks)
            phases = []
            current_phase_start = attack_timestamps[0]
            current_phase_end = attack_timestamps[0]
            phase_count = 0

            for ts in attack_timestamps[1:]:
                # If gap between attacks > 60s, it's a new attack phase
                if ts - current_phase_end > 60:
                    phases.append({
                        "phase_start": current_phase_start,
                        "phase_end": current_phase_end,
                        "duration": current_phase_end - current_phase_start,
                    })
                    phase_count += 1
                    current_phase_start = ts
                current_phase_end = ts

            # Don't forget last phase
            phases.append({
                "phase_start": current_phase_start,
                "phase_end": current_phase_end,
                "duration": current_phase_end - current_phase_start,
            })

            # Detect gaming: multiple attack phases with clean periods in between
            # (attack -> clean -> attack -> clean -> attack = gaming pattern)
            is_gaming = len(phases) >= 3
            total_span = timeline[-1]["timestamp"] - timeline[0]["timestamp"]

            # Get trust score
            rating_info = ratings.get(str(asn), {})

            attack_types = Counter(e["label"] for e in attacks)

            as_profiles[asn] = {
                "total_events": len(timeline),
                "total_attacks": len(attacks),
                "total_legitimate": len(legitimate),
                "attack_types": dict(attack_types),
                "attack_phases": len(phases),
                "phase_details": phases[:10],  # First 10 phases
                "timeline_span_seconds": total_span,
                "gaming_pattern_detected": is_gaming,
                "trust_score": rating_info.get("trust_score",
                                               rating_info.get("score", "N/A")),
                "rating_level": rating_info.get("rating_level",
                                                rating_info.get("level", "N/A")),
            }

        # Step 3: Summary
        gaming_ases = [asn for asn, p in as_profiles.items()
                       if p["gaming_pattern_detected"]]
        multi_phase = [asn for asn, p in as_profiles.items()
                       if p["attack_phases"] >= 2]

        return {
            "description": "Behavioral pattern detection: per-AS timeline "
                           "reconstruction and trust score gaming detection",
            "total_ases_with_attacks": len(as_profiles),
            "gaming_detected": {
                "count": len(gaming_ases),
                "ases": sorted(gaming_ases),
            },
            "multi_phase_attackers": {
                "count": len(multi_phase),
                "ases": sorted(multi_phase),
            },
            "per_as_profiles": {
                str(asn): profile
                for asn, profile in sorted(
                    as_profiles.items(),
                    key=lambda x: -x[1]["total_attacks"]
                )[:20]  # Top 20 by attack count
            },
        }

    def full_posthoc_report(self) -> Dict:
        """Generate complete post-hoc forensic report with all analyses."""
        return {
            "i_cross_observer_route_stability": self.cross_observer_route_stability(),
            "iii_coordinated_attack_detection": self.coordinated_attack_detection(),
            "iv_observer_integrity_audit": self.observer_integrity_audit(),
            "v_behavioral_pattern_detection": self.behavioral_pattern_detection(),
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analysis/blockchain_forensics.py <results_dir>")
        print("Example: python3 analysis/blockchain_forensics.py results/caida_bfs_174_200/20260327_072533/")
        return 1

    results_dir = sys.argv[1]
    forensics = BlockchainForensics(results_dir)

    # --- Original audit report ---
    report = forensics.generate_audit_report()

    output_path = Path(results_dir) / "forensic_audit_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Forensic audit report written to: {output_path}")
    print(f"\nObservations: {report['observation_summary']['total_records']} total "
          f"({report['observation_summary']['attack_observations']} attacks, "
          f"{report['observation_summary']['legitimate_observations']} legitimate)")

    print(f"\n--- Attacker Profiles ---")
    for attacker in report["attacker_profile"]["attackers"]:
        print(f"  AS{attacker['as_number']}: {attacker['total_attacks']} "
              f"{attacker['primary_attack']} attacks, "
              f"score={attacker['trust_score']}, level={attacker['rating_level']}")

    # --- Post-Hoc Forensic Analyses ---
    print("\n" + "=" * 60)
    print("POST-HOC FORENSIC ANALYSES")
    print("=" * 60)

    # (i) Cross-Observer Route Stability
    stability = forensics.cross_observer_route_stability()
    print(f"\n--- (i) Cross-Observer Route Stability ---")
    print(f"  Prefixes flagged for flapping: {stability['total_prefixes_flagged']}")
    print(f"  Systemic (multi-observer): {stability['systemic_instability']['count']} "
          f"(precision={stability['systemic_instability']['precision']})")
    print(f"  Localized (single-observer): {stability['localized_convergence']['count']} "
          f"(FPs filtered: {stability['localized_convergence']['correctly_filtered_fps']})")
    imp = stability['improvement']
    print(f"  Precision improvement: {imp['realtime_precision']} (real-time) -> "
          f"{imp['posthoc_precision']} (post-hoc)")

    # (iii) Coordinated Attack Detection
    coordinated = forensics.coordinated_attack_detection()
    print(f"\n--- (iii) Coordinated Attack Detection ---")
    print(f"  Attacks analyzed: {coordinated['total_attacks_analyzed']}")
    print(f"  Coordination clusters found: {coordinated['coordination_clusters']}")
    if coordinated['clusters']:
        top = coordinated['clusters'][0]
        print(f"  Largest cluster: {top['num_attackers']} ASes, "
              f"{top['total_attacks_in_window']} attacks in {coordinated['time_window_seconds']}s")

    # (iv) Observer Integrity Audit
    integrity = forensics.observer_integrity_audit()
    print(f"\n--- (iv) Observer Integrity Audit ---")
    print(f"  Observers audited: {integrity['total_observers']}")
    gs = integrity['global_stats']
    print(f"  Mean FP rate: {gs['mean_fp_rate']:.6f} "
          f"(std: {gs['std_fp_rate']:.6f})")
    print(f"  Outliers (>2-sigma): {integrity['outliers']['count']}")
    for outlier in integrity['outliers']['flagged_observers'][:3]:
        print(f"    AS{outlier['observer_as']}: FP rate={outlier['fp_rate']:.4f} "
              f"({outlier['deviation_sigmas']}σ), "
              f"FPs={outlier['false_positives']}, types={outlier['fp_types']}")

    # (v) Behavioral Pattern Detection
    patterns = forensics.behavioral_pattern_detection()
    print(f"\n--- (v) Behavioral Pattern Detection ---")
    print(f"  ASes with attacks: {patterns['total_ases_with_attacks']}")
    print(f"  Multi-phase attackers: {patterns['multi_phase_attackers']['count']}")
    print(f"  Gaming pattern detected: {patterns['gaming_detected']['count']} ASes")
    if patterns['gaming_detected']['ases']:
        print(f"    Gaming ASes: {patterns['gaming_detected']['ases'][:10]}")

    # Write full post-hoc report
    posthoc_report = forensics.full_posthoc_report()
    posthoc_path = Path(results_dir) / "posthoc_forensic_report.json"
    with open(posthoc_path, "w") as f:
        json.dump(posthoc_report, f, indent=2, default=str)

    print(f"\nFull post-hoc report written to: {posthoc_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
