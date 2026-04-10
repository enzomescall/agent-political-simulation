"""Viz 6: Election Heatmap."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Cap rows so the chart stays readable.
_MAX_ROWS = 60
_EXCLUDED_TIERS = {"MUNICIPALITY"}


def viz_election_heatmap(all_reports, ALL_PARTIES, output_dir):
    leg_elections = []
    for report in all_reports:
        for er in report.election_results:
            if er.election_type == "legislative":
                # Skip municipal elections to keep the chart readable.
                tier = er.place.tier.name if hasattr(er.place, "tier") else ""
                if tier in _EXCLUDED_TIERS:
                    continue
                leg_elections.append(
                    {
                        "turn": report.turn,
                        "place": er.place.name,
                        "vote_shares": er.vote_shares,
                    }
                )

    # If still too many, take the first _MAX_ROWS.
    leg_elections = leg_elections[:_MAX_ROWS]

    if not leg_elections:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            "No legislative elections found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Legislative Election Vote Shares (Heatmap)")
        plt.tight_layout()
        plt.savefig(
            output_dir / "06_election_heatmap.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    party_names = [p.name for p in ALL_PARTIES]
    row_labels = [f"T{e['turn']} {e['place']}" for e in leg_elections]

    matrix = np.zeros((len(leg_elections), len(party_names)))
    for i, elec in enumerate(leg_elections):
        for j, pname in enumerate(party_names):
            matrix[i, j] = elec["vote_shares"].get(pname, 0.0) * 100

    fig, ax = plt.subplots(
        figsize=(max(10, len(party_names) * 2), max(6, len(leg_elections) * 0.6 + 2))
    )
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=60)

    ax.set_xticks(range(len(party_names)))
    ax.set_xticklabels(party_names, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)

    plt.colorbar(im, ax=ax, label="Vote Share (%)", shrink=0.6)
    ax.set_title("Legislative Election Vote Shares (Federal & State)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "06_election_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
