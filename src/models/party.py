from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .ideology import Ideology
from .types import PartyId, PartyRole

if TYPE_CHECKING:
    from .agent import Agent
    from .interest_group import InterestGroup


@dataclass(eq=False)
class Party:
    """A political party with an ideological position and base constituency."""

    id: PartyId
    name: str
    ideology: Ideology = field(default_factory=Ideology)

    # Interest-group affinity: group → strength of connection [0, 1].
    base_constituency: dict[InterestGroup, float] = field(
        default_factory=dict,
    )

    # Internal roster: agent → role.
    members: dict[Agent, PartyRole] = field(default_factory=dict, repr=False)

    attributes: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Roster management
    # ------------------------------------------------------------------

    def add_member(self, agent: Agent, role: PartyRole = PartyRole.MEMBER) -> None:
        self.members[agent] = role

    def remove_member(self, agent: Agent) -> None:
        self.members.pop(agent, None)

    def set_role(self, agent: Agent, role: PartyRole) -> None:
        if agent in self.members:
            self.members[agent] = role

    def get_leader(self) -> Agent | None:
        for agent, role in self.members.items():
            if role is PartyRole.LEADER:
                return agent
        return None

    def get_by_role(self, role: PartyRole) -> list[Agent]:
        return [a for a, r in self.members.items() if r is role]
