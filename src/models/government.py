from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .types import OfficeType

if TYPE_CHECKING:
    from .agent import Agent
    from .place import Place


@dataclass
class Office:
    """A single government position (executive or cabinet)."""

    office_type: OfficeType
    place: Place
    holder: Agent | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Legislature:
    """A legislative body tied to a place."""

    place: Place
    seat_type: OfficeType  # e.g. COUNCILPERSON
    total_seats: int = 0
    members: list[Agent] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Government:
    """The full government structure for a single place."""

    place: Place
    executive: Office
    cabinet: list[Office] = field(default_factory=list)
    legislature: Legislature | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
