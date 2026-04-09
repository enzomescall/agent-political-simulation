"""Viz 20: Ideology Drift Agents."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_ideology_drift_agents(history_agent_ideologies, output_dir):
    agent_ids = list(history_agent_ideologies.keys())[:20]

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
        ax.set_title("Agent Ideology Drift")
        plt.tight_layout()
        plt.savefig(
            output_dir / "20_ideology_drift_agents.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    for aid in agent_ids:
        ideologies = history_agent_ideologies.get(aid, [])
        if ideologies:
            econs = [i[0] for i in ideologies]
            socs = [i[1] for i in ideologies]
            ax.plot(econs, socs, linewidth=1.5, marker="o", markersize=3, alpha=0.7)

    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Economic", fontsize=11)
    ax.set_ylabel("Social", fontsize=11)
    ax.set_title("Agent Ideology Drift", fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(
        output_dir / "20_ideology_drift_agents.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
