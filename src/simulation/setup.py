from __future__ import annotations

import random as _random
from typing import TYPE_CHECKING

from src.actions.utility import perturb_weights
from src.actions.voting import perturb_vote_weights

if TYPE_CHECKING:
    from src.models.world import World


def initialize_local_variables(world: World) -> None:
    """Seed per-place dynamic state from place.interest_group_presence.

    Call this right before starting the simulation. For each place that
    has interest-group presence defined, this populates the group's
    ``electorate_share`` and (if not already set) ``satisfaction``.
    It also seeds per-agent vote weights from their archetype profile.
    """
    for place in world.places.values():
        for ig, share in place.interest_group_presence.items():
            # Electorate share mirrors presence.
            ig.electorate_share[place] = share
            # Default satisfaction to 0.5 (neutral) if not already set.
            if place not in ig.satisfaction:
                ig.satisfaction[place] = 0.5

    for agent in world.politicians.values():
        if "utility_weights" not in agent.attributes:
            rng = _random.Random(f"{agent.id}:utility")
            agent.attributes["utility_weights"] = perturb_weights(rng)
        if "vote_weights" not in agent.attributes:
            rng = _random.Random(f"{agent.id}:vote")
            agent.attributes["vote_weights"] = perturb_vote_weights(agent.archetype, rng)
