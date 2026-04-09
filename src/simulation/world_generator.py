from __future__ import annotations

import random as _random
from typing import Iterable

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

_INTEREST_GROUP_NAME_POOL = [
    "Urban Workers Union",
    "Business Council",
    "Youth Coalition",
    "Rural Workers League",
    "Public Service Guild",
    "Property Owners Association",
    "Climate Action Network",
    "Faith and Family Coalition",
]

_PARTY_NAME_POOL = [
    "Labor Alliance",
    "Civic Progress",
    "Union Front",
    "National Reform",
    "Green Horizon",
    "Liberty Forum",
    "Community Bloc",
    "Popular Movement",
]

_FIRST_NAMES = [
    "Ana", "Bruno", "Clara", "Diego", "Elisa", "Fernando", "Gabriela", "Henrique",
    "Isabela", "Joao", "Kamila", "Leonardo", "Marina", "Nicolas", "Olivia", "Paulo",
    "Renata", "Sofia", "Tiago", "Valeria",
]

_LAST_NAMES = [
    "Costa", "Souza", "Ramos", "Melo", "Faria", "Nunes", "Alves", "Rocha",
    "Barbosa", "Freitas", "Lima", "Pereira", "Teixeira", "Campos", "Araujo", "Duarte",
]


def generate_world(profile: str, *, seed: int | None = None, **kwargs) -> World:
    rng = _random.Random(seed)
    if profile == "local":
        world = _generate_local_world(rng=rng, **kwargs)
    elif profile == "federated":
        world = _generate_federated_world(rng=rng, **kwargs)
    else:
        raise ValueError(f"Unsupported generation profile '{profile}'")

    world.attributes["generated_profile"] = profile
    world.attributes["seed"] = seed
    initialize_local_variables(world)
    return world


def _generate_local_world(
    *,
    rng: _random.Random,
    num_parties: int = 3,
    num_interest_groups: int = 3,
    council_seats: int = 5,
    party_election_interval: int = 5,
    election_interval: int = 5,
) -> World:
    world = World()
    groups = _create_interest_groups(world, num_interest_groups)
    parties = _create_parties(world, groups, num_parties, party_election_interval, rng)

    city = Place(
        id=PlaceId("municipality_1"),
        name="Capital City",
        tier=PlaceTier.MUNICIPALITY,
        interest_group_presence=_random_distribution_map(groups, rng),
    )
    world.add_place(city)

    place_agents = _populate_place(
        world,
        place=city,
        parties=parties,
        groups=groups,
        executive_office=OfficeType.MAYOR,
        legislative_office=OfficeType.COUNCILPERSON,
        legislature_seats=council_seats,
        election_interval=election_interval,
        rng=rng,
    )

    _assign_party_leaders(world, preferred_agents=place_agents, rng=rng)
    return world


def _generate_federated_world(
    *,
    rng: _random.Random,
    num_states: int = 3,
    municipalities_per_state: int = 3,
    num_parties: int = 4,
    num_interest_groups: int = 3,
    federal_legislature_seats: int = 11,
    state_legislature_seats: int = 7,
    municipal_legislature_seats: int = 5,
    party_election_interval: int = 5,
    election_interval: int = 5,
) -> World:
    world = World()
    groups = _create_interest_groups(world, num_interest_groups)
    parties = _create_parties(world, groups, num_parties, party_election_interval, rng)

    federal = Place(
        id=PlaceId("federal"),
        name="Federal Republic",
        tier=PlaceTier.FEDERAL,
        interest_group_presence=_random_distribution_map(groups, rng),
    )
    world.add_place(federal)
    preferred_agents: list[Agent] = []
    preferred_agents.extend(_populate_place(
        world,
        place=federal,
        parties=parties,
        groups=groups,
        executive_office=OfficeType.PRESIDENT,
        legislative_office=OfficeType.CONGRESSPERSON,
        legislature_seats=federal_legislature_seats,
        election_interval=election_interval,
        rng=rng,
    ))

    for state_index in range(num_states):
        state = Place(
            id=PlaceId(f"state_{state_index + 1}"),
            name=f"State {state_index + 1}",
            tier=PlaceTier.STATE,
            parent=federal,
            interest_group_presence=_random_distribution_map(groups, rng),
        )
        world.add_place(state)
        preferred_agents.extend(_populate_place(
            world,
            place=state,
            parties=parties,
            groups=groups,
            executive_office=OfficeType.GOVERNOR,
            legislative_office=OfficeType.STATE_ASSEMBLYPERSON,
            legislature_seats=state_legislature_seats,
            election_interval=election_interval,
            rng=rng,
        ))

        for municipality_index in range(municipalities_per_state):
            municipality = Place(
                id=PlaceId(f"state_{state_index + 1}_municipality_{municipality_index + 1}"),
                name=f"Municipality {state_index + 1}-{municipality_index + 1}",
                tier=PlaceTier.MUNICIPALITY,
                parent=state,
                interest_group_presence=_random_distribution_map(groups, rng),
            )
            world.add_place(municipality)
            preferred_agents.extend(_populate_place(
                world,
                place=municipality,
                parties=parties,
                groups=groups,
                executive_office=OfficeType.MAYOR,
                legislative_office=OfficeType.COUNCILPERSON,
                legislature_seats=municipal_legislature_seats,
                election_interval=election_interval,
                rng=rng,
            ))

    _assign_party_leaders(world, preferred_agents=preferred_agents, rng=rng)
    return world


def _create_interest_groups(world: World, num_interest_groups: int) -> list[InterestGroup]:
    groups: list[InterestGroup] = []
    for index in range(num_interest_groups):
        base_name = _INTEREST_GROUP_NAME_POOL[index] if index < len(_INTEREST_GROUP_NAME_POOL) else f"Interest Group {index + 1}"
        group = InterestGroup(
            id=InterestGroupId(f"ig_{index + 1}"),
            name=base_name,
            fears=[f"issue_{index + 1}_a", f"issue_{index + 1}_b"],
        )
        world.add_interest_group(group)
        groups.append(group)
    return groups


def _create_parties(
    world: World,
    groups: list[InterestGroup],
    num_parties: int,
    party_election_interval: int,
    rng: _random.Random,
) -> list[Party]:
    parties: list[Party] = []
    for index in range(num_parties):
        name = _PARTY_NAME_POOL[index] if index < len(_PARTY_NAME_POOL) else f"Party {index + 1}"
        if num_parties == 1:
            economic = 0.0
        else:
            economic = -0.8 + (1.6 * index / (num_parties - 1))
        social = rng.uniform(-0.6, 0.6)
        party = Party(
            id=PartyId(f"party_{index + 1}"),
            name=name,
            ideology=Ideology.create(economic=economic, social=social),
            directive_threshold=rng.uniform(0.1, 0.3),
            campaign_budget=5,
            nomination_threshold=0.3,
            leadership_interval=party_election_interval,
            base_constituency=_random_distribution_map(groups, rng),
        )
        world.add_party(party)
        parties.append(party)
    return parties


def _populate_place(
    world: World,
    *,
    place: Place,
    parties: list[Party],
    groups: list[InterestGroup],
    executive_office: OfficeType,
    legislative_office: OfficeType,
    legislature_seats: int,
    election_interval: int,
    rng: _random.Random,
) -> list[Agent]:
    party_pools: dict[Party, list[Agent]] = {}
    pool_size = max(3, legislature_seats // max(len(parties), 1) + 2)
    all_agents: list[Agent] = []
    sequence = len(world.politicians)
    for party in parties:
        party_agents: list[Agent] = []
        for _ in range(pool_size):
            sequence += 1
            agent = _create_agent(
                party=party,
                place=place,
                groups=groups,
                rng=rng,
                sequence=sequence,
            )
            world.add_politician(agent)
            party_agents.append(agent)
            all_agents.append(agent)
        party_pools[party] = party_agents

    _seed_relationships(all_agents, rng)

    executive_holder = max(
        all_agents,
        key=lambda agent: _selection_score(agent, place, executive_bonus=0.2),
    )
    executive_holder.office = executive_office
    executive_holder.detail_level = DetailLevel.L0 if place.tier is PlaceTier.FEDERAL else DetailLevel.L1

    legislators: list[Agent] = []
    round_robin = [agent for agents in party_pools.values() for agent in agents]
    round_robin.sort(key=lambda agent: (agent.party.name, -_selection_score(agent, place)))
    per_party_indices = {party: 0 for party in parties}
    while len(legislators) < legislature_seats:
        progress = False
        for party in parties:
            pool = [agent for agent in party_pools[party] if agent is not executive_holder and agent not in legislators]
            index = per_party_indices[party]
            if index >= len(pool):
                continue
            member = sorted(pool, key=lambda agent: _selection_score(agent, place), reverse=True)[index]
            per_party_indices[party] += 1
            member.office = legislative_office
            member.detail_level = DetailLevel.L1
            legislators.append(member)
            progress = True
            if len(legislators) >= legislature_seats:
                break
        if not progress:
            break

    for agent in all_agents:
        if agent.office is None:
            agent.detail_level = DetailLevel.L2

    legislature = Legislature(
        place=place,
        seat_type=legislative_office,
        total_seats=legislature_seats,
        members=legislators,
    )
    executive = Office(
        office_type=executive_office,
        place=place,
        holder=executive_holder,
    )
    world.add_government(Government(
        place=place,
        executive=executive,
        legislature=legislature,
        attributes={"election_interval": election_interval, "last_election_turn": 0},
    ))

    return [executive_holder, *legislators]


def _create_agent(
    *,
    party: Party,
    place: Place,
    groups: list[InterestGroup],
    rng: _random.Random,
    sequence: int,
) -> Agent:
    ideology = Ideology.create(
        economic=max(-1.0, min(1.0, party.ideology["economic"] + rng.uniform(-0.25, 0.25))),
        social=max(-1.0, min(1.0, party.ideology["social"] + rng.uniform(-0.25, 0.25))),
    )
    allegiances = {}
    popularity = {}
    for group, affinity in party.base_constituency.items():
        allegiances[group] = max(0.0, min(1.0, affinity * rng.uniform(0.6, 1.1)))
    for group in groups:
        base = party.base_constituency.get(group, 0.2)
        popularity[group] = max(0.0, min(1.0, base * rng.uniform(0.4, 1.0)))

    return Agent(
        id=AgentId(f"{place.id}_agent_{sequence}"),
        name=_agent_name(sequence),
        ideology=ideology,
        party=party,
        place=place,
        allegiances=allegiances,
        popularity=popularity,
        party_standing=rng.uniform(0.35, 0.9),
        ambition=rng.uniform(0.2, 0.9),
        archetype=rng.choice(list(Archetype)),
        detail_level=DetailLevel.L2,
    )


def _selection_score(agent: Agent, place: Place, executive_bonus: float = 0.0) -> float:
    electorate_total = 0.0
    popularity_total = 0.0
    for group, share in place.interest_group_presence.items():
        electorate_total += share
        popularity_total += share * agent.popularity.get(group, 0.0)
    local_popularity = popularity_total / electorate_total if electorate_total > 0 else 0.0
    return 0.5 * local_popularity + 0.35 * agent.party_standing + 0.15 * agent.ambition + executive_bonus


def _seed_relationships(agents: Iterable[Agent], rng: _random.Random) -> None:
    agent_list = list(agents)
    for index, left in enumerate(agent_list):
        for right in agent_list[index + 1:]:
            if rng.random() > 0.18:
                continue
            if left.party is right.party:
                value = rng.uniform(0.0, 0.7)
            else:
                value = rng.uniform(-0.2, 0.3)
            left.relationships[right] = value
            right.relationships[left] = value * rng.uniform(0.8, 1.0)


def _assign_party_leaders(world: World, preferred_agents: list[Agent], rng: _random.Random) -> None:
    preferred_set = set(preferred_agents)
    for party in world.parties.values():
        members = world.party_members(party)
        if not members:
            continue
        leader = max(
            members,
            key=lambda agent: (
                agent in preferred_set,
                agent.office is not None,
                agent.party_standing,
                rng.random(),
            ),
        )
        for member in members:
            member.party_role = PartyRole.MEMBER
        party.members = {member: PartyRole.MEMBER for member in members}
        party.set_role(leader, PartyRole.LEADER)
        leader.party_role = PartyRole.LEADER


def _random_distribution_map(items: list, rng: _random.Random) -> dict:
    weights = [rng.uniform(0.2, 1.0) for _ in items]
    total = sum(weights)
    return {item: weight / total for item, weight in zip(items, weights, strict=False)}


def _agent_name(sequence: int) -> str:
    first = _FIRST_NAMES[(sequence - 1) % len(_FIRST_NAMES)]
    last = _LAST_NAMES[((sequence - 1) // len(_FIRST_NAMES)) % len(_LAST_NAMES)]
    return f"{first} {last}"
