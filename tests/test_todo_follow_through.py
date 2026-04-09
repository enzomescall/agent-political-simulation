from __future__ import annotations

import random
import unittest

from src.actions.base import VoteResult
from src.actions.voting import compute_directive_pressure, compute_vote_disposition, _expulsion_risk_score
from src.models import (
    Agent,
    AgentId,
    Archetype,
    DetailLevel,
    Government,
    Ideology,
    InterestGroup,
    InterestGroupId,
    Legislature,
    Office,
    OfficeType,
    Party,
    PartyId,
    PartyRole,
    Place,
    PlaceId,
    PlaceTier,
    Policy,
    World,
)
from src.simulation.consequences import apply_vote_consequences
from src.simulation.elections import _diluted_turnout_share, run_party_election


def make_policy(name: str, support_by_party: dict[Party, float]) -> Policy:
    return Policy(
        name=name,
        interest_group_impacts={},
        ideology_alignment={},
        attributes={"party_support": support_by_party},
    )


class TodoFollowThroughTests(unittest.TestCase):
    def setUp(self) -> None:
        self.place = Place(
            id=PlaceId("city"),
            name="City",
            tier=PlaceTier.MUNICIPALITY,
        )
        self.workers = InterestGroup(
            id=InterestGroupId("workers"),
            name="Workers",
            electorate_share={self.place: 1.0},
            satisfaction={self.place: 0.5},
        )
        self.place.interest_group_presence = {self.workers: 1.0}

        self.major_party = Party(
            id=PartyId("major"),
            name="Major Party",
            ideology=Ideology.create(economic=0.1, social=0.0),
            base_constituency={self.workers: 0.6},
            attributes={"directive_threshold": 0.3},
        )
        self.alt_party = Party(
            id=PartyId("alt"),
            name="Alt Party",
            ideology=Ideology.create(economic=0.9, social=0.0),
            base_constituency={self.workers: 0.2},
        )

        self.agent = Agent(
            id=AgentId("a1"),
            name="Alex",
            ideology=Ideology.create(economic=0.0, social=0.0),
            party=self.major_party,
            place=self.place,
            office=OfficeType.COUNCILPERSON,
            popularity={self.workers: 0.2},
            party_standing=0.2,
            archetype=Archetype.LOYALIST,
            detail_level=DetailLevel.L1,
        )

        self.world = World()
        self.world.add_place(self.place)
        self.world.add_interest_group(self.workers)
        self.world.add_party(self.major_party)
        self.world.add_party(self.alt_party)
        self.world.add_politician(self.agent)

    def test_directive_threshold_changes_vote_pressure_and_standing(self) -> None:
        tolerated = make_policy("Tolerated", {self.major_party: 0.2})
        strong = make_policy("Strong", {self.major_party: 0.9})

        tolerated_pressure = compute_directive_pressure(self.agent, tolerated)
        strong_pressure = compute_directive_pressure(self.agent, strong)

        self.assertEqual(tolerated_pressure, 0.0)
        self.assertGreater(strong_pressure, 0.0)
        self.assertGreater(
            compute_vote_disposition(self.agent, strong, self.world),
            compute_vote_disposition(self.agent, tolerated, self.world),
        )

        tolerated_result = VoteResult(
            policy=tolerated,
            place=self.place,
            no_votes=[self.agent],
            passed=False,
        )
        apply_vote_consequences(tolerated_result, self.world)
        self.assertAlmostEqual(self.agent.party_standing, 0.2)

        strong_result = VoteResult(
            policy=strong,
            place=self.place,
            no_votes=[self.agent],
            passed=False,
        )
        apply_vote_consequences(strong_result, self.world)
        self.assertLess(self.agent.party_standing, 0.2)
        self.assertGreater(self.agent.attributes.get("recent_defiance", 0.0), 0.0)

    def test_expulsion_risk_accounts_for_alternatives_and_popularity(self) -> None:
        policy = make_policy("Party Priority", {self.major_party: 0.9})

        high_pop = Agent(
            id=AgentId("high"),
            name="High Pop",
            ideology=Ideology.create(economic=0.0, social=0.0),
            party=self.major_party,
            place=self.place,
            popularity={self.workers: 0.8},
            party_standing=0.2,
            archetype=Archetype.LOYALIST,
        )
        low_pop = Agent(
            id=AgentId("low"),
            name="Low Pop",
            ideology=Ideology.create(economic=0.0, social=0.0),
            party=self.major_party,
            place=self.place,
            popularity={self.workers: 0.1},
            party_standing=0.2,
            archetype=Archetype.LOYALIST,
        )
        self.world.add_politician(high_pop)
        self.world.add_politician(low_pop)

        high_pop_risk = abs(_expulsion_risk_score(high_pop, policy, self.world))
        low_pop_risk = abs(_expulsion_risk_score(low_pop, policy, self.world))
        self.assertGreater(low_pop_risk, high_pop_risk)

        similar_world = World(
            places={self.place.id: self.place},
            parties={self.major_party.id: self.major_party},
            interest_groups={self.workers.id: self.workers},
        )
        similar_party = Party(
            id=PartyId("similar"),
            name="Similar Party",
            ideology=Ideology.create(economic=0.12, social=0.0),
            base_constituency={self.workers: 0.2},
        )
        similar_world.add_party(similar_party)
        similar_agent = Agent(
            id=AgentId("similar_agent"),
            name="Similar Agent",
            ideology=Ideology.create(economic=0.1, social=0.0),
            party=self.major_party,
            place=self.place,
            popularity={self.workers: 0.1},
            party_standing=0.2,
            archetype=Archetype.LOYALIST,
        )
        similar_world.add_politician(similar_agent)

        far_world = World(
            places={self.place.id: self.place},
            parties={self.major_party.id: self.major_party},
            interest_groups={self.workers.id: self.workers},
        )
        far_party = Party(
            id=PartyId("far"),
            name="Far Party",
            ideology=Ideology.create(economic=-1.0, social=0.0),
            base_constituency={self.workers: 0.2},
        )
        far_world.add_party(far_party)
        far_agent = Agent(
            id=AgentId("far_agent"),
            name="Far Agent",
            ideology=Ideology.create(economic=0.1, social=0.0),
            party=self.major_party,
            place=self.place,
            popularity={self.workers: 0.1},
            party_standing=0.2,
            archetype=Archetype.LOYALIST,
        )
        far_world.add_politician(far_agent)

        self.assertLess(
            abs(_expulsion_risk_score(similar_agent, policy, similar_world)),
            abs(_expulsion_risk_score(far_agent, policy, far_world)),
        )

    def test_fragmented_support_reduces_effective_turnout(self) -> None:
        unified_scores = {"labor": 1.0, "business": 0.4}
        fragmented_scores = {"labor_a": 1.0, "labor_b": 0.95, "business": 0.4}

        unified_turnout = _diluted_turnout_share(unified_scores, 1.0)
        fragmented_turnout = _diluted_turnout_share(fragmented_scores, 1.0)

        self.assertLess(fragmented_turnout, unified_turnout)

    def test_whip_selection_is_multifactor_not_just_highest_standing(self) -> None:
        party = Party(
            id=PartyId("party"),
            name="Party",
            ideology=Ideology.create(economic=0.0, social=0.0),
        )
        world = World()
        world.add_party(party)
        world.add_place(self.place)
        world.add_interest_group(self.workers)

        leader_candidate = Agent(
            id=AgentId("leader"),
            name="Leader Candidate",
            ideology=Ideology.create(economic=0.0, social=0.0),
            party=party,
            place=self.place,
            office=OfficeType.MAYOR,
            popularity={self.workers: 0.95},
            party_standing=0.85,
            archetype=Archetype.LOYALIST,
            detail_level=DetailLevel.L0,
        )
        high_standing = Agent(
            id=AgentId("standing"),
            name="Standing",
            ideology=Ideology.create(economic=0.9, social=0.0),
            party=party,
            place=self.place,
            popularity={self.workers: 0.3},
            party_standing=0.95,
            archetype=Archetype.LOYALIST,
        )
        connected = Agent(
            id=AgentId("connected"),
            name="Connected",
            ideology=Ideology.create(economic=0.05, social=0.0),
            party=party,
            place=self.place,
            office=OfficeType.COUNCILPERSON,
            popularity={self.workers: 0.55},
            party_standing=0.7,
            archetype=Archetype.LOYALIST,
        )

        leader_candidate.relationships = {high_standing: 0.0, connected: 0.95}
        high_standing.relationships = {leader_candidate: 0.1, connected: 0.1}
        connected.relationships = {leader_candidate: 0.9, high_standing: 0.1}

        for member in (leader_candidate, high_standing, connected):
            world.add_politician(member)

        events = run_party_election(party, world, random.Random(7))
        self.assertTrue(events)
        self.assertIs(party.get_leader(), leader_candidate)
        self.assertEqual(party.members[connected], PartyRole.WHIP)
        self.assertNotEqual(party.members[high_standing], PartyRole.WHIP)


if __name__ == "__main__":
    unittest.main()
