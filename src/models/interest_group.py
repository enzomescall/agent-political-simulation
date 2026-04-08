from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import InterestGroupId, PlaceId


@dataclass
class PolicyPreference:
    """A single policy preference held by an interest group."""

    policy_area: str
    preferred_direction: float  # -1.0 (oppose) … 1.0 (support)
    importance: float  # 0.0 … 1.0


@dataclass
class InterestGroup:
    """An organised bloc of the electorate that pressures politicians."""

    id: InterestGroupId
    name: str

    policy_preferences: list[PolicyPreference] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)

    # Per-place scores — keyed by PlaceId.
    satisfaction: dict[PlaceId, float] = field(default_factory=dict)
    electorate_share: dict[PlaceId, float] = field(default_factory=dict)

    attributes: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def pressure_on(self, place_id: PlaceId) -> float:
        """Pressure is proportional to dissatisfaction x local strength."""
        satisfaction = self.satisfaction.get(place_id, 0.0)
        share = self.electorate_share.get(place_id, 0.0)
        return (1.0 - max(satisfaction, 0.0)) * share
