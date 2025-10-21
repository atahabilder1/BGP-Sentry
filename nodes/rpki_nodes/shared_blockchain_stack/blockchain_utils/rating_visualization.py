#!/usr/bin/env python3
"""
=============================================================================
Rating Visualization Dashboard - Color-Coded Rating Analysis
=============================================================================

Purpose: Visualize non-RPKI rating changes over time with color classification

Features:
- 8-plot dashboard (one page, 8 separate AS plots)
- Color classification: Red (bad), Yellow (medium), Green (good)
- Time-series rating evolution
- Attack event markers
- Summary statistics table
- Classification thresholds

Classification:
- RED (0-40): Malicious / Bad behavior
- YELLOW (41-70): Medium / Suspicious
- GREEN (71-100): Good / Trustworthy

Author: BGP-Sentry Team
=============================================================================
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class RatingVisualization:
    """
    Visualizes non-RPKI AS ratings with color-coded classification.

    Creates comprehensive dashboard showing rating evolution.
    """

    # Color classification thresholds
    THRESHOLDS = {
        "red_max": 40,       # 0-40: Red (bad)
        "yellow_max": 70,    # 41-70: Yellow (medium)
        "green_min": 71      # 71-100: Green (good)
    }

    # Color palette
    COLORS = {
        "red": "#FF4444",       # Bad
        "yellow": "#FFB300",    # Medium
        "green": "#00C853",     # Good
        "neutral": "#888888"    # Neutral line
    }

    def __init__(self, data_file: str = None):
        """
        Initialize visualization system.

        Args:
            data_file: Path to monitoring data file
        """
        if data_file:
            self.data_file = Path(data_file)
        else:
            # Default location
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.data_file = (
                project_root /
                "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/rating_visualization_data.json"
            )

        # Load data
        self.data = None
        self._load_data()

        print(f"📊 Rating Visualization Initialized")
        if self.data:
            print(f"   Monitoring Data: {len(self.data.get('monitored_ases', []))} ASes")

    def _load_data(self):
        """Load visualization data"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
                print(f"   ✅ Loaded visualization data from {self.data_file.name}")
            else:
                print(f"   ⚠️  No data file found at {self.data_file}")
                self.data = None
        except Exception as e:
            print(f"   ❌ Error loading data: {e}")
            self.data = None

    def get_classification(self, rating: float) -> str:
        """
        Get color classification for a rating.

        Args:
            rating: Rating score (0-100)

        Returns:
            Classification: "red", "yellow", or "green"
        """
        if rating <= self.THRESHOLDS["red_max"]:
            return "red"
        elif rating <= self.THRESHOLDS["yellow_max"]:
            return "yellow"
        else:
            return "green"

    def get_classification_label(self, rating: float) -> str:
        """Get human-readable classification label"""
        classification = self.get_classification(rating)

        labels = {
            "red": "BAD (Malicious)",
            "yellow": "MEDIUM (Suspicious)",
            "green": "GOOD (Trustworthy)"
        }

        return labels[classification]

    def create_dashboard(self, output_file: str = None, show_plot: bool = True):
        """
        Create 8-plot dashboard showing rating evolution.

        Args:
            output_file: Path to save figure
            show_plot: Whether to display plot interactively
        """
        if not self.data or not self.data.get("time_series"):
            print("❌ No data available for visualization")
            return

        print(f"\n📊 Creating Rating Evolution Dashboard...")

        # Get up to 8 ASes to plot
        monitored_ases = self.data.get("monitored_ases", [])[:8]

        if len(monitored_ases) == 0:
            print("❌ No monitored ASes found in data")
            return

        # Create figure with 8 subplots (2 rows x 4 columns)
        fig = plt.figure(figsize=(20, 10))
        fig.suptitle('Non-RPKI AS Rating Evolution Dashboard\nColor Classification: RED (0-40) | YELLOW (41-70) | GREEN (71-100)',
                     fontsize=16, fontweight='bold')

        # Determine grid layout based on number of ASes
        n_ases = len(monitored_ases)
        if n_ases <= 4:
            n_rows, n_cols = 1, 4
        else:
            n_rows, n_cols = 2, 4

        # Create subplots
        for idx, as_num in enumerate(monitored_ases):
            if idx >= 8:  # Maximum 8 plots
                break

            row = idx // 4
            col = idx % 4

            ax = plt.subplot(n_rows, n_cols, idx + 1)

            # Plot this AS
            self._plot_as_rating(ax, as_num)

        # Adjust layout
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])

        # Save figure
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"rating_dashboard_{timestamp}.png"

        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"   ✅ Dashboard saved to: {output_file}")

        # Show plot
        if show_plot:
            plt.show()

        return output_file

    def _plot_as_rating(self, ax, as_num: int):
        """Plot rating evolution for a single AS"""
        time_series = self.data["time_series"].get(str(as_num))

        if not time_series:
            ax.text(0.5, 0.5, f"No data for AS{as_num}",
                   ha='center', va='center', transform=ax.transAxes)
            return

        # Extract data
        timestamps = time_series["timestamps"]
        ratings = time_series["ratings"]
        attacks = time_series.get("attacks", [])

        # Convert timestamps to indices (time series)
        x = np.arange(len(timestamps))

        # Plot rating line
        ax.plot(x, ratings, 'o-', linewidth=2, markersize=6,
                color='#333333', label='Rating', zorder=3)

        # Color background regions
        ax.axhspan(0, self.THRESHOLDS["red_max"],
                  color=self.COLORS["red"], alpha=0.15, label='BAD')
        ax.axhspan(self.THRESHOLDS["red_max"], self.THRESHOLDS["yellow_max"],
                  color=self.COLORS["yellow"], alpha=0.15, label='MEDIUM')
        ax.axhspan(self.THRESHOLDS["yellow_max"], 100,
                  color=self.COLORS["green"], alpha=0.15, label='GOOD')

        # Add threshold lines
        ax.axhline(y=self.THRESHOLDS["red_max"], color=self.COLORS["red"],
                  linestyle='--', linewidth=1.5, alpha=0.7)
        ax.axhline(y=self.THRESHOLDS["yellow_max"], color=self.COLORS["yellow"],
                  linestyle='--', linewidth=1.5, alpha=0.7)

        # Annotate attack points (if attacks changed)
        if attacks:
            for i in range(1, len(attacks)):
                if attacks[i] > attacks[i-1]:
                    # Attack detected at this point
                    ax.plot(x[i], ratings[i], 'r*', markersize=15,
                           markeredgecolor='darkred', markeredgewidth=1.5, zorder=4)

        # Get final classification
        final_rating = ratings[-1] if ratings else 50
        final_class = self.get_classification(final_rating)
        final_attacks = attacks[-1] if attacks else 0

        # Title with classification
        class_emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
        ax.set_title(f"AS{as_num} {class_emoji[final_class]} - Rating: {final_rating:.1f} | Attacks: {final_attacks}",
                    fontsize=12, fontweight='bold')

        # Labels
        ax.set_xlabel('Time (snapshot index)', fontsize=10)
        ax.set_ylabel('Rating Score', fontsize=10)

        # Set limits
        ax.set_ylim(0, 100)
        ax.set_xlim(-0.5, len(x) - 0.5)

        # Grid
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.8)

        # Final classification badge
        badge_text = f"Final: {self.get_classification_label(final_rating)}"
        bbox_color = self.COLORS[final_class]
        ax.text(0.98, 0.02, badge_text,
               transform=ax.transAxes,
               fontsize=9, fontweight='bold',
               ha='right', va='bottom',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=bbox_color,
                        alpha=0.3, edgecolor=bbox_color, linewidth=2))

    def create_summary_table(self, output_file: str = None) -> str:
        """
        Create summary table of all monitored ASes.

        Args:
            output_file: Path to save table

        Returns:
            Path to saved file
        """
        if not self.data or not self.data.get("summary"):
            print("❌ No summary data available")
            return None

        print(f"\n📋 Creating Summary Table...")

        summary = self.data["summary"]

        # Create table figure
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.axis('tight')
        ax.axis('off')

        # Prepare table data
        headers = ["AS Number", "Initial Rating", "Final Rating", "Rating Change",
                  "Min Rating", "Max Rating", "Attacks Detected", "Classification"]

        rows = []
        for as_num, stats in summary.items():
            final_rating = stats["final_rating"]
            classification = self.get_classification_label(final_rating)

            row = [
                f"AS{as_num}",
                f"{stats['initial_rating']:.1f}",
                f"{stats['final_rating']:.1f}",
                f"{stats['rating_change']:+.1f}",
                f"{stats['min_rating']:.1f}",
                f"{stats['max_rating']:.1f}",
                f"{stats['final_attacks']}",
                classification
            ]
            rows.append(row)

        # Create table
        table = ax.table(cellText=rows, colLabels=headers,
                        cellLoc='center', loc='center',
                        colWidths=[0.10, 0.12, 0.12, 0.12, 0.12, 0.12, 0.15, 0.15])

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        # Color code by classification
        for i, row in enumerate(rows):
            # Get classification color
            final_rating = summary[list(summary.keys())[i]]["final_rating"]
            class_color = self.COLORS[self.get_classification(final_rating)]

            # Color the classification cell
            table[(i+1, 7)].set_facecolor(class_color)
            table[(i+1, 7)].set_alpha(0.3)

        # Header styling
        for j in range(len(headers)):
            table[(0, j)].set_facecolor('#4CAF50')
            table[(0, j)].set_text_props(weight='bold', color='white')

        # Title
        plt.title('Non-RPKI AS Rating Summary\nClassification Thresholds: RED (0-40) | YELLOW (41-70) | GREEN (71-100)',
                 fontsize=14, fontweight='bold', pad=20)

        # Save table
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"rating_summary_table_{timestamp}.png"

        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"   ✅ Summary table saved to: {output_file}")

        plt.close()

        return output_file

    def create_classification_pie_chart(self, output_file: str = None):
        """Create pie chart showing classification distribution"""
        if not self.data or not self.data.get("summary"):
            print("❌ No summary data available")
            return

        print(f"\n📊 Creating Classification Distribution Chart...")

        summary = self.data["summary"]

        # Count classifications
        classification_counts = {"red": 0, "yellow": 0, "green": 0}

        for as_stats in summary.values():
            final_rating = as_stats["final_rating"]
            classification = self.get_classification(final_rating)
            classification_counts[classification] += 1

        # Create pie chart
        fig, ax = plt.subplots(figsize=(10, 8))

        labels = [f"BAD (0-40)\n{classification_counts['red']} ASes",
                 f"MEDIUM (41-70)\n{classification_counts['yellow']} ASes",
                 f"GOOD (71-100)\n{classification_counts['green']} ASes"]

        sizes = [classification_counts["red"],
                classification_counts["yellow"],
                classification_counts["green"]]

        colors = [self.COLORS["red"], self.COLORS["yellow"], self.COLORS["green"]]

        # Only include non-zero slices
        filtered_labels = []
        filtered_sizes = []
        filtered_colors = []

        for label, size, color in zip(labels, sizes, colors):
            if size > 0:
                filtered_labels.append(label)
                filtered_sizes.append(size)
                filtered_colors.append(color)

        if not filtered_sizes:
            print("   ⚠️  No data to plot")
            return

        # Create pie chart
        wedges, texts, autotexts = ax.pie(filtered_sizes, labels=filtered_labels,
                                          colors=filtered_colors, autopct='%1.1f%%',
                                          startangle=90, textprops={'fontsize': 12})

        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(14)

        ax.set_title('Non-RPKI AS Classification Distribution',
                    fontsize=16, fontweight='bold')

        # Save
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"classification_distribution_{timestamp}.png"

        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"   ✅ Classification chart saved to: {output_file}")

        plt.close()

        return output_file


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("RATING VISUALIZATION DASHBOARD - TEST")
    print("="*80)
    print()

    # Initialize visualization
    viz = RatingVisualization()

    # Check if data exists
    if viz.data:
        # Create dashboard
        viz.create_dashboard(show_plot=False)

        # Create summary table
        viz.create_summary_table()

        # Create classification pie chart
        viz.create_classification_pie_chart()

        print("\n✅ All visualizations created successfully!")
    else:
        print("\n⚠️  No monitoring data available")
        print("   Run rating_monitor.py first to collect data")
