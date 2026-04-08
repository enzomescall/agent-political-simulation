from __future__ import annotations

from typing import TYPE_CHECKING

from src.actions.base import Action, ActionType, VoteResult

if TYPE_CHECKING:
    from src.models.world import World


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def apply_vote_consequences(result: VoteResult, world: World) -> list[str]:
    """Update world state after a legislative vote. Returns narrative log entries."""
    events: list[str] = []
    policy = result.policy

    # 1. Interest-group satisfaction (only if the policy passed).
    if result.passed:
        for ig, impact in policy.interest_group_impacts.items():
            if result.place in ig.satisfaction:
                old = ig.satisfaction[result.place]
                ig.satisfaction[result.place] = _clamp(old + impact * 0.3, 0.0, 1.0)

    # 2. Agent popularity — voters remember how you voted.
    all_voters = result.yes_votes + result.no_votes
    for agent in all_voters:
        voted_yes = agent in result.yes_votes
        for ig, impact in policy.interest_group_impacts.items():
            if ig not in agent.popularity:
                continue
            # Voting with the group's interest → popularity up; against → down.
            direction = 1.0 if voted_yes else -1.0
            delta = direction * impact * 0.1
            agent.popularity[ig] = _clamp(agent.popularity[ig] + delta, 0.0, 1.0)

    # 3. Party standing — did they follow the party line?
    for agent in all_voters:
        voted_yes = agent in result.yes_votes
        # Approximate party line from party ideology alignment with the policy.
        party_lean = 0.0
        count = 0
        for axis, direction in policy.ideology_alignment.items():
            party_lean += agent.party.ideology[axis] * direction
            count += 1
        if count > 0:
            party_lean /= count
        party_wants_yes = party_lean > 0.05

        if voted_yes == party_wants_yes:
            agent.party_standing = _clamp(agent.party_standing + 0.03, 0.0, 1.0)
        else:
            agent.party_standing = _clamp(agent.party_standing - 0.05, 0.0, 1.0)
            events.append(f"{agent.name} defied {agent.party.name} party line")

    # 4. Relationships — voting together builds trust.
    for a in result.yes_votes:
        for b in result.yes_votes:
            if a is not b:
                old = a.relationships.get(b, 0.0)
                a.relationships[b] = _clamp(old + 0.02)
    for a in result.no_votes:
        for b in result.no_votes:
            if a is not b:
                old = a.relationships.get(b, 0.0)
                a.relationships[b] = _clamp(old + 0.02)
    # Opposing voters lose trust.
    for a in result.yes_votes:
        for b in result.no_votes:
            old_ab = a.relationships.get(b, 0.0)
            a.relationships[b] = _clamp(old_ab - 0.01)
            old_ba = b.relationships.get(a, 0.0)
            b.relationships[a] = _clamp(old_ba - 0.01)

    status = "PASSED" if result.passed else "FAILED"
    events.insert(0,
        f"Vote on '{policy.name}': {status} "
        f"({len(result.yes_votes)}Y / {len(result.no_votes)}N / {len(result.abstentions)}A)"
    )
    return events


def apply_action_consequences(action: Action, world: World) -> list[str]:
    """Update world state after a non-vote action. Returns narrative log entries."""
    events: list[str] = []
    agent = action.actor

    if action.action_type is ActionType.TAKE_POSITION:
        # Popularity shift: aligned IGs like it, opposed don't.
        for ig, allegiance in agent.allegiances.items():
            if ig in agent.popularity:
                delta = allegiance * 0.05
                agent.popularity[ig] = _clamp(agent.popularity[ig] + delta, 0.0, 1.0)
        events.append(f"{agent.name} took a public position")

    elif action.action_type is ActionType.BUILD_RELATIONSHIP:
        if action.target is not None:
            old = agent.relationships.get(action.target, 0.0)
            agent.relationships[action.target] = _clamp(old + 0.05)
            old_rev = action.target.relationships.get(agent, 0.0)
            action.target.relationships[agent] = _clamp(old_rev + 0.03)
            events.append(f"{agent.name} built relationship with {action.target.name}")

    elif action.action_type is ActionType.CAMPAIGN:
        ig = action.params.get("interest_group")
        if ig is not None and ig in agent.popularity:
            agent.popularity[ig] = _clamp(agent.popularity[ig] + 0.08, 0.0, 1.0)
            events.append(f"{agent.name} campaigned towards {ig.name}")

    elif action.action_type is ActionType.ENFORCE_DISCIPLINE:
        if action.target is not None:
            action.target.party_standing = _clamp(action.target.party_standing - 0.1, 0.0, 1.0)
            events.append(f"{agent.name} disciplined {action.target.name}")

    elif action.action_type is ActionType.EXPEL_MEMBER:
        if action.target is not None:
            agent.party.remove_member(action.target)
            events.append(f"{agent.name} expelled {action.target.name} from {agent.party.name}")

    return events
