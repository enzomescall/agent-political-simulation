from enum import Enum, auto
from typing import NewType


# Opaque ID types — all strings so they serialize easily and can use any
# generation strategy (UUID, slug, sequential) without changing the model.
PlaceId = NewType("PlaceId", str)
PartyId = NewType("PartyId", str)
AgentId = NewType("AgentId", str)
InterestGroupId = NewType("InterestGroupId", str)


class PlaceTier(Enum):
    FEDERAL = auto()
    STATE = auto()
    MUNICIPALITY = auto()


class OfficeType(Enum):
    # Executive
    PRESIDENT = auto()
    GOVERNOR = auto()
    MAYOR = auto()
    # Legislative
    CONGRESSPERSON = auto()
    STATE_ASSEMBLYPERSON = auto()
    COUNCILPERSON = auto()


class Archetype(Enum):
    LOYALIST = auto()
    POPULIST = auto()
    IDEOLOGUE = auto()


class DetailLevel(Enum):
    """Level-of-detail tiers for agent simulation fidelity."""
    L0 = 0  # Key figures — full simulation, potential LLM dialogue
    L1 = 1  # Player's state + national leadership — full weight-based decisions
    L2 = 2  # Neighbouring/relevant states — party-level behaviour, individual rolls
    L3 = 3  # Everyone else — pure aggregate statistics


class PartyRole(Enum):
    LEADER = auto()
    WHIP = auto()
    SPOKESPERSON = auto()
    MEMBER = auto()
