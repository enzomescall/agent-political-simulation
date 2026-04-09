"""
visualize_sim3.py
Runs the Cascadia Federation simulation and generates 10 visualizations.
"""
from __future__ import annotations

import copy
import logging
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.style.use("seaborn-v0_8-whitegrid")

from src.models import (
    Agent, Government, Ideology, InterestGroup, Legislature,
    Office, OfficeType, Party, Place, World,
    AgentId, InterestGroupId, PartyId, PlaceId,
    PlaceTier, Archetype, DetailLevel, PartyRole,
)
from src.actions.utility import perturb_weights
from src.simulation import initialize_local_variables, run_turn

# Suppress simulation logging
logging.getLogger("simulation").setLevel(logging.CRITICAL)

# Output directory
os.makedirs("visualizations", exist_ok=True)

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

# Capture turn-0 snapshot
history_seats.append(snapshot_seats(world))
history_ig_sat.append(snapshot_ig_satisfaction(world))
history_standing.append(snapshot_agent_standing(world))
for name in KEY_AGENT_NAMES:
    agent_obj = next((a for a in world.politicians.values() if a.name == name), None)
    history_key_agents[name].append(avg_popularity(agent_obj) if agent_obj else None)

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

print(f"Simulation complete. {len(all_reports)} reports collected.")

# ==========================================================================
# VIZ 1: Ideological Landscape
# ==========================================================================
print("Generating viz 1/10: Ideological Landscape...")

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
plt.savefig("visualizations/01_ideological_landscape.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 2: Seat Evolution
# ==========================================================================
print("Generating viz 2/10: Seat Evolution...")

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
plt.savefig("visualizations/02_seat_evolution.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 3: Vote Dynamics
# ==========================================================================
print("Generating viz 3/10: Vote Dynamics...")

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
plt.savefig("visualizations/03_vote_dynamics.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 4: Policy Success
# ==========================================================================
print("Generating viz 4/10: Policy Success...")

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
plt.savefig("visualizations/04_policy_success.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 5: IG Satisfaction
# ==========================================================================
print("Generating viz 5/10: IG Satisfaction...")

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
plt.savefig("visualizations/05_ig_satisfaction.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 6: Election Heatmap (Legislative)
# ==========================================================================
print("Generating viz 6/10: Election Heatmap...")

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
    plt.savefig("visualizations/06_election_heatmap.png", dpi=150, bbox_inches="tight")
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
    plt.savefig("visualizations/06_election_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()

# ==========================================================================
# VIZ 7: Popularity Trajectories
# ==========================================================================
print("Generating viz 7/10: Popularity Trajectories...")

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
plt.savefig("visualizations/07_popularity_trajectories.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 8: Party Discipline
# ==========================================================================
print("Generating viz 8/10: Party Discipline...")

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
plt.savefig("visualizations/08_party_discipline.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 9: Action Breakdown
# ==========================================================================
print("Generating viz 9/10: Action Breakdown...")

from src.actions.base import ActionType

action_type_labels = {
    ActionType.VOTE: "VOTE",
    ActionType.REQUEST_VOTE: "REQUEST_VOTE",
    ActionType.CAMPAIGN: "CAMPAIGN",
    ActionType.BUILD_RELATIONSHIP: "BUILD_RELATIONSHIP",
    ActionType.TAKE_POSITION: "TAKE_POSITION",
    ActionType.ENFORCE_DISCIPLINE: "ENFORCE_DISCIPLINE",
    ActionType.EXPEL_MEMBER: "EXPEL_MEMBER",
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
plt.savefig("visualizations/09_action_breakdown.png", dpi=150, bbox_inches="tight")
plt.close()

# ==========================================================================
# VIZ 10: Agent Stories
# ==========================================================================
print("Generating viz 10/10: Agent Stories...")

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

plt.savefig("visualizations/10_agent_stories.png", dpi=150, bbox_inches="tight")
plt.close()

print("Done! Visualizations saved to visualizations/")

