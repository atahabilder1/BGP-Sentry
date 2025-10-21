#!/usr/bin/env python3
"""
=============================================================================
Attack Experiment Runner - Complete Attack Detection Experiment
=============================================================================

Purpose: Run complete attack detection experiment:
         1. Inject 20 attacks (12 to AS666, 8 to AS31337)
         2. Monitor rating changes in real-time
         3. Generate post-hoc analysis and visualizations
         4. Calculate detection rates and accuracy

Usage:
    python run_attack_experiment.py

Output:
    - Attack scenarios file
    - Rating monitoring data
    - 8-plot dashboard (rating evolution)
    - Summary table
    - Classification distribution
    - Detection accuracy report

Author: BGP-Sentry Team
=============================================================================
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add blockchain_utils to path
sys.path.insert(0, str(Path(__file__).parent))

from attack_injection_system import AttackInjectionSystem
from rating_monitor import RatingMonitor
from rating_visualization import RatingVisualization
from blockchain_performance_monitor import BlockchainPerformanceMonitor
from live_rating_monitor import LiveRatingMonitor


class AttackExperimentRunner:
    """
    Orchestrates complete attack detection experiment.

    Workflow:
    1. Inject attacks
    2. Monitor ratings
    3. Generate analysis
    4. Create visualizations
    """

    def __init__(self):
        """Initialize experiment runner"""
        self.project_root = Path(__file__).parent.parent.parent.parent.parent

        # Output directory
        self.output_dir = (
            self.project_root /
            "experiment_results" /
            f"attack_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🧪 Attack Experiment Runner Initialized")
        print(f"   Output Directory: {self.output_dir}")
        print()

    def run_complete_experiment(self,
                                attacker_ases: list = None,
                                monitor_duration: int = 300,
                                monitor_interval: int = 10,
                                enable_live_visualization: bool = True):
        """
        Run complete attack detection experiment.

        Args:
            attacker_ases: List of (as_number, attack_count) tuples
            monitor_duration: How long to monitor (seconds)
            monitor_interval: Snapshot interval (seconds)
            enable_live_visualization: Show live plot during monitoring
        """
        if attacker_ases is None:
            # Default: 12 attacks to AS666, 8 to AS31337
            attacker_ases = [(666, 12), (31337, 8)]

        print(f"{'='*80}")
        print(f"🧪 ATTACK DETECTION EXPERIMENT")
        print(f"{'='*80}\n")

        # =================================================================
        # STEP 1: Attack Injection
        # =================================================================
        print(f"{'='*80}")
        print(f"STEP 1: ATTACK INJECTION")
        print(f"{'='*80}\n")

        injector = AttackInjectionSystem(str(self.project_root))

        attack_results = injector.inject_attack_scenarios(attacker_ases)

        # Save attack scenarios to experiment folder
        attack_file = self.output_dir / "attack_scenarios.json"
        with open(attack_file, 'w') as f:
            json.dump(attack_results, f, indent=2)

        print(f"\n✅ Attack scenarios saved to: {attack_file}")

        # Extract attacker AS numbers for monitoring
        attacker_as_numbers = [as_num for as_num, _ in attacker_ases]

        # =================================================================
        # STEP 2: Rating Monitoring
        # =================================================================
        print(f"\n{'='*80}")
        print(f"STEP 2: RATING MONITORING")
        print(f"{'='*80}\n")

        print(f"⚠️  NOTE: You should now run your BGP-Sentry simulation!")
        print(f"   The simulation will detect attacks and update ratings.")
        print()
        print(f"   While simulation runs, this monitor will track ratings.")
        print()

        response = input("   Start monitoring? (y/n): ").lower().strip()

        if response != 'y':
            print("   ⚠️  Monitoring skipped")
            return

        # Initialize monitors
        rating_monitor = RatingMonitor(str(self.project_root))
        rating_monitor.start_monitoring(attacker_as_numbers)

        perf_monitor = BlockchainPerformanceMonitor(str(self.project_root))
        perf_monitor.start_monitoring()

        # Initialize live visualization if enabled
        live_monitor = None
        if enable_live_visualization:
            print(f"\n   🎨 Initializing live visualization window...")
            try:
                live_monitor = LiveRatingMonitor(attacker_as_numbers, str(self.project_root))
                live_monitor.update_detection(0, attack_results["total_attacks"])
                print(f"   ✅ Live visualization window opened!")
                print(f"   💡 Ratings will update every {monitor_interval} seconds")
            except Exception as e:
                print(f"   ⚠️  Live visualization disabled: {e}")
                live_monitor = None

        print(f"\n   ⚡ Rating and performance monitoring active!")
        print()

        # Run monitoring loop (both monitors in parallel)
        print(f"   📊 Collecting samples for {monitor_duration/60:.1f} minutes...")
        import time
        start_time = time.time()
        sample_count = 0

        while (time.time() - start_time) < monitor_duration:
            # Take rating snapshot
            rating_monitor.take_snapshot(f"Sample #{sample_count + 1}")

            # Take performance sample
            perf_monitor.take_periodic_sample()

            sample_count += 1
            elapsed = time.time() - start_time

            # Update live visualization if enabled
            if live_monitor:
                try:
                    # Update rating data for each AS
                    for as_num in attacker_as_numbers:
                        current_rating = rating_monitor._get_current_rating(as_num)
                        attacks_detected = rating_monitor._get_attack_count(as_num)
                        live_monitor.update_rating(
                            as_num,
                            current_rating.get("score", 50),
                            attacks_detected,
                            datetime.now()
                        )

                    # Update performance data
                    current_snapshot = perf_monitor._take_snapshot()
                    if current_snapshot:
                        tps = current_snapshot.get("tps_instant", 0)
                        total_tx = current_snapshot.get("total_transactions", 0)
                        total_blocks = current_snapshot.get("total_blocks", 0)
                        live_monitor.update_performance(tps, total_tx, total_blocks, elapsed)

                    # Update detection metrics
                    total_detected = sum(
                        rating_monitor._get_attack_count(as_num)
                        for as_num in attacker_as_numbers
                    )
                    live_monitor.update_detection(total_detected, attack_results["total_attacks"])

                    # Refresh the plot
                    live_monitor.refresh_plot()

                except Exception as e:
                    print(f"   ⚠️  Live visualization update error: {e}")

            # Display progress
            remaining = monitor_duration - elapsed
            print(f"   ⏱️  Sample #{sample_count} | Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")

            # Wait for next interval
            time.sleep(monitor_interval)

        print(f"\n   ✅ Monitoring complete! {sample_count} samples collected")

        # Keep live visualization open if enabled
        if live_monitor:
            print(f"\n   💡 Keeping live visualization window open...")
            print(f"   You can review the final state before proceeding.")
            input(f"   Press Enter to continue with post-processing...")
            live_monitor.close()

        # Stop performance monitoring and get metrics
        perf_metrics = perf_monitor.stop_monitoring()

        # Export performance report
        perf_report_file = perf_monitor.export_performance_report(
            str(self.output_dir / "blockchain_performance_report.json")
        )

        # Export rating monitoring data
        viz_data_file = rating_monitor.export_for_visualization(
            str(self.output_dir / "rating_monitoring_data.json")
        )

        print(f"\n✅ Monitoring data saved:")
        print(f"   Rating Data: {viz_data_file}")
        print(f"   Performance Data: {perf_report_file}")

        # =================================================================
        # STEP 3: Visualization & Analysis
        # =================================================================
        print(f"\n{'='*80}")
        print(f"STEP 3: VISUALIZATION & ANALYSIS")
        print(f"{'='*80}\n")

        # Initialize visualization
        viz = RatingVisualization(viz_data_file)

        # Create dashboard (8-plot)
        dashboard_file = str(self.output_dir / "rating_dashboard.png")
        viz.create_dashboard(output_file=dashboard_file, show_plot=False)

        # Create summary table
        table_file = str(self.output_dir / "rating_summary_table.png")
        viz.create_summary_table(output_file=table_file)

        # Create classification pie chart
        pie_file = str(self.output_dir / "classification_distribution.png")
        viz.create_classification_pie_chart(output_file=pie_file)

        # =================================================================
        # STEP 4: Detection Accuracy Report
        # =================================================================
        print(f"\n{'='*80}")
        print(f"STEP 4: DETECTION ACCURACY ANALYSIS")
        print(f"{'='*80}\n")

        accuracy_report = self._generate_detection_report(
            attack_results,
            viz.data
        )

        # Save report
        report_file = self.output_dir / "detection_accuracy_report.json"
        with open(report_file, 'w') as f:
            json.dump(accuracy_report, f, indent=2)

        # Print report summary
        self._print_report_summary(accuracy_report)

        # =================================================================
        # EXPERIMENT COMPLETE
        # =================================================================
        print(f"\n{'='*80}")
        print(f"🎉 EXPERIMENT COMPLETE!")
        print(f"{'='*80}\n")

        print(f"📁 Results Directory: {self.output_dir}")
        print(f"\n📊 Generated Files:")
        print(f"   1. Attack scenarios: attack_scenarios.json")
        print(f"   2. Rating monitoring data: rating_monitoring_data.json")
        print(f"   3. Blockchain performance: blockchain_performance_report.json")
        print(f"   4. Rating dashboard: rating_dashboard.png")
        print(f"   5. Summary table: rating_summary_table.png")
        print(f"   6. Classification pie: classification_distribution.png")
        print(f"   7. Detection report: detection_accuracy_report.json")
        print()

        # Display performance summary
        if perf_metrics and "average_tps" in perf_metrics:
            print(f"⚡ Blockchain Performance Summary:")
            print(f"   Average TPS: {perf_metrics['average_tps']:.2f} transactions/second")
            print(f"   Peak TPS: {perf_metrics['peak_tps']:.2f} transactions/second")
            print(f"   Total Transactions: {perf_metrics['total_transactions']}")
            print(f"   Total Blocks: {perf_metrics['total_blocks']}")
            print(f"   Throughput: {perf_metrics['throughput_kb_per_second']:.2f} KB/s")
            print()

    def _generate_detection_report(self, attack_results: dict, monitoring_data: dict) -> dict:
        """Generate detection accuracy report"""
        print(f"   📊 Analyzing detection accuracy...")

        if not monitoring_data or not monitoring_data.get("summary"):
            print(f"   ⚠️  No monitoring data available")
            return {"error": "No monitoring data"}

        report = {
            "experiment_timestamp": datetime.now().isoformat(),
            "total_attacks_injected": attack_results["total_attacks"],
            "attackers": [],
            "overall_metrics": {}
        }

        # Analyze each attacker
        total_rating_drop = 0
        total_attacks = 0

        for as_num, attack_data in attack_results["attackers"].items():
            as_num_int = int(as_num) if isinstance(as_num, str) else as_num

            # Get monitoring data for this AS
            as_summary = monitoring_data["summary"].get(str(as_num_int))

            if as_summary:
                rating_change = as_summary["rating_change"]
                final_rating = as_summary["final_rating"]
                attacks_injected = attack_data["total_attacks"]

                # Calculate detection metrics
                expected_drop = attacks_injected * -5  # Rough estimate
                actual_drop = rating_change

                detection_efficiency = (actual_drop / expected_drop * 100) if expected_drop != 0 else 0

                as_report = {
                    "as_number": as_num_int,
                    "attacks_injected": attacks_injected,
                    "attack_types": attack_data["attack_breakdown"],
                    "initial_rating": as_summary["initial_rating"],
                    "final_rating": final_rating,
                    "rating_change": rating_change,
                    "expected_drop": expected_drop,
                    "detection_efficiency": f"{min(detection_efficiency, 100):.1f}%",
                    "final_classification": self._get_classification(final_rating)
                }

                report["attackers"].append(as_report)

                total_rating_drop += abs(rating_change)
                total_attacks += attacks_injected

        # Overall metrics
        if total_attacks > 0:
            avg_rating_drop_per_attack = total_rating_drop / total_attacks

            report["overall_metrics"] = {
                "total_attacks": total_attacks,
                "average_rating_drop_per_attack": f"{avg_rating_drop_per_attack:.2f}",
                "attackers_count": len(report["attackers"]),
                "experiment_status": "Completed Successfully"
            }

        return report

    def _get_classification(self, rating: float) -> str:
        """Get classification label"""
        if rating <= 40:
            return "RED (Malicious)"
        elif rating <= 70:
            return "YELLOW (Suspicious)"
        else:
            return "GREEN (Trustworthy)"

    def _print_report_summary(self, report: dict):
        """Print detection report summary"""
        print(f"\n   📊 Detection Accuracy Report Summary:")
        print(f"   {'='*60}")

        if "error" in report:
            print(f"   ❌ Error: {report['error']}")
            return

        print(f"\n   Overall Metrics:")
        metrics = report["overall_metrics"]
        print(f"      Total Attacks Injected: {metrics['total_attacks']}")
        print(f"      Average Rating Drop: {metrics['average_rating_drop_per_attack']}")
        print(f"      Number of Attackers: {metrics['attackers_count']}")

        print(f"\n   Per-Attacker Analysis:")
        print(f"      {'AS':<10} {'Attacks':<10} {'Rating Δ':<12} {'Final':<10} {'Classification':<20}")
        print(f"      {'-'*62}")

        for attacker in report["attackers"]:
            print(f"      AS{attacker['as_number']:<8} "
                  f"{attacker['attacks_injected']:<10} "
                  f"{attacker['rating_change']:<12.1f} "
                  f"{attacker['final_rating']:<10.1f} "
                  f"{attacker['final_classification']:<20}")

        print()


def main():
    """Main entry point"""
    print(f"\n{'='*80}")
    print(f"🧪 BGP-SENTRY ATTACK DETECTION EXPERIMENT")
    print(f"{'='*80}\n")

    print(f"This experiment will:")
    print(f"   1. Inject 20 attack scenarios (12 to AS666, 8 to AS31337)")
    print(f"   2. Monitor rating changes during simulation")
    print(f"   3. Show LIVE visualization of rating changes (real-time plot)")
    print(f"   4. Track blockchain performance (TPS, throughput)")
    print(f"   5. Generate visualizations and analysis")
    print(f"   6. Calculate detection accuracy")
    print()

    response = input(f"Continue? (y/n): ").lower().strip()

    if response != 'y':
        print("Experiment cancelled.")
        return

    # Live visualization info
    print()
    print(f"💡 TIP: To watch live ratings in real-time:")
    print(f"   Open another terminal and run:")
    print(f"   python3 watch_ratings_live.py")
    print()

    enable_live = False  # Disabled by default - use standalone viewer

    # Run experiment
    runner = AttackExperimentRunner()

    runner.run_complete_experiment(
        attacker_ases=[(666, 12), (31337, 8)],
        monitor_duration=300,   # 5 minutes
        monitor_interval=10,     # 10 second snapshots
        enable_live_visualization=enable_live
    )


if __name__ == "__main__":
    main()
