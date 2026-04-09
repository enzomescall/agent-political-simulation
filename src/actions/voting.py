from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.types import Archetype
from src.log_utils import fmt

from .base import VoteResult

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.government import Legislature
    from src.models.policy import Policy
    from src.models.world import World

_log = logging.getLogger("simulation.voting")

_DEFAULT_DIRECTIVE_THRESHOLD = 0.15


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
    """How much the agent's interest groups want this policy [-1, 1].

    IGs to which the agent has low allegiance (< 0.15) are dampened — agents
    don't feel strong pressure from groups they're opposed to.
    """
    total = 0.0
    weight_sum = 0.0
    for ig, allegiance in agent.allegiances.items():
        impact = policy.interest_group_impacts.get(ig, 0.0)
        # Dampen influence of opposed/unaffiliated IGs
        effective = allegiance if allegiance >= 0.15 else allegiance * 0.4
        total += impact * effective
        weight_sum += effective
    return total / weight_sum if weight_sum > 0 else 0.0


def _directive_threshold(agent: Agent) -> float:
    raw_threshold = agent.party.directive_threshold
    return min(max(abs(raw_threshold), 0.0), 0.95)


def get_party_support(agent: Agent, policy: Policy) -> float | None:
    """Return explicit party support for a policy, if available."""
    return policy.attributes.get("party_support", {}).get(agent.party)


def compute_directive_pressure(agent: Agent, policy: Policy) -> float:
    """Return the party's directional pressure on the vote in [-1, 1]."""
    party_support = get_party_support(agent, policy)
    if party_support is None:
        return 0.0

    threshold = _directive_threshold(agent)
    scale = max(1.0 - threshold, 1e-6)
    if party_support > threshold:
        return min((party_support - threshold) / scale, 1.0)
    if party_support < -threshold:
        return max((party_support + threshold) / scale, -1.0)
    return 0.0


def _party_directive_score(agent: Agent, policy: Policy, world: World) -> float:
    """How much the party line favours this policy [-1, 1]."""
    return compute_directive_pressure(agent, policy)


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


def _expulsion_risk_score(agent: Agent, policy: Policy, world: World) -> float:
    """How expulsion fear pulls the agent toward the directive [-1, 1]."""
    directive_pressure = compute_directive_pressure(agent, policy)
    if directive_pressure == 0.0:
        return 0.0

    electorate_total = 0.0
    popularity_total = 0.0
    for ig in agent.place.interest_group_presence:
        share = ig.electorate_share.get(agent.place, agent.place.interest_group_presence.get(ig, 0.0))
        electorate_total += share
        popularity_total += share * agent.popularity.get(ig, 0.0)
    popularity_survivability = popularity_total / electorate_total if electorate_total > 0 else 0.0

    other_parties = [p for p in world.parties.values() if p is not agent.party]
    if other_parties:
        min_dist = min(p.ideology.distance(agent.ideology) for p in other_parties)
        alternative_party_access = max(0.0, 1.0 - min(min_dist / 2.0, 1.0))
    else:
        alternative_party_access = 0.0

    vulnerability = (
        0.45 * (1.0 - agent.party_standing)
        + 0.35 * (1.0 - popularity_survivability)
        + 0.20 * (1.0 - alternative_party_access)
    )
    return directive_pressure * min(max(vulnerability, 0.0), 1.0)


# Archetype weights now include expulsion_risk; rescale others slightly.
ARCHETYPE_WEIGHTS: dict[Archetype, dict[str, float]] = {
    Archetype.LOYALIST: {
        "ideology": 0.18,
        "party_directive": 0.36,
        "ig_pressure": 0.14,
        "electoral": 0.09,
        "relationships": 0.13,
        "expulsion_risk": 0.10,
    },
    Archetype.POPULIST: {
        "ideology": 0.14,
        "party_directive": 0.09,
        "ig_pressure": 0.36,
        "electoral": 0.27,
        "relationships": 0.04,
        "expulsion_risk": 0.10,
    },
    Archetype.IDEOLOGUE: {
        "ideology": 0.45,
        "party_directive": 0.09,
        "ig_pressure": 0.14,
        "electoral": 0.04,
        "relationships": 0.18,
        "expulsion_risk": 0.10,
    },
}


def default_vote_weights(archetype: Archetype) -> dict[str, float]:
    return dict(ARCHETYPE_WEIGHTS[archetype])


def perturb_vote_weights(archetype: Archetype, rng: _random.Random) -> dict[str, float]:
    """Sample per-agent vote coefficients around the archetype baseline."""
    baseline = ARCHETYPE_WEIGHTS[archetype]
    weights = {key: value * rng.uniform(0.8, 1.2) for key, value in baseline.items()}
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def get_vote_weights(agent: Agent) -> dict[str, float]:
    weights = agent.attributes.get("vote_weights")
    if weights is not None:
        return weights

    # Agents created mid-simulation still get individualized vote weights.
    seeded_rng = _random.Random(str(agent.id))
    generated = perturb_vote_weights(agent.archetype, seeded_rng)
    agent.attributes["vote_weights"] = generated
    return generated


def compute_vote_disposition(
    agent: Agent,
    policy: Policy,
    world: World,
    proposer: Agent | None = None,
) -> float:
    """Return a score in [-1, 1] for how inclined the agent is to vote yes."""
    w = get_vote_weights(agent)
    components = {
        "ideology": _ideology_score(agent, policy),
        "party_directive": _party_directive_score(agent, policy, world),
        "ig_pressure": _ig_pressure_score(agent, policy),
        "electoral": _electoral_score(agent, policy),
        "relationships": _relationship_score(agent, policy, proposer),
        "expulsion_risk": _expulsion_risk_score(agent, policy, world),
    }
    score = sum(w[k] * v for k, v in components.items())
    score = max(-1.0, min(1.0, score))
    _log.debug(
        "%s vote disposition on '%s': %.3f  [%s]",
        fmt(agent), policy.name, score,
        ", ".join(f"{k}={w[k]:.2f}*{v:+.3f}" for k, v in components.items()),
    )
    return score


def resolve_vote(
    legislature: Legislature,
    policy: Policy,
    world: World,
    proposer: Agent | None = None,
    executive: Agent | None = None,
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
            # Gray zone: abstain only if the agent personally leans No but
            # the party directive pulls Yes. Otherwise vote No.
            w = get_vote_weights(member)
            party_lean = compute_directive_pressure(member, policy)
            personal_lean = disposition - w["party_directive"] * party_lean
            if personal_lean < 0 and party_lean > 0:
                abstain.append(member)
            else:
                no.append(member)

    passed = len(yes) > (len(legislature.members) / 2)

    # Executive tie-breaking: if yes == no and there are actual votes cast,
    # the executive casts the deciding vote.
    if not passed and executive is not None and len(yes) == len(no) and len(yes) > 0:
        exec_disposition = compute_vote_disposition(executive, policy, world, proposer)
        if exec_disposition > 0.0:
            passed = True
            _log.debug("  Executive %s broke tie in favour (disposition=%.3f)",
                       fmt(executive), exec_disposition)
        else:
            _log.debug("  Executive %s broke tie against (disposition=%.3f)",
                       fmt(executive), exec_disposition)

    # --- Executive veto ---
    vetoed = False
    veto_disposition_val: float | None = None
    if passed and executive is not None:
        gov = world.governments.get(legislature.place.id)
        veto_threshold = gov.veto_threshold if gov is not None else -0.3
        exec_disp = compute_vote_disposition(executive, policy, world, proposer)
        veto_disposition_val = exec_disp
        if exec_disp < veto_threshold:
            vetoed = True
            passed = False
            _log.info(
                "  VETO: %s vetoed '%s' (exec_disp=%.3f < threshold=%.3f)",
                fmt(executive), policy.name, exec_disp, veto_threshold,
            )

    _log.info(
        "  Vote on '%s': %s (%dY/%dN/%dA)%s",
        policy.name, "PASSED" if passed else "FAILED",
        len(yes), len(no), len(abstain),
        " [VETOED]" if vetoed else "",
    )

    return VoteResult(
        policy=policy,
        place=legislature.place,
        proposer=proposer,
        yes_votes=yes,
        no_votes=no,
        abstentions=abstain,
        passed=passed,
        vetoed=vetoed,
        veto_disposition=veto_disposition_val,
    )
