#!/usr/bin/env python3
"""
=============================================================================
Blockchain Performance Monitor - TPS and Throughput Metrics
=============================================================================

Purpose: Measure blockchain performance metrics:
         - Transactions Per Second (TPS)
         - Block creation rate
         - Consensus time
         - Network throughput
         - Transaction latency

Features:
- Real-time TPS calculation
- Historical performance tracking
- Performance report generation
- Bottleneck identification

Author: BGP-Sentry Team
=============================================================================
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class BlockchainPerformanceMonitor:
    """
    Monitors blockchain performance metrics.

    Tracks TPS, block rate, consensus time, and throughput.
    """

    def __init__(self, project_root: str = None):
        """
        Initialize performance monitor.

        Args:
            project_root: Root directory of BGP-Sentry project
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect project root
            self.project_root = Path(__file__).parent.parent.parent.parent.parent

        # Blockchain data directories (check all RPKI nodes)
        self.blockchain_dirs = []
        self._discover_blockchain_dirs()

        # Performance data storage
        self.performance_data = {
            "monitoring_start": None,
            "monitoring_end": None,
            "duration_seconds": 0,
            "total_transactions": 0,
            "total_blocks": 0,
            "tps_samples": [],
            "block_times": [],
            "consensus_times": [],
            "metrics": {}
        }

        # Baseline snapshot
        self.baseline_snapshot = None

        print(f"⚡ Blockchain Performance Monitor Initialized")
        print(f"   Monitoring {len(self.blockchain_dirs)} RPKI nodes")

    def _discover_blockchain_dirs(self):
        """Discover blockchain directories for all RPKI nodes"""
        rpki_nodes_dir = self.project_root / "nodes/rpki_nodes"

        if not rpki_nodes_dir.exists():
            print(f"   ⚠️  RPKI nodes directory not found")
            return

        # Find all AS directories
        for as_dir in rpki_nodes_dir.iterdir():
            if as_dir.is_dir() and as_dir.name.startswith("as"):
                blockchain_dir = as_dir / "blockchain_node/blockchain_data/chain"

                if blockchain_dir.exists():
                    self.blockchain_dirs.append({
                        "as_number": int(as_dir.name[2:]),
                        "blockchain_path": blockchain_dir,
                        "blockchain_file": blockchain_dir / "blockchain.json"
                    })

        print(f"   📁 Found {len(self.blockchain_dirs)} blockchain directories")

    def start_monitoring(self):
        """Start performance monitoring - take baseline snapshot"""
        print(f"\n⚡ Starting Performance Monitoring...")

        self.performance_data["monitoring_start"] = datetime.now().isoformat()

        # Take baseline snapshot
        self.baseline_snapshot = self._take_snapshot()

        print(f"   ✅ Baseline captured:")
        print(f"      Total Transactions: {self.baseline_snapshot['total_transactions']}")
        print(f"      Total Blocks: {self.baseline_snapshot['total_blocks']}")
        print(f"      Timestamp: {self.baseline_snapshot['timestamp']}")

    def _take_snapshot(self) -> Dict:
        """Take snapshot of current blockchain state"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_transactions": 0,
            "total_blocks": 0,
            "per_node_stats": {}
        }

        # Collect from all nodes
        for node_info in self.blockchain_dirs:
            as_number = node_info["as_number"]
            blockchain_file = node_info["blockchain_file"]

            if not blockchain_file.exists():
                continue

            try:
                with open(blockchain_file, 'r') as f:
                    blockchain_data = json.load(f)

                blocks = blockchain_data.get("blocks", [])
                node_tx_count = 0

                # Count transactions in all blocks
                for block in blocks:
                    transactions = block.get("transactions", [])
                    node_tx_count += len(transactions)

                snapshot["per_node_stats"][as_number] = {
                    "blocks": len(blocks),
                    "transactions": node_tx_count
                }

                snapshot["total_blocks"] += len(blocks)
                snapshot["total_transactions"] += node_tx_count

            except Exception as e:
                print(f"   ⚠️  Error reading blockchain for AS{as_number}: {e}")

        return snapshot

    def take_periodic_sample(self):
        """Take periodic TPS sample"""
        current_snapshot = self._take_snapshot()

        if not self.baseline_snapshot:
            return

        # Calculate time elapsed
        baseline_time = datetime.fromisoformat(self.baseline_snapshot["timestamp"])
        current_time = datetime.fromisoformat(current_snapshot["timestamp"])
        elapsed_seconds = (current_time - baseline_time).total_seconds()

        if elapsed_seconds <= 0:
            return

        # Calculate TPS
        tx_diff = current_snapshot["total_transactions"] - self.baseline_snapshot["total_transactions"]
        tps = tx_diff / elapsed_seconds if elapsed_seconds > 0 else 0

        # Calculate block rate
        block_diff = current_snapshot["total_blocks"] - self.baseline_snapshot["total_blocks"]
        blocks_per_second = block_diff / elapsed_seconds if elapsed_seconds > 0 else 0

        # Record sample
        sample = {
            "timestamp": current_snapshot["timestamp"],
            "elapsed_seconds": elapsed_seconds,
            "transactions": tx_diff,
            "blocks": block_diff,
            "tps": tps,
            "blocks_per_second": blocks_per_second
        }

        self.performance_data["tps_samples"].append(sample)

    def stop_monitoring(self) -> Dict:
        """Stop monitoring and generate performance report"""
        print(f"\n⚡ Stopping Performance Monitoring...")

        self.performance_data["monitoring_end"] = datetime.now().isoformat()

        # Take final snapshot
        final_snapshot = self._take_snapshot()

        # Calculate overall metrics
        metrics = self._calculate_metrics(final_snapshot)

        self.performance_data["metrics"] = metrics

        # Display report
        self._display_performance_report(metrics)

        return metrics

    def _calculate_metrics(self, final_snapshot: Dict) -> Dict:
        """Calculate performance metrics"""
        if not self.baseline_snapshot:
            return {"error": "No baseline snapshot"}

        # Calculate time elapsed
        start_time = datetime.fromisoformat(self.performance_data["monitoring_start"])
        end_time = datetime.fromisoformat(self.performance_data["monitoring_end"])
        duration_seconds = (end_time - start_time).total_seconds()

        # Calculate transaction metrics
        total_tx = final_snapshot["total_transactions"] - self.baseline_snapshot["total_transactions"]
        total_blocks = final_snapshot["total_blocks"] - self.baseline_snapshot["total_blocks"]

        # Calculate TPS
        avg_tps = total_tx / duration_seconds if duration_seconds > 0 else 0

        # Calculate block rate
        avg_blocks_per_second = total_blocks / duration_seconds if duration_seconds > 0 else 0
        avg_blocks_per_minute = avg_blocks_per_second * 60

        # Calculate transactions per block
        avg_tx_per_block = total_tx / total_blocks if total_blocks > 0 else 0

        # Calculate peak TPS from samples
        peak_tps = 0
        if self.performance_data["tps_samples"]:
            peak_tps = max(sample["tps"] for sample in self.performance_data["tps_samples"])

        # Calculate throughput (approximate bytes/second)
        # Assume average transaction size ~500 bytes
        avg_tx_size_bytes = 500
        throughput_bytes_per_second = avg_tps * avg_tx_size_bytes
        throughput_kb_per_second = throughput_bytes_per_second / 1024
        throughput_mb_per_second = throughput_kb_per_second / 1024

        metrics = {
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_seconds / 60,
            "total_transactions": total_tx,
            "total_blocks": total_blocks,
            "average_tps": round(avg_tps, 2),
            "peak_tps": round(peak_tps, 2),
            "average_blocks_per_second": round(avg_blocks_per_second, 4),
            "average_blocks_per_minute": round(avg_blocks_per_minute, 2),
            "average_tx_per_block": round(avg_tx_per_block, 2),
            "throughput_kb_per_second": round(throughput_kb_per_second, 2),
            "throughput_mb_per_second": round(throughput_mb_per_second, 4),
            "total_nodes_monitored": len(self.baseline_snapshot.get("per_node_stats", {}))
        }

        return metrics

    def _display_performance_report(self, metrics: Dict):
        """Display performance report"""
        print(f"\n{'='*80}")
        print(f"⚡ BLOCKCHAIN PERFORMANCE REPORT")
        print(f"{'='*80}\n")

        if "error" in metrics:
            print(f"   ❌ Error: {metrics['error']}")
            return

        print(f"📊 Overall Metrics:")
        print(f"   Monitoring Duration: {metrics['duration_minutes']:.2f} minutes ({metrics['duration_seconds']:.1f}s)")
        print(f"   Total Transactions: {metrics['total_transactions']}")
        print(f"   Total Blocks: {metrics['total_blocks']}")
        print(f"   Nodes Monitored: {metrics['total_nodes_monitored']}")
        print()

        print(f"⚡ Transaction Performance:")
        print(f"   Average TPS: {metrics['average_tps']:.2f} transactions/second")
        print(f"   Peak TPS: {metrics['peak_tps']:.2f} transactions/second")
        print(f"   Average Tx/Block: {metrics['average_tx_per_block']:.2f} transactions/block")
        print()

        print(f"📦 Block Performance:")
        print(f"   Block Rate: {metrics['average_blocks_per_minute']:.2f} blocks/minute")
        print(f"   Block Rate: {metrics['average_blocks_per_second']:.4f} blocks/second")
        print()

        print(f"📈 Network Throughput:")
        print(f"   Throughput: {metrics['throughput_kb_per_second']:.2f} KB/s")
        print(f"   Throughput: {metrics['throughput_mb_per_second']:.4f} MB/s")
        print()

        # Performance classification
        print(f"📊 Performance Classification:")
        if metrics['average_tps'] >= 100:
            print(f"   ✅ EXCELLENT (>100 TPS) - High-performance blockchain")
        elif metrics['average_tps'] >= 50:
            print(f"   ✅ GOOD (50-100 TPS) - Efficient transaction processing")
        elif metrics['average_tps'] >= 10:
            print(f"   🟡 MODERATE (10-50 TPS) - Acceptable performance")
        elif metrics['average_tps'] >= 1:
            print(f"   🟡 LOW (1-10 TPS) - Consider optimization")
        else:
            print(f"   🔴 VERY LOW (<1 TPS) - Performance bottleneck detected")
        print()

    def export_performance_report(self, output_file: str = None) -> str:
        """
        Export performance report to file.

        Args:
            output_file: Path to save report

        Returns:
            Path to saved file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"blockchain_performance_report_{timestamp}.json"

        output_path = Path(output_file)

        try:
            with open(output_path, 'w') as f:
                json.dump(self.performance_data, f, indent=2)

            print(f"   💾 Performance report saved to: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"   ❌ Error saving report: {e}")
            return None

    def monitor_loop(self, duration_seconds: int = 300, interval_seconds: int = 30):
        """
        Run monitoring loop with periodic sampling.

        Args:
            duration_seconds: How long to monitor
            interval_seconds: Sample interval
        """
        print(f"\n⚡ Running Performance Monitor Loop...")
        print(f"   Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")
        print(f"   Sample Interval: {interval_seconds}s")
        print()

        start_time = time.time()
        sample_count = 0

        try:
            while (time.time() - start_time) < duration_seconds:
                # Take sample
                self.take_periodic_sample()
                sample_count += 1

                # Display current metrics
                if self.performance_data["tps_samples"]:
                    latest = self.performance_data["tps_samples"][-1]
                    print(f"   📊 Sample #{sample_count} @ {datetime.now().strftime('%H:%M:%S')}")
                    print(f"      TPS: {latest['tps']:.2f} | Blocks: {latest['blocks']} | "
                          f"Elapsed: {latest['elapsed_seconds']:.1f}s")

                # Wait for next interval
                time.sleep(interval_seconds)

            print(f"\n   ✅ Monitoring complete! {sample_count} samples collected")

        except KeyboardInterrupt:
            print(f"\n   ⚠️  Monitoring interrupted by user")
            print(f"   Samples collected: {sample_count}")


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("BLOCKCHAIN PERFORMANCE MONITOR - TEST")
    print("="*80)
    print()

    # Initialize monitor
    monitor = BlockchainPerformanceMonitor()

    # Start monitoring
    monitor.start_monitoring()

    # Simulate some time passing
    print("\n   ⏳ Simulating blockchain activity for 10 seconds...")
    time.sleep(10)

    # Take a sample
    monitor.take_periodic_sample()

    # Stop monitoring
    metrics = monitor.stop_monitoring()

    # Export report
    monitor.export_performance_report()

    print("\n✅ Test complete!")
