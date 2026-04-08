from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .types import InterestGroupId

if TYPE_CHECKING:
    from .place import Place


@dataclass(eq=False)
class InterestGroup:
    """An organised bloc of the electorate that pressures politicians."""

    id: InterestGroupId
    name: str

    fears: list[str] = field(default_factory=list)

    # Per-place scores — populated by the simulation initializer, not at construction.
    satisfaction: dict[Place, float] = field(default_factory=dict)
    electorate_share: dict[Place, float] = field(default_factory=dict)

    attributes: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def pressure_on(self, place: Place) -> float:
        """Pressure is proportional to dissatisfaction x local strength."""
        sat = self.satisfaction.get(place, 0.0)
        share = self.electorate_share.get(place, 0.0)
        return (1.0 - max(sat, 0.0)) * share
