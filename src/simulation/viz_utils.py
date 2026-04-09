"""
Shared visualization utilities.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


def setup_figure(figsize=(12, 8)):
    """Create a figure with standard settings."""
    return plt.subplots(figsize=figsize)


def save_figure(fig, output_path, dpi=150):
    """Save figure and close it."""
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()


def create_party_colormap(ALL_PARTIES):
    """Create a color map for parties."""
    default_colors = [
        "#C0392B",
        "#2980B9",
        "#27AE60",
        "#E67E22",
        "#8E44AD",
        "#F39C12",
        "#1ABC9C",
        "#E74C3C",
    ]
    return {
        p.name: default_colors[i % len(default_colors)]
        for i, p in enumerate(ALL_PARTIES)
    }


def add_epoch_lines(ax, election_interval, max_turn, linestyle=":", alpha=0.5):
    """Add vertical lines for election epochs."""
    for epoch_turn in range(election_interval, max_turn, election_interval):
        ax.axvline(
            epoch_turn, color="black", linewidth=1.5, linestyle=linestyle, alpha=alpha
        )
