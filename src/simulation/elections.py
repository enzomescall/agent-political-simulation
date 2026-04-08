from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.actions.base import ElectionResult
from src.models.types import OfficeType

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.government import Government
    from src.models.interest_group import InterestGroup
    from src.models.party import Party
    from src.models.place import Place
    from src.models.world import World

_log = logging.getLogger("simulation.elections")

# Maps executive office to corresponding legislative seat type.
_EXEC_TO_LEG: dict[OfficeType, OfficeType] = {
    OfficeType.MAYOR: OfficeType.COUNCILPERSON,
    OfficeType.GOVERNOR: OfficeType.STATE_ASSEMBLYPERSON,
    OfficeType.PRESIDENT: OfficeType.CONGRESSPERSON,
}


def check_elections(world: World) -> list[Government]:
    """Return governments that are due for an election this turn."""
    due: list[Government] = []
    for gov in world.governments.values():
        interval = gov.attributes.get("election_interval")
        if interval is None:
            continue
        last = gov.attributes.get("last_election_turn", 0)
        if world.turn > 0 and (world.turn - last) >= interval:
            due.append(gov)
    return due


def _ig_vote_score(ig: InterestGroup, candidate: Agent, place: Place) -> float:
    """How much an interest group favours a candidate.

    Combines:
      - candidate popularity with this IG
      - party base_constituency alignment
      - IG satisfaction (incumbent bonus/penalty)
    """
    popularity = candidate.popularity.get(ig, 0.0)
    party_affinity = candidate.party.base_constituency.get(ig, 0.0)
    satisfaction = ig.satisfaction.get(place, 0.5)

    # Incumbents benefit when satisfaction is high, suffer when low.
    incumbent_factor = 0.0
    if candidate.office is not None:
        incumbent_factor = (satisfaction - 0.5) * 0.4  # [-0.2, +0.2]

    score = popularity * 0.5 + party_affinity * 0.3 + incumbent_factor + 0.2 * satisfaction
    return max(0.0, score)


def run_executive_election(
    gov: Government,
    world: World,
    rng: _random.Random,
) -> ElectionResult:
    """Run an election for the executive seat of a government."""
    place = gov.place
    candidates = [a for a in world.politicians_in_place(place) if a.office is not None]
    # Also include ambitious out-of-office politicians.
    for a in world.politicians_in_place(place):
        if a.office is None and a.ambition > 0.5 and a not in candidates:
            candidates.append(a)

    if not candidates:
        return ElectionResult(place=place, election_type="executive",
                              events=["No candidates for executive election"])

    # Tally votes from interest groups.
    vote_totals: dict[Agent, float] = {c: 0.0 for c in candidates}
    for ig, presence in place.interest_group_presence.items():
        share = ig.electorate_share.get(place, presence)
        scores = {c: _ig_vote_score(ig, c, place) for c in candidates}
        total_score = sum(scores.values())
        if total_score <= 0:
            continue
        for c in candidates:
            vote_totals[c] += share * (scores[c] / total_score)

    # Add small random noise to break ties.
    for c in vote_totals:
        vote_totals[c] += rng.uniform(0.0, 0.01)

    ranked = sorted(vote_totals, key=lambda c: vote_totals[c], reverse=True)
    winner = ranked[0]
    losers = ranked[1:]

    total_votes = sum(vote_totals.values())
    vote_shares = {c.name: vote_totals[c] / total_votes for c in ranked} if total_votes > 0 else {}

    _log.info("  Executive election in %s:", place.name)
    for c in ranked:
        _log.info("    %s: %.1f%%", c.name, vote_shares.get(c.name, 0) * 100)

    events: list[str] = []

    # Update offices.
    old_holder = gov.executive.holder
    if old_holder is not None and old_holder is not winner:
        old_holder.office = None
        events.append(f"{old_holder.name} lost the {gov.executive.office_type.name} seat")

    gov.executive.holder = winner
    winner.office = gov.executive.office_type
    events.append(
        f"{winner.name} elected as {gov.executive.office_type.name} of {place.name} "
        f"({vote_shares.get(winner.name, 0):.1%})"
    )

    # Losers who had offices elsewhere keep them; those contesting lose nothing extra.
    for loser in losers:
        if loser.office == gov.executive.office_type:
            loser.office = None

    return ElectionResult(
        place=place,
        election_type="executive",
        winners=[winner],
        losers=losers,
        vote_shares=vote_shares,
        events=events,
    )


def run_legislative_election(
    gov: Government,
    world: World,
    rng: _random.Random,
) -> ElectionResult:
    """Run proportional legislative election."""
    assert gov.legislature is not None
    place = gov.place
    legislature = gov.legislature
    total_seats = legislature.total_seats

    # Executive holder should not be assigned a legislative seat.
    executive_holder = gov.executive.holder

    # Calculate party vote shares from IG support.
    parties_in_place: list[Party] = []
    seen_parties: set = set()
    for a in world.politicians_in_place(place):
        if a.party.id not in seen_parties:
            seen_parties.add(a.party.id)
            parties_in_place.append(a.party)

    party_votes: dict[Party, float] = {p: 0.0 for p in parties_in_place}
    for ig, presence in place.interest_group_presence.items():
        share = ig.electorate_share.get(place, presence)
        satisfaction = ig.satisfaction.get(place, 0.5)
        for party in parties_in_place:
            affinity = party.base_constituency.get(ig, 0.0)
            # Party members' average popularity with this IG.
            members_in_place = [a for a in world.politicians_in_place(place) if a.party is party]
            avg_pop = 0.0
            if members_in_place:
                avg_pop = sum(a.popularity.get(ig, 0.0) for a in members_in_place) / len(members_in_place)
            party_votes[party] += share * (affinity * 0.4 + avg_pop * 0.4 + satisfaction * 0.2)

    # Add small noise.
    for p in party_votes:
        party_votes[p] += rng.uniform(0.0, 0.01)

    total_pv = sum(party_votes.values())
    if total_pv <= 0:
        return ElectionResult(place=place, election_type="legislative",
                              events=["No votes cast in legislative election"])

    # Allocate seats proportionally (largest remainder method).
    party_share = {p: party_votes[p] / total_pv for p in parties_in_place}
    raw_seats = {p: party_share[p] * total_seats for p in parties_in_place}
    floor_seats = {p: int(raw_seats[p]) for p in parties_in_place}
    remainders = {p: raw_seats[p] - floor_seats[p] for p in parties_in_place}
    allocated = sum(floor_seats.values())
    # Distribute remaining seats by largest remainder.
    for p in sorted(remainders, key=lambda x: remainders[x], reverse=True):
        if allocated >= total_seats:
            break
        floor_seats[p] += 1
        allocated += 1

    _log.info("  Legislative election in %s:", place.name)
    for p in parties_in_place:
        _log.info("    %s: %.1f%% -> %d seats", p.name, party_share[p] * 100, floor_seats[p])

    # Assign seats: pick most popular members from each party.
    events: list[str] = []
    winners: list[Agent] = []
    losers: list[Agent] = []

    # Clear old legislature members' office.
    old_members = set(legislature.members)
    for m in old_members:
        if m.office == legislature.seat_type:
            m.office = None

    new_members: list[Agent] = []
    for party in parties_in_place:
        seats = floor_seats[party]
        if seats == 0:
            continue
        # Rank party members in this place by average popularity.
        candidates = sorted(
            [a for a in world.politicians_in_place(place)
             if a.party is party and a is not executive_holder],
            key=lambda a: sum(a.popularity.values()) / max(len(a.popularity), 1),
            reverse=True,
        )
        elected = candidates[:seats]
        for a in elected:
            a.office = legislature.seat_type
            new_members.append(a)
            winners.append(a)
        events.append(f"{party.name} won {seats} seat(s) in {place.name} legislature")

    # Agents who were in the old legislature but not the new one are losers.
    new_set = set(new_members)
    for m in old_members:
        if m not in new_set:
            losers.append(m)

    legislature.members = new_members

    vote_shares = {p.name: party_share[p] for p in parties_in_place}

    return ElectionResult(
        place=place,
        election_type="legislative",
        winners=winners,
        losers=losers,
        vote_shares=vote_shares,
        events=events,
    )
