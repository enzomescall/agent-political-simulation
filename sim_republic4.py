"""
sim_republic4.py  —  Meridian Federal Republic

Structure
---------
  Federal      : President + 21-seat Congress
  State × 6    : Governor + 11-seat Assembly
    Ironfield   (industrial)   : 4 cities
    Verdana     (agricultural) : 4 cities
    Pacifica    (coastal/tech) : 4 cities
    Northwood   (rural-conservative): 4 cities
    Suncoast    (sunbelt/business)  : 4 cities
    Riverlands  (mixed farm/industry): 4 cities

  24 cities total, 5-seat councils each.

Parties (7) — full political spectrum
--------------------------------------
  Workers Vanguard   far-left: workers + youth + rural underclass
  Labor Front        center-left: workers + youth + farmers
  Green Future       green-left: enviro + youth + urban professionals
  Civic Democrats    centrist: broad moderate coalition
  Reform Alliance    center-right: business + farmers + veterans
  National Conservative  social-right: veterans + rural + farmers
  Liberty Party      libertarian: business + urban professionals

Interest Groups (8)
--------------------
  Industrial Workers Union
  Chamber of Commerce
  Agricultural Producers Guild
  Youth & Students Alliance
  Environment Network
  Veterans & Public Safety League
  Urban Professionals Coalition
  Rural Communities Alliance

Run with:  python sim_republic4.py
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

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
NUM_TURNS = ELECTION_INTERVAL * 10  # 10 election epochs = 50 turns

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
    name="Environment Network",
    fears=["deregulation", "fossil_fuel"],
)
veterans = InterestGroup(
    id=InterestGroupId("veterans"),
    name="Veterans & Public Safety League",
    fears=["military_cuts", "police_defunding"],
)
urban_prof = InterestGroup(
    id=InterestGroupId("urban_prof"),
    name="Urban Professionals Coalition",
    fears=["over_regulation", "high_taxes"],
)
rural_com = InterestGroup(
    id=InterestGroupId("rural_com"),
    name="Rural Communities Alliance",
    fears=["rural_neglect", "globalization"],
)

ALL_IGs = [workers, business, farmers, youth, enviro, veterans, urban_prof, rural_com]

# ---------------------------------------------------------------------------
# 2. Parties
# ---------------------------------------------------------------------------

vanguard = Party(
    id=PartyId("vanguard"), name="Workers Vanguard",
    ideology=Ideology.create(economic=-0.88, social=0.60),
    directive_threshold=-0.25, campaign_budget=8,
    nomination_threshold=0.15, leadership_interval=10,
    base_constituency={workers: 0.90, youth: 0.50, rural_com: 0.30},
)
labor = Party(
    id=PartyId("labor"), name="Labor Front",
    ideology=Ideology.create(economic=-0.55, social=0.35),
    directive_threshold=-0.20, campaign_budget=10,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={workers: 0.75, youth: 0.40, farmers: 0.25, rural_com: 0.20},
)
green = Party(
    id=PartyId("green"), name="Green Future",
    ideology=Ideology.create(economic=-0.35, social=0.85),
    directive_threshold=-0.15, campaign_budget=8,
    nomination_threshold=0.15, leadership_interval=10,
    base_constituency={enviro: 0.90, youth: 0.70, urban_prof: 0.35},
)
civic = Party(
    id=PartyId("civic"), name="Civic Democrats",
    ideology=Ideology.create(economic=-0.05, social=0.10),
    directive_threshold=-0.10, campaign_budget=12,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={workers: 0.35, business: 0.40, youth: 0.35,
                       farmers: 0.30, veterans: 0.35, urban_prof: 0.30},
)
reform = Party(
    id=PartyId("reform"), name="Reform Alliance",
    ideology=Ideology.create(economic=0.55, social=-0.30),
    directive_threshold=-0.20, campaign_budget=10,
    nomination_threshold=0.20, leadership_interval=10,
    base_constituency={business: 0.75, farmers: 0.50, veterans: 0.55, urban_prof: 0.25},
)
nationalist = Party(
    id=PartyId("nationalist"), name="National Conservative",
    ideology=Ideology.create(economic=0.25, social=-0.80),
    directive_threshold=-0.25, campaign_budget=9,
    nomination_threshold=0.18, leadership_interval=10,
    base_constituency={veterans: 0.75, rural_com: 0.80, farmers: 0.45},
)
liberty = Party(
    id=PartyId("liberty"), name="Liberty Party",
    ideology=Ideology.create(economic=0.88, social=0.50),
    directive_threshold=-0.15, campaign_budget=9,
    nomination_threshold=0.15, leadership_interval=10,
    base_constituency={business: 0.70, urban_prof: 0.75},
)

ALL_PARTIES = [vanguard, labor, green, civic, reform, nationalist, liberty]

# ---------------------------------------------------------------------------
# 3. Places — Federal
# ---------------------------------------------------------------------------

federation = Place(
    id=PlaceId("federation"), name="Meridian Republic", tier=PlaceTier.FEDERAL,
)

# ---------------------------------------------------------------------------
# 3a. States
# ---------------------------------------------------------------------------

ironfield = Place(
    id=PlaceId("ironfield"), name="Ironfield", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={workers: 0.40, business: 0.20, veterans: 0.15,
                              youth: 0.10, urban_prof: 0.10, rural_com: 0.05},
)
verdana = Place(
    id=PlaceId("verdana"), name="Verdana", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={farmers: 0.40, rural_com: 0.25, business: 0.15,
                              veterans: 0.15, workers: 0.05},
)
pacifica = Place(
    id=PlaceId("pacifica"), name="Pacifica", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={youth: 0.25, enviro: 0.25, business: 0.20,
                              urban_prof: 0.20, workers: 0.10},
)
northwood = Place(
    id=PlaceId("northwood"), name="Northwood", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={rural_com: 0.40, veterans: 0.30, farmers: 0.25, workers: 0.05},
)
suncoast = Place(
    id=PlaceId("suncoast"), name="Suncoast", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={business: 0.35, urban_prof: 0.30, veterans: 0.20,
                              workers: 0.10, youth: 0.05},
)
riverlands = Place(
    id=PlaceId("riverlands"), name="Riverlands", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={workers: 0.25, farmers: 0.25, rural_com: 0.25,
                              youth: 0.15, enviro: 0.10},
)

ALL_STATES = [ironfield, verdana, pacifica, northwood, suncoast, riverlands]

# ---------------------------------------------------------------------------
# 3b. Cities — Ironfield (industrial)
# ---------------------------------------------------------------------------

steelburg = Place(
    id=PlaceId("steelburg"), name="Steelburg", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.55, business: 0.20, veterans: 0.15, youth: 0.10},
)
coalton = Place(
    id=PlaceId("coalton"), name="Coalton", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.65, veterans: 0.20, business: 0.10, rural_com: 0.05},
)
millford = Place(
    id=PlaceId("millford"), name="Millford", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={workers: 0.40, business: 0.30, veterans: 0.20, youth: 0.10},
)
irondale = Place(
    id=PlaceId("irondale"), name="Irondale", tier=PlaceTier.MUNICIPALITY, parent=ironfield,
    interest_group_presence={business: 0.40, workers: 0.30, youth: 0.20, urban_prof: 0.10},
)

# ---------------------------------------------------------------------------
# Cities — Verdana (agricultural)
# ---------------------------------------------------------------------------

farmington = Place(
    id=PlaceId("farmington"), name="Farmington", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.65, rural_com: 0.20, business: 0.10, veterans: 0.05},
)
crestview = Place(
    id=PlaceId("crestview"), name="Crestview", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.50, rural_com: 0.25, veterans: 0.15, business: 0.10},
)
riverdale = Place(
    id=PlaceId("riverdale"), name="Riverdale", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={farmers: 0.40, workers: 0.25, rural_com: 0.20, youth: 0.15},
)
granville = Place(
    id=PlaceId("granville"), name="Granville", tier=PlaceTier.MUNICIPALITY, parent=verdana,
    interest_group_presence={business: 0.35, farmers: 0.30, veterans: 0.20, rural_com: 0.15},
)

# ---------------------------------------------------------------------------
# Cities — Pacifica (coastal/tech)
# ---------------------------------------------------------------------------

bayshore = Place(
    id=PlaceId("bayshore"), name="Bayshore", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={youth: 0.40, enviro: 0.35, business: 0.15, workers: 0.10},
)
harborview = Place(
    id=PlaceId("harborview"), name="Harborview", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={business: 0.35, urban_prof: 0.30, youth: 0.25, enviro: 0.10},
)
solana = Place(
    id=PlaceId("solana"), name="Solana", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={enviro: 0.50, youth: 0.35, urban_prof: 0.10, business: 0.05},
)
waverly = Place(
    id=PlaceId("waverly"), name="Waverly", tier=PlaceTier.MUNICIPALITY, parent=pacifica,
    interest_group_presence={business: 0.40, urban_prof: 0.30, workers: 0.20, youth: 0.10},
)

# ---------------------------------------------------------------------------
# Cities — Northwood (rural-conservative)
# ---------------------------------------------------------------------------

pineridge = Place(
    id=PlaceId("pineridge"), name="Pineridge", tier=PlaceTier.MUNICIPALITY, parent=northwood,
    interest_group_presence={rural_com: 0.50, veterans: 0.30, farmers: 0.20},
)
coldbrook = Place(
    id=PlaceId("coldbrook"), name="Coldbrook", tier=PlaceTier.MUNICIPALITY, parent=northwood,
    interest_group_presence={veterans: 0.40, rural_com: 0.35, farmers: 0.25},
)
hartfield = Place(
    id=PlaceId("hartfield"), name="Hartfield", tier=PlaceTier.MUNICIPALITY, parent=northwood,
    interest_group_presence={farmers: 0.45, rural_com: 0.30, veterans: 0.25},
)
maplewood = Place(
    id=PlaceId("maplewood"), name="Maplewood", tier=PlaceTier.MUNICIPALITY, parent=northwood,
    interest_group_presence={rural_com: 0.40, farmers: 0.35, veterans: 0.20, workers: 0.05},
)

# ---------------------------------------------------------------------------
# Cities — Suncoast (sunbelt/business)
# ---------------------------------------------------------------------------

palmview = Place(
    id=PlaceId("palmview"), name="Palmview", tier=PlaceTier.MUNICIPALITY, parent=suncoast,
    interest_group_presence={business: 0.45, urban_prof: 0.30, veterans: 0.15, youth: 0.10},
)
seaville = Place(
    id=PlaceId("seaville"), name="Seaville", tier=PlaceTier.MUNICIPALITY, parent=suncoast,
    interest_group_presence={urban_prof: 0.40, business: 0.35, youth: 0.15, enviro: 0.10},
)
goldport = Place(
    id=PlaceId("goldport"), name="Goldport", tier=PlaceTier.MUNICIPALITY, parent=suncoast,
    interest_group_presence={business: 0.50, urban_prof: 0.25, veterans: 0.15, workers: 0.10},
)
sunridge = Place(
    id=PlaceId("sunridge"), name="Sunridge", tier=PlaceTier.MUNICIPALITY, parent=suncoast,
    interest_group_presence={veterans: 0.35, business: 0.30, workers: 0.25, rural_com: 0.10},
)

# ---------------------------------------------------------------------------
# Cities — Riverlands (mixed farm/industry)
# ---------------------------------------------------------------------------

riverton = Place(
    id=PlaceId("riverton"), name="Riverton", tier=PlaceTier.MUNICIPALITY, parent=riverlands,
    interest_group_presence={workers: 0.40, farmers: 0.25, rural_com: 0.20, youth: 0.15},
)
millhaven = Place(
    id=PlaceId("millhaven"), name="Millhaven", tier=PlaceTier.MUNICIPALITY, parent=riverlands,
    interest_group_presence={farmers: 0.40, workers: 0.30, rural_com: 0.20, business: 0.10},
)
clearfield = Place(
    id=PlaceId("clearfield"), name="Clearfield", tier=PlaceTier.MUNICIPALITY, parent=riverlands,
    interest_group_presence={rural_com: 0.45, farmers: 0.30, veterans: 0.15, youth: 0.10},
)
ashford = Place(
    id=PlaceId("ashford"), name="Ashford", tier=PlaceTier.MUNICIPALITY, parent=riverlands,
    interest_group_presence={youth: 0.35, enviro: 0.30, workers: 0.25, rural_com: 0.10},
)

IRONFIELD_CITIES  = [steelburg, coalton, millford, irondale]
VERDANA_CITIES    = [farmington, crestview, riverdale, granville]
PACIFICA_CITIES   = [bayshore, harborview, solana, waverly]
NORTHWOOD_CITIES  = [pineridge, coldbrook, hartfield, maplewood]
SUNCOAST_CITIES   = [palmview, seaville, goldport, sunridge]
RIVERLANDS_CITIES = [riverton, millhaven, clearfield, ashford]
ALL_CITIES = (IRONFIELD_CITIES + VERDANA_CITIES + PACIFICA_CITIES +
              NORTHWOOD_CITIES + SUNCOAST_CITIES + RIVERLANDS_CITIES)

# ---------------------------------------------------------------------------
# 4. Procedural agent generation
# ---------------------------------------------------------------------------

_AGENT_COUNTER = 0


def _next_id(prefix: str) -> AgentId:
    global _AGENT_COUNTER
    _AGENT_COUNTER += 1
    return AgentId(f"{prefix}_{_AGENT_COUNTER:04d}")


_FIRST = [
    "Aaron", "Beatrice", "Carlos", "Diana", "Ethan", "Fatima", "George",
    "Helena", "Ivan", "Julia", "Kevin", "Leila", "Marco", "Naomi", "Oscar",
    "Paula", "Quinn", "Rosa", "Samuel", "Tina", "Ulrich", "Vera", "Walter",
    "Xena", "Yusuf", "Zara", "Alicia", "Brendan", "Chloe", "Derek",
    "Emma", "Felix", "Grace", "Henry", "Iris", "Jonas", "Kira", "Luca",
    "Maya", "Nolan", "Olivia", "Pedro", "Rachel", "Stefan", "Uma", "Victor",
]
_LAST = [
    "Adeyemi", "Bauer", "Chen", "Dalton", "Eriksen", "Flores", "Grant",
    "Huang", "Ibrahim", "Jensen", "Kim", "Laurent", "Mercer", "Navarro",
    "Osei", "Park", "Quinn", "Reyes", "Santos", "Thornton", "Ueda",
    "Vargas", "Walsh", "Xu", "Yilmaz", "Ziegler", "Amara", "Brooks",
    "Castillo", "Donovan", "Everett", "Ferreira", "Goldstein", "Hartley",
    "Ingram", "Johansson", "Kaur", "Lindqvist", "Moreno", "Nakamura",
]

_used_names: set[str] = set()


def _random_name(rng: random.Random) -> str:
    for _ in range(300):
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
        scores.append(max(score, 0.03))
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
    econ = (econ_override if econ_override is not None
            else max(-1.0, min(1.0, party.ideology["economic"] + rng.uniform(-0.25, 0.25))))
    soc  = (soc_override  if soc_override  is not None
            else max(-1.0, min(1.0, party.ideology["social"]   + rng.uniform(-0.25, 0.25))))

    if name is None:
        name = _random_name(rng)
    _used_names.add(name)

    allegiances: dict[InterestGroup, float] = {}
    for ig, share in place.interest_group_presence.items():
        affinity = party.base_constituency.get(ig, 0.0)
        base = affinity * 0.6 + share * 0.2
        allegiances[ig] = max(0.0, min(1.0, base + rng.uniform(-0.1, 0.1)))

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
# 5a. Federal government — President + 21-seat Congress (3 per party)
# ---------------------------------------------------------------------------

pres = _make_agent(
    federation, OfficeType.PRESIDENT, civic, MASTER_RNG,
    detail_level=DetailLevel.L0,
    name="Sophia Carrington",
    party_role=PartyRole.LEADER,
    econ_override=-0.05, soc_override=0.18,
)
_used_names.add("Sophia Carrington")
world.add_politician(pres)

_congress_rotation = [
    vanguard, labor, green, civic, reform, nationalist, liberty,
    vanguard, labor, green, civic, reform, nationalist, liberty,
    vanguard, labor, green, civic, reform, nationalist, liberty,
]
congress_members: list[Agent] = []
for party in _congress_rotation:
    m = _make_agent(federation, OfficeType.CONGRESSPERSON, party, MASTER_RNG)
    world.add_politician(m)
    congress_members.append(m)

fed_legislature = Legislature(
    place=federation, seat_type=OfficeType.CONGRESSPERSON,
    total_seats=21, members=congress_members,
)
fed_exec = Office(office_type=OfficeType.PRESIDENT, place=federation, holder=pres)
fed_gov = Government(
    place=federation, executive=fed_exec, legislature=fed_legislature,
    attributes={"election_interval": ELECTION_INTERVAL, "last_election_turn": 0},
)
world.add_government(fed_gov)

# ---------------------------------------------------------------------------
# 5b. State governments — 11-seat assemblies
# ---------------------------------------------------------------------------


@dataclass
class StateSetup:
    place: Place
    gov_name: str
    gov_party: Party
    gov_econ: float
    gov_soc: float
    assembly_seats: int
    assembly_composition: list[tuple[Party, int]]


STATE_CONFIGS = [
    StateSetup(
        place=ironfield,
        gov_name="Victor Holloway", gov_party=labor,
        gov_econ=-0.60, gov_soc=0.40,
        assembly_seats=11,
        assembly_composition=[(labor, 4), (civic, 3), (reform, 2), (vanguard, 1), (green, 1)],
    ),
    StateSetup(
        place=verdana,
        gov_name="Margaret Tillson", gov_party=reform,
        gov_econ=0.55, gov_soc=-0.28,
        assembly_seats=11,
        assembly_composition=[(reform, 4), (nationalist, 3), (civic, 2), (labor, 1), (liberty, 1)],
    ),
    StateSetup(
        place=pacifica,
        gov_name="Jerome Nakamura", gov_party=green,
        gov_econ=-0.30, gov_soc=0.80,
        assembly_seats=11,
        assembly_composition=[(green, 4), (civic, 3), (labor, 2), (reform, 1), (vanguard, 1)],
    ),
    StateSetup(
        place=northwood,
        gov_name="Robert Ashby", gov_party=nationalist,
        gov_econ=0.20, gov_soc=-0.78,
        assembly_seats=11,
        assembly_composition=[(nationalist, 5), (reform, 3), (civic, 2), (liberty, 1)],
    ),
    StateSetup(
        place=suncoast,
        gov_name="Elena Vargas", gov_party=liberty,
        gov_econ=0.85, gov_soc=0.48,
        assembly_seats=11,
        assembly_composition=[(liberty, 4), (reform, 3), (civic, 3), (nationalist, 1)],
    ),
    StateSetup(
        place=riverlands,
        gov_name="Marco Santos", gov_party=labor,
        gov_econ=-0.50, gov_soc=0.38,
        assembly_seats=11,
        assembly_composition=[(labor, 4), (vanguard, 2), (civic, 2), (green, 2), (reform, 1)],
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
# 5c. City governments — 5-seat councils + mayor
# ---------------------------------------------------------------------------

_CITY_COUNCIL_SEATS = 5
city_govs: dict[PlaceId, Government] = {}

for city in ALL_CITIES:
    mayor_party = _party_for_place(city, MASTER_RNG)
    mayor = _make_agent(
        city, OfficeType.MAYOR, mayor_party, MASTER_RNG,
        detail_level=DetailLevel.L0,
        party_role=PartyRole.MEMBER,
    )
    world.add_politician(mayor)

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
    return ", ".join(f"{name[:4]}: {n}" for name, n in counts.most_common())


def print_gov_header(place: Place, gov: Government, indent: str = "") -> None:
    holder = gov.executive.holder
    exec_str = f"{holder.name} ({holder.party.name})" if holder else "vacant"
    tier = place.tier.name
    print(f"{indent}[{tier}] {place.name}")
    print(f"{indent}  Executive: {exec_str}")
    if gov.legislature:
        seats = _seat_summary(gov.legislature)
        print(f"{indent}  Legislature ({gov.legislature.total_seats} seats): {seats}")


print("=" * 80)
print("MERIDIAN REPUBLIC — FULL SIMULATION")
print(f"  Tiers: Federal -> 6 States -> 24 Cities")
print(f"  Parties: {', '.join(p.name for p in ALL_PARTIES)}")
print(f"  Politicians: {total_agents}")
print(f"  Turns: {NUM_TURNS} ({NUM_TURNS // ELECTION_INTERVAL} election epochs)")
print("=" * 80)

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

print("\n" + "=" * 80)
print(f"Running {NUM_TURNS} turns across {total_agents} politicians…")
print("(verbose log → simulation.log)")
print("=" * 80 + "\n")

sim_rng = random.Random(42)
reports = run_simulation(world, num_turns=NUM_TURNS, rng=sim_rng, debug=True)

# ---------------------------------------------------------------------------
# 9. Final state report
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("FINAL STATE — MERIDIAN REPUBLIC")
print("=" * 80)

print("\n--- Federal ---")
print_gov_header(federation, fed_gov, "  ")

for state in ALL_STATES:
    print(f"\n--- {state.name} ---")
    print_gov_header(state, state_govs[state.id], "  ")
    cities = [c for c in ALL_CITIES if c.parent is state]
    for city in cities:
        print_gov_header(city, city_govs[city.id], "    ")

# Key agent spotlight
print("\n--- Key Agent Stories ---")
_key_agents = {
    "Sophia Carrington": "President, Civic Democrats (Federation)",
    "Victor Holloway":   "Governor, Labor Front (Ironfield)",
    "Jerome Nakamura":   "Governor, Green Future (Pacifica)",
    "Margaret Tillson":  "Governor, Reform Alliance (Verdana)",
}
for _name, _role in _key_agents.items():
    _matched = [a for a in world.politicians.values() if a.name == _name]
    if _matched:
        _a = _matched[0]
        print(f"  {_name} — {_role}")
        print(f"    Ideology: econ={_a.ideology['economic']:+.2f}, soc={_a.ideology['social']:+.2f}")
        print(f"    Party standing: {_a.party_standing:.2f}  Ambition: {_a.ambition:.2f}")
    else:
        print(f"  {_name} — {_role} [not found in world]")

# IG satisfaction
print("\n--- Interest Group Satisfaction by State ---")
header = f"  {'IG':35s}"
for state in ALL_STATES:
    header += f"  {state.name[:9]:9s}"
print(header)
for ig in ALL_IGs:
    row = f"  {ig.name:35s}"
    for state in ALL_STATES:
        cities_in_state = [c for c in ALL_CITIES if c.parent is state]
        city_sats = [ig.satisfaction.get(c, 0.5) for c in cities_in_state]
        avg_sat = sum(city_sats) / len(city_sats) if city_sats else 0.5
        row += f"  {avg_sat:9.2f}"
    print(row)

# Party leadership
print("\n--- Party Leadership ---")
for party in ALL_PARTIES:
    leader = party.get_leader()
    leader_str = f"{leader.name} ({leader.place.name})" if leader else "vacant"
    print(f"  {party.name:22s}  Leader: {leader_str}")

# Seat totals
print("\n--- Party Seat Totals (all levels) ---")
seat_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
for gov in world.governments.values():
    if gov.legislature:
        tier = gov.place.tier.name
        for m in gov.legislature.members:
            seat_counts[m.party.name][tier] += 1

tiers = ["FEDERAL", "STATE", "MUNICIPALITY"]
print(f"  {'Party':24s}" + "".join(f"  {t[:5]:>7s}" for t in tiers) + "  TOTAL")
for party in ALL_PARTIES:
    counts = seat_counts[party.name]
    total = sum(counts.values())
    row = f"  {party.name:24s}"
    for tier in tiers:
        row += f"  {counts.get(tier, 0):7d}"
    row += f"  {total:5d}"
    print(row)

# Summary
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
print(f"\n  Meridian Republic: 6 states, 24 cities, {NUM_TURNS} turns, "
      f"{NUM_TURNS // ELECTION_INTERVAL} election epochs complete.")
