"""Viz 14: Mobility."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_mobility(history_agent_offices, output_dir):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.text(
        0.5,
        0.5,
        "Agent mobility data not available",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.set_title("Agent Mobility")
    plt.tight_layout()
    plt.savefig(output_dir / "14_mobility.png", dpi=150, bbox_inches="tight")
    plt.close()
