"""Viz 12: Exec Timeline."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Only show federal/state execs (not all 800+ municipal mayors).
_MAX_PLACES = 60
_EXCLUDED_TIERS = {"MUNICIPALITY"}


def viz_exec_timeline(
    history_exec_holders, governments, ALL_PARTIES, output_dir, PARTY_COLORS
):
    # Filter to non-municipal places, then cap total shown.
    exec_places = [
        pid
        for pid, gov in governments.items()
        if gov.executive
        and gov.place.tier.name not in _EXCLUDED_TIERS
    ]

    # If still too many (e.g., lots of states), cap at _MAX_PLACES.
    exec_places = exec_places[:_MAX_PLACES]

    party_name_map = {p.name: p.name for p in ALL_PARTIES}

    if not exec_places:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.text(
            0.5,
            0.5,
            "No executives found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Executive Timeline", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_dir / "12_exec_timeline.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(18, max(6, len(exec_places) * 0.6)))

    # Build y-axis labels from place names (not IDs).
    place_labels = [
        governments[pid].place.name if pid in governments else str(pid)
        for pid in exec_places
    ]

    max_turns = 0
    for i, place_id in enumerate(exec_places):
        holders = history_exec_holders.get(place_id, [])
        max_turns = max(max_turns, len(holders))

        start = 0
        prev_name = None
        prev_party = None
        for turn_idx, (name, party) in enumerate(holders):
            if name != prev_name and prev_name is not None:
                color = PARTY_COLORS.get(party_name_map.get(prev_party, ""), "#888888")
                ax.barh(
                    i,
                    turn_idx - start,
                    left=start,
                    height=0.65,
                    color=color,
                    alpha=0.9,
                    edgecolor="white",
                )

                duration = turn_idx - start
                if duration > 2:
                    short_name = (
                        prev_name[:12] + "..." if len(prev_name) > 12 else prev_name
                    )
                    ax.text(
                        start + duration / 2,
                        i,
                        short_name,
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white",
                        fontweight="bold",
                    )
                start = turn_idx
            prev_name = name
            prev_party = party

        if prev_name is not None:
            color = PARTY_COLORS.get(party_name_map.get(prev_party, ""), "#888888")
            ax.barh(
                i,
                len(holders) - start,
                left=start,
                height=0.65,
                color=color,
                alpha=0.9,
                edgecolor="white",
            )

            duration = len(holders) - start
            if duration > 2:
                short_name = (
                    prev_name[:12] + "..." if len(prev_name) > 12 else prev_name
                )
                ax.text(
                    start + duration / 2,
                    i,
                    short_name,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )

    ax.set_yticks(range(len(exec_places)))
    ax.set_yticklabels(place_labels, fontsize=9)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_xlim(0, max(1, max_turns))
    ax.set_title("Executive Timeline (Federal & State)", fontsize=13, fontweight="bold")

    party_patches = [
        mpatches.Patch(color=PARTY_COLORS.get(p.name, "#888888"), label=p.name)
        for p in ALL_PARTIES
    ]
    ax.legend(handles=party_patches, loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig(output_dir / "12_exec_timeline.png", dpi=150, bbox_inches="tight")
    plt.close()
