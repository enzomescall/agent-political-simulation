"""Viz 1b: Ideological Landscape Animated GIF - shows ideology drift at each epoch."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict
from pathlib import Path

from src.models import Archetype, OfficeType

_MAX_AGENTS_PER_FRAME = 10000  # downsample above this to avoid OOM


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

    archetype_markers = {
        Archetype.LOYALIST: "o",
        Archetype.POPULIST: "s",
        Archetype.IDEOLOGUE: "^",
    }

    # Pre-group agent IDs by (party_name, archetype) to avoid re-scanning every frame
    groups: dict[tuple[str, Archetype], list[str]] = defaultdict(list)
    all_agent_ids = list(history_agent_ideologies.keys())
    for agent_id in all_agent_ids:
        info = initial_agents_data.get(agent_id, {})
        pname = info.get("party")
        arch = info.get("archetype")
        if pname and arch is not None:
            groups[(pname, arch)].append(agent_id)

    # Downsample if needed — deterministic so same agents appear each frame
    import random as _rng
    _r = _rng.Random(42)
    total_agents = len(all_agent_ids)
    if total_agents > _MAX_AGENTS_PER_FRAME:
        sample_ratio = _MAX_AGENTS_PER_FRAME / total_agents
        sampled_groups: dict[tuple[str, Archetype], list[str]] = {}
        for key, ids in groups.items():
            k = max(1, round(len(ids) * sample_ratio))
            sampled_groups[key] = _r.sample(ids, k)
        groups = sampled_groups
        print(f"  (Downsampling GIF to ~{_MAX_AGENTS_PER_FRAME} agents from {total_agents})")

    frame_paths = []

    for epoch_turn in epochs:
        fig, ax = plt.subplots(figsize=(10, 8))

        ax.axhspan(0, 1, xmin=0.5, xmax=1, alpha=0.04, color="blue", zorder=0)
        ax.axhspan(0, 1, xmin=0, xmax=0.5, alpha=0.04, color="red", zorder=0)
        ax.axhspan(-1, 0, xmin=0, xmax=0.5, alpha=0.04, color="brown", zorder=0)
        ax.axhspan(-1, 0, xmin=0.5, xmax=1, alpha=0.04, color="green", zorder=0)
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.axvline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)

        party_centroids: dict[str, list[tuple[float, float]]] = defaultdict(list)

        for party in ALL_PARTIES:
            color = PARTY_COLORS.get(party.name, "#888888")
            for archetype, marker in archetype_markers.items():
                ids = groups.get((party.name, archetype), [])
                if not ids:
                    continue
                xs, ys = [], []
                for agent_id in ids:
                    history = history_agent_ideologies.get(agent_id)
                    if history and epoch_turn < len(history):
                        econ, soc = history[epoch_turn]
                        xs.append(econ)
                        ys.append(soc)
                if xs:
                    ax.scatter(
                        xs, ys,
                        c=color,
                        marker=marker,
                        s=20,
                        alpha=0.6,
                        edgecolors="none",
                        zorder=3,
                    )
                    party_centroids[party.name].extend(zip(xs, ys))

        # Party centroid stars
        for party in ALL_PARTIES:
            color = PARTY_COLORS.get(party.name, "#888888")
            points = party_centroids.get(party.name, [])
            if points:
                cx = float(np.mean([p[0] for p in points]))
                cy = float(np.mean([p[1] for p in points]))
                ax.scatter(cx, cy, c=color, marker="*", s=300,
                           edgecolors="black", linewidths=0.8, zorder=5)
                ax.annotate(
                    party.name, (cx, cy),
                    textcoords="offset points", xytext=(6, 6),
                    fontsize=7, fontweight="bold", color=color,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
                )

        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel("Economic Axis", fontsize=10)
        ax.set_ylabel("Social Axis", fontsize=10)
        ax.set_title(f"Ideological Landscape — Turn {epoch_turn}", fontsize=12, fontweight="bold")
        plt.tight_layout()

        frame_path = epoch_dir / f"epoch_{epoch_turn:03d}.png"
        plt.savefig(frame_path, dpi=80, bbox_inches="tight")
        plt.close()
        frame_paths.append(frame_path)

    if not frame_paths:
        return

    # Build GIF loading one frame at a time to avoid holding all in RAM
    gif_path = output_dir / "01_ideological_landscape.gif"
    first = PILImage.open(frame_paths[0]).convert("P", dither=PILImage.Dither.NONE)
    rest = []
    for p in frame_paths[1:]:
        img = PILImage.open(p).convert("P", dither=PILImage.Dither.NONE)
        rest.append(img)

    first.save(
        gif_path, save_all=True, append_images=rest,
        duration=800, loop=0, optimize=False,
    )
    # Free memory
    first.close()
    for img in rest:
        img.close()

    print(f"  Saved GIF to {gif_path}")
