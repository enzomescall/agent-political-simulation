from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.place import Place
    from src.models.policy import Policy


class ActionType(Enum):
    # Base (all agents)
    VOTE = auto()
    TAKE_POSITION = auto()
    BUILD_RELATIONSHIP = auto()
    CAMPAIGN = auto()
    # Office-specific
    REQUEST_VOTE = auto()
    ALLOCATE_BUDGET = auto()
    VETO = auto()
    # Party-role-specific
    ISSUE_DIRECTIVE = auto()
    ENFORCE_DISCIPLINE = auto()
    EXPEL_MEMBER = auto()


@dataclass
class Action:
    """A concrete action taken by an agent in a turn."""

    action_type: ActionType
    actor: Agent
    policy: Policy | None = None
    target: Agent | None = None
    vote: bool | None = None  # True=yes, False=no, None=abstain
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoteResult:
    """Outcome of a legislative vote on a policy."""

    policy: Policy
    place: Place
    proposer: Agent | None = None
    yes_votes: list[Agent] = field(default_factory=list)
    no_votes: list[Agent] = field(default_factory=list)
    abstentions: list[Agent] = field(default_factory=list)
    passed: bool = False


@dataclass
class ElectionResult:
    """Outcome of an election."""

    place: Place
    election_type: str  # "executive" or "legislative"
    winners: list[Agent] = field(default_factory=list)
    losers: list[Agent] = field(default_factory=list)
    vote_shares: dict[str, float] = field(default_factory=dict)  # name -> share
    events: list[str] = field(default_factory=list)


@dataclass
class TurnReport:
    """Summary of everything that happened in a single turn."""

    turn: int
    actions_taken: list[Action] = field(default_factory=list)
    vote_results: list[VoteResult] = field(default_factory=list)
    election_results: list[ElectionResult] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
