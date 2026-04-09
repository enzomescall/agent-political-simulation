"""Viz 18: Party Ideology Drift."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_party_ideology_drift(
    history_party_ideologies, ALL_PARTIES, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(12, 8))

    for party in ALL_PARTIES:
        ideologies = history_party_ideologies.get(party.id, [])
        if ideologies:
            econs = [i[0] for i in ideologies]
            socs = [i[1] for i in ideologies]
            color = PARTY_COLORS.get(party.name, "#888888")
            ax.plot(
                econs,
                socs,
                linewidth=2,
                marker="o",
                markersize=4,
                label=party.name,
                color=color,
            )
            ax.scatter(
                econs[0],
                socs[0],
                s=100,
                marker="o",
                color=color,
            )
            ax.scatter(
                econs[-1],
                socs[-1],
                s=100,
                marker="s",
                color=color,
            )

    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Economic", fontsize=11)
    ax.set_ylabel("Social", fontsize=11)
    ax.set_title("Party Ideology Drift", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(
        output_dir / "18_party_ideology_drift.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
