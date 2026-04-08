from dataclasses import dataclass, field
from enum import Enum, auto


class PlaceLevel(Enum):
    FEDERAL = auto()
    STATE = auto()
    MUNICIPALITY = auto()


class OfficeType(Enum):
    PRESIDENT = auto()
    SENATOR = auto()
    DEPUTY = auto()
    GOVERNOR = auto()
    STATE_ASSEMBLY = auto()
    MAYOR = auto()
    VEREADOR = auto()


class Archetype(Enum):
    LOYALIST = auto()
    POPULIST = auto()
    IDEOLOGUE = auto()


class LODTier(Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3


@dataclass
class InterestGroup:
    id: str
    name: str
    preferences: dict[str, float]  # policy_tag -> desire (-1..1)


@dataclass
class GroupLocalState:
    """Per-place state for an interest group."""
    satisfaction: float          # 0..100
    electorate_share: float      # 0..1
    strength: float              # 0..1, drives pressure intensity


@dataclass
class Party:
    id: str
    name: str
    economic: float              # -1 left .. +1 right
    social: float                # -1 progressive .. +1 conservative
    line: dict[str, float] = field(default_factory=dict)  # bill_id -> directive
    treasury: float = 0.0


@dataclass
class Ideology:
    economic: float              # -1..1
    social: float                # -1..1


@dataclass
class Politician:
    id: str
    name: str
    party_id: str
    place_id: str
    office: OfficeType
    ideology: Ideology
    archetype: Archetype
    allegiances: dict[str, float]              # group_id -> weight (sum=1)
    relationships: dict[str, float] = field(default_factory=dict)  # pol_id -> -1..1
    approval_by_group: dict[str, float] = field(default_factory=dict)  # group_id -> 0..100
    party_standing: float = 0.0                # -1 rebel .. +1 loyalist
    ambition: float = 0.5                      # 0..1
    seniority: int = 0
    lod: LODTier = LODTier.L3

    def decision_weights(self) -> tuple[float, float, float, float, float]:
        """w_ideology, w_party, w_groups, w_electoral, w_relationships."""
        match self.archetype:
            case Archetype.LOYALIST:  return (0.15, 0.45, 0.15, 0.15, 0.10)
            case Archetype.POPULIST:  return (0.10, 0.15, 0.30, 0.35, 0.10)
            case Archetype.IDEOLOGUE: return (0.50, 0.15, 0.15, 0.10, 0.10)


@dataclass
class Legislature:
    seats: int
    members: list[str] = field(default_factory=list)  # politician ids


@dataclass
class Executive:
    head: str | None = None                            # politician id
    cabinet: list[str] = field(default_factory=list)


@dataclass
class Place:
    id: str
    name: str
    level: PlaceLevel
    parent_id: str | None
    executive: Executive
    legislature: Legislature
    group_state: dict[str, GroupLocalState] = field(default_factory=dict)


@dataclass
class Bill:
    id: str
    title: str
    place_id: str
    policy_tags: dict[str, float]                      # tag -> magnitude (-1..1)
    sponsor_id: str


@dataclass
class Vote:
    bill_id: str
    politician_id: str
    value: int                                          # -1, 0, +1


@dataclass
class Coalition:
    id: str
    place_id: str
    member_party_ids: set[str]
    leader_politician_id: str
    cohesion: float = 0.5                              # 0..1


@dataclass
class Election:
    id: str
    place_id: str
    office: OfficeType
    turn: int
    candidates: list[str] = field(default_factory=list)
    results: dict[str, float] = field(default_factory=dict)  # politician_id -> vote share


@dataclass
class World:
    turn: int = 0
    player_id: str = ""
    places: dict[str, Place] = field(default_factory=dict)
    parties: dict[str, Party] = field(default_factory=dict)
    politicians: dict[str, Politician] = field(default_factory=dict)
    interest_groups: dict[str, InterestGroup] = field(default_factory=dict)
    coalitions: dict[str, Coalition] = field(default_factory=dict)
    bills: dict[str, Bill] = field(default_factory=dict)
    elections: dict[str, Election] = field(default_factory=dict)