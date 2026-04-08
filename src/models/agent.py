from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ideology import Ideology
from .types import (
    AgentId,
    Archetype,
    DetailLevel,
    InterestGroupId,
    OfficeType,
    PartyId,
    PlaceId,
)


@dataclass
class Agent:
    """The core simulated entity — an elected (or aspiring) official."""

    id: AgentId
    name: str
    ideology: Ideology
    party_id: PartyId
    place_id: PlaceId

    # Current office held (None if out of office).
    office: OfficeType | None = None

    # Weighted map to interest groups — who they identify with / who funds them.
    allegiances: dict[InterestGroupId, float] = field(default_factory=dict)

    # Bilateral political-trust scores with other politicians.
    relationships: dict[AgentId, float] = field(default_factory=dict)

    # Approval scores broken down by interest group.
    popularity: dict[InterestGroupId, float] = field(default_factory=dict)

    # How loyal vs. rebellious within their party (0.0 = rebel, 1.0 = loyal).
    party_standing: float = 0.5

    # Drives risk-taking behaviour (0.0 = cautious, 1.0 = reckless).
    ambition: float = 0.5

    archetype: Archetype = Archetype.LOYALIST
    detail_level: DetailLevel = DetailLevel.L3

    attributes: dict[str, Any] = field(default_factory=dict)
