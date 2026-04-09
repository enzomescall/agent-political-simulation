"""
Full federal simulation: the Cascadia Federation.

Structure
---------
  Federal   : President + 12-seat Congress
  State x3  : Governor + Assembly
    Ironfield (industrial):  9-seat Assembly, 4 cities
    Verdana   (agricultural):7-seat Assembly, 4 cities
    Pacifica  (coastal/tech): 9-seat Assembly, 5 cities

  13 cities total, 5-seat councils each.

Parties (4)
-----------
  Labor Front        hard-left, workers + farmers
  Civic Democrats    centrist, broad coalition
  Reform Alliance    right, business + fiscal hawks
  Green Future       left-progressive, environment + youth

Interest groups (6)
-------------------
  Industrial Workers Union
  Chamber of Commerce
  Agricultural Producers Guild
  Youth & Students Alliance
  Cascadia Environment Network
  Veterans & Public Safety League

Run with:  python sim_test3.py
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass

from src.models import (
    Agent, Government, Ideology, InterestGroup, Legislature,
    Office, OfficeType, Party, Place, World,
    AgentId, InterestGroupId, PartyId, PlaceId,
    PlaceTier, Archetype, DetailLevel, PartyRole,
)
from src.actions.utility import perturb_weights
from src.simulation import initialize_local_variables, run_simulation

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ELECTION_INTERVAL = 5
NUM_TURNS = ELECTION_INTERVAL * 3  # 3 full epochs

MASTER_RNG = random.Random(31415)

# ---------------------------------------------------------------------------
# 1. Interest groups
# ---------------------------------------------------------------------------

workers = InterestGroup(
    id=InterestGroupId("workers"),
    name="Industrial Workers Union",
    fears=["privatisation", "automation"],
)
business = InterestGroup(
    id=InterestGroupId("business"),
    name="Chamber of Commerce",
    fears=["tax_hikes", "heavy_regulation"],
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
    fears=["deregulation", "fossil_fuel"],
)
veterans = InterestGroup(
    id=InterestGroupId("veterans"),
    name="Veterans & Public Safety League",
    fears=["military_cuts", "police_defunding"],
)

ALL_IGs = [workers, business, farmers, youth, enviro, veterans]

# ---------------------------------------------------------------------------
# 2. Parties
# ---------------------------------------------------------------------------

labor = Party(
    id=PartyId("labor"), name="Labor Front",
    ideology=Ideology.create(economic=-0.70, social=0.45),
    directive_threshold=-0.20, campaign_budget=10,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={workers: 0.85, youth: 0.40, farmers: 0.25},
)
civic = Party(
    id=PartyId("civic"), name="Civic Democrats",
    ideology=Ideology.create(economic=-0.10, social=0.20),
    directive_threshold=-0.10, campaign_budget=10,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={workers: 0.40, business: 0.45, youth: 0.40,
                       farmers: 0.35, veterans: 0.40},
)
reform = Party(
    id=PartyId("reform"), name="Reform Alliance",
    ideology=Ideology.create(economic=0.65, social=-0.35),
    directive_threshold=-0.20, campaign_budget=10,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={business: 0.80, farmers: 0.55, veterans: 0.65},
)
green = Party(
    id=PartyId("green"), name="Green Future",
    ideology=Ideology.create(economic=-0.40, social=0.80),
    directive_threshold=-0.15, campaign_budget=8,
    nomination_threshold=0.15, leadership_interval=10,
    base_constituency={enviro: 0.90, youth: 0.70},
)

ALL_PARTIES = [labor, civic, reform, green]

# ---------------------------------------------------------------------------
# 3. Places
# ---------------------------------------------------------------------------

federation = Place(
    id=PlaceId("federation"), name="Cascadia Federation", tier=PlaceTier.FEDERAL,
)

# ---- States ----
ironfield = Place(
    id=PlaceId("ironfield"), name="Ironfield", tier=PlaceTier.STATE, parent=federation,
    # Heavy industry, manufacturing belt
    interest_group_presence={workers: 0.45, business: 0.25, veterans: 0.15,
                               farmers: 0.10, youth: 0.05},
)
verdana = Place(
    id=PlaceId("verdana"), name="Verdana", tier=PlaceTier.STATE, parent=federation,
    # Agricultural heartland
    interest_group_presence={farmers: 0.50, business: 0.20, veterans: 0.15,
                              workers: 0.10, youth: 0.05},
)
pacifica = Place(
    id=PlaceId("pacifica"), name="Pacifica", tier=PlaceTier.STATE, parent=federation,
    # Coastal tech + tourism
    interest_group_presence={youth: 0.30, enviro: 0.25, business: 0.25,
                              workers: 0.15, veterans: 0.05},
)

# ---- Cities: Ironfield (4) ----
steelburg = Place(
    id=PlaceId("steelburg"), name="Steelburg", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.55, business: 0.20, veterans: 0.15, youth: 0.10},
)
coalton = Place(
    id=PlaceId("coalton"), name="Coalton", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.60, veterans: 0.20, business: 0.15, youth: 0.05},
)
millford = Place(
    id=PlaceId("millford"), name="Millford", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.40, business: 0.30, veterans: 0.20, youth: 0.10},
)
irondale = Place(
    id=PlaceId("irondale"), name="Irondale", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={business: 0.40, workers: 0.35, youth: 0.15, veterans: 0.10},
)

# ---- Cities: Verdana (4) ----
farmington = Place(
    id=PlaceId("farmington"), name="Farmington", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.60, business: 0.20, veterans: 0.15, youth: 0.05},
)
crestview = Place(
    id=PlaceId("crestview"), name="Crestview", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.50, business: 0.25, veterans: 0.15, workers: 0.10},
)
riverdale = Place(
    id=PlaceId("riverdale"), name="Riverdale", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.40, workers: 0.25, business: 0.20, youth: 0.15},
)
granville = Place(
    id=PlaceId("granville"), name="Granville", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={business: 0.35, farmers: 0.35, veterans: 0.20, youth: 0.10},
)

# ---- Cities: Pacifica (5) ----
bayshore = Place(
    id=PlaceId("bayshore"), name="Bayshore", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={youth: 0.40, enviro: 0.30, business: 0.20, workers: 0.10},
)
harborview = Place(
    id=PlaceId("harborview"), name="Harborview", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={business: 0.35, youth: 0.30, enviro: 0.25, workers: 0.10},
)
solana = Place(
    id=PlaceId("solana"), name="Solana", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={enviro: 0.45, youth: 0.35, business: 0.15, workers: 0.05},
)
crestwood = Place(
    id=PlaceId("crestwood"), name="Crestwood", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={youth: 0.35, business: 0.30, enviro: 0.25, workers: 0.10},
)
waverly = Place(
    id=PlaceId("waverly"), name="Waverly", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={business: 0.40, workers: 0.25, veterans: 0.20, youth: 0.15},
)

IRONFIELD_CITIES  = [steelburg, coalton, millford, irondale]
VERDANA_CITIES    = [farmington, crestview, riverdale, granville]
PACIFICA_CITIES   = [bayshore, harborview, solana, crestwood, waverly]
ALL_CITIES        = IRONFIELD_CITIES + VERDANA_CITIES + PACIFICA_CITIES
ALL_STATES        = [ironfield, verdana, pacifica]

# ---------------------------------------------------------------------------
# 4. Procedural agent generation
# ---------------------------------------------------------------------------

# Pre-defined named politicians for key roles (president, governors, some mayors).
# Everyone else is generated procedurally.

_AGENT_COUNTER = 0
def _next_id(prefix: str) -> AgentId:
    global _AGENT_COUNTER
    _AGENT_COUNTER += 1
    return AgentId(f"{prefix}_{_AGENT_COUNTER:04d}")


# Names pool for generated politicians.
_FIRST = [
    "Aaron", "Beatrice", "Carlos", "Diana", "Ethan", "Fatima", "George",
    "Helena", "Ivan", "Julia", "Kevin", "Leila", "Marco", "Naomi", "Oscar",
    "Paula", "Quinn", "Rosa", "Samuel", "Tina", "Ulrich", "Vera", "Walter",
    "Xena", "Yusuf", "Zara", "Alicia", "Brendan", "Chloe", "Derek",
]
_LAST = [
    "Adeyemi", "Bauer", "Chen", "Dalton", "Eriksen", "Flores", "Grant",
    "Huang", "Ibrahim", "Jensen", "Kim", "Laurent", "Mercer", "Navarro",
    "Osei", "Park", "Quinn", "Reyes", "Santos", "Thornton", "Ueda",
    "Vargas", "Walsh", "Xu", "Yilmaz", "Ziegler", "Amara", "Brooks",
    "Castillo", "Donovan",
]

_used_names: set[str] = set()

def _random_name(rng: random.Random) -> str:
    for _ in range(200):
        name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
        if name not in _used_names:
            _used_names.add(name)
            return name
    return f"Politician {len(_used_names)}"


def _party_for_place(place: Place, rng: random.Random) -> Party:
    """Pick a party weighted by how well it fits the place's IG mix."""
    scores = []
    for party in ALL_PARTIES:
        score = sum(
            party.base_constituency.get(ig, 0.0) * share
            for ig, share in place.interest_group_presence.items()
        )
        scores.append(max(score, 0.05))
    return rng.choices(ALL_PARTIES, weights=scores, k=1)[0]


def _make_agent(
    place: Place,
    office: OfficeType | None,
    party: Party,
    rng: random.Random,
    detail_level: DetailLevel = DetailLevel.L1,
    name: str | None = None,
    party_role: PartyRole = PartyRole.MEMBER,
    econ_override: float | None = None,
    soc_override: float | None = None,
) -> Agent:
    """Generate an agent ideologically near their party with some noise."""
    econ = (econ_override if econ_override is not None
            else max(-1.0, min(1.0, party.ideology["economic"] + rng.uniform(-0.25, 0.25))))
    soc  = (soc_override  if soc_override  is not None
            else max(-1.0, min(1.0, party.ideology["social"]   + rng.uniform(-0.25, 0.25))))

    if name is None:
        name = _random_name(rng)
    _used_names.add(name)

    # Allegiances: favour IGs that overlap between place presence and party constituency.
    allegiances: dict[InterestGroup, float] = {}
    for ig, share in place.interest_group_presence.items():
        affinity = party.base_constituency.get(ig, 0.0)
        base = affinity * 0.6 + share * 0.2
        allegiances[ig] = max(0.0, min(1.0, base + rng.uniform(-0.1, 0.1)))

    # Popularity: correlated with allegiances + some noise.
    popularity: dict[InterestGroup, float] = {}
    for ig in place.interest_group_presence:
        base = allegiances.get(ig, 0.0) * 0.7 + rng.uniform(0.0, 0.3)
        popularity[ig] = max(0.0, min(1.0, base))

    return Agent(
        id=_next_id(place.id[:3]),
        name=name,
        ideology=Ideology.create(economic=econ, social=soc),
        party=party,
        place=place,
        office=office,
        party_role=party_role,
        allegiances=allegiances,
        popularity=popularity,
        party_standing=rng.uniform(0.55, 0.90),
        ambition=rng.uniform(0.35, 0.80),
        archetype=rng.choice(list(Archetype)),
        detail_level=detail_level,
    )


# ---------------------------------------------------------------------------
# 5. Build world
# ---------------------------------------------------------------------------

world = World()
for ig in ALL_IGs:
    world.add_interest_group(ig)
for party in ALL_PARTIES:
    world.add_party(party)

world.add_place(federation)
for state in ALL_STATES:
    world.add_place(state)
for city in ALL_CITIES:
    world.add_place(city)

# ---------------------------------------------------------------------------
# 5a. Federal government  — President + 12-seat Congress
# ---------------------------------------------------------------------------

# Hand-craft the president for narrative weight.
pres = _make_agent(
    federation, OfficeType.PRESIDENT, civic, MASTER_RNG,
    detail_level=DetailLevel.L0,
    name="Eleanor Marsh",
    party_role=PartyRole.LEADER,
    econ_override=-0.05, soc_override=0.30,
)
_used_names.add("Eleanor Marsh")
world.add_politician(pres)

# Congress: 3 per party (weighted draw per IG presence at federal level is flat, so just rotate)
_party_rotation = [labor, civic, reform, labor, green, civic, reform, labor, green, civic, reform, green]
congress_members: list[Agent] = []
for party in _party_rotation:
    m = _make_agent(federation, OfficeType.CONGRESSPERSON, party, MASTER_RNG)
    world.add_politician(m)
    congress_members.append(m)

fed_legislature = Legislature(
    place=federation, seat_type=OfficeType.CONGRESSPERSON,
    total_seats=12, members=congress_members,
)
fed_exec = Office(office_type=OfficeType.PRESIDENT, place=federation, holder=pres)
fed_gov = Government(
    place=federation, executive=fed_exec, legislature=fed_legislature,
    attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
)
world.add_government(fed_gov)

# ---------------------------------------------------------------------------
# 5b. State governments
# ---------------------------------------------------------------------------

@dataclass
class StateSetup:
    place: Place
    gov_name: str
    gov_party: Party
    gov_econ: float
    gov_soc: float
    assembly_seats: int
    # (party, count) distribution for initial assembly
    assembly_composition: list[tuple[Party, int]]


STATE_CONFIGS = [
    StateSetup(
        place=ironfield,
        gov_name="Bernard Holloway", gov_party=labor,
        gov_econ=-0.65, gov_soc=0.40,
        assembly_seats=9,
        assembly_composition=[(labor, 4), (civic, 2), (reform, 2), (green, 1)],
    ),
    StateSetup(
        place=verdana,
        gov_name="Margaret Tillson", gov_party=reform,
        gov_econ=0.60, gov_soc=-0.30,
        assembly_seats=7,
        assembly_composition=[(reform, 3), (civic, 2), (labor, 1), (green, 1)],
    ),
    StateSetup(
        place=pacifica,
        gov_name="Jerome Nakamura", gov_party=green,
        gov_econ=-0.30, gov_soc=0.75,
        assembly_seats=9,
        assembly_composition=[(green, 4), (civic, 2), (labor, 2), (reform, 1)],
    ),
]

state_govs: dict[PlaceId, Government] = {}

for cfg in STATE_CONFIGS:
    governor = _make_agent(
        cfg.place, OfficeType.GOVERNOR, cfg.gov_party, MASTER_RNG,
        detail_level=DetailLevel.L0,
        name=cfg.gov_name,
        party_role=PartyRole.LEADER,
        econ_override=cfg.gov_econ, soc_override=cfg.gov_soc,
    )
    _used_names.add(cfg.gov_name)
    world.add_politician(governor)

    assembly_members: list[Agent] = []
    for party, count in cfg.assembly_composition:
        for _ in range(count):
            m = _make_agent(cfg.place, OfficeType.STATE_ASSEMBLYPERSON, party, MASTER_RNG)
            world.add_politician(m)
            assembly_members.append(m)

    state_leg = Legislature(
        place=cfg.place, seat_type=OfficeType.STATE_ASSEMBLYPERSON,
        total_seats=cfg.assembly_seats, members=assembly_members,
    )
    state_exec = Office(office_type=OfficeType.GOVERNOR, place=cfg.place, holder=governor)
    state_gov = Government(
        place=cfg.place, executive=state_exec, legislature=state_leg,
        attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
    )
    world.add_government(state_gov)
    state_govs[cfg.place.id] = state_gov

# ---------------------------------------------------------------------------
# 5c. City governments — 5-seat councils per city
# ---------------------------------------------------------------------------

# City-level party distributions shaped by the place's IG mix.
_CITY_COUNCIL_SEATS = 5

city_govs: dict[PlaceId, Government] = {}

for city in ALL_CITIES:
    # Mayor party: weighted by place IG fit.
    mayor_party = _party_for_place(city, MASTER_RNG)
    mayor = _make_agent(
        city, OfficeType.MAYOR, mayor_party, MASTER_RNG,
        detail_level=DetailLevel.L0,
        party_role=PartyRole.MEMBER,
    )
    world.add_politician(mayor)

    # 5 council members — distribute parties by IG fit.
    council_members: list[Agent] = []
    for _ in range(_CITY_COUNCIL_SEATS):
        party = _party_for_place(city, MASTER_RNG)
        m = _make_agent(city, OfficeType.COUNCILPERSON, party, MASTER_RNG)
        world.add_politician(m)
        council_members.append(m)

    city_leg = Legislature(
        place=city, seat_type=OfficeType.COUNCILPERSON,
        total_seats=_CITY_COUNCIL_SEATS, members=council_members,
    )
    city_exec = Office(office_type=OfficeType.MAYOR, place=city, holder=mayor)
    city_gov = Government(
        place=city, executive=city_exec, legislature=city_leg,
        attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
    )
    world.add_government(city_gov)
    city_govs[city.id] = city_gov

# ---------------------------------------------------------------------------
# 6. Utility weights + IG initialisation
# ---------------------------------------------------------------------------

weight_rng = random.Random(271)
for agent in world.politicians.values():
    agent.attributes["utility_weights"] = perturb_weights(weight_rng)

initialize_local_variables(world)

total_agents = len(world.politicians)

# ---------------------------------------------------------------------------
# 7. Print initial state
# ---------------------------------------------------------------------------

def _seat_summary(legislature: Legislature) -> str:
    counts: Counter = Counter(m.party.name for m in legislature.members)
    return ", ".join(f"{name[:3]}: {n}" for name, n in counts.most_common())


def print_gov_header(place: Place, gov: Government, indent: str = "") -> None:
    holder = gov.executive.holder
    exec_str = f"{holder.name} ({holder.party.name})" if holder else "vacant"
    tier = place.tier.name
    print(f"{indent}[{tier}] {place.name}")
    print(f"{indent}  Executive: {exec_str}")
    if gov.legislature:
        seats = _seat_summary(gov.legislature)
        print(f"{indent}  Legislature ({gov.legislature.total_seats} seats): {seats}")


print("=" * 75)
print("CASCADIA FEDERATION — FULL FEDERAL SIMULATION")
print("  Tiers: Federal → 3 States → 13 Cities")
print(f"  Parties: {', '.join(p.name for p in ALL_PARTIES)}")
print(f"  Politicians: {total_agents}")
print(f"  Turns: {NUM_TURNS} ({NUM_TURNS // ELECTION_INTERVAL} election epochs)")
print("=" * 75)

print("\n--- Federal ---")
print_gov_header(federation, fed_gov, "  ")

for state in ALL_STATES:
    print(f"\n--- {state.name} ---")
    print_gov_header(state, state_govs[state.id], "  ")
    cities = [c for c in ALL_CITIES if c.parent is state]
    for city in cities:
        print_gov_header(city, city_govs[city.id], "    ")

# ---------------------------------------------------------------------------
# 8. Run simulation
# ---------------------------------------------------------------------------

print("\n" + "=" * 75)
print(f"Running {NUM_TURNS} turns across all {total_agents} politicians…")
print("(verbose log → simulation.log)")
print("=" * 75 + "\n")

sim_rng = random.Random(42)
reports = run_simulation(world, num_turns=NUM_TURNS, rng=sim_rng, debug=True)

# ---------------------------------------------------------------------------
# 9. Final state report
# ---------------------------------------------------------------------------

print("\n" + "=" * 75)
print("FINAL STATE")
print("=" * 75)

# Federal
print("\n--- Federal ---")
print_gov_header(federation, fed_gov, "  ")

# States + cities
for state in ALL_STATES:
    print(f"\n--- {state.name} ---")
    print_gov_header(state, state_govs[state.id], "  ")
    cities = [c for c in ALL_CITIES if c.parent is state]
    for city in cities:
        print_gov_header(city, city_govs[city.id], "    ")

# IG satisfaction heatmap
print("\n--- Interest Group Satisfaction by State ---")
header = f"  {'IG':35s}"
for state in ALL_STATES:
    header += f"  {state.name[:9]:9s}"
print(header)
for ig in ALL_IGs:
    row = f"  {ig.name:35s}"
    for state in ALL_STATES:
        sat = ig.satisfaction.get(state, ig.satisfaction.get(list(ig.satisfaction.keys())[0], 0.5) if ig.satisfaction else 0.5)
        # Average satisfaction across cities in this state
        cities_in_state = [c for c in ALL_CITIES if c.parent is state]
        city_sats = [ig.satisfaction.get(c, 0.5) for c in cities_in_state if c in ig.satisfaction]
        avg_sat = sum(city_sats) / len(city_sats) if city_sats else 0.5
        row += f"  {avg_sat:9.2f}"
    print(row)

# Party leadership summary
print("\n--- Party Leadership ---")
for party in ALL_PARTIES:
    leader = party.get_leader()
    whip_list = party.get_by_role(PartyRole.WHIP)
    leader_str = f"{leader.name} ({leader.place.name})" if leader else "vacant"
    whip_str = (", ".join(f"{w.name} ({w.place.name})" for w in whip_list)
                if whip_list else "none")
    print(f"  {party.name:18s}  Leader: {leader_str:35s}  Whip: {whip_str}")

# Party seat totals across all levels
print("\n--- Party Seat Totals (all levels) ---")
seat_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
for gov in world.governments.values():
    if gov.legislature:
        tier = gov.place.tier.name
        for m in gov.legislature.members:
            seat_counts[m.party.name][tier] += 1

tiers = ["FEDERAL", "STATE", "MUNICIPALITY"]
print(f"  {'Party':20s}" + "".join(f"  {t[:5]:>7s}" for t in tiers) + "  TOTAL")
for party in ALL_PARTIES:
    counts = seat_counts[party.name]
    total = sum(counts.values())
    row = f"  {party.name:20s}"
    for tier in tiers:
        row += f"  {counts.get(tier, 0):7d}"
    row += f"  {total:5d}"
    print(row)

# Turn-by-turn event count summary
print("\n--- Simulation Summary ---")
votes_passed = votes_failed = elections = 0
for report in reports:
    for vr in report.vote_results:
        if vr.passed:
            votes_passed += 1
        else:
            votes_failed += 1
    elections += len(report.election_results)
print(f"  Elections held:    {elections}")
print(f"  Votes passed:      {votes_passed}")
print(f"  Votes failed:      {votes_failed}")
print(f"  Total actions:     {sum(len(r.actions_taken) for r in reports)}")
print(f"  Total events:      {sum(len(r.events) for r in reports)}")
