"""Viz 2: Seat Evolution."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_seat_evolution(
    history_seats, ALL_PARTIES, num_turns, election_interval, output_dir, PARTY_COLORS
):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    tier_names = ["FEDERAL", "STATE", "MUNICIPALITY"]
    tier_labels = ["Federal", "State", "Municipal"]

    for ax_idx, (tier, label) in enumerate(zip(tier_names, tier_labels)):
        ax = axes[ax_idx]
        for party in ALL_PARTIES:
            ys = []
            for snap in history_seats:
                tier_data = snap.get(tier, {})
                ys.append(tier_data.get(party.name, 0))
            ax.plot(
                range(len(ys)),
                ys,
                color=PARTY_COLORS.get(party.name, "#888888"),
                linewidth=2.5,
                label=party.name,
                marker="o",
                markersize=4,
            )

        for epoch_turn in range(election_interval, len(ys), election_interval):
            ax.axvline(
                epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6
            )

        ax.set_ylabel("Seats", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Turn", fontsize=11)
    fig.suptitle("Seat Distribution Evolution", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(output_dir / "02_seat_evolution.png", dpi=150, bbox_inches="tight")
    plt.close()
