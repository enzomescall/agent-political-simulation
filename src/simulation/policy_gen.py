from __future__ import annotations

from dataclasses import dataclass
import math
import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.ideology import Ideology
from src.models.policy import Policy
from src.actions.voting import compute_vote_disposition

if TYPE_CHECKING:
    from typing import Any

    from src.models.agent import Agent
    from src.models.government import Government
    from src.models.world import World

_log = logging.getLogger("simulation.policy_gen")


@dataclass(frozen=True)
class PolicyTemplate:
    name: str
    description: str
    ideology_ranges: dict[str, tuple[float, float]]


_POLICY_TEMPLATES = [
    PolicyTemplate(
        "Raise minimum wage",
        "Increase the local minimum wage",
        {"economic": (-1.0, -0.3), "social": (-0.2, 0.4)},
    ),
    PolicyTemplate(
        "Cut business tax",
        "Reduce tax burden on local enterprises",
        {"economic": (0.35, 1.0), "social": (-0.2, 0.2)},
    ),
    PolicyTemplate(
        "Expand public transit",
        "Fund new bus routes and transit lines",
        {"economic": (-0.8, -0.1), "social": (-0.1, 0.6)},
    ),
    PolicyTemplate(
        "Housing subsidy program",
        "Subsidise affordable housing construction",
        {"economic": (-1.0, -0.2), "social": (-0.1, 0.5)},
    ),
    PolicyTemplate(
        "Deregulation package",
        "Remove regulatory barriers for small business",
        {"economic": (0.5, 1.0), "social": (-0.3, 0.2)},
    ),
    PolicyTemplate(
        "Green energy mandate",
        "Require renewable energy for public buildings",
        {"economic": (-0.5, 0.1), "social": (0.2, 0.9)},
    ),
    PolicyTemplate(
        "Public safety initiative",
        "Increase funding for community policing",
        {"economic": (-0.1, 0.5), "social": (-0.7, 0.1)},
    ),
    PolicyTemplate(
        "Education reform",
        "Restructure local school funding",
        {"economic": (-0.6, 0.2), "social": (-0.2, 0.6)},
    ),
    PolicyTemplate(
        "Infrastructure bond",
        "Issue bonds for road and bridge repair",
        {"economic": (-0.4, 0.4), "social": (-0.1, 0.4)},
    ),
    PolicyTemplate(
        "Social services expansion",
        "Expand welfare and social safety net",
        {"economic": (-1.0, -0.4), "social": (-0.1, 0.6)},
    ),
    PolicyTemplate(
        "Family tax credit",
        "Offer a targeted tax credit for households with children",
        {"economic": (-0.1, 0.6), "social": (-0.2, 0.5)},
    ),
    PolicyTemplate(
        "Worker training grant",
        "Fund job retraining and apprenticeship grants",
        {"economic": (-0.6, 0.1), "social": (-0.1, 0.5)},
    ),
    PolicyTemplate(
        "Small business loan program",
        "Create low-interest loans for local small businesses",
        {"economic": (0.0, 0.7), "social": (-0.2, 0.3)},
    ),
    PolicyTemplate(
        "Climate resilience plan",
        "Invest in flood defences, heat mitigation, and emergency prep",
        {"economic": (-0.7, 0.0), "social": (0.1, 0.8)},
    ),
    PolicyTemplate(
        "Police accountability board",
        "Create civilian oversight for public safety agencies",
        {"economic": (-0.4, 0.1), "social": (0.3, 0.9)},
    ),
    PolicyTemplate(
        "Charter school expansion",
        "Expand charter school access and enrollment caps",
        {"economic": (0.0, 0.8), "social": (-0.2, 0.4)},
    ),
    PolicyTemplate(
        "Prescription price cap",
        "Cap out-of-pocket costs for essential medications",
        {"economic": (-1.0, -0.2), "social": (-0.1, 0.3)},
    ),
    PolicyTemplate(
        "Infrastructure privatization",
        "Use private contracts for major infrastructure projects",
        {"economic": (0.4, 1.0), "social": (-0.3, 0.2)},
    ),
    PolicyTemplate(
        "Universal childcare pilot",
        "Launch a public childcare pilot for working families",
        {"economic": (-0.8, -0.2), "social": (0.2, 0.8)},
    ),
    PolicyTemplate(
        "Balanced budget reform",
        "Tighten spending rules and require budget discipline",
        {"economic": (0.2, 0.9), "social": (-0.4, 0.2)},
    ),
]


def _template_weight(template: PolicyTemplate, ideology: Ideology) -> float:
    """Score how well a generated ideology fits a template's ranges."""
    weight = 1.0
    for axis, (low, high) in template.ideology_ranges.items():
        value = ideology[axis]
        center = (low + high) / 2.0
        half_width = max((high - low) / 2.0, 0.15)
        if low <= value <= high:
            distance = abs(value - center)
        elif value < low:
            distance = low - value
        else:
            distance = value - high
        axis_weight = math.exp(-((distance / half_width) ** 2))
        weight *= max(axis_weight, 0.05)
    return weight


def _choose_template(ideology: Ideology, rng: _random.Random) -> PolicyTemplate:
    weights = [_template_weight(template, ideology) for template in _POLICY_TEMPLATES]
    return rng.choices(_POLICY_TEMPLATES, weights=weights, k=1)[0]


def _predict_vote_outcome(
    proposer: Agent,
    policy: Policy,
    world: World,
) -> tuple[float, int, int]:
    """Predict how the legislature would vote on a policy once per policy generation."""
    gov = world.governments.get(proposer.place.id)
    if gov is None or gov.legislature is None:
        return 0.0, 0, 0

    yes, no = 0, 0
    for member in gov.legislature.members:
        disposition = compute_vote_disposition(member, policy, world, proposer=proposer)
        if disposition > 0.1:
            yes += 1
        elif disposition < -0.1:
            no += 1

    total = len(gov.legislature.members)
    if total == 0:
        return 0.0, 0, 0

    passed = yes > total / 2
    margin = abs(yes - total / 2) / total
    prob = min(1.0, 0.5 + margin * 2) if passed else max(0.0, 0.5 - margin * 2)
    return prob, yes, no


def _annotate_predicted_vote(policy: Policy, proposer: Agent, world: World) -> None:
    prob, yes, no = _predict_vote_outcome(proposer, policy, world)
    policy.attributes["predicted_vote"] = {
        "pass_probability": prob,
        "predicted_yes": yes,
        "predicted_no": no,
    }


def generate_policy(
    agent: Agent,
    world: World,
    rng: _random.Random | None = None,
) -> Policy:
    """Generate an ephemeral policy shaped by the agent's ideology and allegiances."""
    if rng is None:
        rng = _random.Random()

    # Interest group impacts derived from agent's ideology + allegiances.
    # Groups the agent is allied with benefit; others may be hurt.
    ig_impacts = {}
    for ig in world.interest_groups.values():
        allegiance = agent.allegiances.get(ig, 0.0)
        # Allied groups benefit, unallied groups may be slightly hurt.
        base_impact = allegiance * 0.5 + rng.uniform(-0.15, 0.15)
        # Agents tend not to propose things that devastate groups entirely.
        ig_impacts[ig] = max(-0.6, min(0.6, base_impact))

    # Ideology alignment mirrors the proposer's ideology, then we pick the
    # best-fitting policy label from the template pool.
    ideology_alignment = {
        axis: position * rng.uniform(0.5, 1.0)
        for axis, position in agent.ideology.axes.items()
    }
    generated_ideology = Ideology(axes=dict(ideology_alignment))
    template = _choose_template(generated_ideology, rng)

    # Compute explicit party support for this policy [-1, 1] for each party.
    party_support: dict[Any, float] = {}
    for party in world.parties.values():
        axes = list(ideology_alignment.keys())
        if axes:
            lean = sum(party.ideology[ax] * ideology_alignment[ax] for ax in axes) / len(axes)
        else:
            lean = 0.0
        party_support[party] = max(-1.0, min(1.0, lean))

    policy = Policy(
        name=f"{template.name} by {agent.name}",
        description=template.description,
        interest_group_impacts=ig_impacts,
        ideology_alignment=ideology_alignment,
        attributes={"party_support": party_support},
    )
    _log.debug(
        "Generated policy '%s' by %s: IG impacts=[%s], ideology=[%s], party_support=[%s]",
        template.name, agent.name,
        ", ".join(f"{ig.name}={v:+.3f}" for ig, v in ig_impacts.items()),
        ", ".join(f"{k}={v:+.3f}" for k, v in ideology_alignment.items()),
        ", ".join(f"{p.name}={v:+.3f}" for p, v in party_support.items()),
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
        _annotate_predicted_vote(policy, gov.executive.holder, world)
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
        _annotate_predicted_vote(policy, champion, world)
        pool.append((policy, champion))
        _log.debug("Pool: %s (%s) generated '%s'", champion.name, party.name, policy.name)

    return pool
