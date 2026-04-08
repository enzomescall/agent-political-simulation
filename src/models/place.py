from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import InterestGroupId, PlaceId, PlaceTier


@dataclass
class Place:
    """A geographic/administrative unit at any tier of government."""

    id: PlaceId
    name: str
    tier: PlaceTier

    parent_id: PlaceId | None = None
    children_ids: list[PlaceId] = field(default_factory=list)

    # Interest-group presence: group_id → share of local population [0, 1].
    interest_group_presence: dict[InterestGroupId, float] = field(
        default_factory=dict,
    )

    # Open-ended bucket for future attributes (demographics, resources, etc.)
    attributes: dict[str, Any] = field(default_factory=dict)
