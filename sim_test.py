"""
Minimal simulation: one municipality, a 5-seat council, and a mayor.
Runs 5 turns of the simulation loop.

Run with:  python sim_test.py
"""

import random

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
    World,
    AgentId,
    InterestGroupId,
    PartyId,
    PlaceId,
    PlaceTier,
    Archetype,
    DetailLevel,
    PartyRole,
)
from src.actions.utility import perturb_weights
from src.simulation import initialize_local_variables, run_simulation

# ---------------------------------------------------------------------------
# 1. Interest groups (national-level, created first)
# ---------------------------------------------------------------------------

workers = InterestGroup(
    id=InterestGroupId("workers"),
    name="Urban Workers Union",
    fears=["privatisation", "job_cuts"],
)
business = InterestGroup(
    id=InterestGroupId("business"),
    name="Business Council",
    fears=["price_controls", "heavy_regulation"],
)
youth = InterestGroup(
    id=InterestGroupId("youth"),
    name="Youth Coalition",
    fears=["austerity"],
)

# ---------------------------------------------------------------------------
# 2. Parties (reference IG objects for constituency)
# ---------------------------------------------------------------------------

labor = Party(
    id=PartyId("labor"),
    name="Labor Alliance",
    ideology=Ideology.create(economic=-0.6, social=0.4),
    base_constituency={workers: 0.8, youth: 0.5},
    attributes={"directive_threshold": -0.2, "campaign_budget": 5, "leadership_interval": 20},
)
civic = Party(
    id=PartyId("civic"),
    name="Civic Progress",
    ideology=Ideology.create(economic=0.3, social=0.1),
    base_constituency={business: 0.7, youth: 0.3},
    attributes={"directive_threshold": -0.15, "campaign_budget": 5, "leadership_interval": 20},
)

# ---------------------------------------------------------------------------
# 3. Place (reference IG objects for presence)
# ---------------------------------------------------------------------------

city = Place(
    id=PlaceId("city"),
    name="Capital City",
    tier=PlaceTier.MUNICIPALITY,
    interest_group_presence={workers: 0.55, business: 0.30, youth: 0.15},
)

# ---------------------------------------------------------------------------
# 4. Agents — 5 councillors + 1 mayor (pass objects, not IDs)
# ---------------------------------------------------------------------------

councillors = [
    Agent(
        id=AgentId("c1"), name="Ana Souza",
        ideology=Ideology.create(economic=-0.7, social=0.5),
        party=labor, place=city,
        office=OfficeType.COUNCILPERSON,
        allegiances={workers: 0.85},
        popularity={workers: 0.75, youth: 0.6},
        party_standing=0.9, ambition=0.4, archetype=Archetype.LOYALIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c2"), name="Bruno Melo",
        ideology=Ideology.create(economic=-0.4, social=0.2),
        party=labor, place=city,
        office=OfficeType.COUNCILPERSON,
        allegiances={workers: 0.5, youth: 0.4},
        popularity={workers: 0.55, youth: 0.5},
        party_standing=0.6, ambition=0.7, archetype=Archetype.POPULIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c3"), name="Clara Faria",
        ideology=Ideology.create(economic=0.2, social=0.0),
        party=civic, place=city,
        office=OfficeType.COUNCILPERSON,
        allegiances={business: 0.6},
        popularity={business: 0.65, workers: 0.3},
        party_standing=0.8, ambition=0.5, archetype=Archetype.IDEOLOGUE,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c4"), name="Diego Ramos",
        ideology=Ideology.create(economic=0.5, social=-0.3),
        party=civic, place=city,
        office=OfficeType.COUNCILPERSON,
        allegiances={business: 0.8},
        popularity={business: 0.7, workers: 0.2},
        party_standing=0.7, ambition=0.6, archetype=Archetype.LOYALIST,
        detail_level=DetailLevel.L1,
    ),
    Agent(
        id=AgentId("c5"), name="Elisa Nunes",
        ideology=Ideology.create(economic=-0.1, social=0.6),
        party=labor, place=city,
        office=OfficeType.COUNCILPERSON,
        allegiances={youth: 0.75},
        popularity={youth: 0.8, workers: 0.45},
        party_standing=0.5, ambition=0.8, archetype=Archetype.POPULIST,
        detail_level=DetailLevel.L1,
    ),
]

mayor = Agent(
    id=AgentId("mayor"), name="Fernando Costa",
    ideology=Ideology.create(economic=-0.3, social=0.3),
    party=labor, place=city,
    office=OfficeType.MAYOR,
    party_role=PartyRole.LEADER,
    allegiances={workers: 0.6, youth: 0.5},
    relationships={},
    popularity={workers: 0.65, youth: 0.55, business: 0.35},
    party_standing=0.75, ambition=0.6, archetype=Archetype.POPULIST,
    detail_level=DetailLevel.L0,
)
# Seed some initial relationships.
mayor.relationships = {councillors[0]: 0.8, councillors[1]: 0.5, councillors[4]: 0.6}

# ---------------------------------------------------------------------------
# 5. Register everything in World
# ---------------------------------------------------------------------------

world = World()
world.add_interest_group(workers)
world.add_interest_group(business)
world.add_interest_group(youth)
world.add_party(labor)
world.add_party(civic)
world.add_place(city)
for c in councillors:
    world.add_politician(c)
world.add_politician(mayor)

# ---------------------------------------------------------------------------
# 6. Government
# ---------------------------------------------------------------------------

council = Legislature(
    place=city,
    seat_type=OfficeType.COUNCILPERSON,
    total_seats=5,
    members=list(councillors),
)
executive_office = Office(
    office_type=OfficeType.MAYOR,
    place=city,
    holder=mayor,
)
gov = Government(place=city, executive=executive_office, legislature=council,
                 attributes={"election_interval": 5, "last_election_turn": 0})
world.add_government(gov)

# ---------------------------------------------------------------------------
# 7. Initialize dynamic variables + run simulation
# ---------------------------------------------------------------------------

# Assign unique utility weights to each agent.
weight_rng = random.Random(123)
for agent in world.politicians.values():
    agent.attributes["utility_weights"] = perturb_weights(weight_rng)

initialize_local_variables(world)

print(f"=== Initial State (Turn {world.turn}) ===")
print(f"Place: {city.name} ({city.tier.name})")
print(f"Mayor: {mayor.name} ({mayor.party.name}, {mayor.party_role.name})")
print(f"  {mayor.name:15s}  {mayor.party.name:20s}  "
          f"ideology=({mayor.ideology['economic']:+.1f}, {mayor.ideology['social']:+.1f})")
print(f"Council ({council.total_seats} seats):")
for c in councillors:
    print(f"  {c.name:15s}  {c.party.name:20s}  "
          f"ideology=({c.ideology['economic']:+.1f}, {c.ideology['social']:+.1f})")
print()
print("Interest group state:")
for ig in [workers, business, youth]:
    sat = ig.satisfaction.get(city, 0.0)
    share = ig.electorate_share.get(city, 0.0)
    pressure = ig.pressure_on(city)
    print(f"  {ig.name:25s}  sat={sat:.2f}  share={share:.2f}  pressure={pressure:.2f}")

print("\n" + "=" * 60)
print("Running 10 turns (verbose log → simulation.log)...")
print("=" * 60 + "\n")

rng = random.Random(42)
reports = run_simulation(world, num_turns=10, rng=rng, debug=True)

print(f"\n=== Final State (Turn {world.turn}) ===")
print("Interest group satisfaction:")
for ig in [workers, business, youth]:
    sat = ig.satisfaction.get(city, 0.0)
    pressure = ig.pressure_on(city)
    print(f"  {ig.name:25s}  sat={sat:.2f}  pressure={pressure:.2f}")

print("\nAgent standings:")
for agent in [mayor] + councillors:
    office_str = agent.office.name if agent.office else "none"
    print(f"  {agent.name:15s}  office={office_str:15s}  party_standing={agent.party_standing:.2f}")
