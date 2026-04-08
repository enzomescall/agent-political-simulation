from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.world import World

_log = logging.getLogger("simulation.utility")

DEFAULT_WEIGHTS = {
    "popularity": 0.3,
    "party_standing": 0.2,
    "ideology": 0.15,
    "ig_appeal": 0.2,
    "relationships": 0.15,
}


def default_utility_weights() -> dict[str, float]:
    return dict(DEFAULT_WEIGHTS)


def perturb_weights(rng: _random.Random) -> dict[str, float]:
    """Randomly sample utility coefficients ±30% from baseline."""
    weights = {}
    for k, v in DEFAULT_WEIGHTS.items():
        weights[k] = v * rng.uniform(0.7, 1.3)
    # Normalize so they sum to 1.
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def get_weights(agent: Agent) -> dict[str, float]:
    return agent.attributes.get("utility_weights", DEFAULT_WEIGHTS)


def compute_utility(agent: Agent, world: World) -> float:
    """Current utility score for an agent — weighted sum of factors."""
    w = get_weights(agent)
    place = agent.place

    # Popularity: avg(popularity[ig] × electorate_share) across IGs in place.
    pop_score = 0.0
    share_sum = 0.0
    for ig, share in place.interest_group_presence.items():
        es = ig.electorate_share.get(place, share)
        pop_score += agent.popularity.get(ig, 0.0) * es
        share_sum += es
    if share_sum > 0:
        pop_score /= share_sum

    # Party standing: direct.
    standing_score = agent.party_standing

    # Ideology: placeholder — 0 for now.
    ideology_score = 0.0

    # IG appeal: weighted sum of allegiance × satisfaction.
    ig_score = 0.0
    alleg_sum = sum(agent.allegiances.values())
    if alleg_sum > 0:
        for ig, allegiance in agent.allegiances.items():
            sat = ig.satisfaction.get(place, 0.5)
            ig_score += allegiance * sat
        ig_score /= alleg_sum

    # Relationships: avg relationship with legislature peers.
    rel_score = 0.0
    gov = world.governments.get(place.id)
    if gov and gov.legislature:
        peers = [m for m in gov.legislature.members if m is not agent]
        if peers:
            rel_score = sum(agent.relationships.get(p, 0.0) for p in peers) / len(peers)

    utility = (
        w["popularity"] * pop_score
        + w["party_standing"] * standing_score
        + w["ideology"] * ideology_score
        + w["ig_appeal"] * ig_score
        + w["relationships"] * rel_score
    )
    return utility
