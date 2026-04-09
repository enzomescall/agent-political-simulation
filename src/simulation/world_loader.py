from __future__ import annotations

import json
import random as _random
from pathlib import Path
import tomllib
from typing import Any

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
    World,
)

from .setup import initialize_local_variables

_SECTION_FILES = (
    "world",
    "interest_groups",
    "parties",
    "places",
    "agents",
    "governments",
)

# Name pools for procedural generation
_FIRST_NAMES = [
    "Aaron",
    "Beatrice",
    "Carlos",
    "Diana",
    "Ethan",
    "Fatima",
    "George",
    "Helena",
    "Ivan",
    "Julia",
    "Kevin",
    "Leila",
    "Marco",
    "Naomi",
    "Oscar",
    "Paula",
    "Quinn",
    "Rosa",
    "Samuel",
    "Tina",
    "Ulrich",
    "Vera",
    "Walter",
    "Xena",
    "Yusuf",
    "Zara",
    "Alicia",
    "Brendan",
    "Chloe",
    "Derek",
]

_LAST_NAMES = [
    "Adeyemi",
    "Bauer",
    "Chen",
    "Dalton",
    "Eriksen",
    "Flores",
    "Grant",
    "Huang",
    "Ibrahim",
    "Jensen",
    "Kim",
    "Laurent",
    "Mercer",
    "Navarro",
    "Osei",
    "Park",
    "Quinn",
    "Reyes",
    "Santos",
    "Thornton",
    "Ueda",
    "Vargas",
    "Walsh",
    "Xu",
    "Yilmaz",
    "Ziegler",
    "Amara",
    "Brooks",
    "Castillo",
    "Donovan",
]

_used_names: set[str] = set()


def load_world_from_path(path: Path) -> World:
    if path.is_dir():
        return load_world_from_directory(path)
    return load_world_from_file(path)


def load_world_from_file(path: Path) -> World:
    raw = _load_data_file(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a top-level object")
    sections = _normalize_root_sections(raw)
    world = _build_world_from_sections(sections)
    world.attributes["config_source"] = str(path)
    return world


def load_world_from_directory(path: Path) -> World:
    if not path.is_dir():
        raise ValueError(f"{path} is not a config directory")

    sections: dict[str, Any] = {
        "world": {},
        "interest_groups": [],
        "parties": [],
        "places": [],
        "agents": [],
        "governments": [],
        "generate": {},
    }
    for section in _SECTION_FILES:
        section_path = _find_section_file(path, section)
        if section_path is None:
            continue
        raw = _load_data_file(section_path)
        sections[section] = _extract_section_payload(raw, section)

    # Also check for generate section in any TOML file
    generate_path = path / "generate.toml"
    if generate_path.exists():
        raw = _load_data_file(generate_path)
        if isinstance(raw, dict) and "generate" in raw:
            sections["generate"] = raw["generate"]
        elif isinstance(raw, dict):
            # Use whole file as generate section
            sections["generate"] = raw

    world = _build_world_from_sections(sections)
    world.attributes["config_source"] = str(path)
    return world


def _find_section_file(path: Path, section: str) -> Path | None:
    matches = [
        candidate
        for candidate in (path / f"{section}.json", path / f"{section}.toml")
        if candidate.exists()
    ]
    if len(matches) > 1:
        raise ValueError(f"Multiple config files found for '{section}' in {path}")
    return matches[0] if matches else None


def _load_data_file(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text())
    if suffix == ".toml":
        return tomllib.loads(path.read_text())
    raise ValueError(f"Unsupported config file format: {path}")


def _normalize_root_sections(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "world": raw.get("world", {}),
        "interest_groups": raw.get("interest_groups", []),
        "parties": raw.get("parties", []),
        "places": raw.get("places", []),
        "agents": raw.get("agents", []),
        "governments": raw.get("governments", []),
        "generate": raw.get("generate", {}),
    }


def _extract_section_payload(raw: Any, section: str) -> Any:
    if isinstance(raw, dict) and section in raw:
        return raw[section]
    return raw


def _parse_enum(enum_cls, value: str | None, context: str):
    if value is None:
        raise ValueError(f"Missing enum value for {context}")
    try:
        return enum_cls[str(value).upper()]
    except KeyError as exc:
        allowed = ", ".join(member.name for member in enum_cls)
        raise ValueError(
            f"Invalid value '{value}' for {context}; expected one of: {allowed}"
        ) from exc


def _parse_ideology(raw: dict[str, Any]) -> Ideology:
    ideology_raw = raw.get("ideology")
    if ideology_raw is None:
        ideology_raw = {
            key: value for key, value in raw.items() if key in {"economic", "social"}
        }
    if not isinstance(ideology_raw, dict):
        raise ValueError(f"Invalid ideology payload: {ideology_raw!r}")
    return Ideology(
        axes={str(axis): float(value) for axis, value in ideology_raw.items()}
    )


def _require_reference(
    mapping: dict[str, Any], ref_id: str, section: str, field: str, owner: str
) -> Any:
    try:
        return mapping[ref_id]
    except KeyError as exc:
        raise ValueError(
            f"Unknown {field} '{ref_id}' in {section} entry '{owner}'"
        ) from exc


def _resolve_weighted_map(
    raw_map: dict[str, Any] | None,
    mapping: dict[str, Any],
    section: str,
    field: str,
    owner: str,
) -> dict[Any, float]:
    result: dict[Any, float] = {}
    for ref_id, value in (raw_map or {}).items():
        result[_require_reference(mapping, ref_id, section, field, owner)] = float(
            value
        )
    return result


def _build_world_from_sections(sections: dict[str, Any]) -> World:
    global _used_names
    _used_names = set()

    world_data = sections.get("world") or {}
    if not isinstance(world_data, dict):
        raise ValueError("Section 'world' must be an object")

    world = World(
        turn=int(world_data.get("turn", 0)),
        attributes=dict(world_data.get("attributes", {})),
    )
    if world_data.get("player_id") is not None:
        world.player_id = AgentId(str(world_data["player_id"]))

    groups_by_id: dict[str, InterestGroup] = {}
    raw_interest_groups = _ensure_list(
        sections.get("interest_groups"), "interest_groups"
    )
    for entry in raw_interest_groups:
        group = InterestGroup(
            id=InterestGroupId(str(entry["id"])),
            name=str(entry["name"]),
            fears=list(entry.get("fears", [])),
            attributes=dict(entry.get("attributes", {})),
        )
        world.add_interest_group(group)
        groups_by_id[str(group.id)] = group

    parties_by_id: dict[str, Party] = {}
    raw_parties = _ensure_list(sections.get("parties"), "parties")
    for entry in raw_parties:
        party_id = str(entry["id"])
        party = Party(
            id=PartyId(party_id),
            name=str(entry["name"]),
            ideology=_parse_ideology(entry),
            directive_threshold=float(entry.get("directive_threshold", 0.15)),
            campaign_budget=int(entry.get("campaign_budget", 3)),
            nomination_threshold=float(entry.get("nomination_threshold", 0.3)),
            leadership_interval=int(entry.get("leadership_interval", 20)),
            last_leadership_turn=int(entry.get("last_leadership_turn", 0)),
            base_constituency=_resolve_weighted_map(
                entry.get("base_constituency"),
                groups_by_id,
                "parties",
                "interest_group",
                party_id,
            ),
        )
        world.add_party(party)
        parties_by_id[party_id] = party

    places_by_id: dict[str, Place] = {}
    raw_places = _ensure_list(sections.get("places"), "places")
    for entry in raw_places:
        place_id = str(entry["id"])
        place = Place(
            id=PlaceId(place_id),
            name=str(entry["name"]),
            tier=_parse_enum(PlaceTier, entry.get("tier"), f"place '{place_id}' tier"),
            attributes=dict(entry.get("attributes", {})),
        )
        places_by_id[place_id] = place

    for entry in raw_places:
        place_id = str(entry["id"])
        place = places_by_id[place_id]
        parent_id = entry.get("parent_id")
        if parent_id is not None:
            place.parent = _require_reference(
                places_by_id, str(parent_id), "places", "parent_id", place_id
            )
        place.interest_group_presence = _resolve_weighted_map(
            entry.get("interest_group_presence"),
            groups_by_id,
            "places",
            "interest_group_presence",
            place_id,
        )
        world.add_place(place)

    # Load explicit agents (from agents.toml)
    agents_by_id: dict[str, Agent] = {}
    raw_agents = _ensure_list(sections.get("agents"), "agents")
    for entry in raw_agents:
        agent_id = str(entry["id"])
        party = _require_reference(
            parties_by_id, str(entry["party_id"]), "agents", "party_id", agent_id
        )
        place = _require_reference(
            places_by_id, str(entry["place_id"]), "agents", "place_id", agent_id
        )
        office = entry.get("office")
        agent = Agent(
            id=AgentId(agent_id),
            name=str(entry["name"]),
            ideology=_parse_ideology(entry),
            party=party,
            place=place,
            office=_parse_enum(OfficeType, office, f"agent '{agent_id}' office")
            if office
            else None,
            party_role=_parse_enum(
                PartyRole,
                entry.get("party_role", "MEMBER"),
                f"agent '{agent_id}' party_role",
            ),
            allegiances=_resolve_weighted_map(
                entry.get("allegiances"),
                groups_by_id,
                "agents",
                "allegiances",
                agent_id,
            ),
            popularity=_resolve_weighted_map(
                entry.get("popularity"),
                groups_by_id,
                "agents",
                "popularity",
                agent_id,
            ),
            party_standing=float(entry.get("party_standing", 0.5)),
            ambition=float(entry.get("ambition", 0.5)),
            archetype=_parse_enum(
                Archetype,
                entry.get("archetype", "LOYALIST"),
                f"agent '{agent_id}' archetype",
            ),
            detail_level=_parse_enum(
                DetailLevel,
                entry.get("detail_level", "L3"),
                f"agent '{agent_id}' detail_level",
            ),
            attributes=dict(entry.get("attributes", {})),
        )
        world.add_politician(agent)
        agents_by_id[agent_id] = agent
        _used_names.add(agent.name)

    for entry in raw_agents:
        agent_id = str(entry["id"])
        agent = agents_by_id[agent_id]
        agent.relationships = _resolve_weighted_map(
            entry.get("relationships"),
            agents_by_id,
            "agents",
            "relationships",
            agent_id,
        )

    for entry in raw_interest_groups:
        group_id = str(entry["id"])
        group = groups_by_id[group_id]
        group.satisfaction = _resolve_weighted_map(
            entry.get("satisfaction"),
            places_by_id,
            "interest_groups",
            "satisfaction",
            group_id,
        )
        group.electorate_share = _resolve_weighted_map(
            entry.get("electorate_share"),
            places_by_id,
            "interest_groups",
            "electorate_share",
            group_id,
        )

    # Handle procedural generation BEFORE loading explicit governments
    # This way generated agents can be linked in governments
    generate_config = sections.get("generate") or {}
    generated_agents: list[Agent] = []
    if generate_config:
        generated_agents = _generate_agents_from_config(
            world=world,
            config=generate_config,
            places_by_id=places_by_id,
            parties_by_id=parties_by_id,
            groups_by_id=groups_by_id,
            agents_by_id=agents_by_id,
        )
        # Update agents_by_id with generated agents
        for agent in generated_agents:
            agents_by_id[str(agent.id)] = agent

    # Load explicit governments (from governments.toml) - AFTER generation
    # This allows generated agents to be linked as legislature members
    raw_governments = _ensure_list(sections.get("governments"), "governments")
    for entry in raw_governments:
        place_id = str(entry["place_id"])
        place = _require_reference(
            places_by_id, place_id, "governments", "place_id", place_id
        )
        executive_raw = entry.get("executive")
        if not isinstance(executive_raw, dict):
            raise ValueError(f"Government '{place_id}' is missing an executive object")
        executive_holder = None
        if executive_raw.get("holder_id") is not None:
            executive_holder = _require_reference(
                agents_by_id,
                str(executive_raw["holder_id"]),
                "governments",
                "executive.holder_id",
                place_id,
            )
        executive = Office(
            office_type=_parse_enum(
                OfficeType,
                executive_raw.get("office_type"),
                f"government '{place_id}' executive",
            ),
            place=place,
            holder=executive_holder,
            attributes=dict(executive_raw.get("attributes", {})),
        )

        legislature = None
        legislature_raw = entry.get("legislature")
        if legislature_raw is not None:
            if not isinstance(legislature_raw, dict):
                raise ValueError(
                    f"Government '{place_id}' legislature must be an object"
                )
            # Try to get explicit members, but also include generated ones
            explicit_member_ids = legislature_raw.get("member_ids", [])
            members = [
                _require_reference(
                    agents_by_id,
                    str(member_id),
                    "governments",
                    "legislature.member_ids",
                    place_id,
                )
                for member_id in explicit_member_ids
            ]
            # Add generated agents for this place if not explicitly listed
            if not explicit_member_ids and generated_agents:
                seat_type = _parse_enum(
                    OfficeType,
                    legislature_raw.get("seat_type"),
                    f"government '{place_id}' legislature seat_type",
                )
                for agent in generated_agents:
                    if agent.place == place and agent.office == seat_type:
                        members.append(agent)

            legislature = Legislature(
                place=place,
                seat_type=_parse_enum(
                    OfficeType,
                    legislature_raw.get("seat_type"),
                    f"government '{place_id}' legislature seat_type",
                ),
                total_seats=int(legislature_raw.get("total_seats", len(members))),
                members=members,
                attributes=dict(legislature_raw.get("attributes", {})),
            )

        cabinet = []
        for office_raw in entry.get("cabinet", []):
            holder = None
            if office_raw.get("holder_id") is not None:
                holder = _require_reference(
                    agents_by_id,
                    str(office_raw["holder_id"]),
                    "governments",
                    "cabinet.holder_id",
                    place_id,
                )
            cabinet.append(
                Office(
                    office_type=_parse_enum(
                        OfficeType,
                        office_raw.get("office_type"),
                        f"government '{place_id}' cabinet office_type",
                    ),
                    place=place,
                    holder=holder,
                    attributes=dict(office_raw.get("attributes", {})),
                )
            )

        world.add_government(
            Government(
                place=place,
                executive=executive,
                cabinet=cabinet,
                legislature=legislature,
                attributes=dict(entry.get("attributes", {})),
            )
        )

    if world.player_id is not None and str(world.player_id) not in agents_by_id:
        raise ValueError(f"Unknown player_id '{world.player_id}' in world section")

    initialize_local_variables(world)
    return world


def _ensure_list(value: Any, section: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Section '{section}' must be a list")
    return value


# ---------------------------------------------------------------------------
# Procedural Generation Functions
# ---------------------------------------------------------------------------


def _random_name(rng: _random.Random) -> str:
    """Generate a random name, avoiding duplicates."""
    global _used_names
    for _ in range(200):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        if name not in _used_names:
            _used_names.add(name)
            return name
    return f"Politician {len(_used_names)}"


def _nearest_party(
    econ: float, soc: float, parties: list[Party], rng: _random.Random
) -> Party:
    """Pick the nearest party based on ideology distance, with some jitter."""
    jitter = 0.15
    best_party = None
    best_distance = float("inf")

    for party in parties:
        dist = (
            (econ - party.ideology["economic"]) ** 2
            + (soc - party.ideology["social"]) ** 2
        ) ** 0.5
        if dist < best_distance:
            best_distance = dist
            best_party = party

    return best_party if best_party else rng.choice(parties)


def _generate_agent(
    place: Place,
    office: OfficeType | None,
    parties: list[Party],
    groups: list[InterestGroup],
    rng: _random.Random,
    detail_level: DetailLevel = DetailLevel.L1,
    party_role: PartyRole = PartyRole.MEMBER,
    econ_override: float | None = None,
    soc_override: float | None = None,
    name: str | None = None,
) -> Agent:
    """Generate an agent with random ideology across the political compass.

    Agents are randomly distributed across the full ideological space (-1 to 1),
    then assigned to the nearest party with some jitter.
    """
    # Ideology: random across full compass, then find nearest party
    if econ_override is not None and soc_override is not None:
        econ, soc = econ_override, soc_override
    else:
        econ = rng.uniform(-1.0, 1.0)
        soc = rng.uniform(-1.0, 1.0)

    # Add jitter, then find nearest party
    jitter_econ = rng.uniform(-0.15, 0.15)
    jitter_soc = rng.uniform(-0.15, 0.15)
    party = _nearest_party(econ + jitter_econ, soc + jitter_soc, parties, rng)

    if name is None:
        name = _random_name(rng)

    # Use the assigned party's base constituency for allegiances
    allegiances: dict[InterestGroup, float] = {}
    for ig in groups:
        if ig in place.interest_group_presence:
            share = place.interest_group_presence[ig]
            affinity = party.base_constituency.get(ig, 0.0)
            base = affinity * 0.6 + share * 0.2
            allegiances[ig] = max(0.0, min(1.0, base + rng.uniform(-0.1, 0.1)))

    # Popularity: correlated with allegiances + noise
    popularity: dict[InterestGroup, float] = {}
    for ig in groups:
        if ig in place.interest_group_presence:
            base = allegiances.get(ig, 0.0) * 0.7 + rng.uniform(0.0, 0.3)
            popularity[ig] = max(0.0, min(1.0, base))

    return Agent(
        id=AgentId(f"{place.id}_gen_{rng.randint(10000, 99999)}"),
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


def _party_for_place(place: Place, parties: list[Party], rng: _random.Random) -> Party:
    """Pick a party weighted by how well it fits the place's IG mix."""
    scores = []
    for party in parties:
        score = sum(
            party.base_constituency.get(ig, 0.0) * share
            for ig, share in place.interest_group_presence.items()
        )
        scores.append(max(score, 0.05))
    return rng.choices(parties, weights=scores, k=1)[0]


def _generate_agents_from_config(
    world: World,
    config: dict[str, Any],
    places_by_id: dict[str, Place],
    parties_by_id: dict[str, Party],
    groups_by_id: dict[str, InterestGroup],
    agents_by_id: dict[str, Agent],
) -> list[Agent]:
    """Generate agents based on the [generate] section configuration."""

    generated_agents: list[Agent] = []
    rng = _random.Random(config.get("seed", 42))

    parties = list(parties_by_id.values())
    groups = list(groups_by_id.values())

    # Check for profile-based generation
    profile = config.get("profile")
    if profile:
        generated_agents.extend(
            _generate_from_profile(
                world=world,
                profile=profile,
                config=config,
                parties=parties,
                groups=groups,
                places_by_id=places_by_id,
                rng=rng,
            )
        )
        return generated_agents

    # Handle explicit structure configuration
    # Federal level
    federal_config = config.get("federal", {})
    if federal_config:
        federal_places = [
            p for p in places_by_id.values() if p.tier == PlaceTier.FEDERAL
        ]
        if federal_places:
            federal_place = federal_places[0]
            num_congress = federal_config.get("num_congress", 0)
            if num_congress > 0:
                generated_agents.extend(
                    _generate_legislative_seats(
                        place=federal_place,
                        office_type=OfficeType.CONGRESSPERSON,
                        num_seats=num_congress,
                        parties=parties,
                        groups=groups,
                        rng=rng,
                        election_interval=federal_config.get("election_interval", 5),
                    )
                )

            # Generate President if not already defined
            if not any(a.office == OfficeType.PRESIDENT for a in agents_by_id.values()):
                pres = _generate_agent(
                    place=federal_place,
                    office=OfficeType.PRESIDENT,
                    parties=parties,
                    groups=groups,
                    rng=rng,
                    detail_level=DetailLevel.L0,
                    party_role=PartyRole.LEADER,
                )
                generated_agents.append(pres)
                world.add_politician(pres)

    # State level
    state_configs = config.get("states", [])
    if isinstance(state_configs, list):
        for state_cfg in state_configs:
            state_id = state_cfg.get("state_id")
            if state_id and state_id in places_by_id:
                place = places_by_id[state_id]

                # Governor
                if not any(
                    a.place == place and a.office == OfficeType.GOVERNOR
                    for a in list(agents_by_id.values()) + generated_agents
                ):
                    gov_party_id = state_cfg.get("governor_party")
                    if gov_party_id and gov_party_id in parties_by_id:
                        gov_party = parties_by_id[gov_party_id]
                    else:
                        gov_party = _party_for_place(place, parties, rng)

                    gov = _generate_agent(
                        place=place,
                        office=OfficeType.GOVERNOR,
                        parties=parties,
                        groups=groups,
                        rng=rng,
                        detail_level=DetailLevel.L0,
                        party_role=PartyRole.LEADER,
                    )
                    generated_agents.append(gov)
                    world.add_politician(gov)

                # State assembly
                assembly_seats = state_cfg.get("assembly_seats", 0)
                if assembly_seats > 0:
                    # Get composition if specified
                    composition = state_cfg.get("assembly_composition", {})
                    assembly_agents = _generate_state_assembly(
                        place=place,
                        num_seats=assembly_seats,
                        parties=parties,
                        groups=groups,
                        composition=composition,
                        rng=rng,
                    )
                    generated_agents.extend(assembly_agents)
                    for a in assembly_agents:
                        world.add_politician(a)

    # City/municipality level
    city_configs = config.get("cities", [])
    if isinstance(city_configs, list):
        for city_cfg in city_configs:
            city_id = city_cfg.get("city_id")
            if city_id and city_id in places_by_id:
                place = places_by_id[city_id]
                council_seats = city_cfg.get("council_seats", 0)

                if council_seats > 0:
                    # Generate mayor
                    if not any(
                        a.place == place and a.office == OfficeType.MAYOR
                        for a in list(agents_by_id.values()) + generated_agents
                    ):
                        mayor = _generate_agent(
                            place=place,
                            office=OfficeType.MAYOR,
                            parties=parties,
                            groups=groups,
                            rng=rng,
                            detail_level=DetailLevel.L0,
                        )
                        generated_agents.append(mayor)
                        world.add_politician(mayor)

                    # Generate council
                    council_agents = _generate_council(
                        place=place,
                        num_seats=council_seats,
                        parties=parties,
                        groups=groups,
                        rng=rng,
                    )
                    generated_agents.extend(council_agents)
                    for a in council_agents:
                        world.add_politician(a)

    # Generate governments for all generated agents (only for places not already in governments)
    _create_governments_for_generated_agents(
        world, generated_agents, places_by_id, config
    )

    return generated_agents


def _generate_from_profile(
    world: World,
    profile: str,
    config: dict[str, Any],
    parties: list[Party],
    groups: list[InterestGroup],
    places_by_id: dict[str, Place],
    rng: _random.Random,
) -> list[Agent]:
    """Generate agents based on a predefined profile."""

    generated_agents: list[Agent] = []

    if profile == "federated":
        # Federated profile: Federal -> States -> Municipalities
        num_states = config.get("num_states", 3)
        municipalities_per_state = config.get("municipalities_per_state", 3)
        federal_legislature_seats = config.get("federal_legislature_seats", 12)
        state_legislature_seats = config.get("state_legislature_seats", 7)
        municipal_legislature_seats = config.get("municipal_legislature_seats", 5)
        election_interval = config.get("election_interval", 5)

        # Find or create federal place
        federal_places = [
            p for p in places_by_id.values() if p.tier == PlaceTier.FEDERAL
        ]
        if not federal_places:
            # Create federal place if not exists
            federal_place = Place(
                id=PlaceId("federal"),
                name="Federal Republic",
                tier=PlaceTier.FEDERAL,
                interest_group_presence=_random_distribution_map(groups, rng),
            )
            world.add_place(federal_place)
            places_by_id["federal"] = federal_place
        else:
            federal_place = federal_places[0]

        # Generate federal executive (President)
        president = _generate_agent(
            place=federal_place,
            office=OfficeType.PRESIDENT,
            parties=parties,
            groups=groups,
            rng=rng,
            detail_level=DetailLevel.L0,
            party_role=PartyRole.LEADER,
        )
        generated_agents.append(president)
        world.add_politician(president)

        # Generate federal legislature
        if federal_legislature_seats > 0:
            federal_legislators = _generate_legislative_seats(
                place=federal_place,
                office_type=OfficeType.CONGRESSPERSON,
                num_seats=federal_legislature_seats,
                parties=parties,
                groups=groups,
                rng=rng,
                election_interval=election_interval,
            )
            generated_agents.extend(federal_legislators)
            for a in federal_legislators:
                world.add_politician(a)

        # Generate states
        for state_index in range(num_states):
            state_id = f"state_{state_index + 1}"

            # Find or create state place
            state_places = [
                p
                for p in places_by_id.values()
                if p.tier == PlaceTier.STATE and str(p.id) == state_id
            ]
            if state_places:
                state_place = state_places[0]
            else:
                state_place = Place(
                    id=PlaceId(state_id),
                    name=f"State {state_index + 1}",
                    tier=PlaceTier.STATE,
                    parent=federal_place,
                    interest_group_presence=_random_distribution_map(groups, rng),
                )
                world.add_place(state_place)
                places_by_id[state_id] = state_place

            # Generate governor
            governor = _generate_agent(
                place=state_place,
                office=OfficeType.GOVERNOR,
                parties=parties,
                groups=groups,
                rng=rng,
                detail_level=DetailLevel.L0,
                party_role=PartyRole.LEADER,
            )
            generated_agents.append(governor)
            world.add_politician(governor)

            # Generate state legislature
            if state_legislature_seats > 0:
                state_legislators = _generate_legislative_seats(
                    place=state_place,
                    office_type=OfficeType.STATE_ASSEMBLYPERSON,
                    num_seats=state_legislature_seats,
                    parties=parties,
                    groups=groups,
                    rng=rng,
                    election_interval=election_interval,
                )
                generated_agents.extend(state_legislators)
                for a in state_legislators:
                    world.add_politician(a)

            # Generate municipalities
            for muni_index in range(municipalities_per_state):
                muni_id = f"{state_id}_municipality_{muni_index + 1}"

                # Find or create municipality place
                muni_places = [p for p in places_by_id.values() if str(p.id) == muni_id]
                if muni_places:
                    muni_place = muni_places[0]
                else:
                    muni_place = Place(
                        id=PlaceId(muni_id),
                        name=f"Municipality {state_index + 1}-{muni_index + 1}",
                        tier=PlaceTier.MUNICIPALITY,
                        parent=state_place,
                        interest_group_presence=_random_distribution_map(groups, rng),
                    )
                    world.add_place(muni_place)
                    places_by_id[muni_id] = muni_place

                # Generate mayor
                mayor = _generate_agent(
                    place=muni_place,
                    office=OfficeType.MAYOR,
                    parties=parties,
                    groups=groups,
                    rng=rng,
                    detail_level=DetailLevel.L0,
                )
                generated_agents.append(mayor)
                world.add_politician(mayor)

                # Generate council
                if municipal_legislature_seats > 0:
                    council_members = _generate_council(
                        place=muni_place,
                        num_seats=municipal_legislature_seats,
                        parties=parties,
                        groups=groups,
                        rng=rng,
                    )
                    generated_agents.extend(council_members)
                    for a in council_members:
                        world.add_politician(a)

        # Create governments for all generated agents
        _create_federated_governments(
            world, generated_agents, places_by_id, election_interval
        )

    elif profile == "local":
        # Local profile: single municipality
        municipal_legislature_seats = config.get("municipal_legislature_seats", 7)
        election_interval = config.get("election_interval", 5)

        # Find or create a municipality place
        muni_places = [
            p for p in places_by_id.values() if p.tier == PlaceTier.MUNICIPALITY
        ]
        if not muni_places:
            # Create one
            muni_place = Place(
                id=PlaceId("municipality_1"),
                name="Capital City",
                tier=PlaceTier.MUNICIPALITY,
                interest_group_presence=_random_distribution_map(groups, rng),
            )
            world.add_place(muni_place)
            places_by_id["municipality_1"] = muni_place
        else:
            muni_place = muni_places[0]

        # Generate mayor
        mayor = _generate_agent(
            place=muni_place,
            office=OfficeType.MAYOR,
            parties=parties,
            groups=groups,
            rng=rng,
            detail_level=DetailLevel.L0,
            party_role=PartyRole.LEADER,
        )
        generated_agents.append(mayor)
        world.add_politician(mayor)

        # Generate council
        if municipal_legislature_seats > 0:
            council_members = _generate_council(
                place=muni_place,
                num_seats=municipal_legislature_seats,
                parties=parties,
                groups=groups,
                rng=rng,
            )
            generated_agents.extend(council_members)
            for a in council_members:
                world.add_politician(a)

        # Create government
        _create_local_government(
            world, generated_agents, places_by_id, election_interval
        )

    else:
        raise ValueError(f"Unsupported generation profile '{profile}'")

    return generated_agents


def _random_distribution_map(items: list, rng: _random.Random) -> dict:
    """Create a random distribution map for place IG presence."""
    weights = [rng.uniform(0.2, 1.0) for _ in items]
    total = sum(weights)
    return {item: weight / total for item, weight in zip(items, weights, strict=False)}


def _generate_legislative_seats(
    place: Place,
    office_type: OfficeType,
    num_seats: int,
    parties: list[Party],
    groups: list[InterestGroup],
    rng: _random.Random,
    election_interval: int = 5,
) -> list[Agent]:
    """Generate legislative seats with proportional party representation."""

    # Distribute seats roughly equally among parties using round-robin
    legislators: list[Agent] = []
    party_index = 0

    while len(legislators) < num_seats:
        party = parties[party_index % len(parties)]
        legislator = _generate_agent(
            place=place,
            office=office_type,
            parties=parties,
            groups=groups,
            rng=rng,
            detail_level=DetailLevel.L1,
        )
        legislators.append(legislator)
        party_index += 1

    return legislators


def _generate_state_assembly(
    place: Place,
    num_seats: int,
    parties: list[Party],
    groups: list[InterestGroup],
    composition: dict[str, int],
    rng: _random.Random,
) -> list[Agent]:
    """Generate state assembly with optional composition specification."""

    legislators: list[Agent] = []

    if composition:
        # Use explicitly specified composition
        for party_id_str, count in composition.items():
            for _ in range(count):
                # Find party by ID (could be name or ID)
                party = None
                for p in parties:
                    if (
                        str(p.id) == party_id_str
                        or p.name.lower() == party_id_str.lower()
                    ):
                        party = p
                        break
                if party is None:
                    party = rng.choice(parties)

                legislator = _generate_agent(
                    place=place,
                    office=OfficeType.STATE_ASSEMBLYPERSON,
                    parties=parties,
                    groups=groups,
                    rng=rng,
                    detail_level=DetailLevel.L1,
                )
                legislators.append(legislator)

        # Fill remaining seats with round-robin
        while len(legislators) < num_seats:
            legislator = _generate_agent(
                place=place,
                office=OfficeType.STATE_ASSEMBLYPERSON,
                parties=parties,
                groups=groups,
                rng=rng,
                detail_level=DetailLevel.L1,
            )
            legislators.append(legislator)
    else:
        # Default: round-robin distribution
        legislators = _generate_legislative_seats(
            place=place,
            office_type=OfficeType.STATE_ASSEMBLYPERSON,
            num_seats=num_seats,
            parties=parties,
            groups=groups,
            rng=rng,
        )

    return legislators


def _generate_council(
    place: Place,
    num_seats: int,
    parties: list[Party],
    groups: list[InterestGroup],
    rng: _random.Random,
) -> list[Agent]:
    """Generate city council members."""

    return _generate_legislative_seats(
        place=place,
        office_type=OfficeType.COUNCILPERSON,
        num_seats=num_seats,
        parties=parties,
        groups=groups,
        rng=rng,
    )


def _create_governments_for_generated_agents(
    world: World,
    agents: list[Agent],
    places_by_id: dict[str, Place],
    config: dict[str, Any],
) -> None:
    """Create governments for generated agents (only for places not already having governments)."""

    election_interval = config.get("election_interval", 5)

    # Group agents by place
    by_place: dict[Place, list[Agent]] = {}
    for agent in agents:
        if agent.place not in by_place:
            by_place[agent.place] = []
        by_place[agent.place].append(agent)

    for place, place_agents in by_place.items():
        # Skip if government already exists
        if place in world.governments:
            continue

        # Find executive
        if place.tier == PlaceTier.FEDERAL:
            executive_type = OfficeType.PRESIDENT
        elif place.tier == PlaceTier.STATE:
            executive_type = OfficeType.GOVERNOR
        else:
            executive_type = OfficeType.MAYOR

        executive_agent = next(
            (a for a in place_agents if a.office == executive_type), None
        )

        # Find legislature
        if place.tier == PlaceTier.FEDERAL:
            legislative_type = OfficeType.CONGRESSPERSON
        elif place.tier == PlaceTier.STATE:
            legislative_type = OfficeType.STATE_ASSEMBLYPERSON
        else:
            legislative_type = OfficeType.COUNCILPERSON

        legislature_agents = [a for a in place_agents if a.office == legislative_type]

        if executive_agent:
            executive = Office(
                office_type=executive_type,
                place=place,
                holder=executive_agent,
            )

            if legislature_agents:
                legislature = Legislature(
                    place=place,
                    seat_type=legislative_type,
                    total_seats=len(legislature_agents),
                    members=legislature_agents,
                )
            else:
                legislature = None

            world.add_government(
                Government(
                    place=place,
                    executive=executive,
                    legislature=legislature,
                    attributes={
                        "election_interval": election_interval,
                        "last_election_turn": 0,
                    },
                )
            )


def _create_federated_governments(
    world: World,
    agents: list[Agent],
    places_by_id: dict[str, Place],
    election_interval: int = 5,
) -> None:
    """Create governments for federated profile."""

    # Group by place
    by_place: dict[Place, list[Agent]] = {}
    for agent in agents:
        if agent.place not in by_place:
            by_place[agent.place] = []
        by_place[agent.place].append(agent)

    for place, place_agents in by_place.items():
        # Skip if government already exists
        if place in world.governments:
            continue

        # Determine office types based on tier
        if place.tier == PlaceTier.FEDERAL:
            executive_type = OfficeType.PRESIDENT
            legislative_type = OfficeType.CONGRESSPERSON
        elif place.tier == PlaceTier.STATE:
            executive_type = OfficeType.GOVERNOR
            legislative_type = OfficeType.STATE_ASSEMBLYPERSON
        else:
            executive_type = OfficeType.MAYOR
            legislative_type = OfficeType.COUNCILPERSON

        executive_agent = next(
            (a for a in place_agents if a.office == executive_type), None
        )
        legislature_agents = [a for a in place_agents if a.office == legislative_type]

        if executive_agent:
            executive = Office(
                office_type=executive_type,
                place=place,
                holder=executive_agent,
            )

            if legislature_agents:
                legislature = Legislature(
                    place=place,
                    seat_type=legislative_type,
                    total_seats=len(legislature_agents),
                    members=legislature_agents,
                )
            else:
                legislature = None

            world.add_government(
                Government(
                    place=place,
                    executive=executive,
                    legislature=legislature,
                    attributes={
                        "election_interval": election_interval,
                        "last_election_turn": 0,
                    },
                )
            )


def _create_local_government(
    world: World,
    agents: list[Agent],
    places_by_id: dict[str, Place],
    election_interval: int = 5,
) -> None:
    """Create government for local profile."""

    mayor = next((a for a in agents if a.office == OfficeType.MAYOR), None)
    council = [a for a in agents if a.office == OfficeType.COUNCILPERSON]

    if mayor and mayor.place:
        place = mayor.place

        if place in world.governments:
            return

        executive = Office(
            office_type=OfficeType.MAYOR,
            place=place,
            holder=mayor,
        )

        if council:
            legislature = Legislature(
                place=place,
                seat_type=OfficeType.COUNCILPERSON,
                total_seats=len(council),
                members=council,
            )
        else:
            legislature = None

        world.add_government(
            Government(
                place=place,
                executive=executive,
                legislature=legislature,
                attributes={
                    "election_interval": election_interval,
                    "last_election_turn": 0,
                },
            )
        )
