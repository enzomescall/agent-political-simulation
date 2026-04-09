"""
visualize_sim3.py
Runs the Cascadia Federation simulation and generates 21 visualizations + animated GIF.
Each run outputs into visualizations/{YYYYMMDD_HHMMSS}/.
"""
from __future__ import annotations

import logging
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.models import (
    Agent, Government, Ideology, InterestGroup, Legislature,
    Office, OfficeType, Party, Place, World,
    AgentId, InterestGroupId, PartyId, PlaceId,
    PlaceTier, Archetype, DetailLevel, PartyRole,
)
from src.actions.utility import perturb_weights
from src.simulation import initialize_local_variables, run_turn

try:
    from PIL import Image as _PIL_Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

plt.style.use("seaborn-v0_8-whitegrid")

# Suppress simulation logging
logging.getLogger("simulation").setLevel(logging.CRITICAL)

# Timestamped output directory
_RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = os.path.join("visualizations", _RUN_TS)
os.makedirs(OUT_DIR, exist_ok=True)
EPOCH_DIR = os.path.join(OUT_DIR, "ideological_epochs")
os.makedirs(EPOCH_DIR, exist_ok=True)
print(f"Output directory: {OUT_DIR}")

# Party colors
PARTY_COLORS = {
    "Labor Front":     "#C0392B",
    "Civic Democrats": "#2980B9",
    "Reform Alliance": "#E67E22",
    "Green Future":    "#27AE60",
}

# ==========================================================================
# WORLD SETUP (copied exactly from sim_test3.py)
# ==========================================================================

ELECTION_INTERVAL = 5
NUM_TURNS = ELECTION_INTERVAL * 3  # 3 full epochs = 15

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

ironfield = Place(
    id=PlaceId("ironfield"), name="Ironfield", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={workers: 0.45, business: 0.25, veterans: 0.15,
                               farmers: 0.10, youth: 0.05},
)
verdana = Place(
    id=PlaceId("verdana"), name="Verdana", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={farmers: 0.50, business: 0.20, veterans: 0.15,
                              workers: 0.10, youth: 0.05},
)
pacifica = Place(
    id=PlaceId("pacifica"), name="Pacifica", tier=PlaceTier.STATE, parent=federation,
    interest_group_presence={youth: 0.30, enviro: 0.25, business: 0.25,
                              workers: 0.15, veterans: 0.05},
)

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

# Federal government
pres = _make_agent(
    federation, OfficeType.PRESIDENT, civic, MASTER_RNG,
    detail_level=DetailLevel.L0,
    name="Eleanor Marsh",
    party_role=PartyRole.LEADER,
    econ_override=-0.05, soc_override=0.30,
)
_used_names.add("Eleanor Marsh")
world.add_politician(pres)

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

# State governments
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

# City governments
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

# Utility weights + IG initialisation
weight_rng = random.Random(271)
for agent in world.politicians.values():
    agent.attributes["utility_weights"] = perturb_weights(weight_rng)

initialize_local_variables(world)

print(f"World built: {len(world.politicians)} politicians, {len(world.governments)} governments")

# ==========================================================================
# SIMULATION RUN — capturing data each turn
# ==========================================================================

def avg_popularity(agent: Agent) -> float:
    """Return the mean popularity across all IGs."""
    vals = list(agent.popularity.values())
    return sum(vals) / len(vals) if vals else 0.0

def snapshot_seats(world: World) -> dict[str, dict[str, int]]:
    """Returns {tier_name -> {party_name -> seat_count}}."""
    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for gov in world.governments.values():
        if gov.legislature:
            tier = gov.place.tier.name
            for m in gov.legislature.members:
                result[tier][m.party.name] += 1
    return {k: dict(v) for k, v in result.items()}

def snapshot_ig_satisfaction(world: World) -> dict[str, dict[str, float]]:
    """Returns {ig_name -> {state_name -> avg_satisfaction}}."""
    result: dict[str, dict[str, float]] = {}
    for ig in ALL_IGs:
        state_avgs: dict[str, float] = {}
        for state in ALL_STATES:
            cities = [c for c in ALL_CITIES if c.parent is state]
            city_sats = [ig.satisfaction.get(c, 0.5) for c in cities]
            state_avgs[state.name] = sum(city_sats) / len(city_sats) if city_sats else 0.5
        result[ig.name] = state_avgs
    return result

def snapshot_agent_standing(world: World) -> dict[str, dict[str, list[float]]]:
    """Returns {party_name -> {agent_id -> [standing, avg_popularity]}}."""
    result: dict[str, list[dict]] = defaultdict(list)
    for agent in world.politicians.values():
        result[agent.party.name].append({
            "id": agent.id,
            "name": agent.name,
            "standing": agent.party_standing,
            "avg_pop": avg_popularity(agent),
        })
    return dict(result)

# Key agents to track
KEY_AGENT_NAMES = ["Eleanor Marsh", "Bernard Holloway", "Jerome Nakamura", "Margaret Tillson"]

# Initial state capture (turn 0 = before any simulation)
initial_agents_data: dict[str, dict] = {}
for agent in world.politicians.values():
    initial_agents_data[agent.id] = {
        "name": agent.name,
        "party": agent.party.name,
        "econ": agent.ideology["economic"],
        "soc": agent.ideology["social"],
        "archetype": agent.archetype,
        "office": agent.office,
        "standing": agent.party_standing,
        "avg_pop": avg_popularity(agent),
    }

# Track over time
history_seats: list[dict[str, dict[str, int]]] = []  # per turn
history_ig_sat: list[dict[str, dict[str, float]]] = []  # per turn
history_standing: list[dict[str, list[dict]]] = []  # per turn
history_key_agents: dict[str, list[float | None]] = {n: [] for n in KEY_AGENT_NAMES}  # name -> [pop per turn]

# NEW: extended tracking
history_agent_ideologies: dict[str, list[tuple[float, float]]] = defaultdict(list)  # id -> [(econ,soc)]
history_exec_holders: dict[str, list[tuple[str, str]]] = defaultdict(list)  # place_id -> [(name,party)]
history_party_leaders: dict[str, list[str]] = defaultdict(list)  # party_id -> [leader_name]
history_party_ideologies: dict[str, list[tuple[float, float]]] = defaultdict(list)  # party_id -> [(econ,soc)]
history_ig_ideologies: dict[str, list[tuple[float, float]]] = defaultdict(list)  # ig_name -> [(econ,soc)]
history_agent_party_standing: dict[str, list[float]] = defaultdict(list)  # id -> [standing]
history_veto_counts: list[tuple[int, int]] = []  # per turn: (vetoed, overrides)
history_exec_actions: list[dict[str, int]] = []  # per turn: {action_type_name: count}
history_agent_offices: dict[str, list] = defaultdict(list)  # id -> [office_type or None]
history_party_total_seats: dict[str, list[int]] = defaultdict(list)  # party_name -> [seats per turn]

def snapshot_extended(world: "World", report=None) -> None:
    """Capture extended per-turn state into history structures."""
    # Agent ideologies, standing, offices
    for agent in world.politicians.values():
        aid = agent.id
        history_agent_ideologies[aid].append(
            (agent.ideology["economic"], agent.ideology["social"])
        )
        history_agent_party_standing[aid].append(agent.party_standing)
        history_agent_offices[aid].append(agent.office)

    # Executive holders per place
    for place_id, gov in world.governments.items():
        if gov.executive and gov.executive.holder:
            h = gov.executive.holder
            history_exec_holders[place_id].append((h.name, h.party.name))
        else:
            history_exec_holders[place_id].append(("vacant", ""))

    # Party leaders per party
    for party_id, party in world.parties.items():
        leaders = [a for a, role in party.members.items() if role.name == "LEADER"]
        if leaders:
            history_party_leaders[party_id].append(leaders[0].name)
        else:
            history_party_leaders[party_id].append("none")

    # Party ideologies
    for party_id, party in world.parties.items():
        history_party_ideologies[party_id].append(
            (party.ideology["economic"], party.ideology["social"])
        )

    # IG ideologies
    for ig in ALL_IGs:
        history_ig_ideologies[ig.name].append(
            (ig.ideology["economic"], ig.ideology["social"])
        )

    # Party total seats across all tiers
    seat_counts: dict[str, int] = defaultdict(int)
    for gov in world.governments.values():
        if gov.legislature:
            for m in gov.legislature.members:
                seat_counts[m.party.name] += 1
    for pname in [p.name for p in ALL_PARTIES]:
        history_party_total_seats[pname].append(seat_counts.get(pname, 0))

    # Veto counts from report
    if report is not None:
        vetoed = sum(1 for vr in report.vote_results if vr.vetoed)
        overrides = sum(1 for vr in report.vote_results if vr.veto_override)
        history_veto_counts.append((vetoed, overrides))
    else:
        history_veto_counts.append((0, 0))

    # Executive agent actions this turn
    from src.actions.base import ActionType as _AT
    exec_action_types = [
        _AT.REQUEST_VOTE, _AT.CAMPAIGN, _AT.BUILD_RELATIONSHIP,
        _AT.TAKE_POSITION, _AT.ENFORCE_DISCIPLINE,
        _AT.IDEOLOGY_PUSH, _AT.PARTY_OUTREACH, _AT.PARTY_MERGE,
    ]
    exec_office_types = {OfficeType.PRESIDENT, OfficeType.GOVERNOR, OfficeType.MAYOR}
    turn_exec_actions: dict[str, int] = defaultdict(int)
    if report is not None:
        for action in report.actions_taken:
            if action.actor.office in exec_office_types:
                turn_exec_actions[action.action_type.name] += 1
    history_exec_actions.append(dict(turn_exec_actions))


# Capture turn-0 snapshot
history_seats.append(snapshot_seats(world))
history_ig_sat.append(snapshot_ig_satisfaction(world))
history_standing.append(snapshot_agent_standing(world))
for name in KEY_AGENT_NAMES:
    agent_obj = next((a for a in world.politicians.values() if a.name == name), None)
    history_key_agents[name].append(avg_popularity(agent_obj) if agent_obj else None)
snapshot_extended(world, report=None)

# Run simulation turn-by-turn
sim_rng = random.Random(42)
all_reports = []

print(f"Running {NUM_TURNS} turns...")
for t in range(NUM_TURNS):
    report = run_turn(world, sim_rng)
    all_reports.append(report)

    # Capture after each turn
    history_seats.append(snapshot_seats(world))
    history_ig_sat.append(snapshot_ig_satisfaction(world))
    history_standing.append(snapshot_agent_standing(world))
    for name in KEY_AGENT_NAMES:
        agent_obj = next((a for a in world.politicians.values() if a.name == name), None)
        history_key_agents[name].append(avg_popularity(agent_obj) if agent_obj else None)
    snapshot_extended(world, report=report)

print(f"Simulation complete. {len(all_reports)} reports collected.")

# ==========================================================================
# VIZ 1: Ideological Landscape
# ==========================================================================
print("Generating viz 1/21: Ideological Landscape...")

fig, ax = plt.subplots(figsize=(12, 9))

# Quadrant shading
ax.axhspan(0, 1, xmin=0.5, xmax=1, alpha=0.04, color="blue", zorder=0)
ax.axhspan(0, 1, xmin=0, xmax=0.5, alpha=0.04, color="red", zorder=0)
ax.axhspan(-1, 0, xmin=0, xmax=0.5, alpha=0.04, color="brown", zorder=0)
ax.axhspan(-1, 0, xmin=0.5, xmax=1, alpha=0.04, color="green", zorder=0)

ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
ax.axvline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)

archetype_markers = {
    Archetype.LOYALIST: "o",
    Archetype.POPULIST: "s",
    Archetype.IDEOLOGUE: "^",
}
office_sizes = {
    OfficeType.PRESIDENT: 200,
    OfficeType.GOVERNOR: 200,
    OfficeType.MAYOR: 200,
    OfficeType.CONGRESSPERSON: 80,
    OfficeType.STATE_ASSEMBLYPERSON: 80,
    OfficeType.COUNCILPERSON: 40,
    None: 40,
}

for archetype, marker in archetype_markers.items():
    for party in ALL_PARTIES:
        color = PARTY_COLORS[party.name]
        agents_subset = [
            d for d in initial_agents_data.values()
            if d["party"] == party.name and d["archetype"] == archetype
        ]
        if not agents_subset:
            continue
        xs = [d["econ"] for d in agents_subset]
        ys = [d["soc"] for d in agents_subset]
        sizes = [office_sizes.get(d["office"], 40) for d in agents_subset]
        ax.scatter(xs, ys, c=color, marker=marker, s=sizes, alpha=0.7, edgecolors="white", linewidths=0.4, zorder=3)

# Party centroids
for party in ALL_PARTIES:
    color = PARTY_COLORS[party.name]
    agents_subset = [d for d in initial_agents_data.values() if d["party"] == party.name]
    if not agents_subset:
        continue
    cx = np.mean([d["econ"] for d in agents_subset])
    cy = np.mean([d["soc"] for d in agents_subset])
    ax.scatter(cx, cy, c=color, marker="*", s=400, edgecolors="black", linewidths=1.0, zorder=5)
    ax.annotate(party.name, (cx, cy), textcoords="offset points", xytext=(6, 6),
                fontsize=8, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

# Legend
party_patches = [mpatches.Patch(color=PARTY_COLORS[p.name], label=p.name) for p in ALL_PARTIES]
archetype_handles = [
    plt.Line2D([0], [0], marker="o", color="gray", linestyle="None", markersize=8, label="LOYALIST"),
    plt.Line2D([0], [0], marker="s", color="gray", linestyle="None", markersize=8, label="POPULIST"),
    plt.Line2D([0], [0], marker="^", color="gray", linestyle="None", markersize=8, label="IDEOLOGUE"),
]
size_handles = [
    plt.Line2D([0], [0], marker="o", color="gray", linestyle="None", markersize=14, label="Executive (200)"),
    plt.Line2D([0], [0], marker="o", color="gray", linestyle="None", markersize=9, label="Legislative (80)"),
    plt.Line2D([0], [0], marker="o", color="gray", linestyle="None", markersize=6, label="None (40)"),
]
ax.legend(handles=party_patches + archetype_handles + size_handles,
          loc="upper right", fontsize=8, framealpha=0.9)

ax.set_xlim(-1.1, 1.1)
ax.set_ylim(-1.1, 1.1)
ax.set_xlabel("Economic Axis (Left ← → Right)", fontsize=11)
ax.set_ylabel("Social Axis (Conservative ← → Progressive)", fontsize=11)
ax.set_title("Ideological Landscape — All 119 Politicians (Initial State)", fontsize=14, fontweight="bold")
ax.text(-1.05, 1.05, "Progressive\nLeft", fontsize=8, color="gray", va="top")
ax.text(0.55, 1.05, "Progressive\nRight", fontsize=8, color="gray", va="top")
ax.text(-1.05, -1.05, "Conservative\nLeft", fontsize=8, color="gray", va="bottom")
ax.text(0.55, -1.05, "Conservative\nRight", fontsize=8, color="gray", va="bottom")

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "01_ideological_landscape.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 2: Seat Evolution
# ==========================================================================
print("Generating viz 2/21: Seat Evolution...")

fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
tier_names = ["FEDERAL", "STATE", "MUNICIPALITY"]
tier_labels = ["Federal (Congress, 12 seats)", "State (Assemblies)", "Municipal (Councils)"]

turns_x = list(range(NUM_TURNS + 1))  # 0..15

for ax_idx, (tier, label) in enumerate(zip(tier_names, tier_labels)):
    ax = axes[ax_idx]
    for party in ALL_PARTIES:
        ys = []
        for snap in history_seats:
            tier_data = snap.get(tier, {})
            ys.append(tier_data.get(party.name, 0))
        ax.plot(turns_x, ys, color=PARTY_COLORS[party.name], linewidth=2.5, label=party.name, marker="o", markersize=4)

    # Election epoch markers
    for epoch_turn in [5, 10, 15]:
        ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6)
        ax.text(epoch_turn + 0.1, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 1,
                f"Election\n(T{epoch_turn})", fontsize=7, va="top", color="black", alpha=0.7)

    ax.set_ylabel("Seats", fontsize=10)
    ax.set_title(label, fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xticks(turns_x)

axes[-1].set_xlabel("Turn", fontsize=11)
fig.suptitle("Seat Distribution Evolution — All Tiers", fontsize=14, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "02_seat_evolution.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 3: Vote Dynamics
# ==========================================================================
print("Generating viz 3/21: Vote Dynamics...")

# Collect per-turn vote counts
turn_passed = []
turn_failed = []
for report in all_reports:
    p = sum(1 for vr in report.vote_results if vr.passed)
    f = sum(1 for vr in report.vote_results if not vr.passed)
    turn_passed.append(p)
    turn_failed.append(f)

turns_x = list(range(1, NUM_TURNS + 1))

# Cumulative pass rate
cum_pass = np.cumsum(turn_passed)
cum_total = np.cumsum([p + f for p, f in zip(turn_passed, turn_failed)])
cum_rate = [cum_pass[i] / cum_total[i] if cum_total[i] > 0 else 0.0 for i in range(len(cum_total))]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Stacked bar
ax1.bar(turns_x, turn_passed, color="#27AE60", label="Passed", alpha=0.85)
ax1.bar(turns_x, turn_failed, bottom=turn_passed, color="#C0392B", label="Failed", alpha=0.85)
for epoch_turn in [5, 10, 15]:
    ax1.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6)
ax1.set_ylabel("Number of Votes", fontsize=10)
ax1.set_title("Votes Per Turn (Passed vs Failed)", fontsize=12, fontweight="bold")
ax1.legend(fontsize=9)
ax1.set_xticks(turns_x)

# Cumulative pass rate line
ax2.plot(turns_x, [r * 100 for r in cum_rate], color="#2980B9", linewidth=2.5, marker="o", markersize=5)
ax2.axhline(50, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="50% threshold")
for epoch_turn in [5, 10, 15]:
    ax2.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6)
ax2.set_ylabel("Cumulative Pass Rate (%)", fontsize=10)
ax2.set_xlabel("Turn", fontsize=11)
ax2.set_title("Cumulative Vote Pass Rate", fontsize=12, fontweight="bold")
ax2.set_ylim(0, 100)
ax2.legend(fontsize=9)
ax2.set_xticks(turns_x)

fig.suptitle("Legislative Vote Dynamics", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "03_vote_dynamics.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 4: Policy Success
# ==========================================================================
print("Generating viz 4/21: Policy Success...")

policy_proposed: dict[str, int] = defaultdict(int)
policy_passed: dict[str, int] = defaultdict(int)

for report in all_reports:
    for vr in report.vote_results:
        name = vr.policy.name
        policy_proposed[name] += 1
        if vr.passed:
            policy_passed[name] += 1

# Sort by total proposed, top 15
sorted_policies = sorted(policy_proposed.items(), key=lambda x: x[1], reverse=True)[:15]

fig, ax = plt.subplots(figsize=(12, 8))

policy_names = [p[0] for p in sorted_policies]
totals = [p[1] for p in sorted_policies]
passed_counts = [policy_passed.get(p[0], 0) for p in sorted_policies]

y_pos = np.arange(len(policy_names))
ax.barh(y_pos, totals, color="lightgray", alpha=0.9, label="Total Proposed", height=0.6)
ax.barh(y_pos, passed_counts, color="#27AE60", alpha=0.85, label="Passed", height=0.6)

# Pass rate text
for i, (total, passed) in enumerate(zip(totals, passed_counts)):
    rate = passed / total * 100 if total > 0 else 0
    ax.text(total + 0.1, i, f"{rate:.0f}%", va="center", fontsize=8, color="#2C3E50")

ax.set_yticks(y_pos)
ax.set_yticklabels([n[:40] for n in policy_names], fontsize=8)
ax.set_xlabel("Count", fontsize=11)
ax.set_title("Top 15 Policy Names — Proposed vs Passed", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.invert_yaxis()

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "04_policy_success.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 5: IG Satisfaction
# ==========================================================================
print("Generating viz 5/21: IG Satisfaction...")

# Compute overall avg satisfaction per IG per turn (average across all states)
# history_ig_sat: list of {ig_name -> {state_name -> avg}}
ig_names = [ig.name for ig in ALL_IGs]
ig_colors = plt.cm.tab10(np.linspace(0, 0.9, len(ig_names)))

fig, ax = plt.subplots(figsize=(14, 7))

turns_x = list(range(NUM_TURNS + 1))  # 0..15

for ig_idx, ig_name in enumerate(ig_names):
    avg_sats = []
    for snap in history_ig_sat:
        state_vals = list(snap.get(ig_name, {}).values())
        avg_sats.append(sum(state_vals) / len(state_vals) if state_vals else 0.5)
    ax.plot(turns_x, avg_sats, color=ig_colors[ig_idx], linewidth=2.5, label=ig_name,
            marker="o", markersize=4)

ax.axhline(0.5, color="gray", linestyle="--", linewidth=1.2, alpha=0.7, label="Neutral (0.5)")

for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)
    ax.text(epoch_turn + 0.1, 0.98, f"T{epoch_turn}", fontsize=8, va="top", color="black", alpha=0.7)

ax.set_xlim(-0.3, NUM_TURNS + 0.3)
ax.set_ylim(0, 1.0)
ax.set_xticks(turns_x)
ax.set_xlabel("Turn", fontsize=11)
ax.set_ylabel("Average Satisfaction (0–1)", fontsize=11)
ax.set_title("Interest Group Satisfaction Over Time\n(averaged across states)", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "05_ig_satisfaction.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 6: Election Heatmap (Legislative)
# ==========================================================================
print("Generating viz 6/21: Election Heatmap...")

# Collect all legislative election results
leg_elections = []
for report in all_reports:
    for er in report.election_results:
        if er.election_type == "legislative":
            leg_elections.append({
                "turn": report.turn,
                "epoch": (report.turn - 1) // ELECTION_INTERVAL + 1,
                "place": er.place.name,
                "vote_shares": er.vote_shares,
            })

if not leg_elections:
    # Create empty figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.text(0.5, 0.5, "No legislative elections found", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Legislative Election Vote Shares (Heatmap)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "06_election_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close()
else:
    party_names = [p.name for p in ALL_PARTIES]
    row_labels = [f"T{e['turn']} {e['place']}" for e in leg_elections]
    
    # Build matrix
    matrix = np.zeros((len(leg_elections), len(party_names)))
    for i, elec in enumerate(leg_elections):
        for j, pname in enumerate(party_names):
            matrix[i, j] = elec["vote_shares"].get(pname, 0.0) * 100

    fig, ax = plt.subplots(figsize=(max(10, len(party_names) * 2), max(6, len(leg_elections) * 0.6 + 2)))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=60)

    ax.set_xticks(range(len(party_names)))
    ax.set_xticklabels(party_names, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)

    # Annotate cells
    for i in range(len(leg_elections)):
        for j in range(len(party_names)):
            val = matrix[i, j]
            text_color = "white" if val > 35 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center", fontsize=7, color=text_color)

    # Epoch separator lines
    epoch_breaks = []
    for idx in range(1, len(leg_elections)):
        if leg_elections[idx]["epoch"] != leg_elections[idx-1]["epoch"]:
            epoch_breaks.append(idx - 0.5)
    for ypos in epoch_breaks:
        ax.axhline(ypos, color="red", linewidth=1.5, linestyle="--", alpha=0.7)

    plt.colorbar(im, ax=ax, label="Vote Share (%)", shrink=0.6)
    ax.set_title("Legislative Election Vote Shares by Place and Party\n(grouped by epoch; red lines = epoch boundaries)", 
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "06_election_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close()

# ==========================================================================
# VIZ 7: Popularity Trajectories
# ==========================================================================
print("Generating viz 7/21: Popularity Trajectories...")

# Key agent initial party colors
key_agent_parties = {}
for agent in world.politicians.values():
    if agent.name in KEY_AGENT_NAMES:
        key_agent_parties[agent.name] = agent.party.name

fig, ax = plt.subplots(figsize=(14, 7))

turns_x = list(range(NUM_TURNS + 1))

for name in KEY_AGENT_NAMES:
    pops = history_key_agents[name]  # list of float|None, length NUM_TURNS+1
    party_name = key_agent_parties.get(name, "Civic Democrats")
    color = PARTY_COLORS.get(party_name, "#555555")

    # Build x and y arrays skipping None
    xs = [t for t, v in zip(turns_x, pops) if v is not None]
    ys = [v for v in pops if v is not None]
    if xs:
        ax.plot(xs, ys, color=color, linewidth=2.5, label=f"{name} ({party_name})",
                marker="o", markersize=5)
        # Mark if agent left simulation (line stops before end)
        if len(xs) < len(turns_x):
            ax.annotate("left sim", (xs[-1], ys[-1]), textcoords="offset points",
                        xytext=(5, 5), fontsize=7, color=color, alpha=0.7)

for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)

ax.set_xlim(-0.3, NUM_TURNS + 0.3)
ax.set_ylim(0, 1.0)
ax.set_xticks(turns_x)
ax.set_xlabel("Turn", fontsize=11)
ax.set_ylabel("Average Popularity (mean across IGs)", fontsize=11)
ax.set_title("Popularity Trajectories — Key Executives Over Time", fontsize=13, fontweight="bold")
ax.legend(fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "07_popularity_trajectories.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 8: Party Discipline
# ==========================================================================
print("Generating viz 8/21: Party Discipline...")

# 3 time points: turn 0, turn 7, turn 14
time_points = [0, 7, 14]
time_labels = [f"Turn {t}" for t in time_points]
party_names = [p.name for p in ALL_PARTIES]

# Extract standings at each time point
data_by_time: list[dict[str, list[float]]] = []
for tp in time_points:
    snap = history_standing[tp]
    tp_data: dict[str, list[float]] = {}
    for pname in party_names:
        agents_in_party = snap.get(pname, [])
        tp_data[pname] = [a["standing"] for a in agents_in_party]
    data_by_time.append(tp_data)

fig, ax = plt.subplots(figsize=(14, 7))

n_parties = len(party_names)
n_times = len(time_points)
group_width = 0.8
box_width = group_width / n_times
spacing = 1.2

positions = []
all_boxes = []
all_colors = []
xtick_positions = []
xtick_labels = []

for p_idx, pname in enumerate(party_names):
    group_center = p_idx * spacing
    xtick_positions.append(group_center)
    xtick_labels.append(pname)
    for t_idx, (tp_data, tlabel) in enumerate(zip(data_by_time, time_labels)):
        pos = group_center - group_width/2 + box_width/2 + t_idx * box_width
        standings = tp_data.get(pname, [0.5])
        all_boxes.append(standings)
        positions.append(pos)
        color = PARTY_COLORS[pname]
        # lighten for earlier time points
        alpha_vals = [0.4, 0.7, 1.0]
        all_colors.append((color, alpha_vals[t_idx]))

bp = ax.boxplot(all_boxes, positions=positions, widths=box_width * 0.85,
                patch_artist=True, medianprops=dict(color="black", linewidth=2))

for patch, (color, alpha) in zip(bp["boxes"], all_colors):
    patch.set_facecolor(color)
    patch.set_alpha(alpha)

# Legend for time points
legend_handles = []
alpha_vals = [0.4, 0.7, 1.0]
for t_idx, tlabel in enumerate(time_labels):
    legend_handles.append(mpatches.Patch(facecolor="gray", alpha=alpha_vals[t_idx], label=tlabel))
ax.legend(handles=legend_handles, fontsize=9, loc="upper right")

ax.set_xticks(xtick_positions)
ax.set_xticklabels(xtick_labels, fontsize=10)
ax.set_ylabel("Party Standing (0=rebel, 1=loyal)", fontsize=11)
ax.set_ylim(0, 1.1)
ax.set_title("Party Discipline Distribution — Standing Scores at 3 Time Points", fontsize=13, fontweight="bold")
ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.5)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "08_party_discipline.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 9: Action Breakdown
# ==========================================================================
print("Generating viz 9/21: Action Breakdown...")

from src.actions.base import ActionType

action_type_labels = {
    # VOTE excluded — it dominates and obscures real decisions
    ActionType.REQUEST_VOTE: "REQUEST_VOTE",
    ActionType.CAMPAIGN: "CAMPAIGN",
    ActionType.BUILD_RELATIONSHIP: "BUILD_RELATIONSHIP",
    ActionType.TAKE_POSITION: "TAKE_POSITION",
    ActionType.ENFORCE_DISCIPLINE: "ENFORCE_DISCIPLINE",
    ActionType.EXPEL_MEMBER: "EXPEL_MEMBER",
    ActionType.IDEOLOGY_PUSH: "IDEOLOGY_PUSH",
    ActionType.PARTY_OUTREACH: "PARTY_OUTREACH",
    ActionType.PARTY_MERGE: "PARTY_MERGE",
}

defined_types = list(action_type_labels.keys())
party_action_counts: dict[str, dict[str, int]] = {p.name: defaultdict(int) for p in ALL_PARTIES}

for report in all_reports:
    for action in report.actions_taken:
        party_name = action.actor.party.name
        atype = action.action_type
        if atype in action_type_labels:
            label = action_type_labels[atype]
        else:
            label = "other"
        if party_name in party_action_counts:
            party_action_counts[party_name][label] += 1

# Build percentage matrix
all_labels = [action_type_labels[t] for t in defined_types] + ["other"]
party_names = [p.name for p in ALL_PARTIES]

# percentage matrix: party × action_type
pct_matrix = []
for pname in party_names:
    counts = party_action_counts[pname]
    total = sum(counts.values())
    if total == 0:
        pct_matrix.append([0.0] * len(all_labels))
    else:
        pct_matrix.append([counts.get(lbl, 0) / total * 100 for lbl in all_labels])

fig, ax = plt.subplots(figsize=(14, 6))

colors_cycle = plt.cm.Set3(np.linspace(0, 1, len(all_labels)))
y_pos = np.arange(len(party_names))
lefts = np.zeros(len(party_names))

for lbl_idx, (lbl, color) in enumerate(zip(all_labels, colors_cycle)):
    widths = [pct_matrix[pi][lbl_idx] for pi in range(len(party_names))]
    bars = ax.barh(y_pos, widths, left=lefts, color=color, label=lbl, height=0.6, alpha=0.9)
    lefts += np.array(widths)

ax.set_yticks(y_pos)
ax.set_yticklabels(party_names, fontsize=10)
ax.set_xlabel("Percentage of Actions (%)", fontsize=11)
ax.set_xlim(0, 100)
ax.set_title("Action Type Breakdown by Party (Normalized)", fontsize=13, fontweight="bold")
ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "09_action_breakdown.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 10: Agent Stories
# ==========================================================================
print("Generating viz 10/21: Agent Stories...")

# Panel 1: Top Policy Proposers (passed policies)
proposer_counts: dict[str, int] = defaultdict(int)
proposer_party: dict[str, str] = {}
for report in all_reports:
    for vr in report.vote_results:
        if vr.passed and vr.proposer is not None:
            name = vr.proposer.name
            proposer_counts[name] += 1
            proposer_party[name] = vr.proposer.party.name

top_proposers = sorted(proposer_counts.items(), key=lambda x: x[1], reverse=True)[:10]

# Panel 2: Executive Election Champions
exec_wins: dict[str, int] = defaultdict(int)
exec_winner_party: dict[str, str] = {}
for report in all_reports:
    for er in report.election_results:
        if er.election_type == "executive":
            for winner in er.winners:
                exec_wins[winner.name] += 1
                exec_winner_party[winner.name] = winner.party.name

top_exec_winners = sorted(exec_wins.items(), key=lambda x: x[1], reverse=True)[:10]

# Panel 3: Popularity Titans — final avg popularity
final_snap = history_standing[-1]
final_pops = []
for pname, agents in final_snap.items():
    for a in agents:
        final_pops.append((a["name"], a["avg_pop"], pname))
top_popular = sorted(final_pops, key=lambda x: x[1], reverse=True)[:10]

# Panel 4: Party Loyalty Leaders — final party standing
final_standings = []
for pname, agents in final_snap.items():
    for a in agents:
        final_standings.append((a["name"], a["standing"], pname))
top_loyal = sorted(final_standings, key=lambda x: x[1], reverse=True)[:10]

# Panel 5: Biggest Popularity Gains (turn 0 to final)
initial_snap = history_standing[0]
initial_pop_map: dict[str, float] = {}
initial_party_map: dict[str, str] = {}
for pname, agents in initial_snap.items():
    for a in agents:
        initial_pop_map[a["name"]] = a["avg_pop"]
        initial_party_map[a["name"]] = pname

pop_gains = []
for pname, agents in final_snap.items():
    for a in agents:
        if a["name"] in initial_pop_map:
            gain = a["avg_pop"] - initial_pop_map[a["name"]]
            pop_gains.append((a["name"], gain, pname))

top_gainers = sorted(pop_gains, key=lambda x: x[1], reverse=True)[:10]

# Build composite figure
fig = plt.figure(figsize=(18, 20))
gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.35)

ax1 = fig.add_subplot(gs[0, 0])  # top-left
ax2 = fig.add_subplot(gs[0, 1])  # top-right
ax3 = fig.add_subplot(gs[1, 0])  # mid-left
ax4 = fig.add_subplot(gs[1, 1])  # mid-right
ax5 = fig.add_subplot(gs[2, :])  # bottom (full width)

def party_colors_list(names_parties):
    return [PARTY_COLORS.get(p, "#888888") for _, _, p in names_parties]

# P1
if top_proposers:
    names1 = [n for n, c in top_proposers]
    counts1 = [c for n, c in top_proposers]
    colors1 = [PARTY_COLORS.get(proposer_party.get(n, ""), "#888888") for n in names1]
    ax1.barh(range(len(names1)), counts1, color=colors1, alpha=0.85)
    ax1.set_yticks(range(len(names1)))
    ax1.set_yticklabels([n[:25] for n in names1], fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("Passed Policies Proposed", fontsize=9)
else:
    ax1.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax1.transAxes)
ax1.set_title("Top Policy Proposers\n(Passed Policies)", fontsize=10, fontweight="bold")

# P2
if top_exec_winners:
    names2 = [n for n, c in top_exec_winners]
    counts2 = [c for n, c in top_exec_winners]
    colors2 = [PARTY_COLORS.get(exec_winner_party.get(n, ""), "#888888") for n in names2]
    ax2.barh(range(len(names2)), counts2, color=colors2, alpha=0.85)
    ax2.set_yticks(range(len(names2)))
    ax2.set_yticklabels([n[:25] for n in names2], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("Executive Election Wins", fontsize=9)
else:
    ax2.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax2.transAxes)
ax2.set_title("Executive Election Champions", fontsize=10, fontweight="bold")

# P3
if top_popular:
    names3 = [n for n, v, p in top_popular]
    vals3 = [v for n, v, p in top_popular]
    colors3 = party_colors_list(top_popular)
    ax3.barh(range(len(names3)), vals3, color=colors3, alpha=0.85)
    ax3.set_yticks(range(len(names3)))
    ax3.set_yticklabels([n[:25] for n in names3], fontsize=8)
    ax3.invert_yaxis()
    ax3.set_xlabel("Avg Popularity (Final)", fontsize=9)
    ax3.set_xlim(0, 1)
else:
    ax3.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax3.transAxes)
ax3.set_title("Popularity Titans\n(Highest Final Avg Popularity)", fontsize=10, fontweight="bold")

# P4
if top_loyal:
    names4 = [n for n, v, p in top_loyal]
    vals4 = [v for n, v, p in top_loyal]
    colors4 = party_colors_list(top_loyal)
    ax4.barh(range(len(names4)), vals4, color=colors4, alpha=0.85)
    ax4.set_yticks(range(len(names4)))
    ax4.set_yticklabels([n[:25] for n in names4], fontsize=8)
    ax4.invert_yaxis()
    ax4.set_xlabel("Party Standing (Final)", fontsize=9)
    ax4.set_xlim(0, 1)
else:
    ax4.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax4.transAxes)
ax4.set_title("Party Loyalty Leaders\n(Highest Final Party Standing)", fontsize=10, fontweight="bold")

# P5
if top_gainers:
    names5 = [n for n, v, p in top_gainers]
    vals5 = [v for n, v, p in top_gainers]
    colors5 = party_colors_list(top_gainers)
    bars5 = ax5.bar(range(len(names5)), vals5, color=colors5, alpha=0.85)
    ax5.set_xticks(range(len(names5)))
    ax5.set_xticklabels([n[:20] for n in names5], rotation=30, ha="right", fontsize=8)
    ax5.axhline(0, color="black", linewidth=0.8)
    ax5.set_ylabel("Popularity Gain", fontsize=9)
else:
    ax5.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax5.transAxes)
ax5.set_title("Biggest Popularity Gains (Turn 0 → Final)", fontsize=10, fontweight="bold")

# Party color legend (shared)
party_patches = [mpatches.Patch(color=PARTY_COLORS[p.name], label=p.name) for p in ALL_PARTIES]
fig.legend(handles=party_patches, loc="upper center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, 1.01))

fig.suptitle("Agent Stories — Key Performance Stats", fontsize=15, fontweight="bold", y=1.03)

plt.savefig(os.path.join(OUT_DIR, "10_agent_stories.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 11: Executive Actions Over Time
# ==========================================================================
print("Generating viz 11/21: Executive Actions Over Time...")

from src.actions.base import ActionType as _AT_ALL

exec_action_names = [
    "REQUEST_VOTE", "CAMPAIGN", "BUILD_RELATIONSHIP", "TAKE_POSITION",
    "ENFORCE_DISCIPLINE", "IDEOLOGY_PUSH", "PARTY_OUTREACH", "PARTY_MERGE",
]
turns_x = list(range(1, NUM_TURNS + 1))
exec_colors = plt.cm.tab10(np.linspace(0, 0.9, len(exec_action_names)))

fig, ax = plt.subplots(figsize=(14, 6))
bottoms = np.zeros(NUM_TURNS)
for aname, color in zip(exec_action_names, exec_colors):
    counts = [history_exec_actions[t].get(aname, 0) for t in range(NUM_TURNS)]
    ax.bar(turns_x, counts, bottom=bottoms, color=color, label=aname, alpha=0.85)
    bottoms += np.array(counts)

for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6)
ax.set_xlabel("Turn", fontsize=11)
ax.set_ylabel("Actions Taken", fontsize=11)
ax.set_title("Executive Agent Actions Over Time (PRESIDENT, GOVERNOR, MAYOR)", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
ax.set_xticks(turns_x)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "11_exec_actions_over_time.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 12: Executive Gantt Chart (Federal + State)
# ==========================================================================
print("Generating viz 12/21: Executive Timeline (Gantt)...")

gantt_places = [federation] + ALL_STATES  # President + 3 Governors
place_ids = [p.id for p in gantt_places]
place_labels = [p.name for p in gantt_places]

fig, ax = plt.subplots(figsize=(16, 5))

# history_exec_holders has turns 0..NUM_TURNS (inclusive, NUM_TURNS+1 entries)
all_party_names_seen = set()
for row_idx, place_id in enumerate(place_ids):
    turns_holders = history_exec_holders[place_id]  # list of (name, party)
    if not turns_holders:
        continue
    seg_start = 0
    seg_name, seg_party = turns_holders[0]
    for t_idx in range(1, len(turns_holders) + 1):
        if t_idx == len(turns_holders) or turns_holders[t_idx] != (seg_name, seg_party):
            color = PARTY_COLORS.get(seg_party, "#888888")
            ax.broken_barh([(seg_start, t_idx - seg_start)], (row_idx - 0.4, 0.8),
                           facecolors=color, alpha=0.85, edgecolors="white", linewidth=0.5)
            mid = seg_start + (t_idx - seg_start) / 2
            if t_idx - seg_start >= 2:
                ax.text(mid, row_idx, seg_name.split()[-1], ha="center", va="center",
                        fontsize=7, fontweight="bold", color="white")
            all_party_names_seen.add(seg_party)
            if t_idx < len(turns_holders):
                seg_start = t_idx
                seg_name, seg_party = turns_holders[t_idx]

for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.6)

ax.set_yticks(range(len(place_labels)))
ax.set_yticklabels(place_labels, fontsize=10)
ax.set_xlabel("Turn", fontsize=11)
ax.set_xlim(0, NUM_TURNS + 1)
ax.set_xticks(list(range(NUM_TURNS + 1)))
ax.set_title("Executive Office Holders Over Time (Federal + State)", fontsize=13, fontweight="bold")
party_patches_gantt = [
    mpatches.Patch(color=PARTY_COLORS.get(pname, "#888888"), label=pname)
    for pname in sorted(all_party_names_seen)
]
ax.legend(handles=party_patches_gantt, loc="upper right", fontsize=9, framealpha=0.9)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "12_exec_timeline.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 13: Party Popularity Over Time
# ==========================================================================
print("Generating viz 13/21: Party Popularity...")

# Party popularity = sum(ig.satisfaction[state] * party.base_constituency.get(ig, 0))
#                   averaged across states per turn
# We use history_ig_sat to reconstruct

def compute_party_popularity_from_ig(party: Party, ig_sat_snap: dict) -> float:
    """Approx party popularity given IG satisfaction snapshot."""
    total_weight = 0.0
    total_pop = 0.0
    for ig_name, state_avgs in ig_sat_snap.items():
        ig_obj = next((i for i in ALL_IGs if i.name == ig_name), None)
        if ig_obj is None:
            continue
        affinity = party.base_constituency.get(ig_obj, 0.0)
        if affinity < 0.05:
            continue
        avg_sat = sum(state_avgs.values()) / len(state_avgs) if state_avgs else 0.5
        total_pop += affinity * avg_sat
        total_weight += affinity
    return total_pop / total_weight if total_weight > 0 else 0.5

fig, ax = plt.subplots(figsize=(14, 7))
turns_x2 = list(range(NUM_TURNS + 1))
for party in ALL_PARTIES:
    pops = [compute_party_popularity_from_ig(party, snap) for snap in history_ig_sat]
    ax.plot(turns_x2, pops, color=PARTY_COLORS[party.name], linewidth=2.5,
            label=party.name, marker="o", markersize=4)
for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.5)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6)
ax.set_xticks(turns_x2)
ax.set_ylim(0.2, 0.9)
ax.set_xlabel("Turn", fontsize=11)
ax.set_ylabel("Party Popularity (IG-weighted)", fontsize=11)
ax.set_title("Party Popularity Over Time", fontsize=13, fontweight="bold")
ax.legend(fontsize=9, framealpha=0.9)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "13_party_popularity.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 14: Agent Mobility (net office-tier change)
# ==========================================================================
print("Generating viz 14/21: Mobility...")

TIER_RANK = {
    None: 0,
    OfficeType.COUNCILPERSON: 1,
    OfficeType.STATE_ASSEMBLYPERSON: 2,
    OfficeType.CONGRESSPERSON: 3,
    OfficeType.MAYOR: 2,
    OfficeType.GOVERNOR: 3,
    OfficeType.PRESIDENT: 4,
}

mobility_data = []
for agent in world.politicians.values():
    offices = history_agent_offices.get(agent.id, [])
    if len(offices) < 2:
        continue
    first_rank = TIER_RANK.get(offices[0], 0)
    last_rank = TIER_RANK.get(offices[-1], 0)
    net = last_rank - first_rank
    if net != 0:
        mobility_data.append((agent.name, net, agent.party.name))

mobility_data.sort(key=lambda x: x[1], reverse=True)
if not mobility_data:
    # create empty
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.text(0.5, 0.5, "No office mobility detected", ha="center", va="center",
            transform=ax.transAxes, fontsize=12)
else:
    fig, ax = plt.subplots(figsize=(max(10, len(mobility_data) * 0.7 + 2), 6))
    names_m = [x[0] for x in mobility_data]
    vals_m = [x[1] for x in mobility_data]
    colors_m = [PARTY_COLORS.get(x[2], "#888888") for x in mobility_data]
    bars_m = ax.bar(range(len(names_m)), vals_m, color=colors_m, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(names_m)))
    ax.set_xticklabels([n.split()[-1] for n in names_m], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Net Office Tier Change", fontsize=11)
    # party legend
    party_patches_m = [mpatches.Patch(color=PARTY_COLORS[p.name], label=p.name) for p in ALL_PARTIES]
    ax.legend(handles=party_patches_m, fontsize=9, loc="upper right")

ax.set_title("Agent Office Mobility (Turn 0 → Final, +upward / −downward)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "14_mobility.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 15: Party Seat Share Stacked Area
# ==========================================================================
print("Generating viz 15/21: Party Seat Share...")

turns_x3 = list(range(NUM_TURNS + 1))
fig, ax = plt.subplots(figsize=(14, 6))
# Compute total seats per turn
total_seats_per_turn = []
for t in range(NUM_TURNS + 1):
    total = sum(history_party_total_seats[p.name][t] for p in ALL_PARTIES
                if len(history_party_total_seats[p.name]) > t)
    total_seats_per_turn.append(total if total > 0 else 1)

prev_bottom = np.zeros(NUM_TURNS + 1)
for party in ALL_PARTIES:
    raw = [history_party_total_seats[party.name][t]
           if len(history_party_total_seats[party.name]) > t else 0
           for t in range(NUM_TURNS + 1)]
    pct = np.array(raw) / np.array(total_seats_per_turn) * 100
    ax.fill_between(turns_x3, prev_bottom, prev_bottom + pct,
                    alpha=0.75, color=PARTY_COLORS[party.name], label=party.name)
    prev_bottom = prev_bottom + pct

for epoch_turn in [5, 10, 15]:
    ax.axvline(epoch_turn, color="white", linewidth=2, linestyle=":", alpha=0.8)
ax.set_xticks(turns_x3)
ax.set_ylim(0, 100)
ax.set_xlabel("Turn", fontsize=11)
ax.set_ylabel("% of Total Seats", fontsize=11)
ax.set_title("Party Seat Share (All Tiers Combined) — Stacked Area", fontsize=13, fontweight="bold")
ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "15_party_seat_share.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 16: Party Leadership Timeline
# ==========================================================================
print("Generating viz 16/21: Party Leadership Timeline...")

fig, axes16 = plt.subplots(len(ALL_PARTIES), 1, figsize=(16, 3 * len(ALL_PARTIES)), sharex=True)
if len(ALL_PARTIES) == 1:
    axes16 = [axes16]

turns_x4 = list(range(NUM_TURNS + 2))  # 0..NUM_TURNS inclusive
for ax16, party in zip(axes16, ALL_PARTIES):
    leaders_list = history_party_leaders.get(party.id, [])
    if not leaders_list:
        ax16.set_yticks([])
        ax16.set_title(party.name, fontsize=10, fontweight="bold")
        continue
    color = PARTY_COLORS[party.name]
    seg_start = 0
    seg_leader = leaders_list[0]
    # Collect all unique leaders for y-axis
    unique_leaders = list(dict.fromkeys(leaders_list))
    leader_y = {ldr: i for i, ldr in enumerate(unique_leaders)}

    for t_idx in range(1, len(leaders_list) + 1):
        cur = leaders_list[t_idx] if t_idx < len(leaders_list) else None
        if cur != seg_leader:
            y_pos = leader_y[seg_leader]
            ax16.broken_barh([(seg_start, t_idx - seg_start)], (y_pos - 0.4, 0.8),
                             facecolors=color, alpha=0.85, edgecolors="white", linewidth=0.5)
            mid = seg_start + (t_idx - seg_start) / 2
            ax16.text(mid, y_pos, seg_leader.split()[-1], ha="center", va="center",
                      fontsize=7, fontweight="bold", color="white")
            seg_start = t_idx
            seg_leader = cur if cur else seg_leader

    ax16.set_yticks(list(leader_y.values()))
    ax16.set_yticklabels([ldr.split()[-1] for ldr in unique_leaders], fontsize=8)
    ax16.set_title(party.name, fontsize=10, fontweight="bold", color=color)
    for epoch_turn in [5, 10, 15]:
        ax16.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)

axes16[-1].set_xlabel("Turn", fontsize=11)
axes16[-1].set_xticks(list(range(NUM_TURNS + 1)))
fig.suptitle("Party Leadership Timelines", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "16_party_leadership_timeline.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 17: Party Discipline Heatmap (agent × turn)
# ==========================================================================
print("Generating viz 17/21: Party Discipline Heatmap...")

# Sort agents by party then by initial standing
sorted_agents_for_heatmap = sorted(
    world.politicians.values(),
    key=lambda a: (a.party.name, -a.party_standing)
)
agent_ids_hmap = [a.id for a in sorted_agents_for_heatmap]

# Build matrix: rows=agents, cols=turns
n_agents_h = len(agent_ids_hmap)
n_turns_h = NUM_TURNS + 1
matrix_h = np.full((n_agents_h, n_turns_h), 0.5)
for row_idx, aid in enumerate(agent_ids_hmap):
    standings = history_agent_party_standing.get(aid, [])
    for t_idx, val in enumerate(standings[:n_turns_h]):
        matrix_h[row_idx, t_idx] = val

fig17, ax17 = plt.subplots(figsize=(max(14, n_turns_h * 0.8), max(8, n_agents_h * 0.18)))
im17 = ax17.imshow(matrix_h, aspect="auto", cmap="RdYlGn", vmin=0.0, vmax=1.0,
                   interpolation="nearest")
plt.colorbar(im17, ax=ax17, label="Party Standing (0=rebel, 1=loyal)", shrink=0.6)

# Party boundary lines
prev_party = None
for row_idx, a in enumerate(sorted_agents_for_heatmap):
    if prev_party is not None and a.party.name != prev_party:
        ax17.axhline(row_idx - 0.5, color="black", linewidth=2)
    prev_party = a.party.name

# Party name annotations on left side
party_start = 0
prev_party_name = sorted_agents_for_heatmap[0].party.name
for row_idx, a in enumerate(sorted_agents_for_heatmap):
    if a.party.name != prev_party_name or row_idx == n_agents_h - 1:
        mid_row = (party_start + row_idx - 1) / 2
        ax17.text(-1.5, mid_row, prev_party_name[:8], ha="right", va="center",
                  fontsize=7, fontweight="bold",
                  color=PARTY_COLORS.get(prev_party_name, "black"))
        party_start = row_idx
        prev_party_name = a.party.name

ax17.set_xticks(list(range(n_turns_h)))
ax17.set_xticklabels(list(range(n_turns_h)), fontsize=8)
ax17.set_yticks(list(range(n_agents_h)))
ax17.set_yticklabels([a.name.split()[-1] for a in sorted_agents_for_heatmap], fontsize=6)
for epoch_turn in [5, 10, 15]:
    ax17.axvline(epoch_turn, color="black", linewidth=1.5, linestyle=":", alpha=0.7)
ax17.set_xlabel("Turn", fontsize=11)
ax17.set_title("Party Discipline Heatmap — All Agents × Turns (green=loyal, red=rebel)",
               fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "17_party_discipline_heatmap.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 18: Party Ideology Drift
# ==========================================================================
print("Generating viz 18/21: Party Ideology Drift...")

fig18, (ax18a, ax18b) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
turns_x5 = list(range(NUM_TURNS + 1))

for party in ALL_PARTIES:
    color = PARTY_COLORS[party.name]
    pid = party.id
    econs = [history_party_ideologies[pid][t][0] if len(history_party_ideologies[pid]) > t else 0
             for t in range(NUM_TURNS + 1)]
    socs = [history_party_ideologies[pid][t][1] if len(history_party_ideologies[pid]) > t else 0
            for t in range(NUM_TURNS + 1)]
    ax18a.plot(turns_x5, econs, color=color, linewidth=2.5, label=party.name, marker="o", markersize=4)
    ax18b.plot(turns_x5, socs, color=color, linewidth=2.5, label=party.name, marker="^", markersize=4)

for epoch_turn in [5, 10, 15]:
    ax18a.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)
    ax18b.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)

ax18a.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
ax18b.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
ax18a.set_ylabel("Economic Axis", fontsize=11)
ax18b.set_ylabel("Social Axis", fontsize=11)
ax18b.set_xlabel("Turn", fontsize=11)
ax18b.set_xticks(turns_x5)
ax18a.set_ylim(-1.1, 1.1)
ax18b.set_ylim(-1.1, 1.1)
ax18a.legend(fontsize=9, framealpha=0.9)
ax18b.legend(fontsize=9, framealpha=0.9)
fig18.suptitle("Party Ideology Centroid Drift Over Time", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "18_party_ideology_drift.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 19: Veto Analysis
# ==========================================================================
print("Generating viz 19/21: Veto Analysis...")

turns_x6 = list(range(1, NUM_TURNS + 1))
vetoed_counts = [history_veto_counts[t][0] for t in range(NUM_TURNS)]
override_counts = [history_veto_counts[t][1] for t in range(NUM_TURNS)]

fig19, ax19 = plt.subplots(figsize=(12, 5))
x19 = np.arange(NUM_TURNS)
w19 = 0.35
ax19.bar(x19 - w19 / 2, vetoed_counts, width=w19, color="#C0392B", alpha=0.85, label="Vetoes")
ax19.bar(x19 + w19 / 2, override_counts, width=w19, color="#27AE60", alpha=0.85, label="Override Attempts")

for epoch_turn in [5, 10, 15]:
    ax19.axvline(epoch_turn - 1, color="black", linewidth=1.5, linestyle=":", alpha=0.6)

ax19.set_xticks(list(range(NUM_TURNS)))
ax19.set_xticklabels([f"T{t + 1}" for t in range(NUM_TURNS)], fontsize=8)
ax19.set_xlabel("Turn", fontsize=11)
ax19.set_ylabel("Count", fontsize=11)
ax19.set_title("Executive Vetoes and Legislature Override Attempts Per Turn", fontsize=13, fontweight="bold")
ax19.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "19_veto_analysis.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 20: Ideology Drift — Key Agents
# ==========================================================================
print("Generating viz 20/21: Ideology Drift (Agents)...")

fig20, (ax20a, ax20b) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
turns_x7 = list(range(NUM_TURNS + 1))

key_agent_objs = [a for a in world.politicians.values() if a.name in KEY_AGENT_NAMES]
colors20 = plt.cm.Set1(np.linspace(0, 0.8, len(key_agent_objs)))

for agent_obj, color20 in zip(key_agent_objs, colors20):
    ideo_hist = history_agent_ideologies.get(agent_obj.id, [])
    if not ideo_hist:
        continue
    econs20 = [v[0] for v in ideo_hist]
    socs20 = [v[1] for v in ideo_hist]
    ts20 = list(range(len(ideo_hist)))
    label20 = f"{agent_obj.name} ({agent_obj.party.name})"
    ax20a.plot(ts20, econs20, color=color20, linewidth=2.5, label=label20, marker="o", markersize=4)
    ax20b.plot(ts20, socs20, color=color20, linewidth=2.5, label=label20, marker="^", markersize=4)

for epoch_turn in [5, 10, 15]:
    ax20a.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)
    ax20b.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)

ax20a.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
ax20b.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
ax20a.set_ylabel("Economic Axis", fontsize=11)
ax20b.set_ylabel("Social Axis", fontsize=11)
ax20b.set_xlabel("Turn", fontsize=11)
ax20b.set_xticks(turns_x7)
ax20a.set_ylim(-1.1, 1.1)
ax20b.set_ylim(-1.1, 1.1)
ax20a.legend(fontsize=9, framealpha=0.9, loc="upper right")
ax20b.legend(fontsize=9, framealpha=0.9, loc="upper right")
fig20.suptitle("Ideology Drift — Key Executive Agents", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "20_ideology_drift_agents.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 21: IG Radicalization
# ==========================================================================
print("Generating viz 21/21: IG Radicalization...")

fig21, (ax21a, ax21b) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
turns_x8 = list(range(NUM_TURNS + 1))
ig_colors21 = plt.cm.tab10(np.linspace(0, 0.9, len(ALL_IGs)))

for ig_obj, color21 in zip(ALL_IGs, ig_colors21):
    ig_name = ig_obj.name
    # Satisfaction over time
    sat_series = []
    for snap in history_ig_sat:
        state_vals = list(snap.get(ig_name, {}).values())
        sat_series.append(sum(state_vals) / len(state_vals) if state_vals else 0.5)
    ax21a.plot(turns_x8, sat_series, color=color21, linewidth=2, label=ig_name, marker="o", markersize=4)

    # Ideology extremism = sqrt(econ^2 + soc^2) over time
    ideo_hist21 = history_ig_ideologies.get(ig_name, [])
    if ideo_hist21:
        extremism = [np.sqrt(e**2 + s**2) for e, s in ideo_hist21]
        ax21b.plot(range(len(extremism)), extremism, color=color21, linewidth=2,
                   label=ig_name, marker="s", markersize=4)

ax21a.axhline(0.25, color="red", linewidth=1.5, linestyle="--", alpha=0.7, label="Radicalization threshold (0.25)")
ax21a.axhline(0.5, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
for epoch_turn in [5, 10, 15]:
    ax21a.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)
    ax21b.axvline(epoch_turn, color="black", linewidth=1, linestyle=":", alpha=0.5)

ax21a.set_ylabel("Avg Satisfaction (0–1)", fontsize=11)
ax21b.set_ylabel("Ideology Extremism (L2 norm)", fontsize=11)
ax21b.set_xlabel("Turn", fontsize=11)
ax21b.set_xticks(turns_x8)
ax21a.set_ylim(0, 1.0)
ax21a.legend(fontsize=7, ncol=2, framealpha=0.9, loc="upper right")
ax21b.legend(fontsize=7, ncol=2, framealpha=0.9, loc="upper right")
fig21.suptitle("Interest Group Radicalization: Satisfaction & Ideology Extremism",
               fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "21_ig_radicalization.png"), dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# EPOCH SNAPSHOTS: Ideological Landscape at elections (turns 5, 10, 15)
# ==========================================================================
print("Generating epoch ideological snapshots + animated GIF...")

EPOCH_TURNS = [0, 5, 10, 15]  # epoch_0 = initial, epoch_1..3 = post-election

def _snapshot_elected_ideologies(world: "World", turn_idx: int) -> list[dict]:
    """Return per-agent data for agents with an office at the given turn snapshot index."""
    data = []
    for aid, agent in world.politicians.items():
        ideo_list = history_agent_ideologies.get(aid, [])
        office_list = history_agent_offices.get(aid, [])
        if turn_idx >= len(ideo_list):
            continue
        office_at_turn = office_list[turn_idx] if turn_idx < len(office_list) else None
        econ, soc = ideo_list[turn_idx]
        data.append({
            "name": agent.name,
            "party": agent.party.name,
            "econ": econ,
            "soc": soc,
            "office": office_at_turn,
            "is_exec": office_at_turn in {OfficeType.PRESIDENT, OfficeType.GOVERNOR, OfficeType.MAYOR},
        })
    return data

epoch_png_paths = []
for epoch_idx, turn_idx in enumerate(EPOCH_TURNS):
    epoch_data = _snapshot_elected_ideologies(world, turn_idx)
    elected = [d for d in epoch_data if d["office"] is not None]
    if not elected:
        elected = epoch_data[:30]  # fallback

    fig_e, ax_e = plt.subplots(figsize=(10, 8))
    ax_e.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax_e.axvline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)

    for d in elected:
        color_e = PARTY_COLORS.get(d["party"], "#888888")
        size_e = 200 if d["is_exec"] else 60
        marker_e = "*" if d["is_exec"] else "o"
        ax_e.scatter(d["econ"], d["soc"], c=color_e, s=size_e, marker=marker_e,
                     alpha=0.8, edgecolors="white", linewidths=0.4, zorder=3)
        if d["is_exec"]:
            ax_e.annotate(d["name"].split()[-1], (d["econ"], d["soc"]),
                          textcoords="offset points", xytext=(5, 5),
                          fontsize=7, color=color_e, fontweight="bold")

    ax_e.set_xlim(-1.1, 1.1)
    ax_e.set_ylim(-1.1, 1.1)
    ax_e.set_xlabel("Economic Axis (Left ← → Right)", fontsize=10)
    ax_e.set_ylabel("Social Axis (Conservative ← → Progressive)", fontsize=10)
    epoch_label = f"Initial State" if epoch_idx == 0 else f"After Election {epoch_idx} (Turn {turn_idx})"
    ax_e.set_title(f"Ideological Landscape — Elected Officials\nEpoch {epoch_idx}: {epoch_label}",
                   fontsize=12, fontweight="bold")

    party_patches_e = [mpatches.Patch(color=PARTY_COLORS[p.name], label=p.name) for p in ALL_PARTIES]
    exec_patch = plt.Line2D([0], [0], marker="*", color="gray", linestyle="None", markersize=12, label="Executive")
    leg_patch = plt.Line2D([0], [0], marker="o", color="gray", linestyle="None", markersize=8, label="Legislative")
    ax_e.legend(handles=party_patches_e + [exec_patch, leg_patch], fontsize=8, loc="upper right", framealpha=0.9)

    plt.tight_layout()
    out_path = os.path.join(EPOCH_DIR, f"epoch_{epoch_idx}.png")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    epoch_png_paths.append(out_path)
    print(f"  Saved {out_path}")

# Build animated GIF if PIL is available
if _HAS_PIL and epoch_png_paths:
    frames = [_PIL_Image.open(p).convert("RGB") for p in epoch_png_paths]
    gif_path = os.path.join(EPOCH_DIR, "animated.gif")
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=1500,
        loop=0,
    )
    print(f"  Animated GIF saved to {gif_path}")
else:
    if not _HAS_PIL:
        print("  (Pillow not installed — skipping animated GIF)")

print(f"\nDone! All visualizations saved to {OUT_DIR}/")

