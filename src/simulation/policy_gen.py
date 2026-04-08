from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.policy import Policy

if TYPE_CHECKING:
    from typing import Any

    from src.models.agent import Agent
    from src.models.government import Government
    from src.models.world import World

_log = logging.getLogger("simulation.policy_gen")

_POLICY_TEMPLATES = [
    ("Raise minimum wage", "Increase the local minimum wage"),
    ("Cut business tax", "Reduce tax burden on local enterprises"),
    ("Expand public transit", "Fund new bus routes and transit lines"),
    ("Housing subsidy program", "Subsidise affordable housing construction"),
    ("Deregulation package", "Remove regulatory barriers for small business"),
    ("Green energy mandate", "Require renewable energy for public buildings"),
    ("Public safety initiative", "Increase funding for community policing"),
    ("Education reform", "Restructure local school funding"),
    ("Infrastructure bond", "Issue bonds for road and bridge repair"),
    ("Social services expansion", "Expand welfare and social safety net"),
]


def generate_policy(
    agent: Agent,
    world: World,
    rng: _random.Random | None = None,
) -> Policy:
    """Generate an ephemeral policy shaped by the agent's ideology and allegiances."""
    if rng is None:
        rng = _random.Random()

    name, description = rng.choice(_POLICY_TEMPLATES)

    # Interest group impacts derived from agent's ideology + allegiances.
    # Groups the agent is allied with benefit; others may be hurt.
    ig_impacts = {}
    for ig in world.interest_groups.values():
        allegiance = agent.allegiances.get(ig, 0.0)
        # Allied groups benefit, unallied groups may be slightly hurt.
        base_impact = allegiance * 0.5 + rng.uniform(-0.15, 0.15)
        # Agents tend not to propose things that devastate groups entirely.
        ig_impacts[ig] = max(-0.6, min(0.6, base_impact))

    # Ideology alignment mirrors the proposer's ideology.
    ideology_alignment = {}
    for axis, position in agent.ideology.axes.items():
        ideology_alignment[axis] = position * rng.uniform(0.5, 1.0)

    policy = Policy(
        name=name,
        description=description,
        interest_group_impacts=ig_impacts,
        ideology_alignment=ideology_alignment,
    )
    _log.debug(
        "Generated policy '%s' by %s: IG impacts=[%s], ideology=[%s]",
        name, agent.name,
        ", ".join(f"{ig.name}={v:+.3f}" for ig, v in ig_impacts.items()),
        ", ".join(f"{k}={v:+.3f}" for k, v in ideology_alignment.items()),
    )
    return policy


def generate_policy_pool(
    gov: Government,
    world: World,
    rng: _random.Random,
    max_party_proposals: int = 3,
) -> list[tuple[Policy, Agent]]:
    """Generate a pool of candidate policies for a legislature.

    The executive generates 1 policy.
    
    For each of the N largest parties in the legislature,
    the highest-standing legislator generates 1 policy.
    """
    pool: list[tuple[Policy, Agent]] = []

    # Executive proposal.
    if gov.executive.holder is not None:
        policy = generate_policy(gov.executive.holder, world, rng)
        pool.append((policy, gov.executive.holder))
        _log.debug("Pool: executive %s generated '%s'", gov.executive.holder.name, policy.name)

    if gov.legislature is None:
        return pool

    # Count party representation in the legislature.
    party_members: dict[Any, list[Agent]] = {}
    for member in gov.legislature.members:
        party_members.setdefault(member.party, []).append(member)

    # Sort parties by number of seats (descending), take top N.
    ranked_parties = sorted(party_members.keys(), key=lambda p: len(party_members[p]), reverse=True)
    for party in ranked_parties[:max_party_proposals]:
        # Highest party_standing legislator proposes.
        champion = max(party_members[party], key=lambda a: a.party_standing)
        policy = generate_policy(champion, world, rng)
        pool.append((policy, champion))
        _log.debug("Pool: %s (%s) generated '%s'", champion.name, party.name, policy.name)

    return pool
