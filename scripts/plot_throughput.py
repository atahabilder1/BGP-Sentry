#!/usr/bin/env python3
"""
Plot throughput benchmark graphs for BGP-Sentry.

Generates:
  1. Network TPS vs Speed Multiplier (with linear reference line)
  2. Wall Time vs Speed Multiplier
  3. TPS Scaling Efficiency (actual vs ideal linear)
  4. Per-Transaction Consensus Overhead

Usage:
    python3 scripts/plot_throughput.py
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ── Benchmark Data (from 1x-10x runs on caida_100, 100 nodes) ──
multipliers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
network_tps = [4.2, 8.1, 12.2, 16.1, 20.2, 23.7, 27.8, 31.0, 35.5, 36.8]
wall_times = [1700, 869, 580, 439, 350, 298, 254, 228, 199, 192]
total_processed = 7069  # Same dataset every run

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Plot Style ──
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f9fa",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
})


def plot_tps_vs_speed():
    """Fig 1: Network TPS vs Speed Multiplier with linear reference."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Ideal linear scaling (extrapolate from 1x TPS)
    ideal_tps = [multipliers[0] * m * network_tps[0] / multipliers[0] for m in multipliers]
    # Simpler: ideal = 4.2 * multiplier
    ideal_tps = [4.2 * m for m in multipliers]

    ax.plot(multipliers, ideal_tps, '--', color='#aaaaaa', linewidth=2,
            label='Ideal Linear Scaling', zorder=1)
    ax.plot(multipliers, network_tps, 'o-', color='#2196F3', linewidth=2.5,
            markersize=8, label='BGP-Sentry (Actual)', zorder=3)

    # Highlight the linear region vs sub-linear region
    ax.axvspan(0.5, 6.5, alpha=0.08, color='green', label='Linear Region (1x–6x)')
    ax.axvspan(6.5, 10.5, alpha=0.08, color='orange', label='Sub-Linear Region (7x–10x)')

    # Annotate peak
    ax.annotate(f'Peak: {max(network_tps)} TPS',
                xy=(10, 36.8), xytext=(7.5, 40),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=12, fontweight='bold', color='red')

    # Reference lines for other blockchains
    ax.axhline(y=7, color='#FF9800', linestyle=':', alpha=0.7, linewidth=1.5)
    ax.text(1.2, 7.8, 'Bitcoin (~7 TPS, network-wide)', color='#FF9800', fontsize=9)
    ax.axhline(y=25, color='#9C27B0', linestyle=':', alpha=0.7, linewidth=1.5)
    ax.text(1.2, 25.8, 'Ethereum PoS (~15-30 TPS, network-wide)', color='#9C27B0', fontsize=9)

    ax.set_xlabel('Speed Multiplier (x)')
    ax.set_ylabel('Network TPS (transactions/second, all nodes combined)')
    ax.set_title('BGP-Sentry: Network Throughput vs Speed Multiplier (network-wide)\n(100 nodes, 58 RPKI validators, caida_100 dataset)')
    ax.set_xticks(multipliers)
    ax.set_xticklabels([f'{m}x' for m in multipliers])
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(0, 50)
    ax.legend(loc='upper left', framealpha=0.9)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_tps_vs_speed.png", dpi=150)
    print(f"  Saved: {OUTPUT_DIR / 'fig_tps_vs_speed.png'}")
    plt.close(fig)


def plot_scaling_efficiency():
    """Fig 2: Scaling efficiency — actual TPS as % of ideal linear."""
    fig, ax = plt.subplots(figsize=(10, 6))

    ideal_tps = [4.2 * m for m in multipliers]
    efficiency = [100 * actual / ideal for actual, ideal in zip(network_tps, ideal_tps)]

    colors = ['#4CAF50' if e >= 90 else '#FF9800' if e >= 80 else '#F44336' for e in efficiency]

    bars = ax.bar(multipliers, efficiency, color=colors, edgecolor='white', linewidth=1.5, width=0.7)

    # Add percentage labels on bars
    for bar, eff in zip(bars, efficiency):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f'{eff:.0f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.axhline(y=100, color='#aaaaaa', linestyle='--', linewidth=1.5, label='100% = Ideal Linear')
    ax.axhline(y=90, color='green', linestyle=':', alpha=0.5, linewidth=1, label='90% threshold')

    ax.set_xlabel('Speed Multiplier (x)')
    ax.set_ylabel('Scaling Efficiency (%)')
    ax.set_title('Scaling Efficiency: Actual TPS vs Ideal Linear TPS\n(Green ≥90%, Orange ≥80%, Red <80%)')
    ax.set_xticks(multipliers)
    ax.set_xticklabels([f'{m}x' for m in multipliers])
    ax.set_ylim(0, 115)
    ax.legend(loc='lower left')

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_scaling_efficiency.png", dpi=150)
    print(f"  Saved: {OUTPUT_DIR / 'fig_scaling_efficiency.png'}")
    plt.close(fig)


def plot_wall_time():
    """Fig 3: Wall-clock time vs speed multiplier."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Ideal wall time (perfectly linear: 1700/multiplier)
    ideal_wall = [1700 / m for m in multipliers]

    ax.plot(multipliers, ideal_wall, '--', color='#aaaaaa', linewidth=2, label='Ideal (1700/x)')
    ax.plot(multipliers, wall_times, 's-', color='#E91E63', linewidth=2.5,
            markersize=8, label='BGP-Sentry (Actual)')

    # Annotate key points
    ax.annotate(f'Real-time: {wall_times[0]}s\n(28 min)',
                xy=(1, 1700), xytext=(2.5, 1500),
                arrowprops=dict(arrowstyle='->', color='gray'),
                fontsize=10)
    ax.annotate(f'10x: {wall_times[-1]}s\n(3.2 min)',
                xy=(10, 192), xytext=(8, 400),
                arrowprops=dict(arrowstyle='->', color='gray'),
                fontsize=10)

    ax.set_xlabel('Speed Multiplier (x)')
    ax.set_ylabel('Wall-Clock Time (seconds)')
    ax.set_title('Wall-Clock Processing Time vs Speed Multiplier\n(28 minutes of BGP data, caida_100)')
    ax.set_xticks(multipliers)
    ax.set_xticklabels([f'{m}x' for m in multipliers])
    ax.set_xlim(0.5, 10.5)
    ax.legend(loc='upper right')

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_wall_time.png", dpi=150)
    print(f"  Saved: {OUTPUT_DIR / 'fig_wall_time.png'}")
    plt.close(fig)


def plot_consensus_overhead():
    """Fig 4: Per-transaction consensus time at each speed."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Effective time per transaction = wall_time / total_processed
    ms_per_tx = [1000 * wt / total_processed for wt in wall_times]

    ax.plot(multipliers, ms_per_tx, 'D-', color='#673AB7', linewidth=2.5,
            markersize=8, label='Time per Transaction')

    # Show the components
    ax.axhline(y=5, color='orange', linestyle=':', alpha=0.6, linewidth=1.5)
    ax.text(8, 5.5, 'Vote collection floor (~5ms)', color='orange', fontsize=9)

    for i, (m, ms) in enumerate(zip(multipliers, ms_per_tx)):
        ax.text(m, ms + 3, f'{ms:.0f}ms', ha='center', fontsize=9, fontweight='bold')

    ax.set_xlabel('Speed Multiplier (x)')
    ax.set_ylabel('Time per Transaction (ms)')
    ax.set_title('Per-Transaction Processing Time\n(includes consensus round-trip, signing, block commit)')
    ax.set_xticks(multipliers)
    ax.set_xticklabels([f'{m}x' for m in multipliers])
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(0, max(ms_per_tx) * 1.3)
    ax.legend(loc='upper right')

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_consensus_overhead.png", dpi=150)
    print(f"  Saved: {OUTPUT_DIR / 'fig_consensus_overhead.png'}")
    plt.close(fig)


def plot_blockchain_comparison():
    """Fig 5: Bar chart comparing BGP-Sentry TPS to other blockchains."""
    fig, ax = plt.subplots(figsize=(10, 6))

    blockchains = ['Bitcoin', 'Ethereum\n(PoW)', 'Ethereum\n(PoS)', 'BGP-Sentry\n(Ours)', 'Solana', 'Hyperledger\nFabric']
    tps_values = [7, 15, 30, 36.8, 830, 3500]
    colors = ['#FF9800', '#9C27B0', '#7B1FA2', '#2196F3', '#00BCD4', '#4CAF50']

    # Use log scale since range is huge
    bars = ax.barh(blockchains, tps_values, color=colors, edgecolor='white', linewidth=1.5, height=0.6)

    # Add TPS labels
    for bar, tps in zip(bars, tps_values):
        ax.text(bar.get_width() * 1.05, bar.get_y() + bar.get_height() / 2,
                f'{tps:,.0f} TPS', va='center', fontsize=11, fontweight='bold')

    # Highlight ours
    bars[3].set_edgecolor('red')
    bars[3].set_linewidth(3)

    ax.set_xscale('log')
    ax.set_xlabel('Network TPS (log scale, all network-wide)')
    ax.set_title('Blockchain TPS Comparison (network-wide)\n(BGP-Sentry vs Major Blockchains)')
    ax.set_xlim(1, 10000)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_blockchain_comparison.png", dpi=150)
    print(f"  Saved: {OUTPUT_DIR / 'fig_blockchain_comparison.png'}")
    plt.close(fig)


if __name__ == "__main__":
    print("Generating throughput benchmark plots...")
    plot_tps_vs_speed()
    plot_scaling_efficiency()
    plot_wall_time()
    plot_consensus_overhead()
    plot_blockchain_comparison()
    print(f"\nAll plots saved to: {OUTPUT_DIR}/")
