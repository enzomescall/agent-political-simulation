from __future__ import annotations

import random as _random
from typing import TYPE_CHECKING

from src.models.types import Archetype, OfficeType, PartyRole

from .availability import available_actions
from .base import Action, ActionType

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.policy import Policy
    from src.models.world import World


# Discretionary action weights per archetype.
_DISCRETIONARY_WEIGHTS: dict[Archetype, dict[ActionType, float]] = {
    Archetype.LOYALIST: {
        ActionType.TAKE_POSITION: 0.2,
        ActionType.BUILD_RELATIONSHIP: 0.4,
        ActionType.CAMPAIGN: 0.4,
    },
    Archetype.POPULIST: {
        ActionType.TAKE_POSITION: 0.15,
        ActionType.BUILD_RELATIONSHIP: 0.15,
        ActionType.CAMPAIGN: 0.7,
    },
    Archetype.IDEOLOGUE: {
        ActionType.TAKE_POSITION: 0.6,
        ActionType.BUILD_RELATIONSHIP: 0.25,
        ActionType.CAMPAIGN: 0.15,
    },
}


def _pick_relationship_target(agent: Agent, world: World, rng: _random.Random) -> Agent | None:
    """Pick another agent in the same place to build a relationship with."""
    candidates = [a for a in world.politicians_in_place(agent.place) if a is not agent]
    return rng.choice(candidates) if candidates else None


def _pick_campaign_target(agent: Agent, world: World, rng: _random.Random):
    """Pick an interest group to campaign towards."""
    igs = list(agent.place.interest_group_presence.keys())
    return rng.choice(igs) if igs else None


def choose_action(
    agent: Agent,
    world: World,
    pending_votes: list[Policy] | None = None,
    rng: _random.Random | None = None,
) -> Action | None:
    """Pick the highest-priority action for this agent this turn.

    Returns None if the agent has nothing meaningful to do.
    """
    if rng is None:
        rng = _random.Random()

    allowed = set(available_actions(agent, world))

    # 1. Mandatory: if there's a pending vote, vote on it.
    if pending_votes and ActionType.VOTE in allowed:
        return Action(
            action_type=ActionType.VOTE,
            actor=agent,
            policy=pending_votes[0],
        )

    # 2. Executive with high IG pressure → propose policy.
    if ActionType.PROPOSE_POLICY in allowed and agent.office in (
        OfficeType.MAYOR, OfficeType.GOVERNOR, OfficeType.PRESIDENT,
    ):
        max_pressure = 0.0
        for ig in agent.place.interest_group_presence:
            max_pressure = max(max_pressure, ig.pressure_on(agent.place))
        if max_pressure > 0.15:
            return Action(action_type=ActionType.PROPOSE_POLICY, actor=agent)

    # 3. Party leader with a low-standing member → enforce discipline.
    if ActionType.ENFORCE_DISCIPLINE in allowed and agent.party_role in (
        PartyRole.LEADER, PartyRole.WHIP,
    ):
        for member, _role in agent.party.members.items():
            if member is not agent and member.party_standing < 0.25:
                return Action(
                    action_type=ActionType.ENFORCE_DISCIPLINE,
                    actor=agent,
                    target=member,
                )

    # 4. Discretionary: weighted random from TAKE_POSITION / BUILD_RELATIONSHIP / CAMPAIGN.
    weights = _DISCRETIONARY_WEIGHTS.get(agent.archetype, _DISCRETIONARY_WEIGHTS[Archetype.LOYALIST])
    # Ambition boosts CAMPAIGN weight.
    adjusted: dict[ActionType, float] = {}
    for at, w in weights.items():
        if at is ActionType.CAMPAIGN:
            adjusted[at] = w * (0.5 + agent.ambition)
        else:
            adjusted[at] = w

    choices = list(adjusted.keys())
    choice_weights = [adjusted[c] for c in choices]
    action_type = rng.choices(choices, weights=choice_weights, k=1)[0]

    if action_type is ActionType.BUILD_RELATIONSHIP:
        target = _pick_relationship_target(agent, world, rng)
        return Action(action_type=action_type, actor=agent, target=target)

    if action_type is ActionType.CAMPAIGN:
        ig = _pick_campaign_target(agent, world, rng)
        return Action(action_type=action_type, actor=agent, params={"interest_group": ig})

    return Action(action_type=action_type, actor=agent)
