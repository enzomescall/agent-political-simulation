"""Viz 17: Party Discipline Heatmap."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def viz_party_discipline_heatmap(
    history_agent_party_standing, history_agent_ideologies, output_dir
):
    agent_ids = list(history_agent_party_standing.keys())[:20]

    if not agent_ids:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            "No agent data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Party Discipline Heatmap")
        plt.tight_layout()
        plt.savefig(
            output_dir / "17_party_discipline_heatmap.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    max_len = max(
        len(history_agent_party_standing.get(aid, [0.5])) for aid in agent_ids
    )
    matrix = []
    for aid in agent_ids:
        history = history_agent_party_standing.get(aid, [0.5])
        padded = list(history) + [0.5] * (max_len - len(history))
        matrix.append(padded)
    matrix = np.array(matrix, dtype=float)

    fig, ax = plt.subplots(figsize=(12, max(4, len(agent_ids) * 0.3)))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    ax.set_yticks(range(len(agent_ids)))
    ax.set_yticklabels(agent_ids, fontsize=8)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_title("Party Discipline Heatmap", fontsize=13, fontweight="bold")

    plt.colorbar(im, ax=ax, label="Party Standing", shrink=0.6)
    plt.tight_layout()
    plt.savefig(
        output_dir / "17_party_discipline_heatmap.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
