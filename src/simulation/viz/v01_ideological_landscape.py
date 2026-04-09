"""Viz 1: Ideological Landscape."""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.models import Archetype, OfficeType


def viz_ideological_landscape(
    initial_agents_data, ALL_PARTIES, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(14, 10))

    ax.axhspan(0, 1, xmin=0.5, xmax=1, alpha=0.04, color="blue", zorder=0)
    ax.axhspan(0, 1, xmin=0, xmax=0.5, alpha=0.04, color="red", zorder=0)
    ax.axhspan(-1, 0, xmin=0, xmax=0.5, alpha=0.04, color="brown", zorder=0)
    ax.axhspan(-1, 0, xmin=0.5, xmax=1, alpha=0.04, color="green", zorder=0)

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)

    archetype_markers = {
        Archetype.LOYALIST: "o",
        Archetype.POPULIST: "s",
        Archetype.IDEOLOGUE: "^",
    }
    office_sizes = {
        OfficeType.PRESIDENT: 200,
        OfficeType.GOVERNOR: 200,
        OfficeType.MAYOR: 200,
        OfficeType.CONGRESSPERSON: 80,
        OfficeType.STATE_ASSEMBLYPERSON: 80,
        OfficeType.COUNCILPERSON: 40,
        None: 40,
    }

    for archetype, marker in archetype_markers.items():
        for party in ALL_PARTIES:
            color = PARTY_COLORS.get(party.name, "#888888")
            agents_subset = [
                d
                for d in initial_agents_data.values()
                if d["party"] == party.name and d["archetype"] == archetype
            ]
            if not agents_subset:
                continue
            xs = [d["econ"] for d in agents_subset]
            ys = [d["soc"] for d in agents_subset]
            sizes = [office_sizes.get(d["office"], 40) for d in agents_subset]
            ax.scatter(
                xs,
                ys,
                c=color,
                marker=marker,
                s=sizes,
                alpha=0.7,
                edgecolors="white",
                linewidths=0.4,
                zorder=3,
            )

    for party in ALL_PARTIES:
        color = PARTY_COLORS.get(party.name, "#888888")
        agents_subset = [
            d for d in initial_agents_data.values() if d["party"] == party.name
        ]
        if not agents_subset:
            continue
        cx = np.mean([d["econ"] for d in agents_subset])
        cy = np.mean([d["soc"] for d in agents_subset])
        ax.scatter(
            cx,
            cy,
            c=color,
            marker="*",
            s=400,
            edgecolors="black",
            linewidths=1.0,
            zorder=5,
        )
        ax.annotate(
            party.name,
            (cx, cy),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
            fontweight="bold",
            color=color,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
        )

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_xlabel("Economic Axis (Left ← → Right)", fontsize=11)
    ax.set_ylabel("Social Axis (Conservative ← → Progressive)", fontsize=11)
    ax.set_title("Ideological Landscape", fontsize=14, fontweight="bold")

    party_patches = [
        mpatches.Patch(color=PARTY_COLORS.get(p.name, "#888888"), label=p.name)
        for p in ALL_PARTIES
    ]
    archetype_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="gray",
            linestyle="None",
            markersize=8,
            label="LOYALIST",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="s",
            color="gray",
            linestyle="None",
            markersize=8,
            label="POPULIST",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="^",
            color="gray",
            linestyle="None",
            markersize=8,
            label="IDEOLOGUE",
        ),
    ]
    size_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="gray",
            linestyle="None",
            markersize=14,
            label="Executive (200)",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="gray",
            linestyle="None",
            markersize=9,
            label="Legislative (80)",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="gray",
            linestyle="None",
            markersize=6,
            label="None (40)",
        ),
    ]
    ax.legend(
        handles=party_patches + archetype_handles + size_handles,
        loc="lower right",
        fontsize=8,
        framealpha=0.9,
        ncol=3,
    )

    plt.tight_layout()
    plt.savefig(
        output_dir / "01_ideological_landscape.png", dpi=150, bbox_inches="tight"
    )
    plt.close()
