"""Viz 9: Action Breakdown."""

from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from src.actions.base import ActionType


def viz_action_breakdown(all_reports, ALL_PARTIES, output_dir):
    action_type_labels = {
        ActionType.VOTE: "VOTE",
        ActionType.TAKE_POSITION: "TAKE_POSITION",
        ActionType.BUILD_RELATIONSHIP: "BUILD_RELATIONSHIP",
        ActionType.CAMPAIGN: "CAMPAIGN",
        ActionType.REQUEST_VOTE: "REQUEST_VOTE",
        ActionType.ALLOCATE_BUDGET: "ALLOCATE_BUDGET",
        ActionType.VETO: "VETO",
        ActionType.ISSUE_DIRECTIVE: "ISSUE_DIRECTIVE",
        ActionType.ENFORCE_DISCIPLINE: "ENFORCE_DISCIPLINE",
        ActionType.EXPEL_MEMBER: "EXPEL_MEMBER",
        ActionType.IDEOLOGY_PUSH: "IDEOLOGY_PUSH",
        ActionType.PARTY_OUTREACH: "PARTY_OUTREACH",
        ActionType.PARTY_MERGE: "PARTY_MERGE",
    }

    party_names = [p.name for p in ALL_PARTIES]

    party_action_counts = {p.name: defaultdict(int) for p in ALL_PARTIES}
    all_action_types = set()
    for report in all_reports:
        for action in report.actions_taken:
            party_name = action.actor.party.name
            atype = action.action_type
            all_action_types.add(atype.name)
            if party_name in party_action_counts:
                party_action_counts[party_name][atype.name] += 1

    all_labels = sorted(all_action_types)

    fig, ax = plt.subplots(figsize=(16, 6))

    colors_cycle = plt.cm.Set3(np.linspace(0, 1, len(all_labels)))
    y_pos = np.arange(len(party_names))
    lefts = np.zeros(len(party_names))

    for lbl_idx, (lbl, color) in enumerate(zip(all_labels, colors_cycle)):
        widths = []
        for pname in party_names:
            counts = party_action_counts[pname]
            total = sum(counts.values())
            widths.append(counts.get(lbl, 0) / total * 100 if total > 0 else 0)
        ax.barh(
            y_pos, widths, left=lefts, color=color, label=lbl, height=0.6, alpha=0.9
        )
        lefts += np.array(widths)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(party_names, fontsize=10)
    ax.set_xlabel("Percentage of Actions (%)", fontsize=11)
    ax.set_title("Action Type Breakdown by Party", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "09_action_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()
