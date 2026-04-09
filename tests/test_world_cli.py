from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import random
import tempfile
import unittest

import sim_test
from src.models import PlaceTier
from src.simulation import generate_world, load_world_from_directory, load_world_from_file, run_simulation


def sample_world_config() -> dict:
    return {
        "world": {"turn": 0},
        "interest_groups": [
            {"id": "workers", "name": "Workers", "fears": ["cuts"]},
            {"id": "business", "name": "Business", "fears": ["taxes"]},
        ],
        "parties": [
            {
                "id": "labor",
                "name": "Labor",
                "ideology": {"economic": -0.5, "social": 0.2},
                "directive_threshold": 0.2,
                "campaign_budget": 5,
                "leadership_interval": 5,
                "base_constituency": {"workers": 0.8, "business": 0.2},
            },
            {
                "id": "civic",
                "name": "Civic",
                "ideology": {"economic": 0.4, "social": 0.0},
                "directive_threshold": 0.2,
                "campaign_budget": 5,
                "leadership_interval": 5,
                "base_constituency": {"workers": 0.3, "business": 0.7},
            },
        ],
        "places": [
            {
                "id": "city",
                "name": "City",
                "tier": "MUNICIPALITY",
                "interest_group_presence": {"workers": 0.6, "business": 0.4},
            },
        ],
        "agents": [
            {
                "id": "mayor",
                "name": "Alex Costa",
                "party_id": "labor",
                "place_id": "city",
                "ideology": {"economic": -0.4, "social": 0.2},
                "office": "MAYOR",
                "party_role": "LEADER",
                "allegiances": {"workers": 0.7},
                "popularity": {"workers": 0.7, "business": 0.3},
                "party_standing": 0.8,
                "ambition": 0.5,
                "archetype": "LOYALIST",
                "detail_level": "L1",
            },
            {
                "id": "c1",
                "name": "Bea Lima",
                "party_id": "labor",
                "place_id": "city",
                "ideology": {"economic": -0.3, "social": 0.1},
                "office": "COUNCILPERSON",
                "allegiances": {"workers": 0.5},
                "popularity": {"workers": 0.6, "business": 0.3},
                "party_standing": 0.6,
                "ambition": 0.4,
                "archetype": "POPULIST",
                "detail_level": "L1",
            },
            {
                "id": "c2",
                "name": "Caio Melo",
                "party_id": "civic",
                "place_id": "city",
                "ideology": {"economic": 0.4, "social": 0.0},
                "office": "COUNCILPERSON",
                "allegiances": {"business": 0.8},
                "popularity": {"workers": 0.3, "business": 0.7},
                "party_standing": 0.7,
                "ambition": 0.5,
                "archetype": "IDEOLOGUE",
                "detail_level": "L1",
                "relationships": {"c1": 0.2},
            },
        ],
        "governments": [
            {
                "place_id": "city",
                "executive": {"office_type": "MAYOR", "holder_id": "mayor"},
                "legislature": {
                    "seat_type": "COUNCILPERSON",
                    "total_seats": 2,
                    "member_ids": ["c1", "c2"],
                },
                "attributes": {"election_interval": 5, "last_election_turn": 0},
            },
        ],
    }


def sample_world_toml() -> str:
    return """
[world]
turn = 0

[[interest_groups]]
id = "workers"
name = "Workers"
fears = ["cuts"]

[[interest_groups]]
id = "business"
name = "Business"
fears = ["taxes"]

[[parties]]
id = "labor"
name = "Labor"
directive_threshold = 0.2
campaign_budget = 5
leadership_interval = 5
[parties.ideology]
economic = -0.5
social = 0.2
[parties.base_constituency]
workers = 0.8
business = 0.2

[[parties]]
id = "civic"
name = "Civic"
directive_threshold = 0.2
campaign_budget = 5
leadership_interval = 5
[parties.ideology]
economic = 0.4
social = 0.0
[parties.base_constituency]
workers = 0.3
business = 0.7

[[places]]
id = "city"
name = "City"
tier = "MUNICIPALITY"
[places.interest_group_presence]
workers = 0.6
business = 0.4

[[agents]]
id = "mayor"
name = "Alex Costa"
party_id = "labor"
place_id = "city"
office = "MAYOR"
party_role = "LEADER"
party_standing = 0.8
ambition = 0.5
archetype = "LOYALIST"
detail_level = "L1"
[agents.ideology]
economic = -0.4
social = 0.2
[agents.allegiances]
workers = 0.7
[agents.popularity]
workers = 0.7
business = 0.3

[[agents]]
id = "c1"
name = "Bea Lima"
party_id = "labor"
place_id = "city"
office = "COUNCILPERSON"
party_standing = 0.6
ambition = 0.4
archetype = "POPULIST"
detail_level = "L1"
[agents.ideology]
economic = -0.3
social = 0.1
[agents.allegiances]
workers = 0.5
[agents.popularity]
workers = 0.6
business = 0.3

[[agents]]
id = "c2"
name = "Caio Melo"
party_id = "civic"
place_id = "city"
office = "COUNCILPERSON"
party_standing = 0.7
ambition = 0.5
archetype = "IDEOLOGUE"
detail_level = "L1"
[agents.ideology]
economic = 0.4
social = 0.0
[agents.allegiances]
business = 0.8
[agents.popularity]
workers = 0.3
business = 0.7
[agents.relationships]
c1 = 0.2

[[governments]]
place_id = "city"
[governments.executive]
office_type = "MAYOR"
holder_id = "mayor"
[governments.legislature]
seat_type = "COUNCILPERSON"
total_seats = 2
member_ids = ["c1", "c2"]
[governments.attributes]
election_interval = 5
last_election_turn = 0
"""


class WorldCliTests(unittest.TestCase):
    def test_load_world_from_single_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.json"
            path.write_text(json.dumps(sample_world_config()))
            world = load_world_from_file(path)

        self.assertEqual(len(world.places), 1)
        self.assertEqual(len(world.parties), 2)
        self.assertEqual(len(world.interest_groups), 2)
        self.assertEqual(len(world.governments), 1)
        self.assertIn("utility_weights", next(iter(world.politicians.values())).attributes)

    def test_load_world_from_single_toml_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.toml"
            path.write_text(sample_world_toml())
            world = load_world_from_file(path)

        self.assertEqual(len(world.politicians), 3)
        government = next(iter(world.governments.values()))
        self.assertEqual(government.legislature.total_seats, 2)

    def test_load_world_from_directory_mixed_formats(self) -> None:
        config = sample_world_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "world.toml").write_text("[world]\nturn = 0\n")
            (root / "interest_groups.json").write_text(json.dumps(config["interest_groups"]))
            (root / "parties.toml").write_text(
                """
[[parties]]
id = "labor"
name = "Labor"
directive_threshold = 0.2
campaign_budget = 5
leadership_interval = 5
[parties.ideology]
economic = -0.5
social = 0.2
[parties.base_constituency]
workers = 0.8
business = 0.2

[[parties]]
id = "civic"
name = "Civic"
directive_threshold = 0.2
campaign_budget = 5
leadership_interval = 5
[parties.ideology]
economic = 0.4
social = 0.0
[parties.base_constituency]
workers = 0.3
business = 0.7
"""
            )
            (root / "places.json").write_text(json.dumps(config["places"]))
            (root / "agents.json").write_text(json.dumps(config["agents"]))
            (root / "governments.json").write_text(json.dumps(config["governments"]))
            world = load_world_from_directory(root)

        self.assertEqual(len(world.parties), 2)
        self.assertEqual(len(world.governments), 1)

    def test_invalid_reference_fails_cleanly(self) -> None:
        config = sample_world_config()
        config["agents"][0]["party_id"] = "missing"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "world.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "party_id"):
                load_world_from_file(path)

    def test_generate_local_world_and_simulate(self) -> None:
        world = generate_world(
            "local",
            seed=7,
            num_parties=3,
            num_interest_groups=3,
            council_seats=5,
            party_election_interval=5,
            election_interval=5,
        )
        municipality_count = sum(1 for place in world.places.values() if place.tier is PlaceTier.MUNICIPALITY)
        self.assertEqual(municipality_count, 1)
        self.assertEqual(len(world.governments), 1)
        government = next(iter(world.governments.values()))
        self.assertEqual(len(government.legislature.members), 5)
        run_simulation(world, num_turns=1, rng=random.Random(7))

    def test_generate_federated_world_counts_and_stability(self) -> None:
        kwargs = {
            "num_states": 2,
            "municipalities_per_state": 2,
            "num_parties": 3,
            "num_interest_groups": 3,
            "federal_legislature_seats": 5,
            "state_legislature_seats": 4,
            "municipal_legislature_seats": 3,
            "party_election_interval": 5,
            "election_interval": 5,
        }
        world_a = generate_world("federated", seed=9, **kwargs)
        world_b = generate_world("federated", seed=9, **kwargs)

        self.assertEqual(sum(1 for place in world_a.places.values() if place.tier is PlaceTier.FEDERAL), 1)
        self.assertEqual(sum(1 for place in world_a.places.values() if place.tier is PlaceTier.STATE), 2)
        self.assertEqual(sum(1 for place in world_a.places.values() if place.tier is PlaceTier.MUNICIPALITY), 4)
        self.assertEqual(sorted(world_a.places.keys()), sorted(world_b.places.keys()))
        self.assertEqual(sorted(world_a.politicians.keys()), sorted(world_b.politicians.keys()))
        for government in world_a.governments.values():
            self.assertIsNotNone(government.executive.holder)
            if government.legislature is not None:
                self.assertEqual(len(government.legislature.members), government.legislature.total_seats)

    def test_cli_from_config_file_and_directory(self) -> None:
        config = sample_world_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            file_path = root / "world.json"
            file_path.write_text(json.dumps(config))

            directory = root / "config_dir"
            directory.mkdir()
            (directory / "world.json").write_text(json.dumps(config["world"]))
            (directory / "interest_groups.json").write_text(json.dumps(config["interest_groups"]))
            (directory / "parties.json").write_text(json.dumps(config["parties"]))
            (directory / "places.json").write_text(json.dumps(config["places"]))
            (directory / "agents.json").write_text(json.dumps(config["agents"]))
            (directory / "governments.json").write_text(json.dumps(config["governments"]))

            for config_path in (file_path, directory):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    result = sim_test.main(["from-config", "--config", str(config_path), "--turns", "0", "--summary", "short"])
                self.assertEqual(result, 0)
                self.assertIn("Initial State", buffer.getvalue())

    def test_cli_generate_profiles_end_to_end(self) -> None:
        for profile, extra_args in (
            ("local", ["--council-seats", "4"]),
            (
                "federated",
                [
                    "--num-states", "2",
                    "--municipalities-per-state", "2",
                    "--federal-legislature-seats", "5",
                    "--state-legislature-seats", "4",
                    "--municipal-legislature-seats", "3",
                ],
            ),
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                result = sim_test.main(
                    ["generate", "--profile", profile, "--turns", "1", "--summary", "short", *extra_args]
                )
            self.assertEqual(result, 0)
            self.assertIn("Final State", buffer.getvalue())

    def test_cli_invalid_argument_combinations_fail_fast(self) -> None:
        with self.assertRaises(SystemExit):
            sim_test.main(["generate", "--profile", "local", "--num-states", "2"])


if __name__ == "__main__":
    unittest.main()
