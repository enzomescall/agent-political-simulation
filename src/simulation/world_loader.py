from __future__ import annotations

import json
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
    }
    for section in _SECTION_FILES:
        section_path = _find_section_file(path, section)
        if section_path is None:
            continue
        raw = _load_data_file(section_path)
        sections[section] = _extract_section_payload(raw, section)

    world = _build_world_from_sections(sections)
    world.attributes["config_source"] = str(path)
    return world


def _find_section_file(path: Path, section: str) -> Path | None:
    matches = [candidate for candidate in (path / f"{section}.json", path / f"{section}.toml") if candidate.exists()]
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
        raise ValueError(f"Invalid value '{value}' for {context}; expected one of: {allowed}") from exc


def _parse_ideology(raw: dict[str, Any]) -> Ideology:
    ideology_raw = raw.get("ideology")
    if ideology_raw is None:
        ideology_raw = {
            key: value
            for key, value in raw.items()
            if key in {"economic", "social"}
        }
    if not isinstance(ideology_raw, dict):
        raise ValueError(f"Invalid ideology payload: {ideology_raw!r}")
    return Ideology(axes={str(axis): float(value) for axis, value in ideology_raw.items()})


def _require_reference(mapping: dict[str, Any], ref_id: str, section: str, field: str, owner: str) -> Any:
    try:
        return mapping[ref_id]
    except KeyError as exc:
        raise ValueError(f"Unknown {field} '{ref_id}' in {section} entry '{owner}'") from exc


def _resolve_weighted_map(
    raw_map: dict[str, Any] | None,
    mapping: dict[str, Any],
    section: str,
    field: str,
    owner: str,
) -> dict[Any, float]:
    result: dict[Any, float] = {}
    for ref_id, value in (raw_map or {}).items():
        result[_require_reference(mapping, ref_id, section, field, owner)] = float(value)
    return result


def _build_world_from_sections(sections: dict[str, Any]) -> World:
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
    raw_interest_groups = _ensure_list(sections.get("interest_groups"), "interest_groups")
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
                entry.get("base_constituency"), groups_by_id, "parties", "interest_group", party_id,
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
            place.parent = _require_reference(places_by_id, str(parent_id), "places", "parent_id", place_id)
        place.interest_group_presence = _resolve_weighted_map(
            entry.get("interest_group_presence"), groups_by_id, "places", "interest_group_presence", place_id,
        )
        world.add_place(place)

    agents_by_id: dict[str, Agent] = {}
    raw_agents = _ensure_list(sections.get("agents"), "agents")
    for entry in raw_agents:
        agent_id = str(entry["id"])
        party = _require_reference(parties_by_id, str(entry["party_id"]), "agents", "party_id", agent_id)
        place = _require_reference(places_by_id, str(entry["place_id"]), "agents", "place_id", agent_id)
        office = entry.get("office")
        agent = Agent(
            id=AgentId(agent_id),
            name=str(entry["name"]),
            ideology=_parse_ideology(entry),
            party=party,
            place=place,
            office=_parse_enum(OfficeType, office, f"agent '{agent_id}' office") if office else None,
            party_role=_parse_enum(PartyRole, entry.get("party_role", "MEMBER"), f"agent '{agent_id}' party_role"),
            allegiances=_resolve_weighted_map(
                entry.get("allegiances"), groups_by_id, "agents", "allegiances", agent_id,
            ),
            popularity=_resolve_weighted_map(
                entry.get("popularity"), groups_by_id, "agents", "popularity", agent_id,
            ),
            party_standing=float(entry.get("party_standing", 0.5)),
            ambition=float(entry.get("ambition", 0.5)),
            archetype=_parse_enum(Archetype, entry.get("archetype", "LOYALIST"), f"agent '{agent_id}' archetype"),
            detail_level=_parse_enum(
                DetailLevel, entry.get("detail_level", "L3"), f"agent '{agent_id}' detail_level",
            ),
            attributes=dict(entry.get("attributes", {})),
        )
        world.add_politician(agent)
        agents_by_id[agent_id] = agent

    for entry in raw_agents:
        agent_id = str(entry["id"])
        agent = agents_by_id[agent_id]
        agent.relationships = _resolve_weighted_map(
            entry.get("relationships"), agents_by_id, "agents", "relationships", agent_id,
        )

    for entry in raw_interest_groups:
        group_id = str(entry["id"])
        group = groups_by_id[group_id]
        group.satisfaction = _resolve_weighted_map(
            entry.get("satisfaction"), places_by_id, "interest_groups", "satisfaction", group_id,
        )
        group.electorate_share = _resolve_weighted_map(
            entry.get("electorate_share"), places_by_id, "interest_groups", "electorate_share", group_id,
        )

    raw_governments = _ensure_list(sections.get("governments"), "governments")
    for entry in raw_governments:
        place_id = str(entry["place_id"])
        place = _require_reference(places_by_id, place_id, "governments", "place_id", place_id)
        executive_raw = entry.get("executive")
        if not isinstance(executive_raw, dict):
            raise ValueError(f"Government '{place_id}' is missing an executive object")
        executive_holder = None
        if executive_raw.get("holder_id") is not None:
            executive_holder = _require_reference(
                agents_by_id, str(executive_raw["holder_id"]), "governments", "executive.holder_id", place_id,
            )
        executive = Office(
            office_type=_parse_enum(OfficeType, executive_raw.get("office_type"), f"government '{place_id}' executive"),
            place=place,
            holder=executive_holder,
            attributes=dict(executive_raw.get("attributes", {})),
        )

        legislature = None
        legislature_raw = entry.get("legislature")
        if legislature_raw is not None:
            if not isinstance(legislature_raw, dict):
                raise ValueError(f"Government '{place_id}' legislature must be an object")
            members = [
                _require_reference(agents_by_id, str(member_id), "governments", "legislature.member_ids", place_id)
                for member_id in legislature_raw.get("member_ids", [])
            ]
            legislature = Legislature(
                place=place,
                seat_type=_parse_enum(
                    OfficeType, legislature_raw.get("seat_type"), f"government '{place_id}' legislature seat_type",
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
                    agents_by_id, str(office_raw["holder_id"]), "governments", "cabinet.holder_id", place_id,
                )
            cabinet.append(Office(
                office_type=_parse_enum(
                    OfficeType, office_raw.get("office_type"), f"government '{place_id}' cabinet office_type",
                ),
                place=place,
                holder=holder,
                attributes=dict(office_raw.get("attributes", {})),
            ))

        world.add_government(Government(
            place=place,
            executive=executive,
            cabinet=cabinet,
            legislature=legislature,
            attributes=dict(entry.get("attributes", {})),
        ))

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
