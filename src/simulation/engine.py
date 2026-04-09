from __future__ import annotations

import logging
import math
import random as _random
from typing import TYPE_CHECKING

from src.actions.base import Action, ActionType, TurnReport
from src.actions.decision import choose_action, choose_party_action
from src.actions.voting import compute_vote_disposition, resolve_vote
from src.simulation.consequences import apply_action_consequences, apply_vote_consequences
from src.simulation.drift import apply_ideological_drift, apply_ig_radicalization
from src.simulation.elections import (
    check_elections, check_party_elections, cleanup_agents,
    run_executive_election, run_legislative_election, run_party_election,
)
from src.simulation.factions import check_splits
from src.simulation.policy_gen import generate_policy_pool
from src.models.types import PartyRole

if TYPE_CHECKING:
    from src.models.world import World
from collections import Counter

_log = logging.getLogger("simulation")


def run_turn(world: World, rng: _random.Random | None = None) -> TurnReport:
    """Execute one simulation turn."""
    if rng is None:
        rng = _random.Random()

    report = TurnReport(turn=world.turn)
    _log.info("=== Turn %d ===", world.turn)

    # --- Phase 0: check for splits, then elections ---
    split_events = check_splits(world, rng)
    report.split_events.extend(split_events)
    report.events.extend(split_events)

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

    for party in check_party_elections(world):
        _log.info("Party leadership election for %s", party.name)
        party_events = run_party_election(party, world, rng)
        report.events.extend(party_events)

    cleanup_events = cleanup_agents(world)
    report.events.extend(cleanup_events)

    # --- Phase 1: policy generation ---
    # For each government, generate a pool of candidate policies.
    policy_pools: dict[str, list[tuple]] = {}  # place_id -> [(Policy, Agent)]
    for place_id, gov in world.governments.items():
        pool = generate_policy_pool(gov, world, rng)
        policy_pools[place_id] = pool
        for policy, author in pool:
            _log.info("  Policy pool: '%s' by %s", policy.name, author.name)

    # --- Phase 2: action selection (all agents, LOD-scored) ---
    agents = sorted(
        world.politicians.values(),
        key=lambda a: a.detail_level.value,
    )
    lod_counts = Counter(a.detail_level for a in agents)
    _log.debug("Agent LOD distribution: %s", dict(lod_counts))

    vote_requests: list[Action] = []
    non_vote_actions: list[Action] = []

    for agent in agents:
        if agent.detail_level.value > 1:
            continue # in future i'll just have three helper functions here for the LODs

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

        # Party leaders also get a second party-level action.
        if agent.party_role is PartyRole.LEADER:
            party_action = choose_party_action(agent, world, rng=rng)
            if party_action is not None:
                non_vote_actions.append(party_action)
                report.actions_taken.append(party_action)

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

    # --- Phase 3b: veto override votes ---
    for result in report.vote_results:
        if not result.vetoed:
            continue
        gov = world.governments.get(result.place.id)
        if gov is None or gov.legislature is None:
            continue
        frac = getattr(gov, "veto_override_fraction", 2 / 3)
        seats = len(gov.legislature.members)
        override_threshold = math.ceil(frac * seats) + 1
        yes_count = sum(
            1 for m in gov.legislature.members
            if compute_vote_disposition(m, result.policy, world, result.proposer) > 0.1
        )
        if yes_count >= override_threshold:
            result.veto_override = True
            result.passed = True
            override_events = apply_vote_consequences(result, world)
            report.veto_events.extend(override_events)
            report.events.append(
                f"Veto overridden on '{result.policy.name}' "
                f"({yes_count}/{seats} votes, needed {override_threshold})"
            )
            _log.info(
                "  VETO OVERRIDE: '%s' passed on override (%d/%d)",
                result.policy.name, yes_count, seats,
            )
        else:
            report.events.append(
                f"Veto sustained on '{result.policy.name}' "
                f"({yes_count}/{seats} votes, needed {override_threshold})"
            )
            _log.info(
                "  VETO SUSTAINED: '%s' (%d/%d, needed %d)",
                result.policy.name, yes_count, seats, override_threshold,
            )
        report.veto_events.append(
            f"{'OVERRIDE' if result.veto_override else 'SUSTAINED'}: "
            f"'{result.policy.name}' ({yes_count}/{seats})"
        )

    # --- Phase 4: apply consequences for non-vote actions ---
    for action in non_vote_actions:
        action_events = apply_action_consequences(action, world)
        report.events.extend(action_events)

    # --- Phase 5: ideological drift and IG radicalization ---
    drift_events = apply_ideological_drift(world, rng)
    rad_events = apply_ig_radicalization(world)
    report.drift_events.extend(drift_events + rad_events)
    # Only log significant drift events to the main event stream
    report.events.extend(e for e in rad_events if "radicalizing" in e)

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
