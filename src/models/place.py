from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .types import PlaceId, PlaceTier

if TYPE_CHECKING:
    from .interest_group import InterestGroup


@dataclass(eq=False)
class Place:
    """A geographic/administrative unit at any tier of government."""

    id: PlaceId
    name: str
    tier: PlaceTier

    parent: Place | None = None
    children: list[Place] = field(default_factory=list)

    # Interest-group presence: group → share of local population [0, 1].
    interest_group_presence: dict[InterestGroup, float] = field(
        default_factory=dict,
    )

    # Open-ended bucket for future attributes (demographics, resources, etc.)
    attributes: dict[str, Any] = field(default_factory=dict)
