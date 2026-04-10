"""Viz 22: Party Splits & Defections Timeline."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
from pathlib import Path


def viz_party_splits(all_reports, output_dir: Path, PARTY_COLORS: dict):
    """Bar chart showing split/defection events per turn, with event annotations."""

    split_counts = []
    defect_counts = []
    split_events_by_turn = []

    for report in all_reports:
        splits = 0
        defections = 0
        events = []
        for evt in getattr(report, "split_events", []):
            events.append(evt)
            if evt.startswith("PARTY SPLIT:"):
                splits += 1
            else:
                defections += 1
        split_counts.append(splits)
        defect_counts.append(defections)
        split_events_by_turn.append(events)

    num_turns = len(all_reports)
    if num_turns == 0 or (sum(split_counts) + sum(defect_counts)) == 0:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.text(0.5, 0.5, "No party splits or defections occurred",
                ha="center", va="center", transform=ax.transAxes, fontsize=12, color="gray")
        ax.set_title("Party Splits & Defections", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_dir / "22_party_splits.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    turns = list(range(1, num_turns + 1))
    fig, ax = plt.subplots(figsize=(max(12, num_turns * 0.4), 6))

    bar_w = 0.4
    xs = [t - 0.2 for t in turns]
    ax.bar(xs, split_counts, width=bar_w, label="Full Splinter Party Formed",
           color="#E74C3C", alpha=0.85)
    ax.bar([t + 0.2 for t in turns], defect_counts, width=bar_w, label="Solo Defection",
           color="#F39C12", alpha=0.85)

    # Annotate turns where splits happened
    for t_idx, events in enumerate(split_events_by_turn):
        if events:
            turn_num = t_idx + 1
            total = split_counts[t_idx] + defect_counts[t_idx]
            ax.text(turn_num, total + 0.05, str(total),
                    ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Events", fontsize=11)
    ax.set_xticks(turns)
    ax.set_xlim(0.5, num_turns + 0.5)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.set_title("Party Splits & Defections Timeline", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    # Side panel listing split events as text
    all_events_text = []
    for t_idx, events in enumerate(split_events_by_turn):
        for e in events:
            all_events_text.append(f"T{t_idx + 1}: {e}")

    if all_events_text:
        fig.text(0.01, 0.02, "\n".join(all_events_text[-20:]),
                 fontsize=6, va="bottom", ha="left",
                 wrap=True, family="monospace",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_dir / "22_party_splits.png", dpi=150, bbox_inches="tight")
    plt.close()
