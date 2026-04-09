"""Viz 10: Agent Stories."""

from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path


def viz_agent_stories(
    initial_agents_data,
    history_standing,
    all_reports,
    ALL_PARTIES,
    output_dir,
    PARTY_COLORS,
):
    proposer_counts = defaultdict(int)
    for report in all_reports:
        for vr in report.vote_results:
            if vr.passed and vr.proposer is not None:
                proposer_counts[vr.proposer.name] += 1

    top_proposers = sorted(proposer_counts.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]

    fig, ax = plt.subplots(figsize=(12, 6))

    if top_proposers:
        names = [n[:25] for n, c in top_proposers]
        counts = [c for n, c in top_proposers]
        ax.barh(range(len(names)), counts, color="#2980B9", alpha=0.85)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Passed Policies Proposed", fontsize=9)

    ax.set_title("Top Policy Proposers", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "10_agent_stories.png", dpi=150, bbox_inches="tight")
    plt.close()
