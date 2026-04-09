from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import Agent
from .government import Government
from .interest_group import InterestGroup
from .party import Party
from .place import Place
from .types import (
    AgentId,
    InterestGroupId,
    PartyId,
    PlaceId,
)


@dataclass
class World:
    """Top-level container for the entire simulation state."""

    places: dict[PlaceId, Place] = field(default_factory=dict)
    parties: dict[PartyId, Party] = field(default_factory=dict)
    interest_groups: dict[InterestGroupId, InterestGroup] = field(
        default_factory=dict,
    )
    politicians: dict[AgentId, Agent] = field(default_factory=dict)
    governments: dict[PlaceId, Government] = field(default_factory=dict)

    turn: int = 0
    player_id: AgentId | None = None

    attributes: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def add_place(self, place: Place) -> None:
        self.places[place.id] = place
        if place.parent is not None:
            if place not in place.parent.children:
                place.parent.children.append(place)

    def add_party(self, party: Party) -> None:
        self.parties[party.id] = party

    def add_interest_group(self, group: InterestGroup) -> None:
        self.interest_groups[group.id] = group

    def add_politician(self, agent: Agent) -> None:
        self.politicians[agent.id] = agent
        agent.party.add_member(agent, agent.party_role)

    def add_government(self, government: Government) -> None:
        self.governments[government.place.id] = government

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def politicians_in_place(self, place: Place) -> list[Agent]:
        return [p for p in self.politicians.values() if p.place is place]

    def party_members(self, party: Party) -> list[Agent]:
        return [p for p in self.politicians.values() if p.party is party]

    def remove_politician(self, agent: Agent) -> None:
        self.politicians.pop(agent.id, None)
        agent.party.members.pop(agent, None)
        agent.office = None

    def siblings_of(self, place: Place) -> list[Place]:
        if place.parent is None:
            return []
        return [p for p in place.parent.children if p is not place]
