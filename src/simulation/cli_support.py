from __future__ import annotations

from collections import Counter

from src.log_utils import fmt
from src.models import PlaceTier, World


def print_world_summary(world: World, summary: str = "full") -> None:
    print(f"=== Simulation Start (Turn {world.turn}) ===")
    _print_brief_summary(world)


def print_final_summary(
    world: World, summary: str = "full", debug: bool = False
) -> None:
    print(f"\n=== Simulation End (Turn {world.turn}) ===")
    _print_brief_summary(world)
    if debug:
        print("\nVerbose log written to simulation.log")


def _print_brief_summary(world: World) -> None:
    total_agents = len(world.politicians)
    tier_counts = Counter(place.tier.name for place in world.places.values())

    print(f"Total Agents: {total_agents}")
    print(
        f"Places: FEDERAL={tier_counts.get('FEDERAL', 0)}, STATE={tier_counts.get('STATE', 0)}, MUNICIPALITY={tier_counts.get('MUNICIPALITY', 0)}"
    )

    print(f"\nInterest Groups ({len(world.interest_groups)}):")
    for group in world.interest_groups.values():
        print(f"  - {group.name}")

    print(f"\nParties ({len(world.parties)}):")
    for party in world.parties.values():
        leader = _get_party_leader(party)
        leader_str = f" [Leader: {leader}]" if leader else ""
        print(
            f"  - {party.name} ({party.ideology['economic']:+.1f},{party.ideology['social']:+.1f}){leader_str}"
        )

    print(f"\nExecutive Positions:")
    federal_gov = next(
        (g for g in world.governments.values() if g.place.tier == PlaceTier.FEDERAL),
        None,
    )
    if federal_gov and federal_gov.executive and federal_gov.executive.holder:
        h = federal_gov.executive.holder
        print(f"  President: {h.name} ({h.party.name})")

    for state in [p for p in world.places.values() if p.tier == PlaceTier.STATE][:5]:
        gov = world.governments.get(state.id)
        if gov and gov.executive and gov.executive.holder:
            h = gov.executive.holder
            print(f"  {state.name} Governor: {h.name} ({h.party.name})")
    if tier_counts.get("STATE", 0) > 5:
        print(f"  ... and {tier_counts.get('STATE', 0) - 5} more state governors")


def _get_party_leader(party):
    for agent, role in party.members.items():
        if role.name == "LEADER":
            return agent.name
    return None


def _focus_places(world: World):
    if len(world.places) <= 3:
        return list(world.places.values())

    selected = []
    for tier in (PlaceTier.FEDERAL, PlaceTier.STATE, PlaceTier.MUNICIPALITY):
        place = next(
            (
                candidate
                for candidate in world.places.values()
                if candidate.tier is tier
            ),
            None,
        )
        if place is not None:
            selected.append(place)
    return selected


def _print_place_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    gov = world.governments.get(place.id)
    print(f"\n{place.name} ({place.tier.name})")
    if gov is not None:
        if gov.executive.holder is not None:
            print(
                f"Executive: {fmt(gov.executive.holder)} [{gov.executive.office_type.name}]"
            )
        if gov.legislature is not None:
            print(
                f"Legislature: {len(gov.legislature.members)}/{gov.legislature.total_seats} seats filled"
            )
    print("Interest group presence:")
    for group, share in place.interest_group_presence.items():
        sat = group.satisfaction.get(place, 0.0)
        print(
            f"  {group.name}: share={share:.2f}, sat={sat:.2f}, pressure={group.pressure_on(place):.2f}"
        )


def _print_satisfaction_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    print(f"\nSatisfaction in {place.name}:")
    for group in place.interest_group_presence:
        sat = group.satisfaction.get(place, 0.0)
        print(f"  {group.name}: sat={sat:.2f}, pressure={group.pressure_on(place):.2f}")


def _print_agent_snapshot(world: World, place_id) -> None:
    place = world.places[place_id]
    politicians = [
        agent for agent in world.politicians.values() if agent.place is place
    ]
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
