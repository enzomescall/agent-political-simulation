"""Viz 21: IG Radicalization."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_ig_radicalization(history_ig_ideologies, ig_names, output_dir):
    fig, ax = plt.subplots(figsize=(12, 8))

    colors = plt.cm.tab10(list(range(len(ig_names))))

    for idx, ig_name in enumerate(ig_names):
        ideologies = history_ig_ideologies.get(ig_name, [])
        if ideologies:
            econs = [i[0] for i in ideologies]
            socs = [i[1] for i in ideologies]
            ax.plot(
                econs,
                socs,
                linewidth=2,
                marker="o",
                markersize=4,
                label=ig_name[:25],
                color=colors[idx],
            )

    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Economic", fontsize=11)
    ax.set_ylabel("Social", fontsize=11)
    ax.set_title("Interest Group Radicalization", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "21_ig_radicalization.png", dpi=150, bbox_inches="tight")
    plt.close()
