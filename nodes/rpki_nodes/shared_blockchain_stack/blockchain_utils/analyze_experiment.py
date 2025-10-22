#!/usr/bin/env python3
"""
=============================================================================
Experiment Results Analyzer - Automated Analysis Tool
=============================================================================

Purpose: Automatically analyze attack experiment results
         - Detection accuracy metrics
         - Rating change analysis
         - Blockchain performance
         - Classification validation

Author: BGP-Sentry Team
=============================================================================
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ExperimentAnalyzer:
    """
    Analyzes attack experiment results and generates insights.
    """

    def __init__(self, experiment_dir: Path):
        """Initialize analyzer with experiment directory"""
        self.experiment_dir = experiment_dir
        self.ground_truth = None
        self.monitoring_data = None
        self.performance_data = None
        self.detection_report = None

        # Load all data files
        self._load_data()

    def _load_data(self):
        """Load all result files"""
        try:
            # Load ground truth
            with open(self.experiment_dir / "attack_scenarios.json") as f:
                self.ground_truth = json.load(f)

            # Load monitoring data
            with open(self.experiment_dir / "rating_monitoring_data.json") as f:
                self.monitoring_data = json.load(f)

            # Load performance data
            perf_file = self.experiment_dir / "blockchain_performance_report.json"
            if perf_file.exists():
                with open(perf_file) as f:
                    self.performance_data = json.load(f)

            # Load detection report
            det_file = self.experiment_dir / "detection_accuracy_report.json"
            if det_file.exists():
                with open(det_file) as f:
                    self.detection_report = json.load(f)

        except Exception as e:
            print(f"❌ Error loading data: {e}")
            sys.exit(1)

    def analyze_attack_detection(self) -> Dict:
        """Analyze attack detection performance"""
        # Handle both old format (with summary) and new format (flat structure)
        if "summary" in self.ground_truth:
            summary = self.ground_truth["summary"]
        else:
            # Create summary from flat structure
            summary = {
                "total_attacks": self.ground_truth.get("total_attacks", 0),
                "total_legitimate": self.ground_truth.get("total_legitimate", 0),
                "total_announcements": self.ground_truth.get("total_announcements", 0),
                "attack_ratio_percent": self.ground_truth.get("attack_ratio", 0) * 100,
                "attacker_ases": {}
            }
            # Build attacker_ases from attackers dict
            for as_num, as_data in self.ground_truth.get("attackers", {}).items():
                summary["attacker_ases"][as_num] = as_data.get("total_attacks", 0)

        total_attacks = summary.get("total_attacks", 0)
        total_legitimate = summary.get("total_legitimate", 0)
        attacker_ases = summary.get("attacker_ases", {})

        # Count detected attacks
        time_series = self.monitoring_data.get("time_series", {})
        detected_attacks = {}

        for as_num, data in time_series.items():
            attacks = data.get("attacks_detected", [])
            if attacks:
                detected_attacks[as_num] = attacks[-1]  # Final count

        # Calculate metrics
        total_detected = sum(detected_attacks.values())
        detection_rate = (total_detected / total_attacks * 100) if total_attacks > 0 else 0

        return {
            "total_injected": total_attacks,
            "total_detected": total_detected,
            "detection_rate": round(detection_rate, 2),
            "attacker_breakdown": {
                as_num: {
                    "injected": count,
                    "detected": detected_attacks.get(str(as_num), 0),
                    "detection_rate": round(detected_attacks.get(str(as_num), 0) / count * 100, 2) if count > 0 else 0
                }
                for as_num, count in attacker_ases.items()
            }
        }

    def analyze_rating_changes(self) -> Dict:
        """Analyze rating changes for all ASes"""
        time_series = self.monitoring_data.get("time_series", {})
        summary = self.monitoring_data.get("summary", {}).get("as_summary", {})

        results = {}

        for as_num, data in time_series.items():
            ratings = data.get("ratings", [])
            if not ratings:
                continue

            initial = ratings[0]
            final = ratings[-1]
            change = final - initial
            min_rating = min(ratings)
            max_rating = max(ratings)

            # Get classification
            classification = summary.get(str(as_num), {}).get("final_classification", "unknown")

            results[as_num] = {
                "initial_rating": round(initial, 2),
                "final_rating": round(final, 2),
                "rating_change": round(change, 2),
                "min_rating": round(min_rating, 2),
                "max_rating": round(max_rating, 2),
                "classification": classification,
                "trend": "decreasing" if change < -5 else ("increasing" if change > 5 else "stable")
            }

        return results

    def analyze_classification_accuracy(self) -> Dict:
        """Analyze classification accuracy"""
        # Handle both old and new format
        if "summary" in self.ground_truth:
            attacker_ases = set(str(k) for k in self.ground_truth["summary"]["attacker_ases"].keys())
        else:
            attacker_ases = set(str(k) for k in self.ground_truth.get("attackers", {}).keys())
        time_series = self.monitoring_data.get("time_series", {})
        summary = self.monitoring_data.get("summary", {}).get("as_summary", {})

        correct_classifications = 0
        total_ases = 0
        misclassifications = []

        for as_num in time_series.keys():
            total_ases += 1
            classification = summary.get(str(as_num), {}).get("final_classification", "unknown")

            is_attacker = str(as_num) in attacker_ases

            # Check if classification is correct
            if is_attacker:
                # Attackers should be RED or YELLOW
                if classification in ["RED", "YELLOW"]:
                    correct_classifications += 1
                else:
                    misclassifications.append({
                        "as_number": as_num,
                        "expected": "RED/YELLOW",
                        "actual": classification,
                        "reason": "Attacker classified as legitimate"
                    })
            else:
                # Legitimate should be GREEN or YELLOW
                if classification in ["GREEN", "YELLOW"]:
                    correct_classifications += 1
                else:
                    misclassifications.append({
                        "as_number": as_num,
                        "expected": "GREEN/YELLOW",
                        "actual": classification,
                        "reason": "Legitimate AS classified as malicious"
                    })

        accuracy = (correct_classifications / total_ases * 100) if total_ases > 0 else 0

        return {
            "total_ases": total_ases,
            "correct_classifications": correct_classifications,
            "accuracy_percent": round(accuracy, 2),
            "misclassifications": misclassifications
        }

    def analyze_performance(self) -> Dict:
        """Analyze blockchain performance"""
        if not self.performance_data:
            return {"status": "No performance data available"}

        metrics = self.performance_data.get("metrics", {})

        avg_tps = metrics.get("average_tps", 0)

        # Classify performance
        if avg_tps >= 100:
            perf_class = "EXCELLENT"
        elif avg_tps >= 50:
            perf_class = "GOOD"
        elif avg_tps >= 10:
            perf_class = "MODERATE"
        elif avg_tps >= 1:
            perf_class = "LOW"
        else:
            perf_class = "VERY_LOW"

        return {
            "average_tps": metrics.get("average_tps", 0),
            "peak_tps": metrics.get("peak_tps", 0),
            "total_transactions": metrics.get("total_transactions", 0),
            "total_blocks": metrics.get("total_blocks", 0),
            "throughput_kb_per_sec": metrics.get("throughput_kb_per_second", 0),
            "duration_minutes": metrics.get("duration_minutes", 0),
            "performance_class": perf_class
        }

    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("=" * 80)
        print("📊 EXPERIMENT ANALYSIS REPORT")
        print("=" * 80)
        print()

        # Experiment info
        print(f"📁 Experiment: {self.experiment_dir.name}")
        print(f"   Location: {self.experiment_dir}")
        print()

        # Ground truth summary - handle both formats
        if "summary" in self.ground_truth:
            summary = self.ground_truth["summary"]
        else:
            summary = {
                "total_attacks": self.ground_truth.get("total_attacks", 0),
                "total_legitimate": self.ground_truth.get("total_legitimate", 0),
                "total_announcements": self.ground_truth.get("total_announcements", 0),
                "attack_ratio_percent": self.ground_truth.get("attack_ratio", 0) * 100,
                "attacker_ases": {}
            }
            for as_num, as_data in self.ground_truth.get("attackers", {}).items():
                summary["attacker_ases"][as_num] = as_data.get("total_attacks", 0)

        print("=" * 80)
        print("📋 GROUND TRUTH SUMMARY")
        print("=" * 80)
        print(f"   Total Attacks: {summary.get('total_attacks', 0)}")
        print(f"   Total Legitimate: {summary.get('total_legitimate', 0)}")
        print(f"   Total Announcements: {summary.get('total_announcements', 0)}")
        print(f"   Attack Ratio: {summary.get('attack_ratio_percent', 0):.2f}%")
        print()
        print("   Attacker Distribution:")
        for as_num, count in summary.get("attacker_ases", {}).items():
            print(f"      AS{as_num}: {count} attacks")
        print()

        # Detection analysis
        print("=" * 80)
        print("🎯 ATTACK DETECTION ANALYSIS")
        print("=" * 80)
        detection = self.analyze_attack_detection()
        print(f"   Total Injected: {detection['total_injected']} attacks")
        print(f"   Total Detected: {detection['total_detected']} attacks")
        print(f"   Detection Rate: {detection['detection_rate']:.2f}%")

        if detection['detection_rate'] >= 95:
            print(f"   Status: ✅ EXCELLENT (≥95%)")
        elif detection['detection_rate'] >= 80:
            print(f"   Status: ✅ GOOD (≥80%)")
        elif detection['detection_rate'] >= 60:
            print(f"   Status: ⚠️  MODERATE (≥60%)")
        else:
            print(f"   Status: ❌ LOW (<60%)")
        print()

        print("   Per-Attacker Breakdown:")
        for as_num, data in detection['attacker_breakdown'].items():
            print(f"      AS{as_num}: {data['detected']}/{data['injected']} detected ({data['detection_rate']:.1f}%)")
        print()

        # Rating changes
        print("=" * 80)
        print("📈 RATING CHANGE ANALYSIS")
        print("=" * 80)
        rating_changes = self.analyze_rating_changes()

        # Sort by rating change (most negative first)
        sorted_ases = sorted(
            rating_changes.items(),
            key=lambda x: x[1]['rating_change']
        )

        attacker_ases = set(str(k) for k in summary.get("attacker_ases", {}).keys())

        print(f"{'AS':<8} {'Initial':<10} {'Final':<10} {'Change':<10} {'Class':<12} {'Trend':<12} {'Type':<10}")
        print("-" * 80)

        for as_num, data in sorted_ases:
            is_attacker = str(as_num) in attacker_ases
            as_type = "ATTACKER" if is_attacker else "Legitimate"

            # Emoji for classification
            class_emoji = {
                "RED": "🔴",
                "YELLOW": "🟡",
                "GREEN": "🟢"
            }.get(data['classification'], "⚪")

            print(
                f"AS{as_num:<6} "
                f"{data['initial_rating']:<10.1f} "
                f"{data['final_rating']:<10.1f} "
                f"{data['rating_change']:<+10.1f} "
                f"{class_emoji} {data['classification']:<9} "
                f"{data['trend']:<12} "
                f"{as_type:<10}"
            )
        print()

        # Classification accuracy
        print("=" * 80)
        print("🎨 CLASSIFICATION ACCURACY")
        print("=" * 80)
        classification = self.analyze_classification_accuracy()
        print(f"   Total ASes: {classification['total_ases']}")
        print(f"   Correctly Classified: {classification['correct_classifications']}")
        print(f"   Accuracy: {classification['accuracy_percent']:.2f}%")

        if classification['accuracy_percent'] >= 90:
            print(f"   Status: ✅ EXCELLENT (≥90%)")
        elif classification['accuracy_percent'] >= 75:
            print(f"   Status: ✅ GOOD (≥75%)")
        else:
            print(f"   Status: ⚠️  NEEDS IMPROVEMENT (<75%)")
        print()

        if classification['misclassifications']:
            print("   ⚠️  Misclassifications:")
            for mis in classification['misclassifications']:
                print(f"      AS{mis['as_number']}: Expected {mis['expected']}, got {mis['actual']}")
                print(f"         Reason: {mis['reason']}")
        else:
            print("   ✅ No misclassifications!")
        print()

        # Performance
        print("=" * 80)
        print("⚡ BLOCKCHAIN PERFORMANCE")
        print("=" * 80)
        perf = self.analyze_performance()

        if "status" in perf:
            print(f"   {perf['status']}")
        else:
            print(f"   Average TPS: {perf['average_tps']:.2f} transactions/second")
            print(f"   Peak TPS: {perf['peak_tps']:.2f} transactions/second")
            print(f"   Total Transactions: {perf['total_transactions']}")
            print(f"   Total Blocks: {perf['total_blocks']}")
            print(f"   Throughput: {perf['throughput_kb_per_sec']:.2f} KB/s")
            print(f"   Duration: {perf['duration_minutes']:.2f} minutes")
            print(f"   Performance Class: {perf['performance_class']}")

            # Performance feedback
            perf_class = perf['performance_class']
            if perf_class == "EXCELLENT":
                print(f"   Status: 🟢 Production-ready performance!")
            elif perf_class == "GOOD":
                print(f"   Status: 🟢 High performance system")
            elif perf_class == "MODERATE":
                print(f"   Status: 🟡 Acceptable for research")
            elif perf_class == "LOW":
                print(f"   Status: 🟡 Basic functionality (consider optimization)")
            else:
                print(f"   Status: 🔴 Performance issues detected")
        print()

        # Overall verdict
        print("=" * 80)
        print("✅ OVERALL VERDICT")
        print("=" * 80)

        detection_rate = detection['detection_rate']
        classification_accuracy = classification['accuracy_percent']

        issues = []
        successes = []

        # Check detection
        if detection_rate >= 95:
            successes.append("Excellent attack detection (≥95%)")
        elif detection_rate >= 80:
            successes.append("Good attack detection (≥80%)")
        else:
            issues.append(f"Low detection rate ({detection_rate:.1f}%) - investigate missed attacks")

        # Check classification
        if classification_accuracy >= 90:
            successes.append("Excellent classification accuracy (≥90%)")
        elif classification_accuracy >= 75:
            successes.append("Good classification accuracy (≥75%)")
        else:
            issues.append(f"Low classification accuracy ({classification_accuracy:.1f}%) - review thresholds")

        # Check attackers are penalized
        attacker_ratings = [
            rating_changes[as_num]
            for as_num in rating_changes
            if str(as_num) in attacker_ases
        ]

        if all(r['rating_change'] < -5 for r in attacker_ratings):
            successes.append("All attackers penalized (rating decreased)")
        else:
            issues.append("Some attackers not sufficiently penalized")

        # Check legitimate ASes protected
        legitimate_ratings = [
            rating_changes[as_num]
            for as_num in rating_changes
            if str(as_num) not in attacker_ases
        ]

        if all(r['classification'] in ["GREEN", "YELLOW"] for r in legitimate_ratings):
            successes.append("Legitimate ASes correctly classified")
        else:
            issues.append("Some legitimate ASes incorrectly flagged as malicious")

        # Display verdict
        if successes:
            print("   ✅ Successes:")
            for success in successes:
                print(f"      • {success}")
            print()

        if issues:
            print("   ⚠️  Issues to Address:")
            for issue in issues:
                print(f"      • {issue}")
            print()
        else:
            print("   🎉 NO ISSUES DETECTED - PERFECT EXPERIMENT!")
            print()

        # Final recommendation
        if not issues and detection_rate >= 95 and classification_accuracy >= 90:
            print("   🏆 RECOMMENDATION: System is working excellently!")
        elif len(issues) <= 1 and detection_rate >= 80:
            print("   👍 RECOMMENDATION: System is working well with minor improvements needed")
        else:
            print("   ⚠️  RECOMMENDATION: Review configuration and run additional experiments")

        print()
        print("=" * 80)


def main():
    """Main entry point"""
    print()

    # Find latest experiment
    project_root = Path(__file__).parent.parent.parent.parent.parent
    results_dir = project_root / "experiment_results"

    if not results_dir.exists():
        print("❌ No experiment results directory found!")
        print(f"   Expected: {results_dir}")
        return

    # Find all experiment directories
    experiment_dirs = [
        d for d in results_dir.iterdir()
        if d.is_dir() and d.name.startswith("attack_experiment_")
    ]

    if not experiment_dirs:
        print("❌ No experiment directories found!")
        print(f"   Run an experiment first: python3 run_attack_experiment.py")
        return

    # Sort by modification time (most recent first)
    experiment_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest = experiment_dirs[0]

    print(f"🔍 Analyzing latest experiment: {latest.name}")
    print()

    # Create analyzer
    analyzer = ExperimentAnalyzer(latest)

    # Generate report
    analyzer.generate_report()


if __name__ == "__main__":
    main()
