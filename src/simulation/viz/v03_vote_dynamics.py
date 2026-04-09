"""Viz 3: Vote Dynamics."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def viz_vote_dynamics(all_reports, num_turns, election_interval, output_dir):
    turn_passed, turn_failed = [], []
    for report in all_reports:
        p = sum(1 for vr in report.vote_results if vr.passed)
        f = sum(1 for vr in report.vote_results if not vr.passed)
        turn_passed.append(p)
        turn_failed.append(f)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax1.bar(
        range(1, num_turns + 1),
        turn_passed,
        color="#27AE60",
        label="Passed",
        alpha=0.85,
    )
    ax1.bar(
        range(1, num_turns + 1),
        turn_failed,
        bottom=turn_passed,
        color="#C0392B",
        label="Failed",
        alpha=0.85,
    )
    ax1.set_ylabel("Number of Votes", fontsize=10)
    ax1.set_title("Votes Per Turn", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=9)

    cum_pass = np.cumsum(turn_passed)
    cum_total = np.cumsum([p + f for p, f in zip(turn_passed, turn_failed)])
    cum_rate = [
        cum_pass[i] / cum_total[i] * 100 if cum_total[i] > 0 else 0
        for i in range(len(cum_total))
    ]

    ax2.plot(
        range(1, num_turns + 1),
        cum_rate,
        color="#2980B9",
        linewidth=2.5,
        marker="o",
        markersize=5,
    )
    ax2.axhline(50, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax2.set_ylabel("Cumulative Pass Rate (%)", fontsize=10)
    ax2.set_xlabel("Turn", fontsize=11)
    ax2.set_title("Cumulative Vote Pass Rate", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, 100)

    fig.suptitle("Legislative Vote Dynamics", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "03_vote_dynamics.png", dpi=150, bbox_inches="tight")
    plt.close()
