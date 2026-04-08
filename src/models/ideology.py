from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Ideology:
    """A position in an n-dimensional ideological space.

    The default axes are *economic* (left/right) and *social*
    (progressive/conservative), but arbitrary axes can be added to
    capture additional dimensions (e.g. federalism, environmentalism).
    Values are conventionally in [-1.0, 1.0].
    """

    axes: dict[str, float] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        economic: float = 0.0,
        social: float = 0.0,
        **extra: float,
    ) -> Ideology:
        return cls(axes={"economic": economic, "social": social, **extra})

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def __getitem__(self, axis: str) -> float:
        return self.axes.get(axis, 0.0)

    def __iter__(self) -> Iterator[str]:
        return iter(self.axes)

    def distance(self, other: Ideology) -> float:
        """Euclidean distance across all axes present in either ideology."""
        all_axes = set(self.axes) | set(other.axes)
        return math.sqrt(
            sum((self[a] - other[a]) ** 2 for a in all_axes)
        )

    def alignment(self, other: Ideology) -> float:
        """A normalised similarity score in [0, 1].

        1.0 means identical positions; 0.0 means maximally opposed
        (assuming the conventional [-1, 1] range on each axis).
        """
        max_dist = math.sqrt(4.0 * max(len(self.axes), len(other.axes), 1))
        return 1.0 - min(self.distance(other) / max_dist, 1.0)
