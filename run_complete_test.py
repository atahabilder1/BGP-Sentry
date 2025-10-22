#!/usr/bin/env python3
"""
=============================================================================
Complete Attack Detection Test - All-in-One
=============================================================================

Purpose: Start everything, run test, analyze results
         Just run: python3 run_complete_test.py

Author: BGP-Sentry Team
=============================================================================
"""

import sys
import subprocess
import time
from pathlib import Path
import signal
import os


class CompleteTestRunner:
    """Run complete test with automatic setup and teardown"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.blockchain_processes = []
        self.simulation_process = None

    def start_blockchain_nodes(self):
        """Start all 9 RPKI blockchain nodes"""
        print("=" * 80)
        print("🚀 STARTING BLOCKCHAIN NODES")
        print("=" * 80)
        print()

        nodes_dir = self.project_root / "nodes/rpki_nodes"
        rpki_nodes = ["as01", "as03", "as05", "as07", "as09", "as11", "as13", "as15", "as17"]

        for node in rpki_nodes:
            # Try different possible script names
            node_dir = nodes_dir / node / "blockchain_node"

            possible_scripts = [
                node_dir / "node.py",
                node_dir / "blockchain_node.py",
                node_dir / "start_node.py"
            ]

            node_script = None
            for script in possible_scripts:
                if script.exists():
                    node_script = script
                    break

            if not node_script:
                print(f"⚠️  {node}: No blockchain script found in {node_dir}")
                continue

            print(f"   Starting {node}...", end=" ")

            try:
                # Start node in background
                process = subprocess.Popen(
                    [sys.executable, str(node_script)],
                    cwd=str(node_script.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                self.blockchain_processes.append((node, process))
                print(f"✅ PID {process.pid}")

            except Exception as e:
                print(f"❌ Failed: {e}")

        print()
        print(f"✅ Started {len(self.blockchain_processes)} blockchain nodes")
        print()

    def start_bgp_simulation(self):
        """Start BGP announcement simulation"""
        print("=" * 80)
        print("🌐 STARTING BGP SIMULATION")
        print("=" * 80)
        print()

        # Look for BGP simulation script
        possible_scripts = [
            self.project_root / "start_bgp_simulation.py",
            self.project_root / "simulation" / "bgp_simulator.py",
            self.project_root / "bgp_simulation.py",
        ]

        simulation_script = None
        for script in possible_scripts:
            if script.exists():
                simulation_script = script
                break

        if not simulation_script:
            print("⚠️  No BGP simulation script found")
            print("   Skipping BGP simulation (you may need to start it manually)")
            print()
            return

        print(f"   Starting BGP simulation: {simulation_script.name}...", end=" ")

        try:
            self.simulation_process = subprocess.Popen(
                [sys.executable, str(simulation_script)],
                cwd=str(simulation_script.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print(f"✅ PID {self.simulation_process.pid}")
            print()

        except Exception as e:
            print(f"❌ Failed: {e}")
            print()

    def wait_for_blockchain_ready(self, timeout=30):
        """Wait for blockchain to start processing"""
        print("=" * 80)
        print("⏳ WAITING FOR BLOCKCHAIN TO BE READY")
        print("=" * 80)
        print()

        blocks_dir = self.project_root / "nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks"

        print(f"   Waiting for blockchain activity (max {timeout}s)...")

        if not blocks_dir.exists():
            print(f"   Creating blocks directory...")
            blocks_dir.mkdir(parents=True, exist_ok=True)

        # Count initial blocks
        initial_blocks = len(list(blocks_dir.glob("block_*.json"))) if blocks_dir.exists() else 0

        # Wait for new blocks
        for i in range(timeout):
            time.sleep(1)

            if blocks_dir.exists():
                current_blocks = len(list(blocks_dir.glob("block_*.json")))

                if current_blocks > initial_blocks:
                    print(f"   ✅ Blockchain is active! ({current_blocks} blocks)")
                    print()
                    return True

            if i % 5 == 0 and i > 0:
                print(f"   Still waiting... ({i}/{timeout}s)")

        print(f"   ⚠️  Blockchain may not be fully active yet")
        print(f"   Continuing anyway...")
        print()
        return False

    def run_attack_experiment(self):
        """Run the attack detection experiment"""
        print("=" * 80)
        print("🧪 RUNNING ATTACK EXPERIMENT")
        print("=" * 80)
        print()

        test_script = self.project_root / "test_attack_detection.py"

        # Run test (will be interactive)
        subprocess.run([sys.executable, str(test_script)])

    def cleanup(self):
        """Stop all processes"""
        print()
        print("=" * 80)
        print("🛑 CLEANUP - STOPPING ALL PROCESSES")
        print("=" * 80)
        print()

        # Stop blockchain nodes
        for node, process in self.blockchain_processes:
            if process.poll() is None:  # Still running
                print(f"   Stopping {node} (PID {process.pid})...", end=" ")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print("✅")
                except:
                    process.kill()
                    print("⚠️ Forced")

        # Stop BGP simulation
        if self.simulation_process and self.simulation_process.poll() is None:
            print(f"   Stopping BGP simulation (PID {self.simulation_process.pid})...", end=" ")
            try:
                self.simulation_process.terminate()
                self.simulation_process.wait(timeout=5)
                print("✅")
            except:
                self.simulation_process.kill()
                print("⚠️ Forced")

        print()
        print("✅ Cleanup complete")
        print()

    def initialize_ratings(self):
        """Initialize non-RPKI AS ratings (80-85 range)"""
        print("=" * 80)
        print("🎲 INITIALIZING NON-RPKI RATINGS")
        print("=" * 80)
        print()

        init_script = self.project_root / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/initialize_ratings.py"

        if not init_script.exists():
            print("⚠️  Rating initialization script not found")
            print("   Skipping initialization...")
            print()
            return

        print("   Setting all non-RPKI ASes to random ratings (80-85)...")
        print()

        try:
            # Run initialization non-interactively
            result = subprocess.run(
                [sys.executable, str(init_script)],
                input=b'y\n',  # Auto-confirm
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(init_script.parent)
            )

            if result.returncode == 0:
                print("   ✅ Ratings initialized successfully")
            else:
                print("   ⚠️  Initialization may have issues")

        except Exception as e:
            print(f"   ⚠️  Error: {e}")

        print()

    def run(self):
        """Run complete test"""
        try:
            print()
            print("=" * 80)
            print("🎯 COMPLETE ATTACK DETECTION TEST - ALL-IN-ONE")
            print("=" * 80)
            print()
            print("This will:")
            print("   1. Initialize non-RPKI ratings (random 80-85)")
            print("   2. Start all 9 blockchain nodes")
            print("   3. Start BGP simulation (if found)")
            print("   4. Wait for blockchain to be ready")
            print("   5. Run attack detection experiment")
            print("   6. Clean up and stop all processes")
            print()

            response = input("Continue? (y/n): ").lower().strip()

            if response != 'y':
                print("Test cancelled.")
                return 0

            # Initialize ratings
            self.initialize_ratings()

            # Start blockchain
            self.start_blockchain_nodes()

            if not self.blockchain_processes:
                print("❌ Failed to start any blockchain nodes!")
                print("   Check that blockchain_node.py exists in each node directory")
                return 1

            # Start BGP simulation
            self.start_bgp_simulation()

            # Wait for blockchain to be ready
            self.wait_for_blockchain_ready(timeout=30)

            # Run experiment
            self.run_attack_experiment()

            # Cleanup
            self.cleanup()

            print("=" * 80)
            print("🎉 COMPLETE TEST FINISHED")
            print("=" * 80)
            print()

            return 0

        except KeyboardInterrupt:
            print()
            print()
            print("⚠️  Test interrupted by user")
            self.cleanup()
            return 1

        except Exception as e:
            print()
            print(f"❌ Error: {e}")
            self.cleanup()
            return 1


def main():
    """Main entry point"""
    runner = CompleteTestRunner()
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
