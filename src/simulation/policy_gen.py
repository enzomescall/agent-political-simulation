from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.policy import Policy

if TYPE_CHECKING:
    from src.models.agent import Agent
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
