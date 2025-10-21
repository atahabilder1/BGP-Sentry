#!/usr/bin/env python3
"""
=============================================================================
Rating Monitor - Real-time Non-RPKI Rating Tracking System
=============================================================================

Purpose: Monitor rating changes for non-RPKI nodes in real-time
         Track detection events and rating evolution over time

Features:
- Real-time rating tracking
- Historical rating snapshots
- Detection event logging
- Time-series data collection
- Export for visualization

Author: BGP-Sentry Team
=============================================================================
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class RatingMonitor:
    """
    Monitors and tracks non-RPKI AS ratings over time.

    Collects time-series data for visualization and analysis.
    """

    def __init__(self, project_root: str = None):
        """
        Initialize rating monitor.

        Args:
            project_root: Root directory of BGP-Sentry project
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect project root
            self.project_root = Path(__file__).parent.parent.parent.parent.parent

        # Monitoring data storage
        self.monitor_data_file = (
            self.project_root /
            "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/rating_monitor_data.json"
        )

        # Rating files location
        self.rating_files_dir = (
            self.project_root /
            "nodes/rpki_nodes"
        )

        # Monitored ASes
        self.monitored_ases = []

        # Time-series data
        self.rating_history = {}

        # Load existing monitoring data
        self._load_monitor_data()

        print(f"📊 Rating Monitor Initialized")
        print(f"   Monitor Data: {self.monitor_data_file}")

    def _load_monitor_data(self):
        """Load existing monitoring data"""
        try:
            if self.monitor_data_file.exists():
                with open(self.monitor_data_file, 'r') as f:
                    data = json.load(f)

                self.monitored_ases = data.get("monitored_ases", [])
                self.rating_history = data.get("rating_history", {})

                print(f"   ✅ Loaded monitoring data")
                print(f"      Monitored ASes: {self.monitored_ases}")
                print(f"      History entries: {sum(len(h) for h in self.rating_history.values())}")
            else:
                print(f"   📝 Creating new monitoring session")

        except Exception as e:
            print(f"   ⚠️  Error loading monitor data: {e}")

    def start_monitoring(self, as_numbers: List[int]):
        """
        Start monitoring specific ASes.

        Args:
            as_numbers: List of AS numbers to monitor
        """
        self.monitored_ases = as_numbers

        print(f"\n🚀 Starting Rating Monitor")
        print(f"   Monitoring ASes: {as_numbers}")

        # Initialize history for each AS
        for as_num in as_numbers:
            if str(as_num) not in self.rating_history:
                self.rating_history[str(as_num)] = []

        # Take initial snapshot
        self.take_snapshot("Monitor started")

        print(f"   ✅ Monitor active")

    def take_snapshot(self, event: str = "Periodic snapshot"):
        """
        Take snapshot of current ratings for all monitored ASes.

        Args:
            event: Description of why snapshot was taken
        """
        timestamp = datetime.now().isoformat()

        for as_num in self.monitored_ases:
            # Get current rating
            current_rating = self._get_current_rating(as_num)

            # Get attack count
            attack_count = self._get_attack_count(as_num)

            # Record snapshot
            snapshot = {
                "timestamp": timestamp,
                "rating": current_rating["score"],
                "level": current_rating["level"],
                "attacks_detected": attack_count,
                "event": event
            }

            self.rating_history[str(as_num)].append(snapshot)

        # Save to disk
        self._save_monitor_data()

    def _get_current_rating(self, as_num: int) -> Dict:
        """Get current rating for an AS"""
        # Check all RPKI nodes for rating file
        # (they all maintain same rating database)

        # Try AS01 first
        rating_file = (
            self.rating_files_dir /
            f"as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json"
        )

        if not rating_file.exists():
            # Return default
            return {
                "score": 50,
                "level": "neutral",
                "as_number": as_num
            }

        try:
            with open(rating_file, 'r') as f:
                rating_data = json.load(f)

            as_ratings = rating_data.get("as_ratings", {})

            if str(as_num) in as_ratings:
                as_info = as_ratings[str(as_num)]
                return {
                    "score": as_info.get("trust_score", 50),
                    "level": as_info.get("rating_level", "neutral"),
                    "as_number": as_num
                }
            else:
                # AS not yet rated
                return {
                    "score": 50,
                    "level": "neutral",
                    "as_number": as_num
                }

        except Exception as e:
            print(f"   ⚠️  Error reading rating for AS{as_num}: {e}")
            return {
                "score": 50,
                "level": "neutral",
                "as_number": as_num
            }

    def _get_attack_count(self, as_num: int) -> int:
        """Get number of attacks detected for an AS"""
        rating_file = (
            self.rating_files_dir /
            f"as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json"
        )

        if not rating_file.exists():
            return 0

        try:
            with open(rating_file, 'r') as f:
                rating_data = json.load(f)

            as_ratings = rating_data.get("as_ratings", {})

            if str(as_num) in as_ratings:
                return as_ratings[str(as_num)].get("attacks_detected", 0)

            return 0

        except:
            return 0

    def _save_monitor_data(self):
        """Save monitoring data to disk"""
        try:
            # Ensure directory exists
            self.monitor_data_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "monitored_ases": self.monitored_ases,
                "rating_history": self.rating_history,
                "total_snapshots": sum(len(h) for h in self.rating_history.values())
            }

            with open(self.monitor_data_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"❌ Error saving monitor data: {e}")

    def monitor_loop(self, duration_seconds: int = 300, interval_seconds: int = 10):
        """
        Run monitoring loop for specified duration.

        Args:
            duration_seconds: How long to monitor (default 5 minutes)
            interval_seconds: Snapshot interval (default 10 seconds)
        """
        print(f"\n📊 Running monitoring loop...")
        print(f"   Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")
        print(f"   Interval: {interval_seconds}s")
        print()

        start_time = time.time()
        snapshot_count = 0

        try:
            while (time.time() - start_time) < duration_seconds:
                # Take snapshot
                self.take_snapshot(f"Periodic snapshot #{snapshot_count + 1}")
                snapshot_count += 1

                # Display current state
                self._display_current_state()

                # Wait for next interval
                print(f"   ⏳ Next snapshot in {interval_seconds}s...")
                time.sleep(interval_seconds)

            print(f"\n✅ Monitoring complete!")
            print(f"   Total snapshots: {snapshot_count}")

        except KeyboardInterrupt:
            print(f"\n⚠️  Monitoring interrupted by user")
            print(f"   Snapshots collected: {snapshot_count}")

    def _display_current_state(self):
        """Display current rating state"""
        print(f"\n📸 Snapshot @ {datetime.now().strftime('%H:%M:%S')}")
        print(f"   {'AS':<10} {'Rating':<10} {'Level':<15} {'Attacks':<10}")
        print(f"   {'-'*45}")

        for as_num in self.monitored_ases:
            rating = self._get_current_rating(as_num)
            attacks = self._get_attack_count(as_num)

            print(f"   AS{as_num:<8} {rating['score']:<10.1f} {rating['level']:<15} {attacks:<10}")

    def export_for_visualization(self, output_file: str = None) -> str:
        """
        Export monitoring data in format ready for visualization.

        Args:
            output_file: Optional output file path

        Returns:
            Path to exported file
        """
        if output_file is None:
            output_file = (
                self.monitor_data_file.parent /
                f"rating_visualization_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        else:
            output_file = Path(output_file)

        # Prepare data for visualization
        viz_data = {
            "export_timestamp": datetime.now().isoformat(),
            "monitored_ases": self.monitored_ases,
            "time_series": {},
            "summary": {}
        }

        # Convert history to plottable format
        for as_num_str, history in self.rating_history.items():
            as_num = int(as_num_str)

            # Extract time series
            timestamps = [entry["timestamp"] for entry in history]
            ratings = [entry["rating"] for entry in history]
            levels = [entry["level"] for entry in history]
            attacks = [entry["attacks_detected"] for entry in history]

            viz_data["time_series"][as_num] = {
                "timestamps": timestamps,
                "ratings": ratings,
                "levels": levels,
                "attacks": attacks
            }

            # Summary statistics
            if ratings:
                viz_data["summary"][as_num] = {
                    "initial_rating": ratings[0],
                    "final_rating": ratings[-1],
                    "rating_change": ratings[-1] - ratings[0],
                    "min_rating": min(ratings),
                    "max_rating": max(ratings),
                    "final_attacks": attacks[-1] if attacks else 0,
                    "final_level": levels[-1] if levels else "unknown"
                }

        # Save to file
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(viz_data, f, indent=2)

            print(f"\n📊 Visualization data exported:")
            print(f"   {output_file}")

            return str(output_file)

        except Exception as e:
            print(f"❌ Error exporting visualization data: {e}")
            return None

    def get_summary(self) -> Dict:
        """Get summary of monitoring session"""
        summary = {
            "monitored_ases": self.monitored_ases,
            "total_snapshots": sum(len(h) for h in self.rating_history.values()),
            "per_as_summary": {}
        }

        for as_num_str, history in self.rating_history.items():
            if not history:
                continue

            ratings = [entry["rating"] for entry in history]

            summary["per_as_summary"][as_num_str] = {
                "snapshots": len(history),
                "initial_rating": ratings[0],
                "final_rating": ratings[-1],
                "rating_change": ratings[-1] - ratings[0],
                "min_rating": min(ratings),
                "max_rating": max(ratings)
            }

        return summary


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("RATING MONITOR - TEST")
    print("="*80)
    print()

    # Initialize monitor
    monitor = RatingMonitor()

    # Start monitoring AS666 and AS31337
    monitor.start_monitoring([666, 31337])

    # Take a few test snapshots
    print("\n📸 Taking test snapshots...")
    for i in range(3):
        monitor.take_snapshot(f"Test snapshot {i+1}")
        time.sleep(1)

    # Export for visualization
    viz_file = monitor.export_for_visualization()

    # Display summary
    print("\n📊 Monitoring Summary:")
    summary = monitor.get_summary()
    print(json.dumps(summary, indent=2))

    print("\n✅ Test complete!")
