"""Shared matplotlib styling for paper figures.

Call `setup_ieee_column()` at the top of every fig_*.py script to get
consistent fonts, sizes, and colors across the whole paper.
"""
from __future__ import annotations


def setup_ieee_column():
    """Configure matplotlib rcParams for IEEE double-column papers.

    Target: ~3.4 inch single-column figures at 600 dpi, Times/serif fonts,
    compact sizing suitable for \\columnwidth \\includegraphics.
    """
    import matplotlib as mpl

    mpl.rcParams.update({
        # Fonts
        "font.family": "serif",
        "font.serif": ["Times", "Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "legend.title_fontsize": 7,
        # Lines and markers
        "lines.linewidth": 1.2,
        "lines.markersize": 4,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        # Layout
        "figure.figsize": (3.4, 2.3),
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        # Grid & axes
        "axes.grid": True,
        "grid.linewidth": 0.3,
        "grid.color": "0.85",
        "axes.spines.top": False,
        "axes.spines.right": False,
        # Legend
        "legend.frameon": False,
    })


# Paper color palette — picked to survive B&W printing
COLORS = {
    "primary":   "#1f77b4",  # blue — main "BGP-Sentry" line
    "secondary": "#ff7f0e",  # orange — ablation / contrast
    "tertiary":  "#2ca02c",  # green — positive / success
    "negative":  "#d62728",  # red — attacks / errors
    "muted":     "#7f7f7f",  # gray — baseline / background
    "highlight": "#9467bd",  # purple — callouts
}

# Per-attack-type colors (consistent across all figures)
ATTACK_COLORS = {
    "PREFIX_HIJACK":               "#1f77b4",
    "SUBPREFIX_HIJACK":            "#ff7f0e",
    "BOGON_INJECTION":             "#2ca02c",
    "ROUTE_FLAPPING":              "#d62728",
    "FORGED_ORIGIN_PREFIX_HIJACK": "#9467bd",
    "ACCIDENTAL_ROUTE_LEAK":       "#8c564b",
}

# Consensus status colors (matches paper's fig_consensus_breakdown)
CONSENSUS_COLORS = {
    "CONFIRMED":              "#2ca02c",
    "INSUFFICIENT_CONSENSUS": "#ff7f0e",
    "SINGLE_WITNESS":         "#7f7f7f",
}
