"""Viz 14: Agent Mobility (office changes over time)."""

from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path


def viz_mobility(history_agent_offices, output_dir):
    """Show how many agents changed office each turn and the distribution of changes."""
    if not history_agent_offices:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No agent mobility data available",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Agent Mobility")
        plt.tight_layout()
        plt.savefig(output_dir / "14_mobility.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    # Determine number of turns from the longest history.
    num_turns = max(len(v) for v in history_agent_offices.values())
    if num_turns < 2:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "Not enough turns to show mobility",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Agent Mobility")
        plt.tight_layout()
        plt.savefig(output_dir / "14_mobility.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    # Count office changes per turn and breakdown by transition type.
    changes_per_turn = [0] * (num_turns - 1)
    # Transition counts: (from_office_name, to_office_name) → total across all turns
    transition_counts: dict[tuple[str, str], int] = defaultdict(int)

    def office_name(office) -> str:
        if office is None:
            return "None"
        return office.name if hasattr(office, "name") else str(office)

    for offices in history_agent_offices.values():
        for t in range(1, len(offices)):
            prev = offices[t - 1]
            curr = offices[t]
            if prev != curr:
                changes_per_turn[t - 1] += 1
                transition_counts[(office_name(prev), office_name(curr))] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Left: changes per turn bar chart.
    ax1.bar(range(1, num_turns), changes_per_turn, color="#2980B9", alpha=0.85)
    ax1.set_xlabel("Turn", fontsize=11)
    ax1.set_ylabel("Number of Office Changes", fontsize=11)
    ax1.set_title("Office Changes Per Turn", fontsize=12, fontweight="bold")

    # Right: top transition types.
    top_transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    if top_transitions:
        labels = [f"{f} → {t}" for (f, t), _ in top_transitions]
        counts = [c for _, c in top_transitions]
        y_pos = range(len(labels))
        ax2.barh(list(y_pos), counts, color="#E67E22", alpha=0.85)
        ax2.set_yticks(list(y_pos))
        ax2.set_yticklabels(labels, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel("Total Changes", fontsize=11)
        ax2.set_title("Top Office Transition Types", fontsize=12, fontweight="bold")
    else:
        ax2.text(0.5, 0.5, "No transitions recorded",
                 ha="center", va="center", transform=ax2.transAxes)
        ax2.set_title("Office Transition Types")

    fig.suptitle("Agent Mobility", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "14_mobility.png", dpi=150, bbox_inches="tight")
    plt.close()
