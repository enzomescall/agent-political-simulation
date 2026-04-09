from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.types import PartyRole
from src.log_utils import fmt

from .availability import available_actions
from .base import Action, ActionType
from .utility import get_weights
from .voting import compute_vote_disposition

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.policy import Policy
    from src.models.world import World

_log = logging.getLogger("simulation.decision")


def _predict_vote_outcome(
    agent: Agent,
    policy: Policy,
    world: World,
) -> tuple[float, int, int]:
    """Predict how a vote would go. Returns (pass_probability, predicted_yes, predicted_no)."""
    gov = world.governments.get(agent.place.id)
    if gov is None or gov.legislature is None:
        return 0.0, 0, 0

    yes, no = 0, 0
    for member in gov.legislature.members:
        # This is probably the one that we need to cache
        disposition = compute_vote_disposition(member, policy, world, proposer=agent)
        if disposition > 0.1:
            yes += 1
        elif disposition < -0.1:
            no += 1

    total = len(gov.legislature.members)
    passed = yes > total / 2
    # Probability is a soft estimate — closer votes are less certain.
    if total == 0:
        return 0.0, 0, 0
    margin = abs(yes - total / 2) / total
    prob = min(1.0, 0.5 + margin * 2) if passed else max(0.0, 0.5 - margin * 2)
    return prob, yes, no


def _estimate_request_vote_utility(
    agent: Agent,
    policy: Policy,
    proposer: Agent,
    world: World,
) -> float:
    """Estimate utility delta from requesting a vote on a policy."""
    w = get_weights(agent)
    predicted_vote = policy.attributes.get("predicted_vote")
    if predicted_vote is not None:
        prob = predicted_vote.get("pass_probability", 0.0)
    else:
        prob, _, _ = _predict_vote_outcome(proposer, policy, world)

    # Utility if the policy passes.
    pass_utility = 0.0
    # Popularity gain: voting yes on a passing policy that helps your IGs.
    for ig, impact in policy.interest_group_impacts.items():
        es = ig.electorate_share.get(agent.place, 0.0)
        pass_utility += w["popularity"] * impact * 0.1 * es
        pass_utility += w["ig_appeal"] * impact * 0.3 * agent.allegiances.get(ig, 0.0)
    # Party standing: does this align with party ideology?
    party_lean = 0.0
    count = 0
    for axis, direction in policy.ideology_alignment.items():
        party_lean += agent.party.ideology[axis] * direction
        count += 1
    if count > 0:
        party_lean /= count
    pass_utility += w["party_standing"] * (0.03 if party_lean > 0.05 else -0.05)

    # Utility if it fails — proposer takes a hit.
    fail_utility = 0.0
    if proposer is agent:
        fail_utility -= w["popularity"] * 0.05
        if party_lean < -0.05:
            fail_utility -= w["party_standing"] * 0.03

    return prob * pass_utility + (1.0 - prob) * fail_utility


def _estimate_campaign_utility(agent: Agent, ig, world: World) -> float:
    """Estimate utility of campaigning towards a specific IG."""
    w = get_weights(agent)
    es = ig.electorate_share.get(agent.place, 0.0)
    # Gain with target IG, lose party standing, lose with other IGs.
    gain = w["popularity"] * 0.08 * es
    cost = w["party_standing"] * 0.02
    neglect = sum(
        w["popularity"] * 0.02 * other.electorate_share.get(agent.place, 0.0)
        for other in agent.place.interest_group_presence
        if other is not ig
    )
    return gain - cost - neglect


def _estimate_build_relationship_utility(agent: Agent, target: Agent, world: World) -> float:
    """Estimate utility of building a relationship with target."""
    w = get_weights(agent)
    gain = w["relationships"] * 0.05
    # Cross-party penalty.
    cost = w["party_standing"] * 0.02 if target.party is not agent.party else 0.0
    return gain - cost


def _estimate_take_position_utility(agent: Agent, world: World) -> float:
    """Estimate utility of taking a public position."""
    w = get_weights(agent)
    total = 0.0
    for ig in agent.place.interest_group_presence:
        allegiance = agent.allegiances.get(ig, 0.0)
        es = ig.electorate_share.get(agent.place, 0.0)
        delta = allegiance * 0.05 - (1.0 - allegiance) * 0.03
        total += w["popularity"] * delta * es
    return total


def _estimate_enforce_discipline_utility(agent: Agent, target: Agent, world: World) -> float:
    """Estimate utility of enforcing discipline on a target."""
    w = get_weights(agent)
    recent_defiance = target.attributes.get("recent_defiance", 0.0)
    if recent_defiance <= 0.0 and target.party_standing >= 0.25:
        return 0.0
    return w["party_standing"] * (0.06 + 0.12 * recent_defiance + 0.05 * (1.0 - target.party_standing))


def choose_action(
    agent: Agent,
    world: World,
    policy_pool: list[tuple[Policy, Agent]] | None = None,
    rng: _random.Random | None = None,
) -> Action | None:
    """Score all available actions and return the best one."""
    if rng is None:
        rng = _random.Random()
    if policy_pool is None:
        policy_pool = []

    allowed = set(available_actions(agent, world))
    candidates: list[tuple[float, Action]] = []

    # REQUEST_VOTE: score each policy in the pool.
    if ActionType.REQUEST_VOTE in allowed and policy_pool:
        for policy, proposer in policy_pool:
            score = _estimate_request_vote_utility(agent, policy, proposer, world)
            candidates.append((score, Action(
                action_type=ActionType.REQUEST_VOTE,
                actor=agent,
                policy=policy,
                params={"proposer": proposer},
            )))

    # CAMPAIGN: score each IG.
    if ActionType.CAMPAIGN in allowed:
        for ig in agent.place.interest_group_presence:
            score = _estimate_campaign_utility(agent, ig, world)
            candidates.append((score, Action(
                action_type=ActionType.CAMPAIGN,
                actor=agent,
                params={"interest_group": ig},
            )))

    # BUILD_RELATIONSHIP: score each peer.
    if ActionType.BUILD_RELATIONSHIP in allowed:
        # TODO: implement LODing here too
        peers = [a for a in world.politicians_in_place(agent.place) if a is not agent]
        for target in peers:
            score = _estimate_build_relationship_utility(agent, target, world)
            candidates.append((score, Action(
                action_type=ActionType.BUILD_RELATIONSHIP,
                actor=agent,
                target=target,
            )))

    # TAKE_POSITION.
    if ActionType.TAKE_POSITION in allowed:
        score = _estimate_take_position_utility(agent, world)
        candidates.append((score, Action(
            action_type=ActionType.TAKE_POSITION,
            actor=agent,
        )))

    # ENFORCE_DISCIPLINE.
    if ActionType.ENFORCE_DISCIPLINE in allowed and agent.party_role in (
        PartyRole.LEADER, PartyRole.WHIP,
    ):
        for member, _role in agent.party.members.items():
            if (
                member is not agent
                and (
                    member.party_standing < 0.25
                    or member.attributes.get("recent_defiance", 0.0) > 0.0
                )
            ):
                score = _estimate_enforce_discipline_utility(agent, member, world)
                candidates.append((score, Action(
                    action_type=ActionType.ENFORCE_DISCIPLINE,
                    actor=agent,
                    target=member,
                )))

    if not candidates:
        _log.debug("%s: no viable actions", fmt(agent))
        return None

    # Add ambition-scaled noise.
    noisy: list[tuple[float, Action]] = []
    for score, action in candidates:
        noise = rng.gauss(0, agent.ambition * 0.02)
        noisy.append((score + noise, action))

    noisy.sort(key=lambda x: x[0], reverse=True)
    best_score, best_action = noisy[0]

    _log.debug(
        "%s: chose %s (score=%.4f) — top 3: [%s]",
        fmt(agent),
        best_action.action_type.name,
        best_score,
        ", ".join(
            f"{a.action_type.name}={s:.4f}"
            for s, a in noisy[:3]
        ),
    )

    return best_action
