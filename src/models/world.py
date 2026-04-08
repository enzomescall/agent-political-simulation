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
        if place.parent_id and place.parent_id in self.places:
            parent = self.places[place.parent_id]
            if place.id not in parent.children_ids:
                parent.children_ids.append(place.id)

    def add_party(self, party: Party) -> None:
        self.parties[party.id] = party

    def add_interest_group(self, group: InterestGroup) -> None:
        self.interest_groups[group.id] = group

    def add_politician(self, agent: Agent) -> None:
        self.politicians[agent.id] = agent

    def add_government(self, government: Government) -> None:
        self.governments[government.place_id] = government

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def politicians_in_place(self, place_id: PlaceId) -> list[Agent]:
        return [p for p in self.politicians.values() if p.place_id == place_id]

    def party_members(self, party_id: PartyId) -> list[Agent]:
        return [p for p in self.politicians.values() if p.party_id == party_id]

    def children_of(self, place_id: PlaceId) -> list[Place]:
        place = self.places.get(place_id)
        if place is None:
            return []
        return [self.places[cid] for cid in place.children_ids if cid in self.places]

    def siblings_of(self, place_id: PlaceId) -> list[Place]:
        place = self.places.get(place_id)
        if place is None or place.parent_id is None:
            return []
        return [
            p
            for p in self.children_of(place.parent_id)
            if p.id != place_id
        ]

    def interest_group_pressure(
        self, group_id: InterestGroupId, place_id: PlaceId
    ) -> float:
        group = self.interest_groups.get(group_id)
        if group is None:
            return 0.0
        return group.pressure_on(place_id)
