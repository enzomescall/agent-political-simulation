"""
Visualization utilities for political simulation.
"""

from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.models import (
    Agent,
    Archetype,
    Government,
    Ideology,
    InterestGroup,
    Legislature,
    Office,
    OfficeType,
    Party,
    Place,
    World,
    DetailLevel,
    PartyRole,
)
from src.actions.base import ActionType
from src.simulation import run_turn


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
