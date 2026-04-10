"""Viz 23: Party Membership Swaps Over Time."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
from pathlib import Path


def viz_party_swaps(
    history_party_membership, initial_agents_data, output_dir: Path, PARTY_COLORS: dict
):
    """
    Two panels:
    - Top: stacked area chart of party membership count over time
    - Bottom: bar chart of membership changes (joins/leaves) per turn
    """
    if not history_party_membership:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.text(0.5, 0.5, "No membership history", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color="gray")
        ax.set_title("Party Membership Over Time", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_dir / "23_party_swaps.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    num_turns = len(history_party_membership)
    turns = list(range(num_turns))

    # Collect all party names ever seen
    all_party_names: set[str] = set()
    for snap in history_party_membership:
        all_party_names.update(snap.values())
    all_party_names = sorted(all_party_names)

    # Membership counts per party per turn
    counts: dict[str, list[int]] = {pn: [] for pn in all_party_names}
    for snap in history_party_membership:
        c: dict[str, int] = defaultdict(int)
        for pname in snap.values():
            c[pname] += 1
        for pn in all_party_names:
            counts[pn].append(c.get(pn, 0))

    # Net changes per turn (number of agents who changed party since last turn)
    changes_per_turn = [0]
    for t in range(1, num_turns):
        prev = history_party_membership[t - 1]
        curr = history_party_membership[t]
        changed = sum(
            1 for aid in curr
            if aid in prev and curr[aid] != prev[aid]
        )
        changes_per_turn.append(changed)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(max(12, num_turns * 0.4), 10),
                                    gridspec_kw={"height_ratios": [3, 1]})

    # Stacked area
    stack_vals = [counts[pn] for pn in all_party_names]
    colors = [PARTY_COLORS.get(pn, f"#{hash(pn) & 0xFFFFFF:06x}") for pn in all_party_names]
    ax1.stackplot(turns, stack_vals, labels=all_party_names, colors=colors, alpha=0.85)
    ax1.set_xlim(0, num_turns - 1)
    ax1.set_xlabel("Turn", fontsize=11)
    ax1.set_ylabel("Member Count", fontsize=11)
    ax1.set_title("Party Membership Over Time", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=8, ncol=2)

    # Bar chart of membership changes
    ax2.bar(turns, changes_per_turn, color="#3498DB", alpha=0.8)
    ax2.set_xlim(0, num_turns - 1)
    ax2.set_xlabel("Turn", fontsize=11)
    ax2.set_ylabel("Agents Changed Party", fontsize=11)
    ax2.set_title("Party Membership Changes Per Turn", fontsize=11)
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    plt.tight_layout()
    plt.savefig(output_dir / "23_party_swaps.png", dpi=150, bbox_inches="tight")
    plt.close()
