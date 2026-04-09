"""Viz 7: Popularity Trajectories."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_popularity_trajectories(
    initial_agents_data,
    history_standing,
    ALL_PARTIES,
    num_turns,
    election_interval,
    output_dir,
    PARTY_COLORS,
):
    key_agents = [
        d["name"] for d in initial_agents_data.values() if d["office"] is not None
    ][:5]

    fig, ax = plt.subplots(figsize=(14, 7))

    for name in key_agents:
        pops = []
        for snap in history_standing:
            for party_agents in snap.values():
                for a in party_agents:
                    if a["name"] == name:
                        pops.append(a["avg_pop"])
                        break

        if pops:
            party_name = next(
                (d["party"] for d in initial_agents_data.values() if d["name"] == name),
                "Unknown",
            )
            color = PARTY_COLORS.get(party_name, "#555555")
            ax.plot(
                range(len(pops)),
                pops,
                color=color,
                linewidth=2.5,
                label=name,
                marker="o",
                markersize=5,
            )

    for epoch_turn in range(election_interval, num_turns + 1, election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlim(-0.3, num_turns + 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Popularity", fontsize=11)
    ax.set_title(
        "Popularity Trajectories — Key Executives", fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(
        output_dir / "07_popularity_trajectories.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
