# GalleyEye Data Dictionary

## Contract

All application data is read-only CSV stored in the repository. UTF-8 encoding, a header row, comma delimiters, `.` decimal separators, and ISO 8601 dates are required. IDs are stable machine keys; display names are never join keys.

Relationships:

```text
flights 1 ── * flight_item_service * ── 1 menu_items
flights 1 ── * consumption_observations * ── 1 menu_items
assumptions ── keyed configuration used by calculations
```

## `flights.csv`

One row per simulated Flight Service.

| Column | Type | Required | Rules |
|---|---|---:|---|
| `flight_id` | string | yes | Unique; stable composite identifier |
| `flight_number` | string | yes | Display value, e.g. `GE101` |
| `origin_iata` | string | yes | Exactly 3 uppercase letters; `FRA` or `HND` in seed data |
| `destination_iata` | string | yes | Exactly 3 uppercase letters; differs from origin |
| `departure_date` | date | yes | `YYYY-MM-DD` |
| `departure_period` | enum | yes | `Day` or `Night` |
| `passenger_count` | integer | yes | Greater than zero |

Direction is derived as `origin_iata + "-" + destination_iata`. Comparable Flight Group membership is derived from direction.

## `menu_items.csv`

One row per catalog item.

| Column | Type | Required | Rules |
|---|---|---:|---|
| `item_id` | string | yes | Unique snake-case key |
| `display_name` | string | yes | Unique non-empty label |
| `category` | enum | yes | `Main Course`, `Side Dish`, `Dessert`, `Beverage`, `Accompaniment`, or `Snack` |
| `portion_mass_kg` | decimal | yes | Greater than zero; simulated |
| `unit_cost_eur` | decimal | yes | Zero or greater; simulated |
| `binary_consumption` | boolean | yes | CSV value `true` or `false` |

`binary_consumption=true` is required for every Beverage, Accompaniment, and Snack. It is false for the remaining seed items, including Bread Roll.

## `flight_item_service.csv`

One row per Flight Service and menu item represented in its catering plan.

| Column | Type | Required | Rules |
|---|---|---:|---|
| `flight_id` | string | yes | References `flights.flight_id` |
| `item_id` | string | yes | References `menu_items.item_id` |
| `loaded_quantity` | integer | yes | Zero or greater |
| `served_quantity` | integer | yes | Zero or greater and no greater than loaded quantity |

The composite `(flight_id, item_id)` is unique. Every flight and every catalog item has exactly one row, including zero-quantity rows.

## `consumption_observations.csv`

One row per model-produced Consumption Observation.

| Column | Type | Required | Rules |
|---|---|---:|---|
| `observation_id` | string | yes | Globally unique |
| `flight_id` | string | yes | References `flights.flight_id` |
| `item_id` | string | yes | References `menu_items.item_id` |
| `source_image_id` | string | yes | Non-empty traceability label; may be simulated |
| `reference_image_id` | string | yes | Non-empty reusable Reference Image label; may occur on many rows |
| `consumption_estimate_pct` | decimal | yes | Inclusive range 0–100 |

For binary-consumption items, `consumption_estimate_pct` is exactly `0` or `100`. For each `(flight_id, item_id)`, observation count equals `served_quantity`. A Reference Image may support many observations and is not interpreted as the physical prior state of the Consumption Image.

## `assumptions.csv`

One row per configurable simulated assumption.

| Column | Type | Required | Rules |
|---|---|---:|---|
| `assumption_key` | string | yes | Unique; must be one of the keys below |
| `scope` | string | yes | `global`, `FRA-HND`, or `HND-FRA` as specified below |
| `value` | decimal | yes | Within the constraint below |
| `unit` | string | yes | Exact unit below |
| `description` | string | yes | Non-empty user-facing explanation |

Required rows:

| Key | Scope | Default | Unit | Constraint |
|---|---|---:|---|---|
| `quantity_safety_buffer_pct` | `global` | 10 | `%` | 0–100 |
| `service_rate_reduction_threshold_pct` | `global` | 80 | `%` | 0–100 |
| `low_consumption_threshold_pct` | `global` | 50 | `%` | 0–100 and less than moderate threshold |
| `moderate_consumption_threshold_pct` | `global` | 75 | `%` | 0–100 and greater than low threshold |
| `low_consumption_portion_reduction_pct` | `global` | 25 | `%` | 0–100 |
| `moderate_consumption_portion_reduction_pct` | `global` | 10 | `%` | 0–100 |
| `maximum_simulated_portion_reduction_pct` | `global` | 90 | `%` | Integer 1–99; must be at least both configured recommendation reductions |
| `minimum_consumption_observations` | `global` | 10 | `count` | Positive integer |
| `fuel_price_eur_per_liter` | `global` | 0.80 | `EUR/L` | Zero or greater |
| `fuel_liters_per_kg_carried` | `FRA-HND` | 0.35 | `L/kg` | Zero or greater |
| `fuel_liters_per_kg_carried` | `HND-FRA` | 0.33 | `L/kg` | Zero or greater |
| `icao_corsia_jet_a_direct_co2_v1` | `global` | 2.528 | `kg CO2/L fuel` | Fixed for v1; exact ICAO source and direct-only scope required in description |

The composite `(assumption_key, scope)` is unique.

`icao_corsia_jet_a_direct_co2_v1` is deliberately versioned. Its description
identifies ICAO Annex 16 Volume IV (second edition, July 2023), the `3.16 kg
CO2/kg` Jet-A factor and `0.8 kg/L` standard density, and states that the result
is direct fuel combustion only with lifecycle and non-CO₂ effects excluded. A
different value, unit, source, or emissions boundary requires a new versioned key;
it MUST NOT silently replace v1. See the [factor research note](./research/CO2_EMISSION_FACTOR.md).

`maximum_simulated_portion_reduction_pct` is a prototype arithmetic bound. It is not an operationally validated minimum portion and does not account for nutritional requirements, packaging constraints, minimum viable portions, service standards, or catering contracts. Keeping it below 100% prevents the scenario planner from producing a zero-mass portion.

## Validation completion criteria

Loading succeeds only when:

- all five files and every required column exist;
- IDs and required composite keys are unique;
- every foreign key resolves;
- values satisfy type, enum, range, and non-null constraints;
- every flight/item service row exists exactly once;
- served quantity never exceeds loaded quantity;
- observation counts reconcile exactly to served quantities;
- binary estimates are 0 or 100;
- the complete required assumption-key set exists once at the required scope;
- all four expected seed flights and catalog items described in the product specification exist.

## Generated recommendation export

`fsair_<flight_id>_recommendations.csv` is a derived, user-initiated export rather than an input dataset. It contains the complete recommendation result for every catalog item. Its evidence fields include:

| Column | Type | Meaning |
|---|---|---|
| `comparable_group_flight_count` | integer | Number of Flight Services in the selected flight's Comparable Flight Group |
| `observation_contributing_flight_count` | integer | Number of distinct group Flight Services contributing at least one Consumption Observation for the item |
| `observation_count` | integer | Total Consumption Observations for the item across the group |
| `quantity_evidence_sufficient` | boolean | Whether every comparable flight has a positive loaded quantity for the item |
| `portion_evidence_applicable` | boolean | Whether the item uses continuous rather than binary consumption |
| `portion_evidence_sufficient` | boolean | Whether the applicable portion-evidence gates pass; remains true when portion evidence is not applicable |
| `simulated_planning_direct_co2_effect_kg` | decimal | Estimated fuel saving multiplied by the versioned ICAO direct-combustion factor; export rounds to 0.1 kg |
| `direct_co2_effect_scope` | string | Direct fuel combustion only; explicitly excludes lifecycle emissions and non-CO₂ effects |

The CO₂ column name and companion scope field identify the result as a simulated
planning estimate rather than a measured or realized emissions reduction. The export
does not contain the former ambiguous `evidence_flight_count` field. Recommendation
thresholds and status precedence are defined in [CALCULATIONS.md](./CALCULATIONS.md).
