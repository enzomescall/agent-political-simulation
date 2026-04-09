"""
Party splitting / faction formation.

An agent who is chronically alienated from their party and finds no better
ideological home can split off to form (or join) a new splinter party.
Multiple agents splitting on the same turn coalesce into one new party.
"""
from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.ideology import Ideology
from src.models.party import Party
from src.models.types import Archetype, DetailLevel, PartyId, PartyRole

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.world import World

_log = logging.getLogger("simulation.factions")

# Thresholds
_SAT_THRESHOLD = 0.25          # party_satisfaction below this → disgruntled
_INERTIA_NEEDED = 3            # consecutive turns below threshold before split
_IDEOLOGICAL_GAP = 0.30        # must be this far from next-closest party to bother
_MIN_SPLINTER_SIZE = 2         # need at least 2 agents to form a new party
_COOLDOWN = -5                 # inertia value set after splitting (prevents instant re-split)
_BUDGET_START = 2              # starting campaign budget for splinter party
_AMBITION_FLOOR = 0.5          # only sufficiently ambitious agents initiate splits


def compute_party_satisfaction(agent: "Agent", world: "World") -> float:
    """How satisfied is this agent with their current party?

    Weighted combination of:
    - Ideological alignment with party (0.5)
    - Average allegiance to party's base IGs (0.3)
    - Current party standing (0.2)
    """
    ideology_align = agent.party.ideology.alignment(agent.ideology)

    base_igs = agent.party.base_constituency
    if base_igs:
        ig_affinity = sum(
            agent.allegiances.get(ig, 0.0) * strength
            for ig, strength in base_igs.items()
        ) / sum(base_igs.values())
    else:
        ig_affinity = 0.5

    return (
        0.5 * ideology_align
        + 0.3 * ig_affinity
        + 0.2 * agent.party_standing
    )


def _no_close_alternative(agent: "Agent", world: "World") -> bool:
    """True if no other party is meaningfully closer ideologically."""
    other_parties = [p for p in world.parties.values() if p is not agent.party]
    if not other_parties:
        return True
    own_dist = agent.party.ideology.distance(agent.ideology)
    best_other = min(p.ideology.distance(agent.ideology) for p in other_parties)
    # Only split if own party is meaningfully farther than next best
    return (own_dist - best_other) > _IDEOLOGICAL_GAP


def check_splits(world: "World", rng: _random.Random) -> list[str]:
    """Update party_satisfaction and inertia; form splinter parties if warranted.

    Returns narrative event strings.
    """
    events: list[str] = []

    # --- Step 1: Update party satisfaction for all agents ---
    for agent in world.politicians.values():
        if agent.detail_level.value > 1:
            continue
        sat = compute_party_satisfaction(agent, world)
        agent.party_satisfaction = sat

        inertia = agent.attributes.get("split_inertia", 0)
        if inertia < 0:
            # Cooldown: count up toward 0
            agent.attributes["split_inertia"] = inertia + 1
            continue

        if sat < _SAT_THRESHOLD and _no_close_alternative(agent, world):
            agent.attributes["split_inertia"] = inertia + 1
        else:
            # Satisfaction returned; reset inertia gradually
            agent.attributes["split_inertia"] = max(0, inertia - 1)

    # --- Step 2: Identify split candidates ---
    candidates: list[Agent] = [
        a for a in world.politicians.values()
        if (
            a.detail_level.value <= 1
            and a.attributes.get("split_inertia", 0) >= _INERTIA_NEEDED
            and a.ambition >= _AMBITION_FLOOR
            and a.party_role is not PartyRole.LEADER  # leaders fight to reform, not leave
        )
    ]

    if not candidates:
        return events

    # --- Step 3: Group by originating party ---
    by_party: dict[str, list[Agent]] = {}
    for agent in candidates:
        key = agent.party.id
        by_party.setdefault(key, []).append(agent)

    # --- Step 4: Form splinter parties for groups large enough ---
    for party_id, group in by_party.items():
        if len(group) < _MIN_SPLINTER_SIZE:
            # Single defector: try to join nearest existing party instead
            agent = group[0]
            other_parties = [p for p in world.parties.values() if p is not agent.party]
            if other_parties:
                new_party = min(other_parties,
                                key=lambda p: p.ideology.distance(agent.ideology))
                old_party = agent.party
                old_party.remove_member(agent)
                new_party.add_member(agent, PartyRole.MEMBER)
                agent.party = new_party
                agent.party_role = PartyRole.MEMBER
                agent.party_standing = 0.3
                agent.party_satisfaction = compute_party_satisfaction(agent, world)
                agent.attributes["split_inertia"] = _COOLDOWN
                events.append(
                    f"{agent.name} left {old_party.name} and joined {new_party.name}"
                )
                _log.info("  %s defected from %s to %s", agent.name, old_party.name, new_party.name)
            continue

        # Enough agents to form a new party
        splinter_events = _form_splinter(group, world, rng)
        events.extend(splinter_events)

    return events


def _form_splinter(agents: list[Agent], world: World, rng: _random.Random) -> list[str]:
    """Create a new splinter party from a group of disgruntled agents."""
    events: list[str] = []
    old_party = agents[0].party

    # New ideology = average of splinters' current ideologies
    axes_names = list(agents[0].ideology.axes.keys())
    avg_axes = {
        ax: sum(a.ideology[ax] for a in agents) / len(agents)
        for ax in axes_names
    }
    new_ideology = Ideology(axes=avg_axes)

    splinter_id = PartyId(f"splinter_{world.turn}_{rng.randint(1000, 9999)}")
    splinter_name = f"{old_party.name} (Splinter)"

    # Inherit a sliver of the old party's IG constituency (weakly)
    base_const = {
        ig: strength * 0.3
        for ig, strength in old_party.base_constituency.items()
    }

    new_party = Party(
        id=splinter_id,
        name=splinter_name,
        ideology=new_ideology,
        directive_threshold=0.10,
        campaign_budget=_BUDGET_START,
        nomination_threshold=0.15,
        leadership_interval=10,
        base_constituency=base_const,
    )
    world.add_party(new_party)

    # Move agents to new party
    for agent in agents:
        old_party.remove_member(agent)
        new_party.add_member(agent, PartyRole.MEMBER)
        agent.party = new_party
        agent.party_role = PartyRole.MEMBER
        agent.party_standing = 0.5
        agent.party_satisfaction = 0.5
        agent.attributes["split_inertia"] = _COOLDOWN
        # Deteriorate relations with old party members
        for old_member in old_party.members:
            agent.relationships[old_member] = max(
                -1.0, agent.relationships.get(old_member, 0.0) - 0.3
            )

    # Elect a leader (highest ambition + popularity among splinters)
    leader = max(agents, key=lambda a: a.ambition * 0.5 + sum(a.popularity.values()) / max(len(a.popularity), 1) * 0.5)
    new_party.set_role(leader, PartyRole.LEADER)
    leader.party_role = PartyRole.LEADER

    names = ", ".join(a.name for a in agents)
    _log.info(
        "  NEW PARTY: %s formed from %s (%d agents: %s)",
        splinter_name, old_party.name, len(agents), names,
    )
    events.append(
        f"PARTY SPLIT: {names} left {old_party.name} to form {splinter_name} "
        f"(leader: {leader.name})"
    )
    return events
