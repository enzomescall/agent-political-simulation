from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.types import OfficeType, PartyRole

from .base import ActionType

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.world import World

# Maps office types to the extra actions they unlock.
_OFFICE_ACTIONS: dict[OfficeType, set[ActionType]] = {
    OfficeType.MAYOR: {ActionType.PROPOSE_POLICY, ActionType.ALLOCATE_BUDGET, ActionType.VETO},
    OfficeType.GOVERNOR: {ActionType.PROPOSE_POLICY, ActionType.ALLOCATE_BUDGET, ActionType.VETO},
    OfficeType.PRESIDENT: {ActionType.PROPOSE_POLICY, ActionType.ALLOCATE_BUDGET, ActionType.VETO},
    OfficeType.COUNCILPERSON: {ActionType.PROPOSE_POLICY},
    OfficeType.STATE_ASSEMBLYPERSON: {ActionType.PROPOSE_POLICY},
    OfficeType.CONGRESSPERSON: {ActionType.PROPOSE_POLICY},
}

# Maps party roles to the extra actions they unlock.
_ROLE_ACTIONS: dict[PartyRole, set[ActionType]] = {
    PartyRole.LEADER: {ActionType.ISSUE_DIRECTIVE, ActionType.ENFORCE_DISCIPLINE, ActionType.EXPEL_MEMBER},
    PartyRole.WHIP: {ActionType.ENFORCE_DISCIPLINE},
}

# Base actions available to every agent.
_BASE_ACTIONS: set[ActionType] = {
    ActionType.VOTE,
    ActionType.TAKE_POSITION,
    ActionType.BUILD_RELATIONSHIP,
    ActionType.CAMPAIGN,
}


def available_actions(agent: Agent, world: World) -> list[ActionType]:
    """Return the action types this agent can perform."""
    actions = set(_BASE_ACTIONS)
    if agent.office is not None:
        actions |= _OFFICE_ACTIONS.get(agent.office, set())
    actions |= _ROLE_ACTIONS.get(agent.party_role, set())
    return sorted(actions, key=lambda a: a.value)
