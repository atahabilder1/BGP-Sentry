#!/usr/bin/env python3
"""
=============================================================================
Complete Attack Detection Test - One-Click Experiment
=============================================================================

Purpose: Run complete attack detection experiment and analysis from anywhere
         Just run: python3 test_attack_detection.py

Author: BGP-Sentry Team
=============================================================================
"""

import sys
import subprocess
from pathlib import Path
import time


def main():
    """Run complete attack detection test"""

    # Get project root
    project_root = Path(__file__).parent
    utils_dir = project_root / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"

    print("=" * 80)
    print("🧪 BGP-SENTRY ATTACK DETECTION TEST")
    print("=" * 80)
    print()
    print(f"Project Root: {project_root}")
    print(f"Utils Directory: {utils_dir}")
    print()

    # Check directory exists
    if not utils_dir.exists():
        print(f"❌ Error: Utils directory not found!")
        print(f"   Expected: {utils_dir}")
        return 1

    print("📋 This will:")
    print("   1. Inject 20 attack scenarios (12 to AS666, 8 to AS31337)")
    print("   2. Monitor rating changes for 5 minutes")
    print("   3. Measure blockchain performance (TPS)")
    print("   4. Generate visualizations (8-plot dashboard)")
    print("   5. Analyze detection accuracy")
    print("   6. Display complete results")
    print()
    print("💡 TIP: Open another terminal and run:")
    print("   cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils")
    print("   python3 watch_ratings_live.py")
    print("   (This shows live visualization during the experiment)")
    print()

    response = input("Continue? (y/n): ").lower().strip()

    if response != 'y':
        print("Test cancelled.")
        return 0

    # =================================================================
    # STEP 1: Run Attack Experiment
    # =================================================================
    print()
    print("=" * 80)
    print("STEP 1: RUNNING ATTACK EXPERIMENT")
    print("=" * 80)
    print()

    experiment_script = utils_dir / "run_attack_experiment.py"

    try:
        result = subprocess.run(
            [sys.executable, str(experiment_script)],
            cwd=str(utils_dir)
        )

        if result.returncode != 0:
            print()
            print("⚠️  Experiment completed with warnings")
            print()

    except Exception as e:
        print(f"❌ Error running experiment: {e}")
        return 1

    # =================================================================
    # STEP 2: Analyze Results
    # =================================================================
    print()
    print("=" * 80)
    print("STEP 2: ANALYZING RESULTS")
    print("=" * 80)
    print()

    analysis_script = utils_dir / "analyze_experiment.py"

    if analysis_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(analysis_script)],
                cwd=str(utils_dir)
            )
        except Exception as e:
            print(f"⚠️  Error running analysis: {e}")
    else:
        print("⚠️  Analysis script not found, skipping analysis")

    # =================================================================
    # STEP 3: Show Visualization Options
    # =================================================================
    print()
    print("=" * 80)
    print("STEP 3: VIEW RESULTS")
    print("=" * 80)
    print()

    results_dir = project_root / "experiment_results"

    if results_dir.exists():
        # Find latest experiment
        experiment_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("attack_experiment_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if experiment_dirs:
            latest = experiment_dirs[0]

            print(f"📁 Results Directory: {latest}")
            print()

            dashboard = latest / "rating_dashboard.png"
            table = latest / "rating_summary_table.png"
            pie = latest / "classification_distribution.png"

            print("📊 Generated Files:")
            if dashboard.exists():
                print(f"   ✅ Rating Dashboard: {dashboard}")
            if table.exists():
                print(f"   ✅ Summary Table: {table}")
            if pie.exists():
                print(f"   ✅ Classification Pie: {pie}")

            print()
            print("💡 To view visualizations:")
            print(f"   eog {dashboard}")
            print()
            print("   Or use the interactive viewer:")
            print("   cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils")
            print("   python3 view_rating_results.py")
            print()

            # Ask to open dashboard
            response = input("Open rating dashboard now? (y/n): ").lower().strip()

            if response == 'y' and dashboard.exists():
                try:
                    subprocess.Popen(['eog', str(dashboard)])
                    print("✅ Dashboard opened!")
                except:
                    subprocess.Popen(['xdg-open', str(dashboard)])
                    print("✅ Dashboard opened!")

    # =================================================================
    # COMPLETE
    # =================================================================
    print()
    print("=" * 80)
    print("🎉 ATTACK DETECTION TEST COMPLETE!")
    print("=" * 80)
    print()
    print("📚 Quick Commands:")
    print()
    print("   # Analyze again")
    print("   cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils")
    print("   python3 analyze_experiment.py")
    print()
    print("   # View results interactively")
    print("   python3 view_rating_results.py")
    print()
    print("   # View dashboard")
    print("   eog experiment_results/attack_experiment_*/rating_dashboard.png")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
