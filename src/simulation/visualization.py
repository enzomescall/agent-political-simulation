"""
Visualization module for political simulation results.
"""

from __future__ import annotations

import logging
import os
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.models import (
    Agent,
    Government,
    Ideology,
    InterestGroup,
    Legislature,
    Office,
    OfficeType,
    Party,
    Place,
    World,
    Archetype,
    DetailLevel,
    PartyRole,
)
from src.actions.base import ActionType
from src.simulation import run_turn

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


VISUALIZATION_NAMES = {
    1: "ideological_landscape",
    2: "seat_evolution",
    3: "vote_dynamics",
    4: "policy_success",
    5: "ig_satisfaction",
    6: "election_heatmap",
    7: "popularity_trajectories",
    8: "party_discipline",
    9: "action_breakdown",
    10: "agent_stories",
    11: "exec_actions_over_time",
    12: "exec_timeline",
    13: "party_popularity",
    14: "mobility",
    15: "party_seat_share",
    16: "party_leadership_timeline",
    17: "party_discipline_heatmap",
    18: "party_ideology_drift",
    19: "veto_analysis",
    20: "ideology_drift_agents",
    21: "ig_radicalization",
}


def avg_popularity(agent: Agent) -> float:
    vals = list(agent.popularity.values())
    return sum(vals) / len(vals) if vals else 0.0


def run_simulation_for_viz(world: World, num_turns: int, seed: int = 42):
    """Run simulation and collect history data for visualizations."""
    ELECTION_INTERVAL = 5

    ALL_PARTIES = list(world.parties.values())
    ALL_IGs = list(world.interest_groups.values())
    ALL_STATES = [p for p in world.places.values() if p.tier.name == "STATE"]
    ALL_CITIES = [p for p in world.places.values() if p.tier.name == "MUNICIPALITY"]

    def snapshot_seats(w: World):
        result = defaultdict(lambda: defaultdict(int))
        for gov in w.governments.values():
            if gov.legislature:
                tier = gov.place.tier.name
                for m in gov.legislature.members:
                    result[tier][m.party.name] += 1
        return {k: dict(v) for k, v in result.items()}

    def snapshot_ig_satisfaction(w: World):
        result = {}
        for ig in ALL_IGs:
            state_avgs = {}
            for state in ALL_STATES:
                cities = [c for c in ALL_CITIES if c.parent is state]
                city_sats = [ig.satisfaction.get(c, 0.5) for c in cities]
                state_avgs[state.name] = (
                    sum(city_sats) / len(city_sats) if city_sats else 0.5
                )
            result[ig.name] = state_avgs
        return result

    def snapshot_standing(w: World):
        result = defaultdict(list)
        for agent in w.politicians.values():
            result[agent.party.name].append(
                {
                    "id": agent.id,
                    "name": agent.name,
                    "standing": agent.party_standing,
                    "avg_pop": avg_popularity(agent),
                }
            )
        return dict(result)

    initial_agents_data = {}
    for agent in world.politicians.values():
        initial_agents_data[agent.id] = {
            "name": agent.name,
            "party": agent.party.name,
            "econ": agent.ideology["economic"],
            "soc": agent.ideology["social"],
            "archetype": agent.archetype,
            "office": agent.office,
            "standing": agent.party_standing,
            "avg_pop": avg_popularity(agent),
        }

    history_seats = [snapshot_seats(world)]
    history_ig_sat = [snapshot_ig_satisfaction(world)]
    history_standing = [snapshot_standing(world)]

    history_agent_ideologies = defaultdict(list)
    history_agent_party_standing = defaultdict(list)
    history_agent_offices = defaultdict(list)
    history_exec_holders = defaultdict(list)
    history_party_leaders = defaultdict(list)
    history_party_ideologies = defaultdict(list)
    history_ig_ideologies = defaultdict(list)
    history_veto_counts = []
    history_exec_actions = []
    history_party_total_seats = defaultdict(list)

    def snapshot_extended(w: World, report=None):
        for agent in w.politicians.values():
            aid = agent.id
            history_agent_ideologies[aid].append(
                (agent.ideology["economic"], agent.ideology["social"])
            )
            history_agent_party_standing[aid].append(agent.party_standing)
            history_agent_offices[aid].append(agent.office)

        for place_id, gov in w.governments.items():
            if gov.executive and gov.executive.holder:
                h = gov.executive.holder
                history_exec_holders[place_id].append((h.name, h.party.name))
            else:
                history_exec_holders[place_id].append(("vacant", ""))

        for party_id, party in w.parties.items():
            leaders = [a for a, role in party.members.items() if role.name == "LEADER"]
            if leaders:
                history_party_leaders[party_id].append(leaders[0].name)
            else:
                history_party_leaders[party_id].append("none")

        for party_id, party in w.parties.items():
            history_party_ideologies[party_id].append(
                (party.ideology["economic"], party.ideology["social"])
            )

        for ig in ALL_IGs:
            history_ig_ideologies[ig.name].append(
                (ig.ideology["economic"], ig.ideology["social"])
            )

        seat_counts = defaultdict(int)
        for gov in w.governments.values():
            if gov.legislature:
                for m in gov.legislature.members:
                    seat_counts[m.party.name] += 1
        for pname in [p.name for p in ALL_PARTIES]:
            history_party_total_seats[pname].append(seat_counts.get(pname, 0))

        if report is not None:
            vetoed = sum(1 for vr in report.vote_results if vr.vetoed)
            overrides = sum(1 for vr in report.vote_results if vr.veto_override)
            history_veto_counts.append((vetoed, overrides))
        else:
            history_veto_counts.append((0, 0))

        exec_action_types = [
            ActionType.REQUEST_VOTE,
            ActionType.CAMPAIGN,
            ActionType.BUILD_RELATIONSHIP,
            ActionType.TAKE_POSITION,
            ActionType.ENFORCE_DISCIPLINE,
            ActionType.IDEOLOGY_PUSH,
            ActionType.PARTY_OUTREACH,
            ActionType.PARTY_MERGE,
        ]
        exec_office_types = {
            OfficeType.PRESIDENT,
            OfficeType.GOVERNOR,
            OfficeType.MAYOR,
        }
        turn_exec_actions = defaultdict(int)
        if report is not None:
            for action in report.actions_taken:
                if action.actor.office in exec_office_types:
                    turn_exec_actions[action.action_type.name] += 1
        history_exec_actions.append(dict(turn_exec_actions))

    snapshot_extended(world, report=None)

    sim_rng = random.Random(seed)
    all_reports = []

    for t in range(num_turns):
        report = run_turn(world, sim_rng)
        all_reports.append(report)

        history_seats.append(snapshot_seats(world))
        history_ig_sat.append(snapshot_ig_satisfaction(world))
        history_standing.append(snapshot_standing(world))
        snapshot_extended(world, report=report)

    return {
        "initial_agents_data": initial_agents_data,
        "history_seats": history_seats,
        "history_ig_sat": history_ig_sat,
        "history_standing": history_standing,
        "history_agent_ideologies": dict(history_agent_ideologies),
        "history_agent_party_standing": dict(history_agent_party_standing),
        "history_agent_offices": dict(history_agent_offices),
        "history_exec_holders": dict(history_exec_holders),
        "history_party_leaders": dict(history_party_leaders),
        "history_party_ideologies": dict(history_party_ideologies),
        "history_ig_ideologies": dict(history_ig_ideologies),
        "history_veto_counts": history_veto_counts,
        "history_exec_actions": history_exec_actions,
        "history_party_total_seats": dict(history_party_total_seats),
        "all_reports": all_reports,
        "num_turns": num_turns,
        "election_interval": ELECTION_INTERVAL,
    }


def generate_visualizations(
    world: World,
    viz_data: dict,
    output_dir: Path | None = None,
    viz_numbers: list[int] | None = None,
    config_name: str | None = None,
):
    """Generate visualizations. If viz_numbers is None, generate all."""
    if output_dir is None:
        if config_name:
            output_dir = (
                Path("visualizations")
                / f"{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
        else:
            output_dir = Path("visualizations") / datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
    output_dir.mkdir(parents=True, exist_ok=True)

    epoch_dir = output_dir / "ideological_epochs"
    epoch_dir.mkdir(exist_ok=True)

    ALL_PARTIES = list(world.parties.values())
    ALL_IGs = list(world.interest_groups.values())
    ALL_STATES = [p for p in world.places.values() if p.tier.name == "STATE"]
    ALL_CITIES = [p for p in world.places.values() if p.tier.name == "MUNICIPALITY"]

    PARTY_COLORS = {
        "Labor Front": "#C0392B",
        "Civic Democrats": "#2980B9",
        "Reform Alliance": "#E67E22",
        "Green Future": "#27AE60",
    }
    for party in ALL_PARTIES:
        if party.name not in PARTY_COLORS:
            PARTY_COLORS[party.name] = f"#{random.randint(0, 0xFFFFFF):06x}"

    plt.style.use("seaborn-v0_8-whitegrid")
    logging.getLogger("simulation").setLevel(logging.CRITICAL)

    num_turns = viz_data["num_turns"]
    election_interval = viz_data["election_interval"]
    initial_agents_data = viz_data["initial_agents_data"]
    history_seats = viz_data["history_seats"]
    history_ig_sat = viz_data["history_ig_sat"]
    history_standing = viz_data["history_standing"]
    history_agent_ideologies = viz_data["history_agent_ideologies"]
    history_agent_party_standing = viz_data["history_agent_party_standing"]
    history_agent_offices = viz_data["history_agent_offices"]
    history_exec_holders = viz_data["history_exec_holders"]
    history_party_leaders = viz_data["history_party_leaders"]
    history_party_ideologies = viz_data["history_party_ideologies"]
    history_ig_ideologies = viz_data["history_ig_ideologies"]
    history_veto_counts = viz_data["history_veto_counts"]
    history_exec_actions = viz_data["history_exec_actions"]
    history_party_total_seats = viz_data["history_party_total_seats"]
    all_reports = viz_data["all_reports"]

    if viz_numbers is None:
        viz_numbers = list(range(1, 22))

    print(f"Generating visualizations in {output_dir}")

    if 1 in viz_numbers:
        print("Generating viz 1/21: Ideological Landscape...")
        _viz_ideological_landscape(
            initial_agents_data, ALL_PARTIES, output_dir, PARTY_COLORS
        )

    if 2 in viz_numbers:
        print("Generating viz 2/21: Seat Evolution...")
        _viz_seat_evolution(
            history_seats,
            ALL_PARTIES,
            num_turns,
            election_interval,
            output_dir,
            PARTY_COLORS,
        )

    if 3 in viz_numbers:
        print("Generating viz 3/21: Vote Dynamics...")
        _viz_vote_dynamics(all_reports, num_turns, election_interval, output_dir)

    if 4 in viz_numbers:
        print("Generating viz 4/21: Policy Success...")
        _viz_policy_success(all_reports, output_dir)

    if 5 in viz_numbers:
        print("Generating viz 5/21: IG Satisfaction...")
        _viz_ig_satisfaction(
            history_ig_sat, ALL_IGs, num_turns, election_interval, output_dir
        )

    if 6 in viz_numbers:
        print("Generating viz 6/21: Election Heatmap...")
        _viz_election_heatmap(all_reports, ALL_PARTIES, output_dir)

    if 7 in viz_numbers:
        print("Generating viz 7/21: Popularity Trajectories...")
        _viz_popularity_trajectories(
            initial_agents_data,
            history_standing,
            ALL_PARTIES,
            num_turns,
            election_interval,
            output_dir,
            PARTY_COLORS,
        )

    if 8 in viz_numbers:
        print("Generating viz 8/21: Party Discipline...")
        _viz_party_discipline(
            history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 9 in viz_numbers:
        print("Generating viz 9/21: Action Breakdown...")
        _viz_action_breakdown(all_reports, ALL_PARTIES, output_dir)

    if 10 in viz_numbers:
        print("Generating viz 10/21: Agent Stories...")
        _viz_agent_stories(
            initial_agents_data,
            history_standing,
            all_reports,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 11 in viz_numbers:
        print("Generating viz 11/21: Exec Actions Over Time...")
        _viz_exec_actions_over_time(
            history_exec_actions, num_turns, election_interval, output_dir
        )

    if 12 in viz_numbers:
        print("Generating viz 12/21: Exec Timeline...")
        _viz_exec_timeline(
            history_exec_holders,
            world.governments,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 13 in viz_numbers:
        print("Generating viz 13/21: Party Popularity...")
        _viz_party_popularity(
            history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 14 in viz_numbers:
        print("Generating viz 14/21: Mobility...")
        _viz_mobility(history_agent_offices, output_dir)

    if 15 in viz_numbers:
        print("Generating viz 15/21: Party Seat Share...")
        _viz_party_seat_share(
            history_party_total_seats, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 16 in viz_numbers:
        print("Generating viz 16/21: Party Leadership Timeline...")
        _viz_party_leadership_timeline(
            history_party_leaders, ALL_PARTIES, output_dir, PARTY_COLORS
        )

    if 17 in viz_numbers:
        print("Generating viz 17/21: Party Discipline Heatmap...")
        _viz_party_discipline_heatmap(
            history_agent_party_standing, history_agent_ideologies, output_dir
        )

    if 18 in viz_numbers:
        print("Generating viz 18/21: Party Ideology Drift...")
        _viz_party_ideology_drift(
            history_party_ideologies,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 19 in viz_numbers:
        print("Generating viz 19/21: Veto Analysis...")
        _viz_veto_analysis(
            history_veto_counts, num_turns, election_interval, output_dir
        )

    if 20 in viz_numbers:
        print("Generating viz 20/21: Ideology Drift Agents...")
        _viz_ideology_drift_agents(history_agent_ideologies, output_dir)

    if 21 in viz_numbers:
        print("Generating viz 21/21: IG Radicalization...")
        _viz_ig_radicalization(
            history_ig_ideologies, [ig.name for ig in ALL_IGs], output_dir
        )

    print(f"Visualizations saved to {output_dir}")
    return output_dir


def _viz_ideological_landscape(
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


def _viz_seat_evolution(
    history_seats, ALL_PARTIES, num_turns, election_interval, output_dir, PARTY_COLORS
):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    tier_names = ["FEDERAL", "STATE", "MUNICIPALITY"]
    tier_labels = ["Federal", "State", "Municipal"]

    for ax_idx, (tier, label) in enumerate(zip(tier_names, tier_labels)):
        ax = axes[ax_idx]
        for party in ALL_PARTIES:
            ys = []
            for snap in history_seats:
                tier_data = snap.get(tier, {})
                ys.append(tier_data.get(party.name, 0))
            ax.plot(
                range(num_turns + 1),
                ys,
                color=PARTY_COLORS.get(party.name, "#888888"),
                linewidth=2.5,
                label=party.name,
                marker="o",
                markersize=4,
            )

        for epoch_turn in range(election_interval, num_turns + 1, election_interval):
            ax.axvline(
                epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6
            )

        ax.set_ylabel("Seats", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Turn", fontsize=11)
    fig.suptitle("Seat Distribution Evolution", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(output_dir / "02_seat_evolution.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_vote_dynamics(all_reports, num_turns, election_interval, output_dir):
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


def _viz_policy_success(all_reports, output_dir):
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

    y_pos = np.arange(len(policy_names))
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


def _viz_ig_satisfaction(
    history_ig_sat, ALL_IGs, num_turns, election_interval, output_dir
):
    ig_names = [ig.name for ig in ALL_IGs]
    ig_colors = plt.cm.tab10(np.linspace(0, 0.9, len(ig_names)))

    fig, ax = plt.subplots(figsize=(14, 7))

    for ig_idx, ig_name in enumerate(ig_names):
        avg_sats = []
        for snap in history_ig_sat:
            state_vals = list(snap.get(ig_name, {}).values())
            avg_sats.append(sum(state_vals) / len(state_vals) if state_vals else 0.5)
        ax.plot(
            range(num_turns + 1),
            avg_sats,
            color=ig_colors[ig_idx],
            linewidth=2.5,
            label=ig_name,
            marker="o",
            markersize=4,
        )

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1.2, alpha=0.7)

    for epoch_turn in range(election_interval, num_turns + 1, election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlim(-0.3, num_turns + 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Satisfaction (0–1)", fontsize=11)
    ax.set_title(
        "Interest Group Satisfaction Over Time", fontsize=13, fontweight="bold"
    )
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "05_ig_satisfaction.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_election_heatmap(all_reports, ALL_PARTIES, output_dir):
    leg_elections = []
    for report in all_reports:
        for er in report.election_results:
            if er.election_type == "legislative":
                leg_elections.append(
                    {
                        "turn": report.turn,
                        "place": er.place.name,
                        "vote_shares": er.vote_shares,
                    }
                )

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
    ax.set_title("Legislative Election Vote Shares", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "06_election_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_popularity_trajectories(
    initial_agents_data,
    history_standing,
    ALL_PARTIES,
    num_turns,
    election_interval,
    output_dir,
    PARTY_COLORS,
):
    key_agents = [
        d["name"] for d in initial_agents_data.values() if d["office"] is not None
    ][:5]

    fig, ax = plt.subplots(figsize=(14, 7))

    for name in key_agents:
        pops = []
        for snap in history_standing:
            for party_agents in snap.values():
                for a in party_agents:
                    if a["name"] == name:
                        pops.append(a["avg_pop"])
                        break

        if pops:
            party_name = next(
                (d["party"] for d in initial_agents_data.values() if d["name"] == name),
                "Unknown",
            )
            color = PARTY_COLORS.get(party_name, "#555555")
            ax.plot(
                range(len(pops)),
                pops,
                color=color,
                linewidth=2.5,
                label=name,
                marker="o",
                markersize=5,
            )

    for epoch_turn in range(election_interval, num_turns + 1, election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlim(-0.3, num_turns + 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Popularity", fontsize=11)
    ax.set_title(
        "Popularity Trajectories — Key Executives", fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(
        output_dir / "07_popularity_trajectories.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_party_discipline(
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


def _viz_action_breakdown(all_reports, ALL_PARTIES, output_dir):
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


def _viz_agent_stories(
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


def _viz_exec_actions_over_time(
    history_exec_actions, num_turns, election_interval, output_dir
):
    action_types = set()
    for turn_actions in history_exec_actions:
        action_types.update(turn_actions.keys())

    if not action_types:
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.text(
            0.5,
            0.5,
            "No executive actions recorded",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Executive Actions Over Time", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(
            output_dir / "11_exec_actions_over_time.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    all_labels = sorted(action_types)
    colors = plt.cm.Set2(np.linspace(0, 1, len(all_labels)))

    x = np.arange(len(history_exec_actions))
    bottoms = np.zeros(len(history_exec_actions))

    for label, color in zip(all_labels, colors):
        heights = [ta.get(label, 0) for ta in history_exec_actions]
        ax.bar(
            x, heights, bottom=bottoms, label=label, color=color, alpha=0.85, width=0.7
        )
        bottoms += np.array(heights)

    for epoch_turn in range(
        election_interval, len(history_exec_actions), election_interval
    ):
        ax.axvline(
            epoch_turn - 0.5, color="black", linewidth=1.5, linestyle=":", alpha=0.5
        )

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Action Count", fontsize=11)
    ax.set_title("Executive Actions Over Time", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(x)
    ax.legend(fontsize=8, framealpha=0.9, loc="upper right")

    plt.tight_layout()
    plt.savefig(
        output_dir / "11_exec_actions_over_time.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_exec_timeline(
    history_exec_holders, governments, ALL_PARTIES, output_dir, PARTY_COLORS
):
    exec_places = [pid for pid, gov in governments.items() if gov.executive]

    party_map = {p.id: p.name for p in ALL_PARTIES}
    party_name_map = {p.name: p.name for p in ALL_PARTIES}

    if not exec_places:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.text(
            0.5,
            0.5,
            "No executives found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Executive Timeline", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_dir / "12_exec_timeline.png", dpi=150, bbox_inches="tight")
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(18, max(6, len(exec_places) * 0.6)))

    max_turns = 0
    for i, place_id in enumerate(exec_places):
        holders = history_exec_holders.get(place_id, [])
        max_turns = max(max_turns, len(holders))

        start = 0
        prev_name = None
        prev_party = None
        for turn_idx, (name, party) in enumerate(holders):
            if name != prev_name and prev_name is not None:
                color = PARTY_COLORS.get(party_name_map.get(prev_party, ""), "#888888")
                bar = ax.barh(
                    i,
                    turn_idx - start,
                    left=start,
                    height=0.65,
                    color=color,
                    alpha=0.9,
                    edgecolor="white",
                )

                duration = turn_idx - start
                if duration > 2:
                    short_name = (
                        prev_name[:12] + "..." if len(prev_name) > 12 else prev_name
                    )
                    ax.text(
                        start + duration / 2,
                        i,
                        short_name,
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white",
                        fontweight="bold",
                    )
                start = turn_idx
            prev_name = name
            prev_party = party

        if prev_name is not None:
            color = PARTY_COLORS.get(party_name_map.get(prev_party, ""), "#888888")
            bar = ax.barh(
                i,
                len(holders) - start,
                left=start,
                height=0.65,
                color=color,
                alpha=0.9,
                edgecolor="white",
            )

            duration = len(holders) - start
            if duration > 2:
                short_name = (
                    prev_name[:12] + "..." if len(prev_name) > 12 else prev_name
                )
                ax.text(
                    start + duration / 2,
                    i,
                    short_name,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )

    ax.set_yticks(range(len(exec_places)))
    ax.set_yticklabels(exec_places, fontsize=9)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_xlim(0, max(1, max_turns))
    ax.set_title("Executive Timeline", fontsize=13, fontweight="bold")

    party_patches = [
        mpatches.Patch(color=PARTY_COLORS.get(p.name, "#888888"), label=p.name)
        for p in ALL_PARTIES
    ]
    ax.legend(handles=party_patches, loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig(output_dir / "12_exec_timeline.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_party_popularity(
    history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(14, 7))

    for party in ALL_PARTIES:
        pops = []
        for snap in history_standing:
            party_agents = snap.get(party.name, [])
            if party_agents:
                avg = sum(a["avg_pop"] for a in party_agents) / len(party_agents)
                pops.append(avg)
            else:
                pops.append(0.5)

        ax.plot(
            range(len(pops)),
            pops,
            color=PARTY_COLORS.get(party.name, "#888888"),
            linewidth=2.5,
            label=party.name,
            marker="o",
            markersize=4,
        )

    ax.set_xlim(-0.3, len(pops) - 0.3)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Average Popularity", fontsize=11)
    ax.set_title("Party Popularity Over Time", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "13_party_popularity.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_mobility(history_agent_offices, output_dir):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.text(
        0.5,
        0.5,
        "Agent mobility data not available",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    ax.set_title("Agent Mobility")
    plt.tight_layout()
    plt.savefig(output_dir / "14_mobility.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_party_seat_share(
    history_party_total_seats, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(14, 7))

    for party in ALL_PARTIES:
        seats = history_party_total_seats.get(party.name, [0] * (num_turns + 1))
        ax.plot(
            range(num_turns + 1),
            seats,
            color=PARTY_COLORS.get(party.name, "#888888"),
            linewidth=2.5,
            label=party.name,
            marker="o",
            markersize=4,
        )

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Total Seats", fontsize=11)
    ax.set_title("Party Seat Share Over Time", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_dir / "15_party_seat_share.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_party_leadership_timeline(
    history_party_leaders, ALL_PARTIES, output_dir, PARTY_COLORS
):
    party_ids = [p.id for p in ALL_PARTIES]
    party_names = [p.name for p in ALL_PARTIES]

    if not party_ids:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.text(
            0.5,
            0.5,
            "No parties found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Party Leadership Timeline", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(
            output_dir / "16_party_leadership_timeline.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(16, max(6, len(party_ids) * 0.5)))

    max_turns = 0
    for i, party_id in enumerate(party_ids):
        leaders = history_party_leaders.get(party_id, ["none"])
        max_turns = max(max_turns, len(leaders))

        start = 0
        prev_leader = None
        for turn_idx, leader_name in enumerate(leaders):
            if leader_name != prev_leader and prev_leader is not None:
                color = PARTY_COLORS.get(party_names[i], "#888888")
                ax.barh(
                    i,
                    turn_idx - start,
                    left=start,
                    height=0.6,
                    color=color,
                    alpha=0.85,
                    edgecolor="white",
                )
                start = turn_idx
            prev_leader = leader_name

        if prev_leader is not None:
            color = PARTY_COLORS.get(party_names[i], "#888888")
            ax.barh(
                i,
                len(leaders) - start,
                left=start,
                height=0.6,
                color=color,
                alpha=0.85,
                edgecolor="white",
            )

    ax.set_yticks(range(len(party_ids)))
    ax.set_yticklabels(party_names, fontsize=9)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_xlim(0, max(1, max_turns))
    ax.set_title("Party Leadership Timeline", fontsize=13, fontweight="bold")

    party_patches = [
        mpatches.Patch(color=PARTY_COLORS.get(p.name, "#888888"), label=p.name)
        for p in ALL_PARTIES
    ]
    ax.legend(handles=party_patches, loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig(
        output_dir / "16_party_leadership_timeline.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_party_discipline_heatmap(
    history_agent_party_standing, history_agent_ideologies, output_dir
):
    agent_ids = list(history_agent_party_standing.keys())[:20]

    if not agent_ids:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            "No agent data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Party Discipline Heatmap")
        plt.tight_layout()
        plt.savefig(
            output_dir / "17_party_discipline_heatmap.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    max_len = max(
        len(history_agent_party_standing.get(aid, [0.5])) for aid in agent_ids
    )
    matrix = []
    for aid in agent_ids:
        history = history_agent_party_standing.get(aid, [0.5])
        padded = list(history) + [0.5] * (max_len - len(history))
        matrix.append(padded)
    matrix = np.array(matrix, dtype=float)

    fig, ax = plt.subplots(figsize=(12, max(4, len(agent_ids) * 0.3)))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    ax.set_yticks(range(len(agent_ids)))
    ax.set_yticklabels(agent_ids, fontsize=8)
    ax.set_xlabel("Turn", fontsize=11)
    ax.set_title("Party Discipline Heatmap", fontsize=13, fontweight="bold")

    plt.colorbar(im, ax=ax, label="Party Standing", shrink=0.6)
    plt.tight_layout()
    plt.savefig(
        output_dir / "17_party_discipline_heatmap.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_party_ideology_drift(
    history_party_ideologies, ALL_PARTIES, output_dir, PARTY_COLORS
):
    fig, ax = plt.subplots(figsize=(12, 8))

    for party in ALL_PARTIES:
        ideologies = history_party_ideologies.get(party.id, [])
        if ideologies:
            econs = [i[0] for i in ideologies]
            socs = [i[1] for i in ideologies]
            color = PARTY_COLORS.get(party.name, "#888888")
            ax.plot(
                econs,
                socs,
                linewidth=2,
                marker="o",
                markersize=4,
                label=party.name,
                color=color,
            )
            ax.scatter(
                econs[0],
                socs[0],
                s=100,
                marker="o",
                color=color,
            )
            ax.scatter(
                econs[-1],
                socs[-1],
                s=100,
                marker="s",
                color=color,
            )

    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Economic", fontsize=11)
    ax.set_ylabel("Social", fontsize=11)
    ax.set_title("Party Ideology Drift", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(
        output_dir / "18_party_ideology_drift.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_veto_analysis(history_veto_counts, num_turns, election_interval, output_dir):
    vetoed = [v[0] for v in history_veto_counts]
    overrides = [v[1] for v in history_veto_counts]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(vetoed))
    ax.bar(x, vetoed, color="#E74C3C", label="Vetoed", alpha=0.85)
    ax.bar(x, overrides, bottom=vetoed, color="#F39C12", label="Overrides", alpha=0.85)

    for epoch_turn in range(election_interval, len(vetoed), election_interval):
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title("Veto Analysis", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "19_veto_analysis.png", dpi=150, bbox_inches="tight")
    plt.close()


def _viz_ideology_drift_agents(history_agent_ideologies, output_dir):
    agent_ids = list(history_agent_ideologies.keys())[:20]

    if not agent_ids:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(
            0.5,
            0.5,
            "No agent data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title("Agent Ideology Drift")
        plt.tight_layout()
        plt.savefig(
            output_dir / "20_ideology_drift_agents.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    for aid in agent_ids:
        ideologies = history_agent_ideologies.get(aid, [])
        if ideologies:
            econs = [i[0] for i in ideologies]
            socs = [i[1] for i in ideologies]
            ax.plot(econs, socs, linewidth=1.5, marker="o", markersize=3, alpha=0.7)

    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Economic", fontsize=11)
    ax.set_ylabel("Social", fontsize=11)
    ax.set_title("Agent Ideology Drift", fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(
        output_dir / "20_ideology_drift_agents.png", dpi=150, bbox_inches="tight"
    )
    plt.close()


def _viz_ig_radicalization(history_ig_ideologies, ig_names, output_dir):
    fig, ax = plt.subplots(figsize=(12, 8))

    colors = plt.cm.tab10(np.linspace(0, 0.9, len(ig_names)))

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
                label=ig_name,
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
