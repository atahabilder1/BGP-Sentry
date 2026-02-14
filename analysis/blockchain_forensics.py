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
                obs = det.get("observer_as")
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analysis/blockchain_forensics.py <results_dir>")
        print("Example: python3 analysis/blockchain_forensics.py results/caida_500/20260213_233454/")
        return 1

    results_dir = sys.argv[1]
    forensics = BlockchainForensics(results_dir)
    report = forensics.generate_audit_report()

    # Write report
    output_path = Path(results_dir) / "forensic_audit_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Forensic audit report written to: {output_path}")
    print(f"\nBlockchain: {report['blockchain_summary']['total_blocks']} blocks, "
          f"{report['blockchain_summary']['total_transactions']} TX")
    print(f"Chain integrity: {report['blockchain_summary']['chain_integrity']}")
    print(f"\nObservations: {report['observation_summary']['total_records']} total "
          f"({report['observation_summary']['attack_observations']} attacks, "
          f"{report['observation_summary']['legitimate_observations']} legitimate)")
    print(f"Unique observers: {report['observer_coverage']['unique_observers']}")
    print(f"Affected prefixes: {report['affected_prefixes']}")

    print(f"\n--- Attacker Profiles ---")
    for attacker in report["attacker_profile"]["attackers"]:
        print(f"  AS{attacker['as_number']}: {attacker['total_attacks']} {attacker['primary_attack']} attacks, "
              f"score={attacker['trust_score']}, level={attacker['rating_level']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
