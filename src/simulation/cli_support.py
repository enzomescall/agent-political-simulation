from __future__ import annotations

from collections import Counter

from src.log_utils import fmt
from src.models import PlaceTier, World


def print_world_summary(world: World, summary: str = "full") -> None:
    print(f"=== Initial State (Turn {world.turn}) ===")
    _print_world_header(world)
    if summary == "short":
        return

    focus_places = _focus_places(world)
    for place in focus_places:
        _print_place_snapshot(world, place.id)


def print_final_summary(world: World, summary: str = "full", debug: bool = False) -> None:
    print(f"\n=== Final State (Turn {world.turn}) ===")
    _print_world_header(world)

    if summary == "full":
        for place in _focus_places(world):
            _print_satisfaction_snapshot(world, place.id)
            _print_agent_snapshot(world, place.id)

    if debug:
        print("\nVerbose log written to simulation.log")


def _print_world_header(world: World) -> None:
    tier_counts = Counter(place.tier.name for place in world.places.values())
    print(
        "Places: "
        + ", ".join(
            f"{tier}={tier_counts.get(tier, 0)}"
            for tier in ("FEDERAL", "STATE", "MUNICIPALITY")
        )
    )
    print("Parties: " + ", ".join(
        f"{party.name}({party.ideology['economic']:+.1f},{party.ideology['social']:+.1f})"
        for party in world.parties.values()
    ))
    print("Interest groups: " + ", ".join(group.name for group in world.interest_groups.values()))


def _focus_places(world: World):
    if len(world.places) <= 3:
        return list(world.places.values())

    selected = []
    for tier in (PlaceTier.FEDERAL, PlaceTier.STATE, PlaceTier.MUNICIPALITY):
        place = next((candidate for candidate in world.places.values() if candidate.tier is tier), None)
        if place is not None:
            selected.append(place)
    return selected


def _print_place_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    gov = world.governments.get(place.id)
    print(f"\n{place.name} ({place.tier.name})")
    if gov is not None:
        if gov.executive.holder is not None:
            print(f"Executive: {fmt(gov.executive.holder)} [{gov.executive.office_type.name}]")
        if gov.legislature is not None:
            print(f"Legislature: {len(gov.legislature.members)}/{gov.legislature.total_seats} seats filled")
    print("Interest group presence:")
    for group, share in place.interest_group_presence.items():
        sat = group.satisfaction.get(place, 0.0)
        print(f"  {group.name}: share={share:.2f}, sat={sat:.2f}, pressure={group.pressure_on(place):.2f}")


def _print_satisfaction_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    print(f"\nSatisfaction in {place.name}:")
    for group in place.interest_group_presence:
        sat = group.satisfaction.get(place, 0.0)
        print(f"  {group.name}: sat={sat:.2f}, pressure={group.pressure_on(place):.2f}")


def _print_agent_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    politicians = [agent for agent in world.politicians.values() if agent.place is place]
    politicians.sort(key=lambda agent: (agent.office is None, agent.name))
    if not politicians:
        return

    print(f"Agents in {place.name}:")
    for agent in politicians[:12]:
        office = agent.office.name if agent.office is not None else "NONE"
        print(
            f"  {fmt(agent)} office={office} party={agent.party.name} "
            f"standing={agent.party_standing:.2f}"
        )
