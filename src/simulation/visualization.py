"""
Visualization module for political simulation results.
Orchestrates visualization generation by calling individual viz modules.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.models import (
    Government,
    Party,
    World,
)

# Import from viz_data module
from src.simulation.viz_data import avg_popularity, run_simulation_for_viz

# Import viz functions from individual viz modules
from src.simulation.viz.v01_ideological_landscape import viz_ideological_landscape
from src.simulation.viz.v02_seat_evolution import viz_seat_evolution
from src.simulation.viz.v03_vote_dynamics import viz_vote_dynamics
from src.simulation.viz.v04_policy_success import viz_policy_success
from src.simulation.viz.v05_ig_satisfaction import viz_ig_satisfaction
from src.simulation.viz.v06_election_heatmap import viz_election_heatmap
from src.simulation.viz.v07_popularity_trajectories import viz_popularity_trajectories
from src.simulation.viz.v08_party_discipline import viz_party_discipline
from src.simulation.viz.v09_action_breakdown import viz_action_breakdown
from src.simulation.viz.v10_agent_stories import viz_agent_stories
from src.simulation.viz.v11_exec_actions_over_time import viz_exec_actions_over_time
from src.simulation.viz.v12_exec_timeline import viz_exec_timeline
from src.simulation.viz.v13_party_popularity import viz_party_popularity
from src.simulation.viz.v14_mobility import viz_mobility
from src.simulation.viz.v15_party_seat_share import viz_party_seat_share
from src.simulation.viz.v16_party_leadership_timeline import viz_party_leadership_timeline
from src.simulation.viz.v17_party_discipline_heatmap import viz_party_discipline_heatmap
from src.simulation.viz.v18_party_ideology_drift import viz_party_ideology_drift
from src.simulation.viz.v19_veto_analysis import viz_veto_analysis
from src.simulation.viz.v20_ideology_drift_agents import viz_ideology_drift_agents
from src.simulation.viz.v21_ig_radicalization import viz_ig_radicalization


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

    ALL_PARTIES = list(world.parties.values())
    ALL_IGs = list(world.interest_groups.values())

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
        viz_ideological_landscape(
            initial_agents_data, ALL_PARTIES, output_dir, PARTY_COLORS
        )

    if 2 in viz_numbers:
        print("Generating viz 2/21: Seat Evolution...")
        viz_seat_evolution(
            history_seats,
            ALL_PARTIES,
            num_turns,
            election_interval,
            output_dir,
            PARTY_COLORS,
        )

    if 3 in viz_numbers:
        print("Generating viz 3/21: Vote Dynamics...")
        viz_vote_dynamics(all_reports, num_turns, election_interval, output_dir)

    if 4 in viz_numbers:
        print("Generating viz 4/21: Policy Success...")
        viz_policy_success(all_reports, output_dir)

    if 5 in viz_numbers:
        print("Generating viz 5/21: IG Satisfaction...")
        viz_ig_satisfaction(
            history_ig_sat, ALL_IGs, num_turns, election_interval, output_dir
        )

    if 6 in viz_numbers:
        print("Generating viz 6/21: Election Heatmap...")
        viz_election_heatmap(all_reports, ALL_PARTIES, output_dir)

    if 7 in viz_numbers:
        print("Generating viz 7/21: Popularity Trajectories...")
        viz_popularity_trajectories(
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
        viz_party_discipline(
            history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 9 in viz_numbers:
        print("Generating viz 9/21: Action Breakdown...")
        viz_action_breakdown(all_reports, ALL_PARTIES, output_dir)

    if 10 in viz_numbers:
        print("Generating viz 10/21: Agent Stories...")
        viz_agent_stories(
            initial_agents_data,
            history_standing,
            all_reports,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 11 in viz_numbers:
        print("Generating viz 11/21: Exec Actions Over Time...")
        viz_exec_actions_over_time(
            history_exec_actions, num_turns, election_interval, output_dir
        )

    if 12 in viz_numbers:
        print("Generating viz 12/21: Exec Timeline...")
        viz_exec_timeline(
            history_exec_holders,
            world.governments,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 13 in viz_numbers:
        print("Generating viz 13/21: Party Popularity...")
        viz_party_popularity(
            history_standing, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 14 in viz_numbers:
        print("Generating viz 14/21: Mobility...")
        viz_mobility(history_agent_offices, output_dir)

    if 15 in viz_numbers:
        print("Generating viz 15/21: Party Seat Share...")
        viz_party_seat_share(
            history_party_total_seats, ALL_PARTIES, num_turns, output_dir, PARTY_COLORS
        )

    if 16 in viz_numbers:
        print("Generating viz 16/21: Party Leadership Timeline...")
        viz_party_leadership_timeline(
            history_party_leaders, ALL_PARTIES, output_dir, PARTY_COLORS
        )

    if 17 in viz_numbers:
        print("Generating viz 17/21: Party Discipline Heatmap...")
        viz_party_discipline_heatmap(
            history_agent_party_standing, history_agent_ideologies, output_dir
        )

    if 18 in viz_numbers:
        print("Generating viz 18/21: Party Ideology Drift...")
        viz_party_ideology_drift(
            history_party_ideologies,
            ALL_PARTIES,
            output_dir,
            PARTY_COLORS,
        )

    if 19 in viz_numbers:
        print("Generating viz 19/21: Veto Analysis...")
        viz_veto_analysis(
            history_veto_counts, num_turns, election_interval, output_dir
        )

    if 20 in viz_numbers:
        print("Generating viz 20/21: Ideology Drift Agents...")
        viz_ideology_drift_agents(history_agent_ideologies, output_dir)

    if 21 in viz_numbers:
        print("Generating viz 21/21: IG Radicalization...")
        viz_ig_radicalization(
            history_ig_ideologies, [ig.name for ig in ALL_IGs], output_dir
        )

    print(f"Visualizations saved to {output_dir}")
    return output_dir
