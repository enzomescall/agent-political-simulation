from __future__ import annotations

import random as _random
from typing import TYPE_CHECKING

from src.actions.base import Action, ActionType, TurnReport
from src.actions.decision import choose_action
from src.actions.voting import resolve_vote
from src.simulation.consequences import apply_action_consequences, apply_vote_consequences
from src.simulation.policy_gen import generate_policy

if TYPE_CHECKING:
    from src.models.world import World


def run_turn(world: World, rng: _random.Random | None = None) -> TurnReport:
    """Execute one simulation turn."""
    if rng is None:
        rng = _random.Random()

    report = TurnReport(turn=world.turn)
    proposed_policies: list[tuple[Action, ...]] = []
    non_vote_actions: list[Action] = []

    # Sort agents: L0 first, then L1 — skip L2/L3 for now.
    agents = sorted(
        world.politicians.values(),
        key=lambda a: a.detail_level.value,
    )

    # --- Phase 1: each agent chooses an action ---
    for agent in agents:
        if agent.detail_level.value > 1:
            continue  # Skip L2/L3 for now.

        action = choose_action(agent, world, rng=rng)
        if action is None:
            continue

        if action.action_type is ActionType.PROPOSE_POLICY:
            policy = generate_policy(agent, world, rng)
            action.policy = policy
            proposed_policies.append((action,))
            report.actions_taken.append(action)
            report.events.append(f"{agent.name} proposed '{policy.name}'")
        elif action.action_type is not ActionType.VOTE:
            non_vote_actions.append(action)
            report.actions_taken.append(action)

    # --- Phase 2: vote on all proposed policies ---
    for (proposal_action,) in proposed_policies:
        policy = proposal_action.policy
        assert policy is not None
        place = proposal_action.actor.place

        # Find the legislature for this place.
        gov = world.governments.get(place.id)
        if gov is None or gov.legislature is None:
            report.events.append(f"No legislature to vote on '{policy.name}' — skipped")
            continue

        result = resolve_vote(gov.legislature, policy, world, proposer=proposal_action.actor)
        report.vote_results.append(result)

        # Record individual vote actions.
        for member in gov.legislature.members:
            voted_yes = member in result.yes_votes
            voted_no = member in result.no_votes
            vote_action = Action(
                action_type=ActionType.VOTE,
                actor=member,
                policy=policy,
                vote=True if voted_yes else (False if voted_no else None),
            )
            report.actions_taken.append(vote_action)

        # Apply vote consequences.
        vote_events = apply_vote_consequences(result, world)
        report.events.extend(vote_events)

    # --- Phase 3: apply consequences for non-vote actions ---
    for action in non_vote_actions:
        action_events = apply_action_consequences(action, world)
        report.events.extend(action_events)

    world.turn += 1
    return report


def run_simulation(
    world: World,
    num_turns: int,
    rng: _random.Random | None = None,
) -> list[TurnReport]:
    """Run multiple turns and return all reports."""
    if rng is None:
        rng = _random.Random()
    reports = []
    for _ in range(num_turns):
        reports.append(run_turn(world, rng))
    return reports
