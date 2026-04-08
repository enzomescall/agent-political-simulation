from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.actions.base import Action, ActionType, TurnReport
from src.actions.decision import choose_action
from src.actions.voting import resolve_vote
from src.simulation.consequences import apply_action_consequences, apply_vote_consequences
from src.simulation.elections import check_elections, run_executive_election, run_legislative_election
from src.simulation.policy_gen import generate_policy_pool

if TYPE_CHECKING:
    from src.models.world import World

_log = logging.getLogger("simulation")


def run_turn(world: World, rng: _random.Random | None = None) -> TurnReport:
    """Execute one simulation turn."""
    if rng is None:
        rng = _random.Random()

    report = TurnReport(turn=world.turn)
    _log.info("=== Turn %d ===", world.turn)

    # --- Phase 0: check for scheduled elections ---
    for gov in check_elections(world):
        _log.info("Election triggered for %s", gov.place.name)
        exec_result = run_executive_election(gov, world, rng)
        report.election_results.append(exec_result)
        report.events.extend(exec_result.events)
        if gov.legislature is not None:
            leg_result = run_legislative_election(gov, world, rng)
            report.election_results.append(leg_result)
            report.events.extend(leg_result.events)
        gov.attributes["last_election_turn"] = world.turn

    # --- Phase 1: policy generation ---
    # For each government, generate a pool of candidate policies.
    policy_pools: dict[str, list[tuple]] = {}  # place_id -> [(Policy, Agent)]
    for place_id, gov in world.governments.items():
        pool = generate_policy_pool(gov, world, rng)
        policy_pools[place_id] = pool
        for policy, author in pool:
            _log.info("  Policy pool: '%s' by %s", policy.name, author.name)

    # --- Phase 2: action selection (all agents, utility-scored) ---
    agents = sorted(
        world.politicians.values(),
        key=lambda a: a.detail_level.value,
    )

    vote_requests: list[Action] = []
    non_vote_actions: list[Action] = []

    for agent in agents:
        if agent.detail_level.value > 1:
            continue

        # Get the policy pool for this agent's place.
        pool = policy_pools.get(agent.place.id, [])

        action = choose_action(agent, world, policy_pool=pool, rng=rng)
        if action is None:
            continue

        if action.action_type is ActionType.REQUEST_VOTE and action.policy is not None:
            vote_requests.append(action)
            report.actions_taken.append(action)
            report.events.append(
                f"{agent.name} requested vote on '{action.policy.name}'"
            )
            _log.info("  %s requested vote on '%s'", agent.name, action.policy.name)
        else:
            non_vote_actions.append(action)
            report.actions_taken.append(action)

    # --- Phase 3: vote resolution ---
    # Deduplicate: if multiple agents requested the same policy, only vote once.
    voted_policies: set[int] = set()
    for request in vote_requests:
        policy = request.policy
        assert policy is not None
        policy_id = id(policy)
        if policy_id in voted_policies:
            continue
        voted_policies.add(policy_id)

        proposer = request.params.get("proposer", request.actor)
        place = request.actor.place
        gov = world.governments.get(place.id)
        if gov is None or gov.legislature is None:
            report.events.append(f"No legislature to vote on '{policy.name}' — skipped")
            continue

        executive = gov.executive.holder
        result = resolve_vote(
            gov.legislature, policy, world,
            proposer=proposer, executive=executive,
        )
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

        vote_events = apply_vote_consequences(result, world)
        report.events.extend(vote_events)

    # --- Phase 4: apply consequences for non-vote actions ---
    for action in non_vote_actions:
        action_events = apply_action_consequences(action, world)
        report.events.extend(action_events)

    world.turn += 1
    return report


def run_simulation(
    world: World,
    num_turns: int,
    rng: _random.Random | None = None,
    debug: bool = False,
) -> list[TurnReport]:
    """Run multiple turns and return all reports."""
    if rng is None:
        rng = _random.Random()

    if debug:
        sim_logger = logging.getLogger("simulation")
        sim_logger.setLevel(logging.DEBUG)
        if not sim_logger.handlers:
            # Verbose log → file
            fh = logging.FileHandler("simulation.log", mode="w")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter("%(name)s | %(message)s"))
            sim_logger.addHandler(fh)
            # Summary log → terminal (INFO only)
            sh = logging.StreamHandler()
            sh.setLevel(logging.INFO)
            sh.setFormatter(logging.Formatter("%(message)s"))
            sim_logger.addHandler(sh)

    reports = []
    for _ in range(num_turns):
        reports.append(run_turn(world, rng))
    return reports
