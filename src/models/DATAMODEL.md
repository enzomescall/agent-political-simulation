# Data Model

Python data model for the political simulation. All classes are plain `dataclasses` — no external dependencies required.

## Structure

```
src/models/
├── types.py          # Shared ID types and enums
├── ideology.py       # N-dimensional ideology positions
├── place.py          # Geographic/administrative units
├── interest_group.py # Voter blocs that pressure politicians
├── party.py          # Political parties
├── agent.py          # Agent class (the core entity)
├── government.py     # Government structure per place
└── world.py          # Top-level simulation state container
```

## Core Concepts

### Ideology
A position in an n-dimensional space. Default axes are `economic` (left/right) and `social` (progressive/conservative), but any axis can be added:
```python
Ideology.create(economic=-0.6, social=0.2, environmentalism=0.8)
```
Values are in `[-1.0, 1.0]`. Use `ideology.distance(other)` or `ideology.alignment(other)` to compare positions.

### Place
The geographic hierarchy: `FEDERAL → STATE → MUNICIPALITY`. Places store interest group presence (what share of the local population each group represents) and link to their parent/children.

### InterestGroup
A voter bloc (e.g. urban workers, rural workers, wealthy elites). Each group tracks:
- **Policy preferences** — what they want and how much they care
- **Satisfaction** — per place, how happy they are with current policy outcomes
- **Electorate share** — per place, what fraction of voters they represent

`group.pressure_on(place_id)` gives a scalar representing how hard they're pushing politicians right now — high when dissatisfied *and* locally powerful.

### Party
An ideology position plus a map of affinity to interest groups (their base constituency). No party wins outright majorities by design.

### Agent
The core agent. Key attributes:
| Attribute | Type | Description |
|---|---|---|
| `ideology` | `Ideology` | Their 2D (or more) political position |
| `allegiances` | `dict[InterestGroupId, float]` | Who funds/identifies with them |
| `relationships` | `dict[AgentId, float]` | Political trust with other politicians |
| `popularity` | `dict[InterestGroupId, float]` | Approval scores per interest group |
| `party_standing` | `float` | Loyalty score (0 = rebel, 1 = loyal) |
| `ambition` | `float` | Risk-taking drive (0 = cautious, 1 = reckless) |
| `archetype` | `Archetype` | `LOYALIST`, `POPULIST`, or `IDEOLOGUE` |
| `detail_level` | `DetailLevel` | Simulation fidelity tier (L0–L3) |

### Government
Per-place structure: one executive `Office`, optional cabinet offices, and a `Legislature` (the elected body). The legislature tracks seat count and which politician agents hold those seats.

### World
The top-level container. Holds all places, parties, interest groups, politicians, and governments in dicts keyed by ID. Useful query methods:
- `world.politicians_in_place(place_id)`
- `world.party_members(party_id)`
- `world.children_of(place_id)` / `world.siblings_of(place_id)`
- `world.interest_group_pressure(group_id, place_id)`

## Extensibility
- Every entity has `attributes: dict[str, Any]` for data that doesn't fit the core schema
- `Ideology` accepts any number of axes — just add kwargs to `Ideology.create()`
- New office types, archetypes, or place tiers are just enum additions in `types.py`
- All collections in `World` are plain dicts — adding more states, parties, or groups is just `world.add_*()`
