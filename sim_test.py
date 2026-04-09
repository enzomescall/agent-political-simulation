from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys

from src.simulation import (
    generate_world,
    load_world_from_path,
    print_final_summary,
    print_world_summary,
    run_simulation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or load a political simulation world and run it.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    from_config = subparsers.add_parser(
        "from-config",
        help="Load a world from a JSON/TOML file or config directory.",
    )
    from_config.add_argument("--config", type=Path, required=True, help="Path to a config file or directory.")
    _add_common_run_args(from_config)

    generate = subparsers.add_parser(
        "generate",
        help="Generate a world from CLI parameters.",
    )
    generate.add_argument("--profile", choices=("local", "federated"), required=True)

    generate.add_argument("--num-parties", type=int)
    generate.add_argument("--num-interest-groups", type=int)
    generate.add_argument("--council-seats", type=int)

    generate.add_argument("--num-states", type=int)
    generate.add_argument("--municipalities-per-state", type=int)
    generate.add_argument("--federal-legislature-seats", type=int)
    generate.add_argument("--state-legislature-seats", type=int)
    generate.add_argument("--municipal-legislature-seats", type=int)

    generate.add_argument("--party-election-interval", type=int)
    generate.add_argument("--election-interval", type=int)
    _add_common_run_args(generate)

    return parser


def _add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for generation/simulation.")
    parser.add_argument("--debug", action="store_true", help="Write verbose simulation logs to simulation.log.")
    parser.add_argument(
        "--summary",
        choices=("short", "full"),
        default="full",
        help="How much world state to print before and after simulation.",
    )


def _validate_generate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    local_only = ("council_seats",)
    federated_only = (
        "num_states",
        "municipalities_per_state",
        "federal_legislature_seats",
        "state_legislature_seats",
        "municipal_legislature_seats",
    )
    if args.profile == "local":
        invalid = [flag for flag in federated_only if getattr(args, flag) is not None]
        if invalid:
            parser.error(
                "Profile 'local' does not accept: "
                + ", ".join(f"--{flag.replace('_', '-')}" for flag in invalid)
            )
    if args.profile == "federated":
        invalid = [flag for flag in local_only if getattr(args, flag) is not None]
        if invalid:
            parser.error(
                "Profile 'federated' does not accept: "
                + ", ".join(f"--{flag.replace('_', '-')}" for flag in invalid)
            )


def _build_generate_kwargs(args: argparse.Namespace) -> dict[str, int]:
    keys = (
        "num_parties",
        "num_interest_groups",
        "council_seats",
        "num_states",
        "municipalities_per_state",
        "federal_legislature_seats",
        "state_legislature_seats",
        "municipal_legislature_seats",
        "party_election_interval",
        "election_interval",
    )
    return {
        key: value
        for key in keys
        if (value := getattr(args, key)) is not None
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "from-config":
        world = load_world_from_path(args.config)
    else:
        _validate_generate_args(args, parser)
        world = generate_world(
            args.profile,
            seed=args.seed,
            **_build_generate_kwargs(args),
        )

    print_world_summary(world, summary=args.summary)

    if args.turns > 0:
        print(f"\nRunning {args.turns} turn(s)...\n")
        sim_rng = random.Random(args.seed)
        run_simulation(world, num_turns=args.turns, rng=sim_rng, debug=args.debug)
    else:
        print("\nSkipping simulation because --turns was set to 0.")

    print_final_summary(world, summary=args.summary, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
