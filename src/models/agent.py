from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .ideology import Ideology
from .types import (
    AgentId,
    Archetype,
    DetailLevel,
    OfficeType,
    PartyRole,
)

if TYPE_CHECKING:
    from .interest_group import InterestGroup
    from .party import Party
    from .place import Place


@dataclass(eq=False)
class Agent:
    """The core simulated entity — an elected (or aspiring) official."""

    id: AgentId
    name: str
    ideology: Ideology
    party: Party
    place: Place

    # Current office held (None if out of office).
    office: OfficeType | None = None
    party_role: PartyRole = PartyRole.MEMBER

    # Weighted map to interest groups — who they identify with / who funds them.
    allegiances: dict[InterestGroup, float] = field(default_factory=dict)

    # Bilateral political-trust scores with other agents.
    relationships: dict[Agent, float] = field(default_factory=dict, repr=False)

    # Approval scores broken down by interest group.
    popularity: dict[InterestGroup, float] = field(default_factory=dict, repr=False)

    # How loyal vs. rebellious within their party (0.0 = rebel, 1.0 = loyal).
    party_standing: float = 0.5

    # Drives risk-taking behaviour (0.0 = cautious, 1.0 = reckless).
    ambition: float = 0.5

    archetype: Archetype = Archetype.LOYALIST
    detail_level: DetailLevel = DetailLevel.L3

    attributes: dict[str, Any] = field(default_factory=dict)
