from __future__ import annotations

import logging
import random as _random
from typing import TYPE_CHECKING

from src.actions.base import ElectionResult
from src.models.ideology import Ideology
from src.models.types import AgentId, Archetype, DetailLevel, OfficeType, PartyRole
from src.log_utils import fmt

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.government import Government
    from src.models.interest_group import InterestGroup
    from src.models.party import Party
    from src.models.place import Place
    from src.models.world import World

_log = logging.getLogger("simulation.elections")

_EXEC_TO_LEG: dict[OfficeType, OfficeType] = {
    OfficeType.MAYOR: OfficeType.COUNCILPERSON,
    OfficeType.GOVERNOR: OfficeType.STATE_ASSEMBLYPERSON,
    OfficeType.PRESIDENT: OfficeType.CONGRESSPERSON,
}

# Default term limits.
_EXEC_TERM_LIMIT = 2
_LEG_TERM_LIMIT = 4
_L2_CLEANUP_THRESHOLD = 10  # turns at L2 before removal
_SUPPORT_DILUTION_FACTOR = 0.25
_VIABILITY_RATIO = 0.6


# ---------------------------------------------------------------------------
# Scheduling checks
# ---------------------------------------------------------------------------

def check_elections(world: World) -> list[Government]:
    """Return governments due for an election this turn."""
    due: list[Government] = []
    for gov in world.governments.values():
        interval = gov.attributes.get("election_interval")
        if interval is None:
            continue
        last = gov.attributes.get("last_election_turn", 0)
        if world.turn > 0 and (world.turn - last) >= interval:
            due.append(gov)
    return due


def check_party_elections(world: World) -> list[Party]:
    """Return parties that need a leadership election this turn."""
    due: list[Party] = []
    for party in world.parties.values():
        if not party.members:
            continue
        # No leader → immediate election.
        if party.get_leader() is None:
            due.append(party)
            continue
        interval = party.leadership_interval
        last = party.last_leadership_turn
        if world.turn > 0 and (world.turn - last) >= interval:
            due.append(party)
    return due


# ---------------------------------------------------------------------------
# Agent cleanup (LOD downgrade + pruning)
# ---------------------------------------------------------------------------

def cleanup_agents(world: World) -> list[str]:
    """Increment L2 counters and remove stale agents. Returns event strings."""
    events: list[str] = []
    to_remove: list[Agent] = []
    for agent in world.politicians.values():
        if agent.detail_level is DetailLevel.L2:
            count = agent.attributes.get("turns_at_l2", 0) + 1
            agent.attributes["turns_at_l2"] = count
            if count >= _L2_CLEANUP_THRESHOLD:
                to_remove.append(agent)
    for agent in to_remove:
        world.remove_politician(agent)
        events.append(f"{fmt(agent)} removed from simulation (L2 for {_L2_CLEANUP_THRESHOLD} turns)")
        _log.info("  Removed %s from simulation (stale L2)", fmt(agent))
    return events


# ---------------------------------------------------------------------------
# Nomination helpers
# ---------------------------------------------------------------------------

def _nomination_score(candidate: Agent, party: Party) -> float:
    """Score a candidate for party nomination: popularity + standing + leader relation."""
    avg_pop = sum(candidate.popularity.values()) / max(len(candidate.popularity), 1)
    leader = party.get_leader()
    leader_rel = candidate.relationships.get(leader, 0.0) if leader else 0.0
    return 0.4 * avg_pop + 0.4 * candidate.party_standing + 0.2 * leader_rel


def _is_term_limited_exec(agent: Agent) -> bool:
    limit = agent.attributes.get("term_limit_exec", _EXEC_TERM_LIMIT)
    return agent.attributes.get("consecutive_terms_exec", 0) >= limit


def _is_term_limited_leg(agent: Agent) -> bool:
    limit = agent.attributes.get("term_limit_leg", _LEG_TERM_LIMIT)
    return agent.attributes.get("consecutive_terms_leg", 0) >= limit


def nominate_executive_candidates(gov: Government, world: World) -> dict[Party, Agent | None]:
    """Each party nominates one executive candidate, or None if declining."""
    place = gov.place
    parties_present: set[Party] = {a.party for a in world.politicians_in_place(place)}
    nominations: dict[Party, Agent | None] = {}

    for party in parties_present:
        budget = party.campaign_budget
        if budget <= 0:
            nominations[party] = None
            _log.debug("  %s declined to run (no campaign budget)", party.name)
            continue

        threshold = party.nomination_threshold
        eligible = [
            a for a in world.politicians_in_place(place)
            if a.party is party and not _is_term_limited_exec(a)
        ]
        if not eligible:
            nominations[party] = None
            continue

        scored = sorted(eligible, key=lambda a: _nomination_score(a, party), reverse=True)
        best = scored[0]
        if _nomination_score(best, party) >= threshold:
            nominations[party] = best
            party.campaign_budget = budget - 1
            _log.debug("  %s nominates %s for executive", party.name, fmt(best))
        else:
            nominations[party] = None

    return nominations


def _generate_agent(party: Party, place: Place, world: World, rng: _random.Random) -> Agent:
    """Generate a placeholder agent for legislative seat filling."""
    from src.models.agent import Agent

    agent_id = AgentId(f"gen_{rng.randint(10000, 99999)}")
    # Ideology close to party's but with noise.
    axes = {
        ax: max(-1.0, min(1.0, val + rng.uniform(-0.3, 0.3)))
        for ax, val in party.ideology.axes.items()
    }
    agent = Agent(
        id=agent_id,
        name=f"{party.name} Candidate {agent_id[-5:]}",
        ideology=Ideology(axes=axes),
        party=party,
        place=place,
        office=None,
        party_standing=rng.uniform(0.4, 0.7),
        ambition=rng.uniform(0.3, 0.7),
        archetype=rng.choice(list(Archetype)),
        detail_level=DetailLevel.L2,
    )
    # Seed minimal popularity.
    for ig in place.interest_group_presence:
        affinity = party.base_constituency.get(ig, 0.0)
        agent.popularity[ig] = max(0.0, min(1.0, affinity * 0.5 + rng.uniform(-0.1, 0.1)))
    world.add_politician(agent)
    _log.debug("  Generated placeholder agent %s for %s", fmt(agent), party.name)
    return agent


def nominate_legislative_candidates(
    gov: Government, world: World, rng: _random.Random
) -> dict[Party, list[Agent]]:
    """Each party nominates up to total_seats candidates; generates new agents if needed."""
    assert gov.legislature is not None
    place = gov.place
    total_seats = gov.legislature.total_seats
    parties_present: set[Party] = {a.party for a in world.politicians_in_place(place)}
    nominations: dict[Party, list[Agent]] = {}

    for party in parties_present:
        eligible = sorted(
            [a for a in world.politicians_in_place(place)
             if a.party is party and not _is_term_limited_leg(a)
             and a is not gov.executive.holder],
            key=lambda a: _nomination_score(a, party),
            reverse=True,
        )
        # Fill up to total_seats with existing agents.
        nominated = list(eligible[:total_seats])
        # Generate new agents for any gap.
        while len(nominated) < total_seats:
            new_agent = _generate_agent(party, place, world, rng)
            nominated.append(new_agent)
        nominations[party] = nominated

    return nominations


# ---------------------------------------------------------------------------
# IG vote scoring
# ---------------------------------------------------------------------------

def _ig_vote_score(ig: InterestGroup, candidate: Agent, place: Place) -> float:
    """How much an interest group favours a candidate."""
    popularity = candidate.popularity.get(ig, 0.0)
    party_affinity = candidate.party.base_constituency.get(ig, 0.0)
    satisfaction = ig.satisfaction.get(place, 0.5)
    incumbent_factor = 0.0
    if candidate.office is not None:
        incumbent_factor = (satisfaction - 0.5) * 0.4
    return max(0.0, popularity * 0.5 + party_affinity * 0.3 + incumbent_factor + 0.2 * satisfaction)


def _diluted_turnout_share(raw_scores: dict[object, float], share: float) -> float:
    """Reduce usable IG turnout when support fragments across viable options."""
    positive_scores = [score for score in raw_scores.values() if score > 0.0]
    if not positive_scores:
        return 0.0

    max_score = max(positive_scores)
    viability_cutoff = max_score * _VIABILITY_RATIO
    viable_count = sum(1 for score in positive_scores if score >= viability_cutoff)
    dilution = 1.0 / (1.0 + _SUPPORT_DILUTION_FACTOR * max(0, viable_count - 1))
    return share * dilution


def _whip_score(candidate: Agent, leader: Agent) -> float:
    """Score a member for whip assignment."""
    office_bonus = 0.2 if candidate.office is not None else 0.0
    max_dist = len(leader.ideology.axes) ** 0.5
    dist = leader.ideology.distance(candidate.ideology)
    ideology_align = max(0.0, 1.0 - dist / max(max_dist, 1.0))
    return (
        0.35 * leader.relationships.get(candidate, 0.0)
        + 0.30 * candidate.party_standing
        + 0.20 * office_bonus
        + 0.15 * ideology_align
    )


# ---------------------------------------------------------------------------
# Executive election
# ---------------------------------------------------------------------------

def run_executive_election(gov: Government, world: World, rng: _random.Random) -> ElectionResult:
    """Run a party-nominated executive election with term limits."""
    place = gov.place
    nominations = nominate_executive_candidates(gov, world)

    candidates: list[Agent] = [a for a in nominations.values() if a is not None]
    if not candidates:
        return ElectionResult(place=place, election_type="executive",
                              events=["No candidates for executive election"])

    # Tally IG votes — split same-party IG support across candidates.
    party_of: dict[Agent, Party] = {a: a.party for a in candidates}
    vote_totals: dict[Agent, float] = {c: 0.0 for c in candidates}

    for ig, presence in place.interest_group_presence.items():
        share = ig.electorate_share.get(place, presence)
        scores = {c: _ig_vote_score(ig, c, place) for c in candidates}

        # Split IG support within each party across its candidates.
        parties_in_race = set(party_of.values())
        adjusted: dict[Agent, float] = {}
        for party in parties_in_race:
            party_candidates = [c for c in candidates if party_of[c] is party]
            party_total_score = sum(scores[c] for c in party_candidates)
            party_ig_affinity = party.base_constituency.get(ig, 0.0)
            for c in party_candidates:
                if party_total_score > 0:
                    adjusted[c] = party_ig_affinity * (scores[c] / party_total_score)
                else:
                    adjusted[c] = scores[c]

        total_adjusted = sum(adjusted.values())
        if total_adjusted <= 0:
            continue
        effective_share = _diluted_turnout_share(scores, share)
        for c in candidates:
            vote_totals[c] += effective_share * (adjusted[c] / total_adjusted)

    for c in vote_totals:
        vote_totals[c] += rng.uniform(0.0, 0.01)

    ranked = sorted(vote_totals, key=lambda c: vote_totals[c], reverse=True)
    winner = ranked[0]
    losers = ranked[1:]

    total_votes = sum(vote_totals.values())
    vote_shares = {c.name: vote_totals[c] / total_votes for c in ranked} if total_votes > 0 else {}

    _log.info("  Executive election in %s:", place.name)
    for c in ranked:
        _log.info("    %s: %.1f%%", fmt(c), vote_shares.get(c.name, 0) * 100)

    events: list[str] = []

    # Update term counters.
    winner.attributes["consecutive_terms_exec"] = (
        winner.attributes.get("consecutive_terms_exec", 0) + 1
    )
    for loser in losers:
        loser.attributes["consecutive_terms_exec"] = 0
        # Downgrade losers who held office to L2.
        if loser.office == gov.executive.office_type:
            loser.detail_level = DetailLevel.L2
            loser.attributes["turns_at_l2"] = 0

    # Update offices.
    old_holder = gov.executive.holder
    if old_holder is not None and old_holder is not winner:
        old_holder.office = None
        events.append(f"{fmt(old_holder)} lost the {gov.executive.office_type.name} seat")

    gov.executive.holder = winner
    winner.office = gov.executive.office_type
    winner.detail_level = DetailLevel.L0  # winners are key figures
    events.append(
        f"{fmt(winner)} elected as {gov.executive.office_type.name} of {place.name} "
        f"({vote_shares.get(winner.name, 0):.1%})"
    )

    return ElectionResult(
        place=place, election_type="executive",
        winners=[winner], losers=losers,
        vote_shares=vote_shares, events=events,
    )


# ---------------------------------------------------------------------------
# Legislative election
# ---------------------------------------------------------------------------

def run_legislative_election(gov: Government, world: World, rng: _random.Random) -> ElectionResult:
    """Proportional legislative election with party nominations and term limits."""
    assert gov.legislature is not None
    place = gov.place
    legislature = gov.legislature
    total_seats = legislature.total_seats
    executive_holder = gov.executive.holder

    # Get nominated candidates.
    nominations = nominate_legislative_candidates(gov, world, rng)
    all_candidates = [a for nominees in nominations.values() for a in nominees]

    # Party vote shares from IG support.
    parties_in_place = list(nominations.keys())
    party_votes: dict[Party, float] = {p: 0.0 for p in parties_in_place}
    for ig, presence in place.interest_group_presence.items():
        share = ig.electorate_share.get(place, presence)
        satisfaction = ig.satisfaction.get(place, 0.5)
        ig_party_scores: dict[Party, float] = {}
        for party in parties_in_place:
            affinity = party.base_constituency.get(ig, 0.0)
            candidates_for_party = nominations[party]
            avg_pop = 0.0
            if candidates_for_party:
                avg_pop = sum(a.popularity.get(ig, 0.0) for a in candidates_for_party) / len(candidates_for_party)
            ig_party_scores[party] = affinity * 0.4 + avg_pop * 0.4 + satisfaction * 0.2

        effective_share = _diluted_turnout_share(ig_party_scores, share)
        for party in parties_in_place:
            party_votes[party] += effective_share * ig_party_scores[party]

    for p in party_votes:
        party_votes[p] += rng.uniform(0.0, 0.01)

    total_pv = sum(party_votes.values())
    if total_pv <= 0:
        return ElectionResult(place=place, election_type="legislative",
                              events=["No votes cast in legislative election"])

    # Largest remainder seat allocation.
    party_share = {p: party_votes[p] / total_pv for p in parties_in_place}
    raw_seats = {p: party_share[p] * total_seats for p in parties_in_place}
    floor_seats = {p: int(raw_seats[p]) for p in parties_in_place}
    remainders = {p: raw_seats[p] - floor_seats[p] for p in parties_in_place}
    allocated = sum(floor_seats.values())
    for p in sorted(remainders, key=lambda x: remainders[x], reverse=True):
        if allocated >= total_seats:
            break
        floor_seats[p] += 1
        allocated += 1

    _log.info("  Legislative election in %s:", place.name)
    for p in parties_in_place:
        _log.info("    %s: %.1f%% -> %d seats", p.name, party_share[p] * 100, floor_seats[p])

    events: list[str] = []
    winners: list[Agent] = []
    losers: list[Agent] = []

    # Clear old member offices and track term counters.
    old_members = set(legislature.members)
    for m in old_members:
        if m.office == legislature.seat_type:
            m.office = None

    new_members: list[Agent] = []
    for party in parties_in_place:
        seats = floor_seats[party]
        if seats == 0:
            continue
        elected = nominations[party][:seats]
        for a in elected:
            a.office = legislature.seat_type
            a.detail_level = DetailLevel.L1
            a.attributes["consecutive_terms_leg"] = a.attributes.get("consecutive_terms_leg", 0) + 1
            new_members.append(a)
            winners.append(a)
        events.append(f"{party.name} won {seats} seat(s) in {place.name} legislature")

    # Downgrade losers.
    new_set = set(new_members)
    for m in old_members:
        if m not in new_set:
            m.attributes["consecutive_terms_leg"] = 0
            m.detail_level = DetailLevel.L2
            m.attributes["turns_at_l2"] = 0
            losers.append(m)

    # Unelected nominees who are new agents also go to L2.
    for party in parties_in_place:
        for a in nominations[party][floor_seats[party]:]:
            if a not in old_members:
                a.detail_level = DetailLevel.L2
                a.attributes["turns_at_l2"] = 0

    legislature.members = new_members
    vote_shares = {p.name: party_share[p] for p in parties_in_place}

    return ElectionResult(
        place=place, election_type="legislative",
        winners=winners, losers=losers,
        vote_shares=vote_shares, events=events,
    )


# ---------------------------------------------------------------------------
# Party leadership election
# ---------------------------------------------------------------------------

def run_party_election(party: Party, world: World, rng: _random.Random) -> list[str]:
    """Run a party leadership election. Returns event strings."""
    members = list(party.members.keys())
    if len(members) < 2:
        return []

    # Each member votes for a candidate (not themselves).
    vote_totals: dict[Agent, float] = {m: 0.0 for m in members}
    for voter in members:
        for candidate in members:
            if candidate is voter:
                continue
            avg_pop = sum(candidate.popularity.values()) / max(len(candidate.popularity), 1)
            office_bonus = 0.2 if candidate.office is not None else 0.0
            # Ideology distance normalized to [0,1] — closer = higher score.
            max_dist = len(voter.ideology.axes) ** 0.5
            dist = voter.ideology.distance(candidate.ideology)
            ideology_align = max(0.0, 1.0 - dist / max(max_dist, 1.0))
            score = (
                0.3 * voter.relationships.get(candidate, 0.0)
                + 0.3 * avg_pop
                + 0.2 * office_bonus
                + 0.2 * ideology_align
            )
            vote_totals[candidate] += score

    winner = max(vote_totals, key=lambda c: vote_totals[c])

    # Clear old leader/whip roles.
    for m in members:
        if party.members[m] in (PartyRole.LEADER, PartyRole.WHIP):
            party.set_role(m, PartyRole.MEMBER)

    party.set_role(winner, PartyRole.LEADER)
    winner.party_role = PartyRole.LEADER

    # Assign whip: highest party_standing member who isn't the leader.
    non_leaders = [m for m in members if m is not winner]
    if non_leaders:
        whip = max(non_leaders, key=lambda m: _whip_score(m, winner))
        party.set_role(whip, PartyRole.WHIP)
        whip.party_role = PartyRole.WHIP
        # Boost standing/relationship for both.
        winner.relationships[whip] = min(1.0, winner.relationships.get(whip, 0.0) + 0.1)
        whip.relationships[winner] = min(1.0, whip.relationships.get(winner, 0.0) + 0.1)
        winner.party_standing = min(1.0, winner.party_standing + 0.05)
        whip.party_standing = min(1.0, whip.party_standing + 0.03)

    party.last_leadership_turn = world.turn

    events = [f"{fmt(winner)} elected as {party.name} leader"]
    _log.info("  %s elected as %s leader", fmt(winner), party.name)
    return events
