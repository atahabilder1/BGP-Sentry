#!/usr/bin/env python3
"""
=============================================================================
Rating Results Viewer - View Non-RPKI Rating Evolution
=============================================================================

Purpose: View and visualize non-RPKI AS ratings anytime
         - Display latest experiment results
         - Show current ratings for all non-RPKI nodes
         - Re-generate visualizations
         - Open dashboard images

Author: BGP-Sentry Team
=============================================================================
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add blockchain_utils to path
sys.path.insert(0, str(Path(__file__).parent))

from rating_visualization import RatingVisualization


class RatingResultsViewer:
    """
    View and visualize non-RPKI rating results.

    Shows current ratings and experiment visualizations.
    """

    def __init__(self):
        """Initialize results viewer"""
        self.project_root = Path(__file__).parent.parent.parent.parent.parent

        # Find experiment results directories
        self.results_dir = self.project_root / "experiment_results"

        # Rating files directory
        self.rating_files_dir = self.project_root / "nodes/rpki_nodes"

        print(f"📊 Rating Results Viewer Initialized")
        print(f"   Results Directory: {self.results_dir}")
        print()

    def find_latest_experiment(self) -> Optional[Path]:
        """Find the most recent experiment directory"""
        if not self.results_dir.exists():
            print(f"   ⚠️  No experiment results found")
            print(f"   Directory doesn't exist: {self.results_dir}")
            return None

        # Find all experiment directories
        experiment_dirs = [
            d for d in self.results_dir.iterdir()
            if d.is_dir() and d.name.startswith("attack_experiment_")
        ]

        if not experiment_dirs:
            print(f"   ⚠️  No experiment directories found")
            return None

        # Sort by modification time (most recent first)
        experiment_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        latest = experiment_dirs[0]
        print(f"✅ Found latest experiment:")
        print(f"   {latest.name}")
        print()

        return latest

    def show_current_ratings(self):
        """Show current ratings for all non-RPKI nodes"""
        print(f"{'='*80}")
        print(f"📊 CURRENT NON-RPKI AS RATINGS")
        print(f"{'='*80}\n")

        # Try to find rating file (check AS01)
        rating_file = (
            self.rating_files_dir /
            "as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json"
        )

        if not rating_file.exists():
            print(f"   ⚠️  No rating file found at:")
            print(f"   {rating_file}")
            print()
            print(f"   💡 Ratings are created when attacks are detected")
            print(f"   Run the experiment first: python3 run_attack_experiment.py")
            return

        try:
            with open(rating_file, 'r') as f:
                rating_data = json.load(f)

            as_ratings = rating_data.get("as_ratings", {})

            if not as_ratings:
                print(f"   ℹ️  No non-RPKI ASes have been rated yet")
                return

            # Display ratings table
            print(f"{'AS Number':<15} {'Rating':<10} {'Level':<15} {'Attacks':<10} {'Last Updated':<20}")
            print(f"{'-'*70}")

            for as_num, as_info in sorted(as_ratings.items(), key=lambda x: int(x[0])):
                rating = as_info.get("trust_score", 50)
                level = as_info.get("rating_level", "neutral")
                attacks = as_info.get("attacks_detected", 0)
                last_updated = as_info.get("last_updated", "N/A")

                # Color code the level
                if last_updated != "N/A":
                    last_updated = datetime.fromisoformat(last_updated).strftime("%Y-%m-%d %H:%M:%S")

                # Add emoji based on level
                emoji_map = {
                    "excellent": "🟢",
                    "good": "🟢",
                    "neutral": "⚪",
                    "suspicious": "🟡",
                    "bad": "🔴",
                    "critical": "🔴"
                }
                emoji = emoji_map.get(level, "⚪")

                print(f"AS{as_num:<13} {rating:<10.1f} {emoji} {level:<13} {attacks:<10} {last_updated:<20}")

            print()
            print(f"📊 Total non-RPKI ASes rated: {len(as_ratings)}")
            print()

            # Show rating distribution
            self._show_rating_distribution(as_ratings)

        except Exception as e:
            print(f"   ❌ Error reading rating file: {e}")

    def _show_rating_distribution(self, as_ratings: Dict):
        """Show rating level distribution"""
        distribution = {}

        for as_info in as_ratings.values():
            level = as_info.get("rating_level", "neutral")
            distribution[level] = distribution.get(level, 0) + 1

        print(f"📈 Rating Distribution:")
        for level, count in sorted(distribution.items()):
            bar = "█" * count
            print(f"   {level:<15} {bar} ({count})")
        print()

    def view_experiment_results(self):
        """View results from latest experiment"""
        print(f"{'='*80}")
        print(f"🔍 VIEWING EXPERIMENT RESULTS")
        print(f"{'='*80}\n")

        # Find latest experiment
        latest_exp = self.find_latest_experiment()

        if not latest_exp:
            print(f"   ⚠️  No experiments found")
            print(f"   Run an experiment first: python3 run_attack_experiment.py")
            return

        # List all files in experiment directory
        print(f"📁 Experiment Files:")
        files = sorted(latest_exp.iterdir())

        for file in files:
            size = file.stat().st_size / 1024  # KB
            modified = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            if file.suffix == '.png':
                print(f"   🖼️  {file.name:<40} {size:>8.1f} KB  {modified}")
            elif file.suffix == '.json':
                print(f"   📄 {file.name:<40} {size:>8.1f} KB  {modified}")
            else:
                print(f"   📋 {file.name:<40} {size:>8.1f} KB  {modified}")

        print()

        # Show which visualizations exist
        dashboard_file = latest_exp / "rating_dashboard.png"
        table_file = latest_exp / "rating_summary_table.png"
        pie_file = latest_exp / "classification_distribution.png"

        print(f"📊 Visualization Status:")
        print(f"   Rating Dashboard: {'✅ Available' if dashboard_file.exists() else '❌ Not found'}")
        print(f"   Summary Table: {'✅ Available' if table_file.exists() else '❌ Not found'}")
        print(f"   Classification Pie: {'✅ Available' if pie_file.exists() else '❌ Not found'}")
        print()

        # Show paths
        print(f"📂 File Locations:")
        if dashboard_file.exists():
            print(f"   Dashboard: {dashboard_file}")
        if table_file.exists():
            print(f"   Table: {table_file}")
        if pie_file.exists():
            print(f"   Pie Chart: {pie_file}")
        print()

        # Offer to open files
        print(f"💡 To view visualizations, use one of these methods:")
        print(f"   1. File manager: Open {latest_exp}")
        print(f"   2. Command line: xdg-open {dashboard_file if dashboard_file.exists() else latest_exp}")
        print(f"   3. Image viewer: eog {dashboard_file if dashboard_file.exists() else ''}")
        print()

    def regenerate_visualizations(self):
        """Re-generate visualizations from existing data"""
        print(f"{'='*80}")
        print(f"🔄 REGENERATING VISUALIZATIONS")
        print(f"{'='*80}\n")

        # Find latest experiment
        latest_exp = self.find_latest_experiment()

        if not latest_exp:
            return

        # Check if monitoring data exists
        viz_data_file = latest_exp / "rating_monitoring_data.json"

        if not viz_data_file.exists():
            print(f"   ❌ No monitoring data found")
            print(f"   Expected: {viz_data_file}")
            return

        print(f"   📊 Found monitoring data: {viz_data_file.name}")
        print()

        # Initialize visualization
        viz = RatingVisualization(str(viz_data_file))

        # Create dashboard
        print(f"   🎨 Creating 8-plot dashboard...")
        dashboard_file = str(latest_exp / "rating_dashboard.png")
        viz.create_dashboard(output_file=dashboard_file, show_plot=False)

        # Create summary table
        print(f"   📊 Creating summary table...")
        table_file = str(latest_exp / "rating_summary_table.png")
        viz.create_summary_table(output_file=table_file)

        # Create pie chart
        print(f"   📈 Creating classification pie chart...")
        pie_file = str(latest_exp / "classification_distribution.png")
        viz.create_classification_pie_chart(output_file=pie_file)

        print(f"\n   ✅ Visualizations regenerated!")
        print(f"   📁 Saved to: {latest_exp}")
        print()

    def show_performance_report(self):
        """Show blockchain performance metrics"""
        print(f"{'='*80}")
        print(f"⚡ BLOCKCHAIN PERFORMANCE METRICS")
        print(f"{'='*80}\n")

        # Find latest experiment
        latest_exp = self.find_latest_experiment()

        if not latest_exp:
            return

        # Check if performance report exists
        perf_file = latest_exp / "blockchain_performance_report.json"

        if not perf_file.exists():
            print(f"   ⚠️  No performance report found")
            print(f"   Expected: {perf_file}")
            return

        try:
            with open(perf_file, 'r') as f:
                perf_data = json.load(f)

            metrics = perf_data.get("metrics", {})

            if not metrics:
                print(f"   ⚠️  No metrics in report")
                return

            # Display metrics
            print(f"📊 Performance Summary:")
            print(f"   Duration: {metrics.get('duration_minutes', 0):.2f} minutes")
            print(f"   Total Transactions: {metrics.get('total_transactions', 0)}")
            print(f"   Total Blocks: {metrics.get('total_blocks', 0)}")
            print()

            print(f"⚡ Transaction Performance:")
            print(f"   Average TPS: {metrics.get('average_tps', 0):.2f} transactions/second")
            print(f"   Peak TPS: {metrics.get('peak_tps', 0):.2f} transactions/second")
            print(f"   Avg Tx/Block: {metrics.get('average_tx_per_block', 0):.2f}")
            print()

            print(f"📦 Block Performance:")
            print(f"   Block Rate: {metrics.get('average_blocks_per_minute', 0):.2f} blocks/minute")
            print()

            print(f"📈 Network Throughput:")
            print(f"   Throughput: {metrics.get('throughput_kb_per_second', 0):.2f} KB/s")
            print(f"   Throughput: {metrics.get('throughput_mb_per_second', 0):.4f} MB/s")
            print()

            # Performance classification
            avg_tps = metrics.get('average_tps', 0)
            if avg_tps >= 100:
                print(f"   ✅ Performance: EXCELLENT (>100 TPS)")
            elif avg_tps >= 50:
                print(f"   ✅ Performance: GOOD (50-100 TPS)")
            elif avg_tps >= 10:
                print(f"   🟡 Performance: MODERATE (10-50 TPS)")
            elif avg_tps >= 1:
                print(f"   🟡 Performance: LOW (1-10 TPS)")
            else:
                print(f"   🔴 Performance: VERY LOW (<1 TPS)")
            print()

        except Exception as e:
            print(f"   ❌ Error reading performance report: {e}")

    def run_analysis(self):
        """Run automated experiment analysis"""
        print(f"{'='*80}")
        print(f"🔬 RUNNING AUTOMATED ANALYSIS")
        print(f"{'='*80}\n")

        # Path to analysis script
        analysis_script = Path(__file__).parent / "analyze_experiment.py"

        if not analysis_script.exists():
            print(f"   ❌ Analysis script not found at: {analysis_script}")
            return

        print(f"   📊 Launching automated analysis...\n")

        try:
            # Run the analysis script
            result = subprocess.run(
                [sys.executable, str(analysis_script)],
                capture_output=False,
                text=True
            )

            if result.returncode != 0:
                print(f"\n   ⚠️  Analysis completed with warnings")
            else:
                print(f"\n   ✅ Analysis complete!")

        except Exception as e:
            print(f"   ❌ Error running analysis: {e}")

    def interactive_menu(self):
        """Show interactive menu"""
        while True:
            print(f"\n{'='*80}")
            print(f"📊 RATING RESULTS VIEWER - MENU")
            print(f"{'='*80}\n")

            print(f"1. Show current non-RPKI ratings")
            print(f"2. View latest experiment results")
            print(f"3. Regenerate visualizations")
            print(f"4. Show blockchain performance")
            print(f"5. Run automated analysis (Detection + Classification + Performance)")
            print(f"6. Exit")
            print()

            choice = input("Select option (1-6): ").strip()

            if choice == "1":
                self.show_current_ratings()
            elif choice == "2":
                self.view_experiment_results()
            elif choice == "3":
                self.regenerate_visualizations()
            elif choice == "4":
                self.show_performance_report()
            elif choice == "5":
                self.run_analysis()
            elif choice == "6":
                print(f"\n👋 Goodbye!")
                break
            else:
                print(f"\n❌ Invalid choice. Please select 1-6.")

            input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    print(f"\n{'='*80}")
    print(f"📊 NON-RPKI RATING RESULTS VIEWER")
    print(f"{'='*80}\n")

    viewer = RatingResultsViewer()

    # Check if we have any data to show
    latest_exp = viewer.find_latest_experiment()

    if latest_exp:
        print(f"✅ Experiment results available!")
        print()

    # Show interactive menu
    viewer.interactive_menu()


if __name__ == "__main__":
    main()
