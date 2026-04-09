from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.actions.base import Action, ActionType, VoteResult
from src.actions.voting import compute_directive_pressure, get_party_support
from src.models.types import PartyRole
from src.log_utils import fmt

if TYPE_CHECKING:
    from src.models.world import World

_log = logging.getLogger("simulation.consequences")


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
                _log.debug("  %s satisfaction: %.3f -> %.3f (impact=%.3f)",
                           ig.name, old, ig.satisfaction[result.place], impact)

    # 2. Agent popularity — voters remember how you voted.
    all_voters = result.yes_votes + result.no_votes
    for agent in all_voters:
        voted_yes = agent in result.yes_votes
        for ig, impact in policy.interest_group_impacts.items():
            if ig not in agent.popularity:
                continue
            direction = 1.0 if voted_yes else -1.0
            delta = direction * impact * 0.1
            old_pop = agent.popularity[ig]
            agent.popularity[ig] = _clamp(old_pop + delta, 0.0, 1.0)
            _log.debug("  %s popularity[%s]: %.3f -> %.3f (delta=%.3f)",
                       fmt(agent), ig.name, old_pop, agent.popularity[ig], delta)

    # 3. Party standing — explicit party_support is the source of truth.
    party_support_map: dict = policy.attributes.get("party_support", {})
    for agent in all_voters:
        voted_yes = agent in result.yes_votes
        party_support = get_party_support(agent, policy)
        directive_pressure = compute_directive_pressure(agent, policy)
        party_wants_yes = directive_pressure > 0.0

        old_standing = agent.party_standing
        if directive_pressure == 0.0:
            agent.attributes["recent_defiance"] = 0.0
        elif voted_yes == party_wants_yes:
            standing_gain = 0.01 + 0.03 * abs(directive_pressure)
            agent.party_standing = _clamp(agent.party_standing + standing_gain, 0.0, 1.0)
            agent.attributes["recent_defiance"] = 0.0
        else:
            standing_loss = 0.02 + 0.08 * abs(directive_pressure)
            agent.party_standing = _clamp(agent.party_standing - standing_loss, 0.0, 1.0)
            agent.attributes["recent_defiance"] = abs(directive_pressure)
            events.append(f"{fmt(agent)} defied {agent.party.name} party line")
        _log.debug("  %s party_standing: %.3f -> %.3f (party_support=%.3f, voted_yes=%s)",
                   fmt(agent), old_standing, agent.party_standing, party_support or 0.0, voted_yes)

    # 4. Relationships — voting together builds trust.
    for a in result.yes_votes:
        for b in result.yes_votes:
            if a is not b:
                a.relationships[b] = _clamp(a.relationships.get(b, 0.0) + 0.02)
    for a in result.no_votes:
        for b in result.no_votes:
            if a is not b:
                a.relationships[b] = _clamp(a.relationships.get(b, 0.0) + 0.02)
    for a in result.yes_votes:
        for b in result.no_votes:
            a.relationships[b] = _clamp(a.relationships.get(b, 0.0) - 0.01)
            b.relationships[a] = _clamp(b.relationships.get(a, 0.0) - 0.01)

    # 5. Failed proposal penalty — proposer showed their hand.
    if not result.passed and result.proposer is not None:
        proposer = result.proposer
        for ig, impact in policy.interest_group_impacts.items():
            if impact < 0 and ig in proposer.popularity:
                old_pop = proposer.popularity[ig]
                proposer.popularity[ig] = _clamp(old_pop + impact * 0.05, 0.0, 1.0)
                _log.debug("  %s popularity[%s]: %.3f -> %.3f (failed proposal exposure)",
                           fmt(proposer), ig.name, old_pop, proposer.popularity[ig])
        party_support = party_support_map.get(proposer.party, 0.0)
        if party_support < -0.05:
            old_standing = proposer.party_standing
            proposer.party_standing = _clamp(proposer.party_standing - 0.03, 0.0, 1.0)
            _log.debug("  %s party_standing: %.3f -> %.3f (failed anti-party proposal)",
                       fmt(proposer), old_standing, proposer.party_standing)

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
        impact_lines: list[str] = []
        for ig in agent.place.interest_group_presence:
            if ig not in agent.popularity:
                continue
            allegiance = agent.allegiances.get(ig, 0.0)
            delta = allegiance * 0.05 - (1.0 - allegiance) * 0.03
            old = agent.popularity[ig]
            agent.popularity[ig] = _clamp(old + delta, 0.0, 1.0)
            impact_lines.append(
                f"{ig.name}:{old:.2f}->{agent.popularity[ig]:.2f} "
                f"(allegiance={allegiance:.2f}, delta={delta:+.3f})"
            )
            _log.debug(
                "  %s take_position on %s: popularity %.3f -> %.3f "
                "(allegiance=%.3f, delta=%.3f)",
                fmt(agent), ig.name, old, agent.popularity[ig], allegiance, delta,
            )
        events.append(
            f"{fmt(agent)} took a public position "
            f"[{'; '.join(impact_lines)}]"
        )

    elif action.action_type is ActionType.BUILD_RELATIONSHIP:
        if action.target is not None:
            old = agent.relationships.get(action.target, 0.0)
            new_val = _clamp(old + 0.05)
            agent.relationships[action.target] = new_val
            old_rev = action.target.relationships.get(agent, 0.0)
            new_rev = _clamp(old_rev + 0.03)
            action.target.relationships[agent] = new_rev
            if action.target.party is not agent.party:
                old_standing = agent.party_standing
                agent.party_standing = _clamp(agent.party_standing - 0.02, 0.0, 1.0)
                _log.debug(
                    "  %s build_relationship with %s: rel %.3f -> %.3f, reverse %.3f -> %.3f, "
                    "party_standing %.3f -> %.3f (cross-party)",
                    fmt(agent), fmt(action.target), old, new_val, old_rev, new_rev,
                    old_standing, agent.party_standing,
                )
            else:
                _log.debug(
                    "  %s build_relationship with %s: rel %.3f -> %.3f, reverse %.3f -> %.3f",
                    fmt(agent), fmt(action.target), old, new_val, old_rev, new_rev,
                )
            events.append(
                f"{fmt(agent)} built relationship with {fmt(action.target)} "
                f"(rel: {old:+.2f} → {new_val:+.2f}, reverse: {old_rev:+.2f} → {new_rev:+.2f})"
            )

    elif action.action_type is ActionType.CAMPAIGN:
        ig = action.params.get("interest_group")
        if ig is not None and ig in agent.popularity:
            campaign_old_pop = agent.popularity[ig]
            new_pop = _clamp(campaign_old_pop + 0.08, 0.0, 1.0)
            agent.popularity[ig] = new_pop
            old_standing = agent.party_standing
            new_standing = _clamp(agent.party_standing - 0.02, 0.0, 1.0)
            agent.party_standing = new_standing
            _log.debug(
                "  %s campaign towards %s: popularity %.3f -> %.3f, party_standing %.3f -> %.3f",
                fmt(agent), ig.name, campaign_old_pop, new_pop, old_standing, new_standing,
            )
            neglect_lines: list[str] = []
            for other_ig in agent.place.interest_group_presence:
                if other_ig is not ig and other_ig in agent.popularity:
                    other_old_pop = agent.popularity[other_ig]
                    new_other_pop = _clamp(other_old_pop - 0.02, 0.0, 1.0)
                    agent.popularity[other_ig] = new_other_pop
                    neglect_lines.append(
                        f"{other_ig.name}:{other_old_pop:.2f}->{new_other_pop:.2f}"
                    )
                    _log.debug(
                        "  %s campaign neglect on %s: popularity %.3f -> %.3f",
                        fmt(agent), other_ig.name, other_old_pop, new_other_pop,
                    )
            event = (
                f"{fmt(agent)} campaigned towards {ig.name} "
                f"(popularity: {campaign_old_pop:.2f} -> {new_pop:.2f}, "
                f"party_standing: {old_standing:.2f} -> {new_standing:.2f}"
            )
            if neglect_lines:
                event += f", neglect: [{'; '.join(neglect_lines)}]"
            event += ")"
            events.append(event)

    elif action.action_type is ActionType.ENFORCE_DISCIPLINE:
        if action.target is not None:
            action.target.party_standing = _clamp(action.target.party_standing - 0.1, 0.0, 1.0)
            action.target.attributes["recent_defiance"] = max(
                0.0, action.target.attributes.get("recent_defiance", 0.0) - 0.5
            )
            events.append(f"{fmt(agent)} disciplined {fmt(action.target)}")

    elif action.action_type is ActionType.EXPEL_MEMBER:
        if action.target is not None:
            target = action.target
            old_party = agent.party
            old_party.remove_member(target)

            # Find ideologically closest other party.
            other_parties = [p for p in world.parties.values() if p is not old_party]
            if other_parties:
                new_party = min(other_parties,
                                key=lambda p: p.ideology.distance(target.ideology))
                new_party.add_member(target, PartyRole.MEMBER)
                target.party = new_party

                # Popularity penalty from old party IGs; small gain from new party IGs.
                for ig, affinity in old_party.base_constituency.items():
                    if ig in target.popularity:
                        target.popularity[ig] = _clamp(
                            target.popularity[ig] - 0.15 * affinity, 0.0, 1.0)
                for ig, affinity in new_party.base_constituency.items():
                    if ig in target.popularity:
                        target.popularity[ig] = _clamp(
                            target.popularity[ig] + 0.05 * affinity, 0.0, 1.0)

                events.append(
                    f"{fmt(agent)} expelled {fmt(target)} from {old_party.name} "
                    f"— {fmt(target)} joined {new_party.name}"
                )
                _log.info("  %s expelled from %s, joined %s",
                          fmt(target), old_party.name, new_party.name)
            else:
                events.append(f"{fmt(agent)} expelled {fmt(target)} from {old_party.name} (no party to join)")

    return events
