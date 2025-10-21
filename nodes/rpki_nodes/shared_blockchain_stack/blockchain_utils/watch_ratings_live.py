#!/usr/bin/env python3
"""
=============================================================================
Standalone Live Rating Viewer - Watch Experiment in Real-Time
=============================================================================

Purpose: Run this in a separate terminal to watch live rating changes
         while your experiment runs in another terminal.

Usage:
    python3 watch_ratings_live.py
    python3 watch_ratings_live.py --refresh 5  # Update every 5 seconds
    python3 watch_ratings_live.py --ases 666 31337 100  # Monitor specific ASes

Author: BGP-Sentry Team
=============================================================================
"""

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import time
import argparse
import sys


class StandaloneLiveViewer:
    """
    Standalone live viewer that reads from rating files.

    Runs independently of the experiment runner.
    """

    # Color thresholds
    RED_MAX = 40
    YELLOW_MAX = 70
    GREEN_MIN = 71

    # Colors
    COLOR_RED = '#FF4444'
    COLOR_YELLOW = '#FFB300'
    COLOR_GREEN = '#00C853'
    COLOR_LINE = '#1976D2'

    def __init__(self, refresh_interval: int = 10, monitored_ases: list = None):
        """
        Initialize standalone viewer.

        Args:
            refresh_interval: Seconds between updates
            monitored_ases: List of AS numbers to monitor (None = auto-detect)
        """
        self.refresh_interval = refresh_interval
        self.monitored_ases = monitored_ases or []

        self.project_root = Path(__file__).parent.parent.parent.parent.parent
        self.rating_file = (
            self.project_root /
            "nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json"
        )

        # Data storage
        self.rating_history = {}
        self.start_time = datetime.now()

        # Performance data
        self.perf_data = {
            'timestamps': [],
            'tps': [],
            'total_tx': 0,
            'total_blocks': 0
        }

        # Detection data
        self.total_detected = 0
        self.total_injected = 20  # Default

        # Figure
        self.fig = None
        self.axes = []
        self.perf_ax = None
        self.det_ax = None

        print("🔴 LIVE RATING VIEWER 🔴")
        print("=" * 80)
        print(f"Watching: {self.rating_file}")
        print(f"Refresh interval: {self.refresh_interval} seconds")
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

    def read_current_ratings(self) -> dict:
        """Read current ratings from file"""
        if not self.rating_file.exists():
            return {}

        try:
            with open(self.rating_file, 'r') as f:
                data = json.load(f)
            return data.get("as_ratings", {})
        except Exception as e:
            print(f"⚠️  Error reading ratings: {e}")
            return {}

    def read_blockchain_stats(self) -> dict:
        """Read blockchain statistics"""
        # Try to read from multiple nodes
        for node in ['as01', 'as03', 'as05']:
            blockchain_dir = (
                self.project_root /
                f"nodes/rpki_nodes/{node}/blockchain_node/blockchain_data/blocks"
            )

            if blockchain_dir.exists():
                try:
                    blocks = list(blockchain_dir.glob("block_*.json"))
                    total_blocks = len(blocks)

                    # Count transactions
                    total_tx = 0
                    for block_file in blocks[-10:]:  # Last 10 blocks
                        with open(block_file, 'r') as f:
                            block_data = json.load(f)
                            total_tx += len(block_data.get("transactions", []))

                    return {
                        'total_blocks': total_blocks,
                        'total_tx': total_tx * (total_blocks // 10 + 1)  # Estimate
                    }
                except:
                    pass

        return {'total_blocks': 0, 'total_tx': 0}

    def setup_plot(self):
        """Set up the matplotlib figure"""
        # Auto-detect ASes if not specified
        if not self.monitored_ases:
            ratings = self.read_current_ratings()
            self.monitored_ases = sorted([int(as_num) for as_num in ratings.keys()])[:8]

        if not self.monitored_ases:
            print("⚠️  No ASes found to monitor yet. Will retry...")
            return False

        print(f"📊 Monitoring ASes: {self.monitored_ases}")
        print()

        # Create figure
        self.fig = plt.figure(figsize=(20, 12))
        self.fig.suptitle(
            '🔴 LIVE NON-RPKI RATING MONITOR 🔴\n'
            f'Started: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")} | '
            f'Refresh: {self.refresh_interval}s',
            fontsize=16,
            fontweight='bold'
        )

        # Create grid
        gs = GridSpec(4, 4, figure=self.fig, hspace=0.4, wspace=0.3)

        # Rating plots
        self.axes = []
        for i in range(min(8, len(self.monitored_ases))):
            row = i // 4
            col = i % 4
            ax = self.fig.add_subplot(gs[row, col])
            self.axes.append(ax)
            self._setup_rating_axis(ax, self.monitored_ases[i])

        # Performance plot
        self.perf_ax = self.fig.add_subplot(gs[2:, :2])
        self._setup_performance_axis()

        # Detection plot
        self.det_ax = self.fig.add_subplot(gs[2:, 2:])
        self._setup_detection_axis()

        plt.ion()
        plt.show(block=False)

        return True

    def _setup_rating_axis(self, ax, as_num: int):
        """Set up individual rating axis"""
        ax.set_title(f'AS{as_num}', fontsize=12, fontweight='bold')
        ax.set_xlabel('Time (seconds)', fontsize=9)
        ax.set_ylabel('Rating', fontsize=9)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)

        # Color zones
        ax.axhspan(0, self.RED_MAX, color=self.COLOR_RED, alpha=0.15)
        ax.axhspan(self.RED_MAX, self.YELLOW_MAX, color=self.COLOR_YELLOW, alpha=0.15)
        ax.axhspan(self.YELLOW_MAX, 100, color=self.COLOR_GREEN, alpha=0.15)

        # Threshold lines
        ax.axhline(y=self.RED_MAX, color=self.COLOR_RED, linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline(y=self.YELLOW_MAX, color=self.COLOR_YELLOW, linestyle='--', linewidth=1, alpha=0.5)

    def _setup_performance_axis(self):
        """Set up performance axis"""
        self.perf_ax.set_title('⚡ Blockchain Performance (TPS)', fontsize=12, fontweight='bold')
        self.perf_ax.set_xlabel('Time (seconds)', fontsize=9)
        self.perf_ax.set_ylabel('Transactions/Second', fontsize=9)
        self.perf_ax.grid(True, alpha=0.3)

    def _setup_detection_axis(self):
        """Set up detection axis"""
        self.det_ax.set_title('🎯 Attack Detection Metrics', fontsize=12, fontweight='bold')
        self.det_ax.axis('off')

    def update_data(self):
        """Update data from files"""
        ratings = self.read_current_ratings()
        elapsed = (datetime.now() - self.start_time).total_seconds()

        # Update rating history
        for as_num_str, as_data in ratings.items():
            as_num = int(as_num_str)

            if as_num not in self.monitored_ases:
                continue

            if as_num not in self.rating_history:
                self.rating_history[as_num] = {
                    'timestamps': [],
                    'ratings': [],
                    'attacks': []
                }

            hist = self.rating_history[as_num]
            current_rating = as_data.get("trust_score", 50)
            current_attacks = as_data.get("attacks_detected", 0)

            hist['timestamps'].append(elapsed)
            hist['ratings'].append(current_rating)
            hist['attacks'].append(current_attacks)

        # Update blockchain stats
        stats = self.read_blockchain_stats()
        if stats['total_tx'] > 0:
            tps = stats['total_tx'] / max(elapsed, 1)
            self.perf_data['timestamps'].append(elapsed)
            self.perf_data['tps'].append(tps)
            self.perf_data['total_tx'] = stats['total_tx']
            self.perf_data['total_blocks'] = stats['total_blocks']

        # Update detection count
        self.total_detected = sum(
            ratings.get(str(as_num), {}).get("attacks_detected", 0)
            for as_num in self.monitored_ases
        )

    def refresh_plot(self):
        """Refresh the plot with latest data"""
        # Update rating plots
        for i, as_num in enumerate(self.monitored_ases[:len(self.axes)]):
            if as_num not in self.rating_history:
                continue

            ax = self.axes[i]
            hist = self.rating_history[as_num]

            if not hist['ratings']:
                continue

            # Clear and redraw
            ax.clear()
            self._setup_rating_axis(ax, as_num)

            # Plot rating line
            ax.plot(
                hist['timestamps'],
                hist['ratings'],
                'o-',
                color=self.COLOR_LINE,
                linewidth=2,
                markersize=6
            )

            # Mark attack detections
            if len(hist['attacks']) > 1:
                for j in range(1, len(hist['attacks'])):
                    if hist['attacks'][j] > hist['attacks'][j-1]:
                        ax.plot(
                            hist['timestamps'][j],
                            hist['ratings'][j],
                            'r*',
                            markersize=15
                        )

            # Current stats
            current_rating = hist['ratings'][-1]
            current_attacks = hist['attacks'][-1]

            if current_rating <= self.RED_MAX:
                classification = '🔴 RED'
            elif current_rating <= self.YELLOW_MAX:
                classification = '🟡 YELLOW'
            else:
                classification = '🟢 GREEN'

            stats_text = (
                f'Rating: {current_rating:.1f}\n'
                f'Attacks: {current_attacks}\n'
                f'{classification}'
            )

            ax.text(
                0.02, 0.98,
                stats_text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            )

        # Update performance plot
        self.perf_ax.clear()
        self._setup_performance_axis()

        if self.perf_data['tps']:
            self.perf_ax.plot(
                self.perf_data['timestamps'],
                self.perf_data['tps'],
                'o-',
                color='#1976D2',
                linewidth=2,
                markersize=6
            )

            avg_tps = np.mean(self.perf_data['tps'])
            peak_tps = max(self.perf_data['tps'])

            stats_text = (
                f"Total Tx: {self.perf_data['total_tx']}\n"
                f"Total Blocks: {self.perf_data['total_blocks']}\n"
                f"Avg TPS: {avg_tps:.2f}\n"
                f"Peak TPS: {peak_tps:.2f}"
            )

            self.perf_ax.text(
                0.02, 0.98,
                stats_text,
                transform=self.perf_ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8)
            )

        # Update detection metrics
        self.det_ax.clear()
        self.det_ax.set_title('🎯 Attack Detection Metrics', fontsize=12, fontweight='bold')
        self.det_ax.axis('off')

        detection_rate = (self.total_detected / self.total_injected * 100) if self.total_injected > 0 else 0

        if detection_rate >= 95:
            status_color = '#00C853'
            status_text = '✅ EXCELLENT'
        elif detection_rate >= 80:
            status_color = '#4CAF50'
            status_text = '✅ GOOD'
        elif detection_rate >= 60:
            status_color = '#FFB300'
            status_text = '⚠️ MODERATE'
        else:
            status_color = '#FF4444'
            status_text = '❌ LOW'

        det_summary = (
            f"Total Attacks Injected: {self.total_injected}\n\n"
            f"Total Attacks Detected: {self.total_detected}\n\n"
            f"Detection Rate: {detection_rate:.1f}%\n\n"
            f"Status: {status_text}"
        )

        self.det_ax.text(
            0.5, 0.5,
            det_summary,
            transform=self.det_ax.transAxes,
            fontsize=14,
            verticalalignment='center',
            horizontalalignment='center',
            bbox=dict(
                boxstyle='round,pad=1',
                facecolor=status_color,
                alpha=0.3,
                edgecolor=status_color,
                linewidth=3
            )
        )

        # Force redraw
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)

    def run(self):
        """Run the live viewer"""
        print("🎨 Initializing live viewer...")
        print("⏳ Waiting for rating file to appear...")
        print()

        # Wait for rating file
        plot_ready = False
        while not plot_ready:
            if self.rating_file.exists():
                plot_ready = self.setup_plot()
                if plot_ready:
                    break

            print(f"   Waiting for ratings... ({datetime.now().strftime('%H:%M:%S')})")
            time.sleep(self.refresh_interval)

        print("✅ Live viewer started!")
        print(f"📊 Updating every {self.refresh_interval} seconds")
        print("💡 Close the plot window to exit")
        print()

        # Main loop
        try:
            iteration = 0
            while plt.fignum_exists(self.fig.number):
                iteration += 1

                # Update data
                self.update_data()

                # Refresh plot
                self.refresh_plot()

                # Log
                elapsed = (datetime.now() - self.start_time).total_seconds()
                print(f"🔄 Update #{iteration} | Elapsed: {elapsed:.0f}s | "
                      f"Detected: {self.total_detected}/{self.total_injected} | "
                      f"Detection Rate: {(self.total_detected/self.total_injected*100) if self.total_injected > 0 else 0:.1f}%")

                # Wait
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\n\n⏹️  Viewer stopped by user")

        print("\n✅ Live viewer closed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Live Rating Viewer - Watch experiment in real-time'
    )

    parser.add_argument(
        '--refresh',
        type=int,
        default=10,
        help='Refresh interval in seconds (default: 10)'
    )

    parser.add_argument(
        '--ases',
        type=int,
        nargs='+',
        help='Specific AS numbers to monitor (default: auto-detect)'
    )

    args = parser.parse_args()

    # Create and run viewer
    viewer = StandaloneLiveViewer(
        refresh_interval=args.refresh,
        monitored_ases=args.ases
    )

    viewer.run()


if __name__ == "__main__":
    main()
