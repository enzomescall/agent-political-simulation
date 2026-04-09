"""Viz 19: Veto Analysis."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_veto_analysis(history_veto_counts, num_turns, election_interval, output_dir):
    vetoed = [v[0] for v in history_veto_counts]
    overrides = [v[1] for v in history_veto_counts]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(vetoed))
    ax.bar(x, vetoed, color="#E74C3C", label="Vetoed", alpha=0.85)
    ax.bar(x, overrides, bottom=vetoed, color="#F39C12", label="Overrides", alpha=0.85)

    for epoch_turn in range(election_interval, len(vetoed), election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title("Veto Analysis", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "19_veto_analysis.png", dpi=150, bbox_inches="tight")
    plt.close()
