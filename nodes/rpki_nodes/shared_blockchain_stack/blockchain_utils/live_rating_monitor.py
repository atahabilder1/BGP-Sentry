#!/usr/bin/env python3
"""
=============================================================================
Live Rating Monitor - Real-time Visualization
=============================================================================

Purpose: Display live rating changes for non-RPKI ASes during experiment
         - Real-time plot updates every 10 seconds
         - Color-coded zones (RED/YELLOW/GREEN)
         - Shows detection rate and blockchain performance
         - Interactive matplotlib window

Author: BGP-Sentry Team
=============================================================================
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json


class LiveRatingMonitor:
    """
    Real-time visualization of non-RPKI AS ratings.

    Shows live updates during experiment execution.
    """

    # Color thresholds (matching visualization standards)
    RED_MAX = 40
    YELLOW_MAX = 70
    GREEN_MIN = 71

    # Colors
    COLOR_RED = '#FF4444'
    COLOR_YELLOW = '#FFB300'
    COLOR_GREEN = '#00C853'
    COLOR_LINE = '#1976D2'

    def __init__(self, monitored_ases: List[int], project_root: str):
        """
        Initialize live monitor.

        Args:
            monitored_ases: List of AS numbers to monitor
            project_root: Path to project root
        """
        self.monitored_ases = monitored_ases[:8]  # Max 8 ASes
        self.project_root = Path(project_root)

        # Rating data storage
        self.rating_data = {
            str(as_num): {
                'timestamps': [],
                'ratings': [],
                'attacks': [],
                'start_time': None
            }
            for as_num in self.monitored_ases
        }

        # Performance metrics
        self.performance_metrics = {
            'tps': [],
            'timestamps': [],
            'total_tx': 0,
            'total_blocks': 0
        }

        # Detection metrics
        self.detection_metrics = {
            'total_detected': 0,
            'total_injected': 20,  # Default
            'detection_rate': 0.0
        }

        # Figure and axes
        self.fig = None
        self.axes = None
        self.perf_ax = None
        self.det_ax = None

        # Initialize plot
        self._setup_plot()

    def _setup_plot(self):
        """Set up the matplotlib figure and axes"""
        # Create figure with subplots
        self.fig = plt.figure(figsize=(20, 12))
        self.fig.suptitle(
            '🔴 LIVE NON-RPKI RATING MONITOR 🔴\n'
            'Real-time Rating Evolution During Attack Experiment',
            fontsize=16,
            fontweight='bold'
        )

        # Create grid layout
        gs = GridSpec(4, 4, figure=self.fig, hspace=0.4, wspace=0.3)

        # Rating plots (2 rows x 4 columns = 8 plots)
        self.axes = []
        for i in range(min(8, len(self.monitored_ases))):
            row = i // 4
            col = i % 4
            ax = self.fig.add_subplot(gs[row, col])
            self.axes.append(ax)
            self._setup_rating_axis(ax, self.monitored_ases[i])

        # Performance plot (bottom left, spanning 2 columns)
        self.perf_ax = self.fig.add_subplot(gs[2:, :2])
        self._setup_performance_axis()

        # Detection metrics plot (bottom right, spanning 2 columns)
        self.det_ax = self.fig.add_subplot(gs[2:, 2:])
        self._setup_detection_axis()

        # Enable interactive mode
        plt.ion()
        plt.show(block=False)

    def _setup_rating_axis(self, ax, as_num: int):
        """Set up individual rating plot axis"""
        ax.set_title(f'AS{as_num}', fontsize=12, fontweight='bold')
        ax.set_xlabel('Time (seconds)', fontsize=9)
        ax.set_ylabel('Rating', fontsize=9)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)

        # Add color zones
        ax.axhspan(0, self.RED_MAX, color=self.COLOR_RED, alpha=0.15, label='RED (Bad)')
        ax.axhspan(self.RED_MAX, self.YELLOW_MAX, color=self.COLOR_YELLOW, alpha=0.15, label='YELLOW (Medium)')
        ax.axhspan(self.YELLOW_MAX, 100, color=self.COLOR_GREEN, alpha=0.15, label='GREEN (Good)')

        # Add threshold lines
        ax.axhline(y=self.RED_MAX, color=self.COLOR_RED, linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline(y=self.YELLOW_MAX, color=self.COLOR_YELLOW, linestyle='--', linewidth=1, alpha=0.5)

    def _setup_performance_axis(self):
        """Set up blockchain performance plot"""
        self.perf_ax.set_title('⚡ Blockchain Performance (TPS)', fontsize=12, fontweight='bold')
        self.perf_ax.set_xlabel('Time (seconds)', fontsize=9)
        self.perf_ax.set_ylabel('Transactions/Second', fontsize=9)
        self.perf_ax.grid(True, alpha=0.3)

        # Add performance zones
        self.perf_ax.axhspan(0, 1, color='#FF4444', alpha=0.1)
        self.perf_ax.axhspan(1, 10, color='#FFB300', alpha=0.1)
        self.perf_ax.axhspan(10, 50, color='#4CAF50', alpha=0.1)
        self.perf_ax.axhspan(50, 1000, color='#00C853', alpha=0.1)

    def _setup_detection_axis(self):
        """Set up detection metrics display"""
        self.det_ax.set_title('🎯 Attack Detection Metrics', fontsize=12, fontweight='bold')
        self.det_ax.axis('off')

    def update_rating(self, as_num: int, rating: float, attacks_detected: int,
                     timestamp: Optional[datetime] = None):
        """
        Update rating for a specific AS.

        Args:
            as_num: AS number
            rating: Current rating (0-100)
            attacks_detected: Number of attacks detected
            timestamp: Timestamp of update
        """
        if str(as_num) not in self.rating_data:
            return

        data = self.rating_data[str(as_num)]

        # Set start time if first update
        if data['start_time'] is None:
            data['start_time'] = timestamp or datetime.now()

        # Calculate elapsed time
        current_time = timestamp or datetime.now()
        elapsed_seconds = (current_time - data['start_time']).total_seconds()

        # Store data
        data['timestamps'].append(elapsed_seconds)
        data['ratings'].append(rating)
        data['attacks'].append(attacks_detected)

    def update_performance(self, tps: float, total_tx: int, total_blocks: int,
                          elapsed_seconds: float):
        """
        Update blockchain performance metrics.

        Args:
            tps: Current transactions per second
            total_tx: Total transactions processed
            total_blocks: Total blocks created
            elapsed_seconds: Elapsed time
        """
        self.performance_metrics['timestamps'].append(elapsed_seconds)
        self.performance_metrics['tps'].append(tps)
        self.performance_metrics['total_tx'] = total_tx
        self.performance_metrics['total_blocks'] = total_blocks

    def update_detection(self, total_detected: int, total_injected: int):
        """
        Update detection metrics.

        Args:
            total_detected: Number of attacks detected
            total_injected: Total attacks injected
        """
        self.detection_metrics['total_detected'] = total_detected
        self.detection_metrics['total_injected'] = total_injected
        self.detection_metrics['detection_rate'] = (
            (total_detected / total_injected * 100) if total_injected > 0 else 0
        )

    def refresh_plot(self):
        """Refresh the live plot with latest data"""
        # Update rating plots
        for i, as_num in enumerate(self.monitored_ases[:len(self.axes)]):
            ax = self.axes[i]
            data = self.rating_data[str(as_num)]

            if not data['ratings']:
                continue

            # Clear and redraw
            ax.clear()
            self._setup_rating_axis(ax, as_num)

            # Plot rating line
            ax.plot(
                data['timestamps'],
                data['ratings'],
                'o-',
                color=self.COLOR_LINE,
                linewidth=2,
                markersize=6,
                label='Rating'
            )

            # Mark attack detections
            if len(data['attacks']) > 1:
                for j in range(1, len(data['attacks'])):
                    if data['attacks'][j] > data['attacks'][j-1]:
                        ax.plot(
                            data['timestamps'][j],
                            data['ratings'][j],
                            'r*',
                            markersize=15,
                            label='Attack Detected' if j == 1 else ''
                        )

            # Show current rating
            if data['ratings']:
                current_rating = data['ratings'][-1]
                current_attacks = data['attacks'][-1] if data['attacks'] else 0

                # Determine classification
                if current_rating <= self.RED_MAX:
                    classification = '🔴 RED'
                elif current_rating <= self.YELLOW_MAX:
                    classification = '🟡 YELLOW'
                else:
                    classification = '🟢 GREEN'

                # Add text box with current stats
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

        if self.performance_metrics['tps']:
            self.perf_ax.plot(
                self.performance_metrics['timestamps'],
                self.performance_metrics['tps'],
                'o-',
                color='#1976D2',
                linewidth=2,
                markersize=6
            )

            # Show current stats
            avg_tps = np.mean(self.performance_metrics['tps'])
            peak_tps = max(self.performance_metrics['tps'])

            stats_text = (
                f"Total Tx: {self.performance_metrics['total_tx']}\n"
                f"Total Blocks: {self.performance_metrics['total_blocks']}\n"
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

        # Update detection metrics display
        self.det_ax.clear()
        self.det_ax.set_title('🎯 Attack Detection Metrics', fontsize=12, fontweight='bold')
        self.det_ax.axis('off')

        detection_rate = self.detection_metrics['detection_rate']
        total_detected = self.detection_metrics['total_detected']
        total_injected = self.detection_metrics['total_injected']

        # Determine status color
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

        # Create detection summary text
        det_summary = (
            f"Total Attacks Injected: {total_injected}\n\n"
            f"Total Attacks Detected: {total_detected}\n\n"
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

    def close(self):
        """Close the plot window"""
        plt.ioff()
        if self.fig:
            plt.close(self.fig)

    def keep_open(self):
        """Keep the plot window open after monitoring ends"""
        print("\n" + "="*80)
        print("📊 LIVE MONITORING COMPLETE")
        print("="*80)
        print("\n💡 The plot window will remain open for review.")
        print("   Close the window when done, or press Ctrl+C to exit.")
        print()

        plt.ioff()
        plt.show()  # Block until window closed


def test_live_monitor():
    """Test the live monitor with dummy data"""
    import time
    import random

    print("🧪 Testing Live Rating Monitor...")
    print("   This will show dummy data for 30 seconds\n")

    # Create monitor
    monitor = LiveRatingMonitor([666, 31337, 100, 200, 300, 400, 500, 600], ".")

    # Simulate 30 seconds of updates
    start_time = datetime.now()

    for i in range(30):
        elapsed = i

        # Update ratings (AS666 and AS31337 decrease, others stable/increase)
        monitor.update_rating(666, 50 - i*0.6, i // 3, datetime.now())
        monitor.update_rating(31337, 50 - i*0.4, i // 4, datetime.now())
        monitor.update_rating(100, 50 + random.uniform(-2, 5), 0, datetime.now())
        monitor.update_rating(200, 50 + random.uniform(-2, 8), random.randint(0, 1), datetime.now())
        monitor.update_rating(300, 50 + random.uniform(-1, 6), 0, datetime.now())
        monitor.update_rating(400, 50 + random.uniform(-2, 7), 0, datetime.now())
        monitor.update_rating(500, 50 + random.uniform(-1, 9), 0, datetime.now())
        monitor.update_rating(600, 50 + random.uniform(-2, 8), 0, datetime.now())

        # Update performance
        tps = random.uniform(3, 12)
        monitor.update_performance(tps, i * 70, i * 5, elapsed)

        # Update detection
        monitor.update_detection(min(i // 2, 20), 20)

        # Refresh plot
        monitor.refresh_plot()

        time.sleep(1)

    print("\n✅ Test complete!")
    monitor.keep_open()


if __name__ == "__main__":
    test_live_monitor()
