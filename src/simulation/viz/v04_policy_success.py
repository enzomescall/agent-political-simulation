"""Viz 4: Policy Success."""

from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path


def viz_policy_success(all_reports, output_dir):
    policy_proposed, policy_passed = defaultdict(int), defaultdict(int)

    for report in all_reports:
        for vr in report.vote_results:
            name = vr.policy.name
            policy_proposed[name] += 1
            if vr.passed:
                policy_passed[name] += 1

    sorted_policies = sorted(policy_proposed.items(), key=lambda x: x[1], reverse=True)[
        :15
    ]

    fig, ax = plt.subplots(figsize=(12, 8))

    policy_names = [p[0][:40] for p in sorted_policies]
    totals = [p[1] for p in sorted_policies]
    passed_counts = [policy_passed.get(p[0], 0) for p in sorted_policies]

    y_pos = list(range(len(policy_names)))
    ax.barh(
        y_pos, totals, color="lightgray", alpha=0.9, label="Total Proposed", height=0.6
    )
    ax.barh(
        y_pos, passed_counts, color="#27AE60", alpha=0.85, label="Passed", height=0.6
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(policy_names, fontsize=8)
    ax.set_xlabel("Count", fontsize=11)
    ax.set_title(
        "Top 15 Policy Names — Proposed vs Passed", fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.invert_yaxis()

    plt.tight_layout()
    plt.savefig(output_dir / "04_policy_success.png", dpi=150, bbox_inches="tight")
    plt.close()
