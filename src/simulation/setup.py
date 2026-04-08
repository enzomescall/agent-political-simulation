from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.world import World


def initialize_local_variables(world: World) -> None:
    """Seed per-place dynamic state from place.interest_group_presence.

    Call this right before starting the simulation. For each place that
    has interest-group presence defined, this populates the group's
    ``electorate_share`` and (if not already set) ``satisfaction``.
    """
    for place in world.places.values():
        for ig, share in place.interest_group_presence.items():
            # Electorate share mirrors presence.
            ig.electorate_share[place] = share
            # Default satisfaction to 0.5 (neutral) if not already set.
            if place not in ig.satisfaction:
                ig.satisfaction[place] = 0.5
