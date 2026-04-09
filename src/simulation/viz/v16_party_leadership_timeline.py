"""Viz 16: Party Leadership Timeline."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path


def viz_party_leadership_timeline(
    history_party_leaders, ALL_PARTIES, output_dir, PARTY_COLORS
):
    party_ids = [p.id for p in ALL_PARTIES]
    party_names = [p.name for p in ALL_PARTIES]

    if not party_ids:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.text(
            0.5,
            0.5,
            "No parties found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Party Leadership Timeline", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(
            output_dir / "16_party_leadership_timeline.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(16, max(6, len(party_ids) * 0.5)))

    max_turns = 0
    for i, party_id in enumerate(party_ids):
        leaders = history_party_leaders.get(party_id, ["none"])
        max_turns = max(max_turns, len(leaders))

        start = 0
        prev_leader = None
        for turn_idx, leader_name in enumerate(leaders):
            if leader_name != prev_leader and prev_leader is not None:
                color = PARTY_COLORS.get(party_names[i], "#888888")
                ax.barh(
                    i,
                    turn_idx - start,
                    left=start,
                    height=0.6,
                    color=color,
                    alpha=0.85,
                    edgecolor="white",
                )
                start = turn_idx
            prev_leader = leader_name

        if prev_leader is not None:
            color = PARTY_COLORS.get(party_names[i], "#888888")
            ax.barh(
                i,
                len(leaders) - start,
                left=start,
                height=0.6,
                color=color,
                alpha=0.85,
                edgecolor="white",
            )

    ax.set_yticks(range(len(party_ids)))
    ax.set_yticklabels(party_names, fontsize=9)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_xlim(0, max(1, max_turns))
    ax.set_title("Party Leadership Timeline", fontsize=13, fontweight="bold")

    party_patches = [
        mpatches.Patch(color=PARTY_COLORS.get(p.name, "#888888"), label=p.name)
        for p in ALL_PARTIES
    ]
    ax.legend(handles=party_patches, loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig(
        output_dir / "16_party_leadership_timeline.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
