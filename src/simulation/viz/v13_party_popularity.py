"""Viz 13: Party Popularity."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_party_popularity(
    history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(14, 7))

    for party in ALL_PARTIES:
        pops = []
        for snap in history_standing:
            party_agents = snap.get(party.name, [])
            if party_agents:
                avg = sum(a["avg_pop"] for a in party_agents) / len(party_agents)
                pops.append(avg)
            else:
                pops.append(0.5)

        ax.plot(
            range(len(pops)),
            pops,
            color=PARTY_COLORS.get(party.name, "#888888"),
            linewidth=2.5,
            label=party.name,
            marker="o",
            markersize=4,
        )

    ax.set_xlim(-0.3, len(pops) - 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Popularity", fontsize=11)
    ax.set_title("Party Popularity Over Time", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "13_party_popularity.png", dpi=150, bbox_inches="tight")
    plt.close()
