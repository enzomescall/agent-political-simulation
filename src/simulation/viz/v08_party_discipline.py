"""Viz 8: Party Discipline."""

import matplotlib.pyplot as plt
from pathlib import Path


def viz_party_discipline(
    history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
):
    time_points = [0, num_turns // 2, num_turns]
    party_names = [p.name for p in ALL_PARTIES]

    fig, ax = plt.subplots(figsize=(14, 7))

    for p_idx, pname in enumerate(party_names):
        for t_idx, tp in enumerate(time_points):
            if tp < len(history_standing):
                snap = history_standing[tp]
                standings = [a["standing"] for a in snap.get(pname, [])]
                if standings:
                    pos = p_idx * 3 + t_idx
                    bp = ax.boxplot(
                        [standings], positions=[pos], widths=0.6, patch_artist=True
                    )
                    color = PARTY_COLORS.get(pname, "#888888")
                    bp["boxes"][0].set_facecolor(color)
                    bp["boxes"][0].set_alpha(0.5 + t_idx * 0.25)

    ax.set_xticks([p_idx * 3 + 1 for p_idx in range(len(party_names))])
    ax.set_xticklabels(party_names, fontsize=10)
    ax.set_ylabel("Party Standing", fontsize=11)
    ax.set_title("Party Discipline Distribution", fontsize=13, fontweight="bold")
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_dir / "08_party_discipline.png", dpi=150, bbox_inches="tight")
    plt.close()
