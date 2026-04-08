from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4


# ----------------------------
# Core enums
# ----------------------------

class GovernmentLevel(Enum):
    FEDERAL = "federal"
    STATE = "state"
    MUNICIPAL = "municipal"


class BranchType(Enum):
    EXECUTIVE = "executive"
    LEGISLATIVE = "legislative"


class ChamberType(Enum):
    LOWER = "lower"
    UPPER = "upper"
    UNICAMERAL = "unicameral"


class OfficeType(Enum):
    PRESIDENT = "president"
    FEDERAL_DEPUTY = "federal_deputy"
    SENATOR = "senator"
    GOVERNOR = "governor"
    STATE_DEPUTY = "state_deputy"
    MAYOR = "mayor"
    COUNCILOR = "councilor"  # vereador
    CABINET_MINISTER = "cabinet_minister"
    INTEREST_GROUP_OPERATOR = "interest_group_operator"


class InterestGroupType(Enum):
    RURAL_WORKERS = "rural_workers"
    URBAN_WORKERS = "urban_workers"
    WEALTHY_ELITES = "wealthy_elites"


class Archetype(Enum):
    LOYALIST = "loyalist"
    POPULIST = "populist"
    IDEOLOGUE = "ideologue"


class LODTier(Enum):
    L0 = "L0"  # direct interaction
    L1 = "L1"  # player's state + national leadership
    L2 = "L2"  # neighboring/relevant states
    L3 = "L3"  # aggregate only


class VoteDecision(Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    ABSTAIN = "abstain"


# ----------------------------
# Basic value objects
# ----------------------------

@dataclass(slots=True)
class Ideology2D:
    """
    Range suggestion:
    economic: -1.0 (left) to +1.0 (right)
    social:   -1.0 (progressive) to +1.0 (conservative)
    """
    economic: float
    social: float


@dataclass(slots=True)
class PolicyPreference:
    policy_key: str
    preferred_direction: float  # e.g. -1.0 to +1.0
    salience: float             # importance to the group


@dataclass(slots=True)
class PartyDisciplineRule:
    rebellion_tolerance: float  # how much dissent is tolerated
    expulsion_threshold: float  # standing below this risks expulsion
    leadership_threshold: float # standing above this opens leadership paths


@dataclass(slots=True)
class DecisionWeights:
    ideology_alignment: float
    party_directive: float
    interest_group_pressure: float
    electoral_calculus: float
    relationship_cost: float


@dataclass(slots=True)
class ElectorateProfile:
    """
    Share of electorate in a given place by interest group.
    Total does not have to strictly sum to 1.0, but ideally should.
    """
    group_shares: Dict[InterestGroupType, float] = field(default_factory=dict)


@dataclass(slots=True)
class SatisfactionProfile:
    """
    Local satisfaction of each interest group in a place.
    Suggested range: -1.0 to +1.0
    """
    by_group: Dict[InterestGroupType, float] = field(default_factory=dict)


# ----------------------------
# Parties
# ----------------------------

@dataclass(slots=True)
class Party:
    id: str
    name: str
    short_name: str
    ideology: Ideology2D

    # Dynamic constituency: strength with each interest group
    base_constituency: Dict[InterestGroupType, float] = field(default_factory=dict)

    # Internal party culture / discipline
    discipline_rule: PartyDisciplineRule = field(
        default_factory=lambda: PartyDisciplineRule(
            rebellion_tolerance=0.25,
            expulsion_threshold=-0.75,
            leadership_threshold=0.75,
        )
    )

    # Current members by politician id
    member_ids: Set[str] = field(default_factory=set)


# ----------------------------
# Offices and government structure
# ----------------------------

@dataclass(slots=True)
class Office:
    id: str
    title: str
    office_type: OfficeType
    level: GovernmentLevel
    branch: BranchType
    place_id: str
    chamber_type: Optional[ChamberType] = None

    # Holder is optional because the office may be vacant during transitions
    holder_id: Optional[str] = None


@dataclass(slots=True)
class CabinetPosition:
    id: str
    title: str
    office_id: str
    holder_id: Optional[str] = None


@dataclass(slots=True)
class LegislativeBody:
    id: str
    name: str
    level: GovernmentLevel
    place_id: str
    chamber_type: ChamberType
    seat_count: int
    office_ids: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutiveBody:
    id: str
    name: str
    level: GovernmentLevel
    place_id: str
    head_office_id: str
    cabinet_positions: List[CabinetPosition] = field(default_factory=list)


# ----------------------------
# Places
# ----------------------------

@dataclass(slots=True)
class Place:
    id: str
    name: str
    level: GovernmentLevel

    parent_id: Optional[str] = None
    state_id: Optional[str] = None  # helpful shortcut for municipalities

    executive_body_id: Optional[str] = None
    legislative_body_ids: List[str] = field(default_factory=list)

    electorate: ElectorateProfile = field(default_factory=ElectorateProfile)
    group_satisfaction: SatisfactionProfile = field(default_factory=SatisfactionProfile)

    # Political relevance / simulation fidelity
    lod_tier: LODTier = LODTier.L3


# ----------------------------
# Interest groups
# ----------------------------

@dataclass(slots=True)
class InterestGroup:
    id: str
    group_type: InterestGroupType
    name: str

    policy_preferences: List[PolicyPreference] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)

    # Optional leader/operator actor ids
    operator_ids: Set[str] = field(default_factory=set)

    def pressure_strength(self, place: Place) -> float:
        """
        Basic derived measure: pressure rises when the group is large locally
        and dissatisfied locally.
        """
        share = place.electorate.group_shares.get(self.group_type, 0.0)
        satisfaction = place.group_satisfaction.by_group.get(self.group_type, 0.0)

        dissatisfaction = max(0.0, -satisfaction)
        return share * dissatisfaction


# ----------------------------
# Politicians / agents
# ----------------------------

@dataclass(slots=True)
class Politician:
    id: str
    name: str
    party_id: Optional[str]

    ideology: Ideology2D
    archetype: Archetype

    # Who they identify with / who funds them
    allegiances: Dict[InterestGroupType, float] = field(default_factory=dict)

    # Political trust / realpolitik alignment
    relationships: Dict[str, float] = field(default_factory=dict)  # other politician_id -> trust score

    # Approval by interest group
    popularity: Dict[InterestGroupType, float] = field(default_factory=dict)

    # Party standing: negative = rebellious / endangered, positive = favored
    party_standing: float = 0.0

    # Ambition and temperature drive behavior
    ambition: float = 0.5      # appetite for advancement
    temperature: float = 0.5   # risk-taking / impulsiveness

    # Current office holdings
    office_ids: List[str] = field(default_factory=list)

    lod_tier: LODTier = LODTier.L3

    # Used for external pressure actors / operators
    is_interest_group_adjacent: bool = False

    def get_decision_weights(self) -> DecisionWeights:
        """
        Archetype-specific weighting for political decisions.
        These are defaults; you can tune them later.
        """
        if self.archetype == Archetype.LOYALIST:
            return DecisionWeights(
                ideology_alignment=0.20,
                party_directive=0.35,
                interest_group_pressure=0.15,
                electoral_calculus=0.15,
                relationship_cost=0.15,
            )
        if self.archetype == Archetype.POPULIST:
            return DecisionWeights(
                ideology_alignment=0.10,
                party_directive=0.15,
                interest_group_pressure=0.25,
                electoral_calculus=0.35,
                relationship_cost=0.15,
            )
        if self.archetype == Archetype.IDEOLOGUE:
            return DecisionWeights(
                ideology_alignment=0.45,
                party_directive=0.15,
                interest_group_pressure=0.10,
                electoral_calculus=0.10,
                relationship_cost=0.20,
            )

        return DecisionWeights(0.2, 0.2, 0.2, 0.2, 0.2)


# ----------------------------
# Decision / consequence systems
# ----------------------------

@dataclass(slots=True)
class Bill:
    id: str
    title: str
    place_id: str
    sponsor_id: str

    economic_direction: float  # -1 left, +1 right
    social_direction: float    # -1 progressive, +1 conservative

    affected_groups: Dict[InterestGroupType, float] = field(default_factory=dict)
    party_positions: Dict[str, VoteDecision] = field(default_factory=dict)  # party_id -> directive


@dataclass(slots=True)
class VoteRecord:
    bill_id: str
    politician_id: str
    decision: VoteDecision

    ideology_score: float
    party_score: float
    group_pressure_score: float
    electoral_score: float
    relationship_score: float

    final_score: float


@dataclass(slots=True)
class Coalition:
    id: str
    name: str
    leader_id: str
    member_party_ids: Set[str] = field(default_factory=set)
    member_politician_ids: Set[str] = field(default_factory=set)

    # If support falls below this threshold, coalition crisis/collapse can trigger
    legislative_support_threshold: float = 0.5

    def contains_politician(self, politician_id: str) -> bool:
        return politician_id in self.member_politician_ids


@dataclass(slots=True)
class RelationshipChange:
    source_id: str
    target_id: str
    delta: float
    reason: str


@dataclass(slots=True)
class PopularityShift:
    politician_id: str
    place_id: str
    by_group_delta: Dict[InterestGroupType, float] = field(default_factory=dict)
    reason: str = ""


@dataclass(slots=True)
class PartyStandingShift:
    politician_id: str
    party_id: str
    delta: float
    reason: str


@dataclass(slots=True)
class ElectionResult:
    office_id: str
    place_id: str
    winner_id: str
    vote_share_by_candidate: Dict[str, float] = field(default_factory=dict)
    endorsements: Dict[str, List[str]] = field(default_factory=dict)  # candidate_id -> coalition/party ids


# ----------------------------
# World / simulation container
# ----------------------------

@dataclass(slots=True)
class WorldState:
    turn: int = 0

    places: Dict[str, Place] = field(default_factory=dict)
    parties: Dict[str, Party] = field(default_factory=dict)
    politicians: Dict[str, Politician] = field(default_factory=dict)
    offices: Dict[str, Office] = field(default_factory=dict)
    executive_bodies: Dict[str, ExecutiveBody] = field(default_factory=dict)
    legislative_bodies: Dict[str, LegislativeBody] = field(default_factory=dict)
    interest_groups: Dict[str, InterestGroup] = field(default_factory=dict)
    coalitions: Dict[str, Coalition] = field(default_factory=dict)
    bills: Dict[str, Bill] = field(default_factory=dict)

    player_politician_id: Optional[str] = None

    def get_politician(self, politician_id: str) -> Politician:
        return self.politicians[politician_id]

    def get_party(self, party_id: str) -> Party:
        return self.parties[party_id]

    def get_place(self, place_id: str) -> Place:
        return self.places[place_id]

    def get_office(self, office_id: str) -> Office:
        return self.offices[office_id]


# ----------------------------
# Utility helpers
# ----------------------------

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


# ----------------------------
# Example bootstrap helpers
# ----------------------------

def make_party(name: str, short_name: str, economic: float, social: float) -> Party:
    return Party(
        id=new_id("party"),
        name=name,
        short_name=short_name,
        ideology=Ideology2D(economic=economic, social=social),
    )


def make_politician(
    name: str,
    party_id: Optional[str],
    economic: float,
    social: float,
    archetype: Archetype,
) -> Politician:
    return Politician(
        id=new_id("pol"),
        name=name,
        party_id=party_id,
        ideology=Ideology2D(economic=economic, social=social),
        archetype=archetype,
    )