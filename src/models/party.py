from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ideology import Ideology
from .types import InterestGroupId, PartyId


@dataclass
class Party:
    """A political party with an ideological position and base constituency."""

    id: PartyId
    name: str
    ideology: Ideology = field(default_factory=Ideology)

    # Interest-group affinity: group_id → strength of connection [0, 1].
    base_constituency: dict[InterestGroupId, float] = field(
        default_factory=dict,
    )

    attributes: dict[str, Any] = field(default_factory=dict)
