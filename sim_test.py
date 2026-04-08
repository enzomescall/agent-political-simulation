"""
Minimal simulation: one municipality, a 5-seat council, and a mayor.

Run with:  python sim_test.py

Sections marked  # MISSING  call out what needs to be built before
a real turn-by-turn loop can execute.
"""

from src.models import (
    Agent,
    Government,
    Ideology,
    InterestGroup,
    Legislature,
    Office,
    OfficeType,
    Party,
    Place,
    PolicyPreference,
    World,
    AgentId,
    InterestGroupId,
    PartyId,
    PlaceId,
    PlaceTier,
    Archetype,
    DetailLevel,
)

# ---------------------------------------------------------------------------
# 1. World + place
# ---------------------------------------------------------------------------

world = World()

city = Place(
    id=PlaceId("city"),
    name="Capital City",
    tier=PlaceTier.MUNICIPALITY,
    interest_group_presence={
        InterestGroupId("workers"): 0.55,
        InterestGroupId("business"): 0.30,
        InterestGroupId("youth"): 0.15,
    },
)
world.add_place(city)

# ---------------------------------------------------------------------------
# 2. Parties
# ---------------------------------------------------------------------------

labor = Party(
    id=PartyId("labor"),
    name="Labor Alliance",
    ideology=Ideology.create(economic=-0.6, social=0.4),
    base_constituency={InterestGroupId("workers"): 0.8, InterestGroupId("youth"): 0.5},
)
civic = Party(
    id=PartyId("civic"),
    name="Civic Progress",
    ideology=Ideology.create(economic=0.3, social=0.1),
    base_constituency={InterestGroupId("business"): 0.7, InterestGroupId("youth"): 0.3},
)
world.add_party(labor)
world.add_party(civic)

# ---------------------------------------------------------------------------
# 3. Interest groups
# ---------------------------------------------------------------------------

workers = InterestGroup(
    id=InterestGroupId("workers"),
    name="Urban Workers Union",
    policy_preferences=[
        PolicyPreference("min_wage", preferred_direction=1.0, importance=0.9),
        PolicyPreference("housing", preferred_direction=1.0, importance=0.7),
    ],
    fears=["privatisation", "job_cuts"],
    satisfaction={PlaceId("city"): 0.4},
    electorate_share={PlaceId("city"): 0.55},
)
business = InterestGroup(
    id=InterestGroupId("business"),
    name="Business Council",
    policy_preferences=[
        PolicyPreference("tax_rate", preferred_direction=-1.0, importance=0.8),
        PolicyPreference("regulation", preferred_direction=-0.6, importance=0.6),
    ],
    fears=["price_controls", "heavy_regulation"],
    satisfaction={PlaceId("city"): 0.6},
    electorate_share={PlaceId("city"): 0.30},
)
youth = InterestGroup(
    id=InterestGroupId("youth"),
    name="Youth Coalition",
    policy_preferences=[
        PolicyPreference("housing", preferred_direction=1.0, importance=0.8),
        PolicyPreference("climate", preferred_direction=1.0, importance= 0.9),
    ],
    fears=["austerity"],
    satisfaction={PlaceId("city"): 0.3},
    electorate_share={PlaceId("city"): 0.15},
)
world.add_interest_group(workers)
world.add_interest_group(business)
world.add_interest_group(youth)

# ---------------------------------------------------------------------------
# 4. Agents — 5 councillors + 1 mayor
# ---------------------------------------------------------------------------

councillors = [
    Agent(
        id=AgentId("c1"), name="Ana Souza",
        ideology=Ideology.create(economic=-0.7, social=0.5),
        party_id=PartyId("labor"), place_id=PlaceId("city"),
        office=OfficeType.COUNCILPERSON,
        allegiances={InterestGroupId("workers"): 0.85},
        popularity={InterestGroupId("workers"): 0.75, InterestGroupId("youth"): 0.6},
        party_standing=0.9, ambition=0.4, archetype=Archetype.LOYALIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c2"), name="Bruno Melo",
        ideology=Ideology.create(economic=-0.4, social=0.2),
        party_id=PartyId("labor"), place_id=PlaceId("city"),
        office=OfficeType.COUNCILPERSON,
        allegiances={InterestGroupId("workers"): 0.5, InterestGroupId("youth"): 0.4},
        popularity={InterestGroupId("workers"): 0.55},
        party_standing=0.6, ambition=0.7, archetype=Archetype.POPULIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c3"), name="Clara Faria",
        ideology=Ideology.create(economic=0.2, social=0.0),
        party_id=PartyId("civic"), place_id=PlaceId("city"),
        office=OfficeType.COUNCILPERSON,
        allegiances={InterestGroupId("business"): 0.6},
        popularity={InterestGroupId("business"): 0.65},
        party_standing=0.8, ambition=0.5, archetype=Archetype.IDEOLOGUE,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c4"), name="Diego Ramos",
        ideology=Ideology.create(economic=0.5, social=-0.3),
        party_id=PartyId("civic"), place_id=PlaceId("city"),
        office=OfficeType.COUNCILPERSON,
        allegiances={InterestGroupId("business"): 0.8},
        popularity={InterestGroupId("business"): 0.7, InterestGroupId("workers"): 0.2},
        party_standing=0.7, ambition=0.6, archetype=Archetype.LOYALIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c5"), name="Elisa Nunes",
        ideology=Ideology.create(economic=-0.1, social=0.6),
        party_id=PartyId("labor"), place_id=PlaceId("city"),
        office=OfficeType.COUNCILPERSON,
        allegiances={InterestGroupId("youth"): 0.75},
        popularity={InterestGroupId("youth"): 0.8, InterestGroupId("workers"): 0.45},
        party_standing=0.5, ambition=0.8, archetype=Archetype.POPULIST,
        detail_level=DetailLevel.L1,
    ),
]

mayor = Agent(
    id=AgentId("mayor"), name="Fernando Costa",
    ideology=Ideology.create(economic=-0.3, social=0.3),
    party_id=PartyId("labor"), place_id=PlaceId("city"),
    office=OfficeType.MAYOR,
    allegiances={
        InterestGroupId("workers"): 0.6,
        InterestGroupId("youth"): 0.5,
    },
    relationships={AgentId("c1"): 0.8, AgentId("c2"): 0.5, AgentId("c5"): 0.6},
    popularity={
        InterestGroupId("workers"): 0.65,
        InterestGroupId("youth"): 0.55,
        InterestGroupId("business"): 0.35,
    },
    party_standing=0.75, ambition=0.6, archetype=Archetype.POPULIST,
    detail_level=DetailLevel.L0,
)

for c in councillors:
    world.add_politician(c)
world.add_politician(mayor)

# ---------------------------------------------------------------------------
# 5. Government
# ---------------------------------------------------------------------------

council = Legislature(
    place_id=PlaceId("city"),
    seat_type=OfficeType.COUNCILPERSON,
    total_seats=5,
    member_ids=[c.id for c in councillors],
)
executive_office = Office(
    office_type=OfficeType.MAYOR,
    place_id=PlaceId("city"),
    holder_id=mayor.id,
)
gov = Government(
    place_id=PlaceId("city"),
    executive=executive_office,
    legislature=council,
)
world.add_government(gov)

# ---------------------------------------------------------------------------
# 6. State printout
# ---------------------------------------------------------------------------

print(f"Turn {world.turn}")
print(f"Place: {city.name} ({city.tier.name})")
print(f"Mayor: {mayor.name} ({world.parties[mayor.party_id].name})")
print(f"Council ({council.total_seats} seats):")
for cid in council.member_ids:
    c = world.politicians[cid]
    print(f"  {c.name:15s}  {world.parties[c.party_id].name:20s}  "
          f"ideology=({c.ideology['economic']:+.1f}, {c.ideology['social']:+.1f})")

print()
print("Interest group pressures this turn:")
for gid, group in world.interest_groups.items():
    p = world.interest_group_pressure(gid, PlaceId("city"))
    print(f"  {group.name:25s}  pressure={p:.2f}  satisfaction={group.satisfaction.get(PlaceId('city'), 0):.2f}")

# ---------------------------------------------------------------------------
# MISSING — what needs to be built for a real simulation loop
# ---------------------------------------------------------------------------
#
# 1. PROPOSALS / ACTIONS
#    Agents have no actions to take. Need a Proposal or Action model:
#    what policies they can propose, vote on, or block.
#
# 2. VOTING LOGIC
#    No mechanism for agents to vote on proposals. Outcome should depend
#    on ideology alignment, allegiances, relationships, and party_standing.
#
# 3. CONSEQUENCE PROPAGATION
#    After a vote passes/fails, nothing updates interest-group satisfaction,
#    agent popularity, or party_standing. Need a consequence resolver.
#
# 4. TURN ADVANCEMENT
#    world.turn is a bare counter. Need world.advance_turn() that:
#      - triggers agent decisions
#      - resolves votes
#      - propagates consequences
#      - optionally fires elections if a term ends
#
# 5. ELECTION MECHANICS
#    No model for elections: when they happen, how seats are contested,
#    how votes are tallied from electorate_share + satisfaction.
#
# 6. AGENT DECISION ENGINE
#    Agent has no decide(world) method. The decision logic (weight-based
#    at L1, aggregate at L2/L3, LLM-driven at L0) is entirely absent.