from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.models.types import Archetype

from .base import VoteResult

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.government import Legislature
    from src.models.policy import Policy
    from src.models.world import World

_log = logging.getLogger("simulation.voting")


# Archetype weight profiles for vote disposition.
# Keys: ideology, party_directive, ig_pressure, electoral, relationships
ARCHETYPE_WEIGHTS: dict[Archetype, dict[str, float]] = {
    Archetype.LOYALIST: {
        "ideology": 0.20,
        "party_directive": 0.40,
        "ig_pressure": 0.15,
        "electoral": 0.10,
        "relationships": 0.15,
    },
    Archetype.POPULIST: {
        "ideology": 0.15,
        "party_directive": 0.10,
        "ig_pressure": 0.40,
        "electoral": 0.30,
        "relationships": 0.05,
    },
    Archetype.IDEOLOGUE: {
        "ideology": 0.50,
        "party_directive": 0.10,
        "ig_pressure": 0.15,
        "electoral": 0.05,
        "relationships": 0.20,
    },
}


def _ideology_score(agent: Agent, policy: Policy) -> float:
    """How much the agent's ideology aligns with the policy [-1, 1]."""
    if not policy.ideology_alignment:
        return 0.0
    total = 0.0
    count = 0
    for axis, direction in policy.ideology_alignment.items():
        total += agent.ideology[axis] * direction
        count += 1
    return total / count if count else 0.0


def _ig_pressure_score(agent: Agent, policy: Policy) -> float:
    """How much the agent's interest groups want this policy [-1, 1]."""
    total = 0.0
    weight_sum = 0.0
    for ig, allegiance in agent.allegiances.items():
        impact = policy.interest_group_impacts.get(ig, 0.0)
        total += impact * allegiance
        weight_sum += allegiance
    return total / weight_sum if weight_sum > 0 else 0.0


def _party_directive_score(agent: Agent, policy: Policy, world: World) -> float:
    """How much the party line favours this policy [-1, 1]."""
    return _ideology_score(agent.__class__(
        id=agent.id, name="", ideology=agent.party.ideology,
        party=agent.party, place=agent.place,
    ), policy)


def _electoral_score(agent: Agent, policy: Policy) -> float:
    """How electorally beneficial voting yes would be [-1, 1].

    Approximation: weighted average of policy impacts on groups where
    the agent has high popularity.
    """
    total = 0.0
    weight_sum = 0.0
    for ig, pop in agent.popularity.items():
        impact = policy.interest_group_impacts.get(ig, 0.0)
        total += impact * pop
        weight_sum += pop
    return total / weight_sum if weight_sum > 0 else 0.0


def _relationship_score(agent: Agent, policy: Policy, proposer: Agent | None) -> float:
    """Relationship trust with the proposer [-1, 1]."""
    if proposer is None:
        return 0.0
    return agent.relationships.get(proposer, 0.0)


def compute_vote_disposition(
    agent: Agent,
    policy: Policy,
    world: World,
    proposer: Agent | None = None,
) -> float:
    """Return a score in [-1, 1] for how inclined the agent is to vote yes."""
    w = ARCHETYPE_WEIGHTS[agent.archetype]
    components = {
        "ideology": _ideology_score(agent, policy),
        "party_directive": _party_directive_score(agent, policy, world),
        "ig_pressure": _ig_pressure_score(agent, policy),
        "electoral": _electoral_score(agent, policy),
        "relationships": _relationship_score(agent, policy, proposer),
    }
    score = sum(w[k] * v for k, v in components.items())
    score = max(-1.0, min(1.0, score))
    _log.debug(
        "%s vote disposition on '%s': %.3f  [%s]",
        agent.name, policy.name, score,
        ", ".join(f"{k}={w[k]:.2f}*{v:+.3f}" for k, v in components.items()),
    )
    return score


def resolve_vote(
    legislature: Legislature,
    policy: Policy,
    world: World,
    proposer: Agent | None = None,
) -> VoteResult:
    """Run a vote across the legislature and return the result."""
    yes: list[Agent] = []
    no: list[Agent] = []
    abstain: list[Agent] = []

    for member in legislature.members:
        disposition = compute_vote_disposition(member, policy, world, proposer)
        if disposition > 0.1:
            yes.append(member)
        elif disposition < -0.1:
            no.append(member)
        else:
            abstain.append(member)

    passed = len(yes) > (len(legislature.members) / 2)
    _log.info(
        "  Vote on '%s': %s (%dY/%dN/%dA)",
        policy.name, "PASSED" if passed else "FAILED",
        len(yes), len(no), len(abstain),
    )

    return VoteResult(
        policy=policy,
        place=legislature.place,
        yes_votes=yes,
        no_votes=no,
        abstentions=abstain,
        passed=passed,
    )
