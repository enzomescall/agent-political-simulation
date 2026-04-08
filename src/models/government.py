from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import AgentId, OfficeType, PlaceId


@dataclass
class Office:
    """A single government position (executive or cabinet)."""

    office_type: OfficeType
    place_id: PlaceId
    holder_id: AgentId | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Legislature:
    """A legislative body tied to a place."""

    place_id: PlaceId
    seat_type: OfficeType  # e.g. CONGRESSPERSON, COUNCILPERSON
    total_seats: int = 0
    member_ids: list[AgentId] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Government:
    """The full government structure for a single place."""

    place_id: PlaceId
    executive: Office
    cabinet: list[Office] = field(default_factory=list)
    legislature: Legislature | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
