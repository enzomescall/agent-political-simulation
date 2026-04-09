"""Viz 11: Exec Actions Over Time."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def viz_exec_actions_over_time(
    history_exec_actions, num_turns, election_interval, output_dir
):
    action_types = set()
    for turn_actions in history_exec_actions:
        action_types.update(turn_actions.keys())

    if not action_types:
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.text(
            0.5,
            0.5,
            "No executive actions recorded",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Executive Actions Over Time", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(
            output_dir / "11_exec_actions_over_time.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    all_labels = sorted(action_types)
    colors = plt.cm.Set2(np.linspace(0, 1, len(all_labels)))

    x = np.arange(len(history_exec_actions))
    bottoms = np.zeros(len(history_exec_actions))

    for label, color in zip(all_labels, colors):
        heights = [ta.get(label, 0) for ta in history_exec_actions]
        ax.bar(
            x, heights, bottom=bottoms, label=label, color=color, alpha=0.85, width=0.7
        )
        bottoms += np.array(heights)

    for epoch_turn in range(
        election_interval, len(history_exec_actions), election_interval
    ):
        ax.axvline(
            epoch_turn - 0.5, color="black", linewidth=1.5, linestyle=":", alpha=0.5
        )

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Action Count", fontsize=11)
    ax.set_title("Executive Actions Over Time", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(x)
    ax.legend(fontsize=8, framealpha=0.9, loc="upper right")

    plt.tight_layout()
    plt.savefig(
        output_dir / "11_exec_actions_over_time.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
