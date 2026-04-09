from __future__ import annotations

import random as _random
from typing import TYPE_CHECKING

from src.actions.utility import perturb_weights
from src.actions.voting import perturb_vote_weights
from src.models.ideology import Ideology
from src.models.types import PlaceTier

if TYPE_CHECKING:
    from src.models.world import World

# Default populations by tier (used when place has no explicit population set).
_DEFAULT_POPULATION = {
    PlaceTier.FEDERAL: 25_000_000,
    PlaceTier.STATE: 2_000_000,
    PlaceTier.MUNICIPALITY: 150_000,
}


def initialize_local_variables(world: World, rng: _random.Random | None = None) -> None:
    """Seed per-place dynamic state from place.interest_group_presence.

    Call this right before starting the simulation. For each place that
    has interest-group presence defined, this populates the group's
    ``electorate_share`` and (if not already set) ``satisfaction``.
    It also seeds per-agent vote weights from their archetype profile,
    IG ideology from best-matching party, and place populations.
    """
    if rng is None:
        rng = _random.Random("setup_seed")

    # --- Place populations ---
    for place in world.places.values():
        if "population" not in place.attributes:
            base = _DEFAULT_POPULATION.get(place.tier, 100_000)
            place.attributes["population"] = int(base * rng.uniform(0.5, 1.5))

    # --- IG electorate share and satisfaction ---
    for place in world.places.values():
        for ig, share in place.interest_group_presence.items():
            # Electorate share mirrors presence but weighted by population.
            pop = place.attributes.get("population", 100_000)
            ig.electorate_share[place] = share
            # Store population-weighted share for election use.
            ig.attributes.setdefault("pop_share", {})[place] = share * pop
            # Default satisfaction to 0.5 (neutral) if not already set.
            if place not in ig.satisfaction:
                ig.satisfaction[place] = 0.5

    # --- IG ideology: seed from highest-affinity party with noise ---
    all_parties = list(world.parties.values())
    for ig in world.interest_groups.values():
        if ig.ideology.axes:
            continue  # already set
        best_party = max(
            all_parties,
            key=lambda p: p.base_constituency.get(ig, 0.0),
            default=None,
        )
        if best_party is not None:
            ig_rng = _random.Random(f"{ig.id}:ideology")
            axes = {
                ax: max(-1.0, min(1.0, val + ig_rng.uniform(-0.15, 0.15)))
                for ax, val in best_party.ideology.axes.items()
            }
            ig.ideology = Ideology(axes=axes)

    # --- Agent weights and inertia ---
    for agent in world.politicians.values():
        if "utility_weights" not in agent.attributes:
            arng = _random.Random(f"{agent.id}:utility")
            agent.attributes["utility_weights"] = perturb_weights(arng)
        if "vote_weights" not in agent.attributes:
            arng = _random.Random(f"{agent.id}:vote")
            agent.attributes["vote_weights"] = perturb_vote_weights(agent.archetype, arng)
        agent.attributes.setdefault("split_inertia", 0)
