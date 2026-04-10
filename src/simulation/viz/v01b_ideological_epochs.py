"""Viz 1b: Ideological Landscape Animated GIF - shows ideology drift at each epoch."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

from src.models import Archetype, OfficeType


def viz_ideological_epochs(
    history_agent_ideologies,
    initial_agents_data,
    ALL_PARTIES,
    output_dir,
    PARTY_COLORS,
    election_interval,
    num_turns,
):
    """Generate ideological landscape snapshots at each epoch and combine into GIF."""
    try:
        from PIL import Image as PILImage
    except ImportError:
        print("  (PIL not available, skipping epoch GIF)")
        return

    epoch_dir = output_dir / "ideological_epochs"
    epoch_dir.mkdir(exist_ok=True)

    epochs = list(range(0, num_turns + 1, election_interval))
    if epochs[-1] != num_turns:
        epochs.append(num_turns)

    frames = []

    for epoch_turn in epochs:
        fig, ax = plt.subplots(figsize=(12, 9))

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

        # Get agents at this epoch
        for archetype, marker in archetype_markers.items():
            for party in ALL_PARTIES:
                color = PARTY_COLORS.get(party.name, "#888888")

                for agent_id, ideology_history in history_agent_ideologies.items():
                    if epoch_turn < len(ideology_history):
                        econ, soc = ideology_history[epoch_turn]

                        initial = initial_agents_data.get(agent_id, {})
                        if (
                            initial.get("party") == party.name
                            and initial.get("archetype") == archetype
                        ):
                            ax.scatter(
                                econ,
                                soc,
                                c=color,
                                marker=marker,
                                s=60,
                                alpha=0.7,
                                edgecolors="white",
                                linewidths=0.4,
                                zorder=3,
                            )

        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel("Economic Axis", fontsize=10)
        ax.set_ylabel("Social Axis", fontsize=10)
        ax.set_title(
            f"Ideological Landscape - Turn {epoch_turn}", fontsize=12, fontweight="bold"
        )

        plt.tight_layout()

        frame_path = epoch_dir / f"epoch_{epoch_turn:03d}.png"
        plt.savefig(frame_path, dpi=100, bbox_inches="tight")
        plt.close()

        frames.append(PILImage.open(frame_path))

    if frames:
        gif_path = output_dir / "01_ideological_landscape.gif"
        frames[0].save(
            gif_path, save_all=True, append_images=frames[1:], duration=800, loop=0
        )
        print(f"  Saved GIF to {gif_path}")
