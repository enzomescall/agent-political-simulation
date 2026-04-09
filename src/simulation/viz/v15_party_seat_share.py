"""Viz 15: Party Seat Share."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_party_seat_share(
    history_party_total_seats, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(14, 7))

    for party in ALL_PARTIES:
        seats = history_party_total_seats.get(party.name, [0] * (num_turns + 1))
        ax.plot(
            range(num_turns + 1),
            seats,
            color=PARTY_COLORS.get(party.name, "#888888"),
            linewidth=2.5,
            label=party.name,
            marker="o",
            markersize=4,
        )

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Total Seats", fontsize=11)
    ax.set_title("Party Seat Share Over Time", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "15_party_seat_share.png", dpi=150, bbox_inches="tight")
    plt.close()
