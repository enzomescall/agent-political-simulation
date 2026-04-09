"""Viz 5: IG Satisfaction."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_ig_satisfaction(
    history_ig_sat, ALL_IGs, num_turns, election_interval, output_dir
):
    ig_names = [ig.name for ig in ALL_IGs]
    ig_colors = plt.cm.tab10(list(range(len(ig_names))))

    fig, ax = plt.subplots(figsize=(14, 7))

    for ig_idx, ig_name in enumerate(ig_names):
        avg_sats = []
        for snap in history_ig_sat:
            state_vals = list(snap.get(ig_name, {}).values())
            avg_sats.append(sum(state_vals) / len(state_vals) if state_vals else 0.5)
        ax.plot(
            range(len(avg_sats)),
            avg_sats,
            color=ig_colors[ig_idx],
            linewidth=2.5,
            label=ig_name[:25],
            marker="o",
            markersize=4,
        )

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1.2, alpha=0.7)
    for epoch_turn in range(election_interval, len(avg_sats), election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlim(-0.3, len(avg_sats) - 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Satisfaction (0–1)", fontsize=11)
    ax.set_title(
        "Interest Group Satisfaction Over Time", fontsize=13, fontweight="bold"
    )
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "05_ig_satisfaction.png", dpi=150, bbox_inches="tight")
    plt.close()
