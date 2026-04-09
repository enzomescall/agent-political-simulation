"""
Elaborate multi-city simulation: three municipalities inside the state of Cascadia.
Four parties, five interest groups, 30+ politicians, 3 election epochs (15 turns).

Cities:
  - Riverport    (industrial port city, 9-seat council)
  - Millhaven    (agricultural inland town, 7-seat council)
  - Seaside Cove (tourist/tech coastal city, 7-seat council)

Parties:
  - Labor Front    (hard left: workers + unions)
  - Civic Democrats (centre: broad coalition)
  - Reform Alliance (right: business + fiscal hawks)
  - Green Future   (left-progressive: environment + youth)

Run with:  python sim_test2.py
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

ELECTION_INTERVAL = 5
NUM_TURNS = ELECTION_INTERVAL * 3  # 3 full election epochs

rng = random.Random(7)

# ---------------------------------------------------------------------------
# 1. Interest groups
# ---------------------------------------------------------------------------

workers = InterestGroup(
    id=InterestGroupId("workers"),
    name="Industrial Workers Union",
    fears=["privatisation", "automation", "job_cuts"],
)
business = InterestGroup(
    id=InterestGroupId("business"),
    name="Chamber of Commerce",
    fears=["price_controls", "heavy_regulation", "tax_hikes"],
)
farmers = InterestGroup(
    id=InterestGroupId("farmers"),
    name="Agricultural Producers Guild",
    fears=["trade_deals", "subsidy_cuts"],
)
youth = InterestGroup(
    id=InterestGroupId("youth"),
    name="Youth & Students Alliance",
    fears=["austerity", "housing_costs"],
)
enviro = InterestGroup(
    id=InterestGroupId("enviro"),
    name="Cascadia Environment Network",
    fears=["deregulation", "fossil_fuel_expansion"],
)

# ---------------------------------------------------------------------------
# 2. Parties
# ---------------------------------------------------------------------------

labor = Party(
    id=PartyId("labor"),
    name="Labor Front",
    ideology=Ideology.create(economic=-0.75, social=0.5),
    directive_threshold=-0.25,
    campaign_budget=8,
    nomination_threshold=0.25,
    leadership_interval=10,
    base_constituency={workers: 0.85, youth: 0.45, farmers: 0.30},
)
civic = Party(
    id=PartyId("civic"),
    name="Civic Democrats",
    ideology=Ideology.create(economic=-0.1, social=0.2),
    directive_threshold=-0.10,
    campaign_budget=8,
    nomination_threshold=0.25,
    leadership_interval=10,
    base_constituency={workers: 0.40, business: 0.45, youth: 0.40, farmers: 0.35},
)
reform = Party(
    id=PartyId("reform"),
    name="Reform Alliance",
    ideology=Ideology.create(economic=0.65, social=-0.3),
    directive_threshold=-0.20,
    campaign_budget=8,
    nomination_threshold=0.25,
    leadership_interval=10,
    base_constituency={business: 0.80, farmers: 0.55},
)
green = Party(
    id=PartyId("green"),
    name="Green Future",
    ideology=Ideology.create(economic=-0.4, social=0.8),
    directive_threshold=-0.15,
    campaign_budget=6,
    nomination_threshold=0.20,
    leadership_interval=10,
    base_constituency={enviro: 0.90, youth: 0.70},
)

# ---------------------------------------------------------------------------
# 3. Places (state + three municipalities)
# ---------------------------------------------------------------------------

cascadia = Place(
    id=PlaceId("cascadia"),
    name="State of Cascadia",
    tier=PlaceTier.STATE,
)

riverport = Place(
    id=PlaceId("riverport"),
    name="Riverport",
    tier=PlaceTier.MUNICIPALITY,
    parent=cascadia,
    # Heavy industry, union-dense port city
    interest_group_presence={workers: 0.50, business: 0.25, youth: 0.15, enviro: 0.10},
)
millhaven = Place(
    id=PlaceId("millhaven"),
    name="Millhaven",
    tier=PlaceTier.MUNICIPALITY,
    parent=cascadia,
    # Rural-ish agricultural market town
    interest_group_presence={farmers: 0.45, business: 0.30, workers: 0.15, youth: 0.10},
)
seaside = Place(
    id=PlaceId("seaside"),
    name="Seaside Cove",
    tier=PlaceTier.MUNICIPALITY,
    parent=cascadia,
    # Coastal tourist/tech hub
    interest_group_presence={youth: 0.35, enviro: 0.30, business: 0.25, workers: 0.10},
)

# ---------------------------------------------------------------------------
# 4. Agents — helper for brevity
# ---------------------------------------------------------------------------

def make_agent(
    aid: str, name: str, party: Party, place: Place,
    econ: float, soc: float,
    office: OfficeType | None,
    allegiances: dict, popularity: dict,
    party_standing: float, ambition: float,
    archetype: Archetype,
    detail_level: DetailLevel = DetailLevel.L1,
    party_role: PartyRole = PartyRole.MEMBER,
) -> Agent:
    return Agent(
        id=AgentId(aid), name=name,
        ideology=Ideology.create(economic=econ, social=soc),
        party=party, place=place,
        office=office, party_role=party_role,
        allegiances=allegiances,
        popularity=popularity,
        party_standing=party_standing,
        ambition=ambition,
        archetype=archetype,
        detail_level=detail_level,
    )

# --- Riverport (9 seats) ---

rp_mayor = make_agent(
    "rp_mayor", "Harriet Voss", labor, riverport,
    econ=-0.8, soc=0.6,
    office=OfficeType.MAYOR,
    allegiances={workers: 0.90, youth: 0.4},
    popularity={workers: 0.80, youth: 0.60, business: 0.25, enviro: 0.40},
    party_standing=0.85, ambition=0.55,
    archetype=Archetype.LOYALIST,
    detail_level=DetailLevel.L0,
    party_role=PartyRole.LEADER,
)

rp_council = [
    make_agent("rp_c1", "Morris Tanaka", labor, riverport,
               econ=-0.65, soc=0.4, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.80}, popularity={workers: 0.72, youth: 0.45},
               party_standing=0.80, ambition=0.50, archetype=Archetype.LOYALIST),
    make_agent("rp_c2", "Petra Okafor", labor, riverport,
               econ=-0.55, soc=0.55, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.60, youth: 0.50}, popularity={workers: 0.60, youth: 0.65, enviro: 0.40},
               party_standing=0.65, ambition=0.70, archetype=Archetype.POPULIST),
    make_agent("rp_c3", "Jae-won Lim", labor, riverport,
               econ=-0.70, soc=0.35, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.75}, popularity={workers: 0.68, business: 0.20},
               party_standing=0.55, ambition=0.40, archetype=Archetype.IDEOLOGUE),
    make_agent("rp_c4", "Sandra Bretz", civic, riverport,
               econ=-0.15, soc=0.25, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.50, workers: 0.40}, popularity={business: 0.55, workers: 0.50, youth: 0.45},
               party_standing=0.75, ambition=0.55, archetype=Archetype.POPULIST),
    make_agent("rp_c5", "Omar Fenton", civic, riverport,
               econ=-0.05, soc=0.15, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.55, youth: 0.35}, popularity={business: 0.60, youth: 0.40},
               party_standing=0.70, ambition=0.45, archetype=Archetype.LOYALIST),
    make_agent("rp_c6", "Vivian Schroeder", reform, riverport,
               econ=0.60, soc=-0.25, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.80}, popularity={business: 0.70, workers: 0.20},
               party_standing=0.80, ambition=0.65, archetype=Archetype.IDEOLOGUE),
    make_agent("rp_c7", "Douglas Ashby", reform, riverport,
               econ=0.70, soc=-0.40, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.75, farmers: 0.30}, popularity={business: 0.65, farmers: 0.35},
               party_standing=0.72, ambition=0.60, archetype=Archetype.LOYALIST),
    make_agent("rp_c8", "Nadia Ferretti", green, riverport,
               econ=-0.45, soc=0.80, office=OfficeType.COUNCILPERSON,
               allegiances={enviro: 0.90, youth: 0.70}, popularity={enviro: 0.78, youth: 0.72, workers: 0.30},
               party_standing=0.88, ambition=0.75, archetype=Archetype.IDEOLOGUE),
    make_agent("rp_c9", "Kwame Asante", green, riverport,
               econ=-0.35, soc=0.75, office=OfficeType.COUNCILPERSON,
               allegiances={enviro: 0.80, youth: 0.60}, popularity={enviro: 0.70, youth: 0.65},
               party_standing=0.70, ambition=0.65, archetype=Archetype.POPULIST),
]

# --- Millhaven (7 seats) ---

mh_mayor = make_agent(
    "mh_mayor", "Roland Specter", reform, millhaven,
    econ=0.55, soc=-0.35,
    office=OfficeType.MAYOR,
    allegiances={business: 0.75, farmers: 0.70},
    popularity={business: 0.72, farmers: 0.68, workers: 0.25, youth: 0.30},
    party_standing=0.80, ambition=0.60,
    archetype=Archetype.LOYALIST,
    detail_level=DetailLevel.L0,
    party_role=PartyRole.LEADER,
)

mh_council = [
    make_agent("mh_c1", "Cecilia Holt", reform, millhaven,
               econ=0.60, soc=-0.30, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.70, farmers: 0.60}, popularity={business: 0.65, farmers: 0.62},
               party_standing=0.85, ambition=0.50, archetype=Archetype.LOYALIST),
    make_agent("mh_c2", "Walter Gruber", reform, millhaven,
               econ=0.50, soc=-0.20, office=OfficeType.COUNCILPERSON,
               allegiances={farmers: 0.75, business: 0.50}, popularity={farmers: 0.70, business: 0.55},
               party_standing=0.70, ambition=0.55, archetype=Archetype.POPULIST),
    make_agent("mh_c3", "Ines Carvalho", civic, millhaven,
               econ=-0.10, soc=0.20, office=OfficeType.COUNCILPERSON,
               allegiances={farmers: 0.50, workers: 0.45}, popularity={farmers: 0.55, workers: 0.50, youth: 0.40},
               party_standing=0.75, ambition=0.60, archetype=Archetype.POPULIST),
    make_agent("mh_c4", "Thomas Peel", civic, millhaven,
               econ=0.05, soc=0.10, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.45, farmers: 0.45}, popularity={business: 0.50, farmers: 0.48},
               party_standing=0.65, ambition=0.45, archetype=Archetype.LOYALIST),
    make_agent("mh_c5", "Abena Darko", labor, millhaven,
               econ=-0.60, soc=0.45, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.80, youth: 0.40}, popularity={workers: 0.65, youth: 0.50},
               party_standing=0.72, ambition=0.65, archetype=Archetype.IDEOLOGUE),
    make_agent("mh_c6", "Luca Marchetti", labor, millhaven,
               econ=-0.50, soc=0.30, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.65, farmers: 0.35}, popularity={workers: 0.60, farmers: 0.40},
               party_standing=0.60, ambition=0.50, archetype=Archetype.LOYALIST),
    make_agent("mh_c7", "Simone Beaumont", green, millhaven,
               econ=-0.40, soc=0.70, office=OfficeType.COUNCILPERSON,
               allegiances={enviro: 0.85, youth: 0.65, farmers: 0.30},
               popularity={enviro: 0.72, youth: 0.68, farmers: 0.35},
               party_standing=0.80, ambition=0.70, archetype=Archetype.IDEOLOGUE),
]

# --- Seaside Cove (7 seats) ---

sc_mayor = make_agent(
    "sc_mayor", "Yuki Tanomura", green, seaside,
    econ=-0.35, soc=0.85,
    office=OfficeType.MAYOR,
    allegiances={enviro: 0.90, youth: 0.75},
    popularity={enviro: 0.82, youth: 0.78, business: 0.35, workers: 0.25},
    party_standing=0.90, ambition=0.65,
    archetype=Archetype.IDEOLOGUE,
    detail_level=DetailLevel.L0,
    party_role=PartyRole.LEADER,
)

sc_council = [
    make_agent("sc_c1", "Felix Oduya", green, seaside,
               econ=-0.45, soc=0.80, office=OfficeType.COUNCILPERSON,
               allegiances={enviro: 0.85, youth: 0.65}, popularity={enviro: 0.78, youth: 0.72},
               party_standing=0.85, ambition=0.55, archetype=Archetype.IDEOLOGUE),
    make_agent("sc_c2", "Priya Sundaram", green, seaside,
               econ=-0.30, soc=0.75, office=OfficeType.COUNCILPERSON,
               allegiances={enviro: 0.80, youth: 0.70}, popularity={enviro: 0.72, youth: 0.70, business: 0.30},
               party_standing=0.75, ambition=0.60, archetype=Archetype.POPULIST),
    make_agent("sc_c3", "Miles Corrigan", civic, seaside,
               econ=-0.05, soc=0.30, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.50, youth: 0.45}, popularity={business: 0.60, youth: 0.55, enviro: 0.40},
               party_standing=0.78, ambition=0.55, archetype=Archetype.POPULIST),
    make_agent("sc_c4", "Rashida Osei", civic, seaside,
               econ=0.10, soc=0.20, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.60, youth: 0.35}, popularity={business: 0.65, youth: 0.45},
               party_standing=0.70, ambition=0.50, archetype=Archetype.LOYALIST),
    make_agent("sc_c5", "Henrik Strand", reform, seaside,
               econ=0.65, soc=-0.15, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.80}, popularity={business: 0.75, youth: 0.30, workers: 0.20},
               party_standing=0.75, ambition=0.70, archetype=Archetype.IDEOLOGUE),
    make_agent("sc_c6", "Amara Nwosu", reform, seaside,
               econ=0.55, soc=-0.10, office=OfficeType.COUNCILPERSON,
               allegiances={business: 0.70, youth: 0.25}, popularity={business: 0.65, youth: 0.35},
               party_standing=0.65, ambition=0.55, archetype=Archetype.LOYALIST),
    make_agent("sc_c7", "Theo Brandt", labor, seaside,
               econ=-0.55, soc=0.50, office=OfficeType.COUNCILPERSON,
               allegiances={workers: 0.75, youth: 0.50}, popularity={workers: 0.60, youth: 0.55, enviro: 0.35},
               party_standing=0.65, ambition=0.60, archetype=Archetype.POPULIST),
]

# Seed cross-city relationships for a few key figures.
rp_mayor.relationships = {
    rp_council[0]: 0.75, rp_council[1]: 0.60, rp_council[2]: 0.55,
    mh_council[4]: 0.40,  # cross-city labor solidarity
}
mh_mayor.relationships = {
    mh_council[0]: 0.80, mh_council[1]: 0.65,
    sc_council[4]: 0.35,  # reform cross-city
}
sc_mayor.relationships = {
    sc_council[0]: 0.85, sc_council[1]: 0.70,
    rp_council[7]: 0.50, rp_council[8]: 0.45,  # green cross-city
}

# ---------------------------------------------------------------------------
# 5. World registration
# ---------------------------------------------------------------------------

world = World()

for ig in [workers, business, farmers, youth, enviro]:
    world.add_interest_group(ig)

for party in [labor, civic, reform, green]:
    world.add_party(party)

world.add_place(cascadia)
for place in [riverport, millhaven, seaside]:
    world.add_place(place)

# Riverport politicians
world.add_politician(rp_mayor)
for c in rp_council:
    world.add_politician(c)

# Millhaven politicians
world.add_politician(mh_mayor)
for c in mh_council:
    world.add_politician(c)

# Seaside Cove politicians
world.add_politician(sc_mayor)
for c in sc_council:
    world.add_politician(c)

# ---------------------------------------------------------------------------
# 6. Governments
# ---------------------------------------------------------------------------

rp_legislature = Legislature(
    place=riverport,
    seat_type=OfficeType.COUNCILPERSON,
    total_seats=9,
    members=list(rp_council),
)
rp_exec = Office(office_type=OfficeType.MAYOR, place=riverport, holder=rp_mayor)
rp_gov = Government(
    place=riverport, executive=rp_exec, legislature=rp_legislature,
    attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
)
world.add_government(rp_gov)

mh_legislature = Legislature(
    place=millhaven,
    seat_type=OfficeType.COUNCILPERSON,
    total_seats=7,
    members=list(mh_council),
)
mh_exec = Office(office_type=OfficeType.MAYOR, place=millhaven, holder=mh_mayor)
mh_gov = Government(
    place=millhaven, executive=mh_exec, legislature=mh_legislature,
    attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
)
world.add_government(mh_gov)

sc_legislature = Legislature(
    place=seaside,
    seat_type=OfficeType.COUNCILPERSON,
    total_seats=7,
    members=list(sc_council),
)
sc_exec = Office(office_type=OfficeType.MAYOR, place=seaside, holder=sc_mayor)
sc_gov = Government(
    place=seaside, executive=sc_exec, legislature=sc_legislature,
    attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
)
world.add_government(sc_gov)

# ---------------------------------------------------------------------------
# 7. Initialise and run
# ---------------------------------------------------------------------------

weight_rng = random.Random(99)
for agent in world.politicians.values():
    agent.attributes["utility_weights"] = perturb_weights(weight_rng)

initialize_local_variables(world)

# ---------------------------------------------------------------------------
# 8. Print initial state
# ---------------------------------------------------------------------------

def print_city_state(place: Place, gov: Government) -> None:
    holder = gov.executive.holder
    mayor_str = f"{holder.name} ({holder.party.name})" if holder else "vacant"
    print(f"\n  {place.name}  —  Mayor: {mayor_str}")
    if gov.legislature:
        from collections import Counter
        seat_count: Counter = Counter()
        for m in gov.legislature.members:
            seat_count[m.party.name] += 1
        seats_str = ", ".join(f"{p}: {n}" for p, n in seat_count.most_common())
        print(f"    Council seats: {seats_str}")
    for ig, share in place.interest_group_presence.items():
        sat = ig.satisfaction.get(place, 0.5)
        print(f"    {ig.name:35s}  share={share:.2f}  sat={sat:.2f}")


print("=" * 70)
print("CASCADIA MULTI-CITY SIMULATION")
print(f"  Cities: Riverport (9 seats), Millhaven (7 seats), Seaside Cove (7 seats)")
print(f"  Parties: {', '.join(p.name for p in [labor, civic, reform, green])}")
print(f"  Turns: {NUM_TURNS} ({NUM_TURNS // ELECTION_INTERVAL} election epochs)")
print("=" * 70)
print("\n--- Initial State ---")
print_city_state(riverport, rp_gov)
print_city_state(millhaven, mh_gov)
print_city_state(seaside, sc_gov)

print("\n" + "=" * 70)
print(f"Running {NUM_TURNS} turns (verbose log → simulation.log)...")
print("=" * 70 + "\n")

sim_rng = random.Random(42)
reports = run_simulation(world, num_turns=NUM_TURNS, rng=sim_rng, debug=True)

# ---------------------------------------------------------------------------
# 9. Final state summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL STATE")
print("=" * 70)

for place, gov in [(riverport, rp_gov), (millhaven, mh_gov), (seaside, sc_gov)]:
    print_city_state(place, gov)

print("\n--- Interest Group Satisfaction ---")
for ig in [workers, business, farmers, youth, enviro]:
    row = []
    for place in [riverport, millhaven, seaside]:
        sat = ig.satisfaction.get(place, 0.5)
        row.append(f"{place.name[:8]}: {sat:.2f}")
    print(f"  {ig.name:35s}  " + "  ".join(row))

print("\n--- Agent Standings (active politicians) ---")
for agent in sorted(world.politicians.values(), key=lambda a: a.place.name):
    if agent.detail_level.value <= 1:
        office_str = agent.office.name if agent.office else "—"
        print(f"  {agent.name:20s}  {agent.party.name:18s}  "
              f"{agent.place.name:12s}  office={office_str:15s}  "
              f"standing={agent.party_standing:.2f}  LOD={agent.detail_level.name}")

print("\n--- Party Leadership ---")
for party in [labor, civic, reform, green]:
    leader = party.get_leader()
    whip = party.get_by_role(PartyRole.WHIP)
    leader_str = f"{leader.name} ({leader.place.name})" if leader else "vacant"
    whip_str = ", ".join(f"{w.name} ({w.place.name})" for w in whip) if whip else "none"
    print(f"  {party.name:18s}  Leader: {leader_str:30s}  Whip: {whip_str}")
