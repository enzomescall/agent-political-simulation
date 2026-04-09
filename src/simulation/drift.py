"""
Ideological drift and interest-group radicalization.

Called once per turn (Phase 5) after all action consequences are applied.
"""
from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.models.types import DetailLevel

if TYPE_CHECKING:
    from src.models.world import World

_log = logging.getLogger("simulation.drift")

# Max drift per turn per axis (random component).
_RANDOM_DRIFT_SIGMA = 0.01
# How strongly the agent's top IG pulls ideology.
_IG_PULL_RATE = 0.02
# Soft party pull when agent diverges more than this distance.
_PARTY_PULL_THRESHOLD = 0.4
_PARTY_PULL_RATE = 0.015
# IG radicalization: satisfaction below this threshold triggers extremism.
_RAD_THRESHOLD = 0.25
_RAD_AXIS_SCALE = 1.05   # per-turn extremism multiplier
_RAD_SHARE_BOOST = 1.02  # per-turn mobilization multiplier


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def apply_ideological_drift(world: World, rng: _random.Random) -> list[str]:
    """Apply per-turn ideological drift to all L0/L1 agents.

    Three forces:
    1. Random Brownian noise (small, keeps things dynamic).
    2. Pull from the agent's highest-allegiance IG's ideology.
    3. Soft pull back toward party ideology when divergence is large.
    """
    events: list[str] = []
    for agent in world.politicians.values():
        if agent.detail_level.value > 1:
            continue

        old_axes = dict(agent.ideology.axes)

        for axis in list(agent.ideology.axes.keys()):
            delta = 0.0

            # 1. Random noise
            delta += rng.gauss(0, _RANDOM_DRIFT_SIGMA)

            # 2. IG pull — highest-allegiance IG
            if agent.allegiances:
                top_ig = max(agent.allegiances, key=lambda ig: agent.allegiances[ig])
                ig_pos = top_ig.ideology[axis]
                delta += (ig_pos - agent.ideology[axis]) * _IG_PULL_RATE

            # 3. Party pull (soft correction when too far from party)
            party_pos = agent.party.ideology[axis]
            dist = abs(agent.ideology[axis] - party_pos)
            if dist > _PARTY_PULL_THRESHOLD:
                delta += (party_pos - agent.ideology[axis]) * _PARTY_PULL_RATE

            agent.ideology.axes[axis] = _clamp(agent.ideology.axes[axis] + delta)

        # Log only if meaningful drift occurred
        total_drift = sum(
            abs(agent.ideology.axes[ax] - old_axes[ax])
            for ax in old_axes
        )
        if total_drift > 0.03:
            _log.debug(
                "  %s ideology drifted: econ %.3f→%.3f soc %.3f→%.3f",
                agent.name,
                old_axes.get("economic", 0), agent.ideology["economic"],
                old_axes.get("social", 0), agent.ideology["social"],
            )
            events.append(
                f"{agent.name} ideology shifted "
                f"(econ {old_axes.get('economic', 0):+.2f}→{agent.ideology['economic']:+.2f})"
            )

    return events


def apply_ig_radicalization(world: World) -> list[str]:
    """Radicalize marginalized IGs: low satisfaction → more extreme ideology
    and higher electorate mobilization.
    """
    events: list[str] = []
    all_places = list(world.places.values())

    for ig in world.interest_groups.values():
        if not ig.satisfaction:
            continue

        sat_values = [ig.satisfaction[p] for p in all_places if p in ig.satisfaction]
        if not sat_values:
            continue
        avg_sat = sum(sat_values) / len(sat_values)

        if avg_sat < _RAD_THRESHOLD:
            # Extremize ideology — push axes further from center
            old_axes = dict(ig.ideology.axes)
            for axis in list(ig.ideology.axes.keys()):
                val = ig.ideology.axes[axis]
                # Push away from zero (radicalize in current direction)
                sign = 1.0 if val >= 0 else -1.0
                ig.ideology.axes[axis] = _clamp(val * _RAD_AXIS_SCALE + sign * 0.005)

            # Boost electorate share (mobilization)
            for place in all_places:
                if place in ig.electorate_share:
                    ig.electorate_share[place] = min(
                        1.0, ig.electorate_share[place] * _RAD_SHARE_BOOST
                    )

            old_econ = old_axes.get("economic", 0)
            new_econ = ig.ideology["economic"]
            if abs(new_econ - old_econ) > 0.005:
                _log.info(
                    "  IG '%s' radicalizing (avg_sat=%.3f): econ %.3f→%.3f",
                    ig.name, avg_sat, old_econ, new_econ,
                )
                events.append(
                    f"{ig.name} is radicalizing (satisfaction={avg_sat:.2f})"
                )

    return events
