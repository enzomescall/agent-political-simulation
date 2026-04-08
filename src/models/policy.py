from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .interest_group import InterestGroup


@dataclass(eq=False)
class Policy:
    """An ephemeral policy proposal with interest-group consequences.

    Policies are created during simulation, voted on, their consequences
    applied, and then kept only in turn reports — they do not accumulate
    in World.
    """

    name: str
    description: str = ""

    # group → impact magnitude [-1.0, 1.0]; positive = good for that group.
    interest_group_impacts: dict[InterestGroup, float] = field(
        default_factory=dict,
    )

    # Which ideology axes this aligns with and how strongly.
    ideology_alignment: dict[str, float] = field(default_factory=dict)

    attributes: dict[str, Any] = field(default_factory=dict)
