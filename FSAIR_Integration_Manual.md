# FSAIR Technical Integration Manual

**Document status:** Prototype integration manual  
**Intended audience:** Software engineers, AI-assisted development agents, and technical integrators  
**System version described:** Offline FSAIR thesis prototype  

## 1. Purpose and scope

FSAIR is an offline decision-support prototype for airline catering planning. It combines simulated flight-service records with item-level Consumption Estimates and presents the resulting loading, service, consumption, waste, weight, fuel, and cost indicators in a Streamlit dashboard. It also produces transparent suggestions for changing future loaded quantities or portion sizes.

This manual defines the technical boundary through which data enters and leaves FSAIR. It explains how an upstream image-analysis pipeline or a future cabin simulator can prepare data for the dashboard, how FSAIR validates that data, how to start and verify the application, and which restrictions apply to the present prototype.

FSAIR does not currently execute the object-detection or consumption-estimation models. It does not connect to a cabin simulator, operational airline system, database, or runtime API. The current release reads five repository-bundled CSV files and treats them as read-only. All operational values, prices, and fuel factors supplied with the prototype are simulated.

The dashboard provides decision support only. A recommendation does not approve or automatically apply a catering change.

### 1.1 Normative language

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** indicate requirements for a compatible dataset or future integration adapter.

### 1.2 Domain terminology

| Term | Meaning in FSAIR |
|---|---|
| Loaded Item | An item placed aboard for a Flight Service, whether or not it is served. |
| Served Item | An item handed to a passenger. Served quantity represents fulfilled passenger demand in the prototype. |
| Consumption Estimate | The model-predicted percentage of a Served Item's initial mass that was consumed. It is not ground truth. |
| Consumption Observation | One Consumption Estimate for one item identified in a Consumption Image. |
| Unserved Mass | Mass of Loaded Items that were not served. |
| Consumption Waste | Estimated unconsumed mass from portions that were served. |
| Decision-Support Recommendation | A suggestion for future loaded quantity or portion size; it is not an automatic decision. |

The word *ordered* is avoided in the interface contract because the prototype contains no separate catering-order table. If passenger ordering is discussed, the corresponding implemented field is `served_quantity`.

## 2. System architecture

The current integration boundary is a set of five validated CSV datasets. Operational records and model results are joined by stable flight and menu-item identifiers before dashboard calculations begin.

```text
Flight or simulator data                 Image-analysis pipeline
  - flight metadata                       - item detection
  - loaded quantities                     - item classification
  - served quantities                     - consumption estimation
            |                                      |
            +---------------+----------------------+
                            |
                            v
                 Integration/translation adapter
                  - stable identifier mapping
                  - unit and type conversion
                  - CSV contract generation
                            |
                            v
                   Five validated CSV files
                            |
                            v
                 FSAIR validation and analytics
                            |
                            v
                    Streamlit dashboard
                            |
                 +----------+-----------+
                 v                      v
        Human decision support     CSV result exports
```

The source code separates these responsibilities:

| Component | Responsibility |
|---|---|
| `app.py` | Streamlit user interface and CSV download controls |
| `galleyeye/data.py` | CSV loading and blocking validation |
| `galleyeye/analytics.py` | Metrics, comparisons, recommendations, and scenarios |
| `galleyeye/presentation.py` | Display and export formatting |
| `data/` | Five read-only input datasets |

Validation MUST finish successfully before analytics or dashboard rendering begins. FSAIR stops at the first detected contract violation and reports the affected file and, when available, the row or identifier.

## 3. Current prototype restrictions

The present release is a deterministic thesis demonstration rather than a general ingestion service. Integrators MUST account for the following restrictions:

1. The loader requires exactly the four Flight Services defined by the product specification.
2. The loader requires exactly the fixed thesis menu catalog.
3. Every flight/menu-item combination must appear once in `flight_item_service.csv`, including combinations with zero loaded and served units.
4. For each flight/menu-item combination, the number of Consumption Observations must equal `served_quantity`.
5. The application has no upload function, database, runtime API, model execution, authentication, or persistence layer.
6. Source CSV files are not modified by dashboard use or scenario planning.

Consequently, replacing the bundled data with arbitrary simulator flights will not work without adapting the validation contract in `galleyeye/data.py` and the expected flight and catalog constants in `galleyeye/constants.py`. A future production adapter SHOULD make the accepted flight and menu catalog configurable while retaining type, range, uniqueness, and referential-integrity checks.

## 4. Input data contract

All five files MUST be placed in the repository's `data/` directory. They MUST use UTF-8 encoding, a header row, comma delimiters, a period as decimal separator, and ISO 8601 dates. Machine-readable IDs MUST be used for joins; display names MUST NOT be used as join keys.

```text
flights 1 ---- * flight_item_service * ---- 1 menu_items
flights 1 ---- * consumption_observations * ---- 1 menu_items
assumptions ---- keyed configuration used by calculations
```

### 4.1 `flights.csv`

One row represents one actual Flight Service.

| Column | Type | Requirement |
|---|---|---|
| `flight_id` | string | Unique stable identifier |
| `flight_number` | string | Non-empty display value |
| `origin_iata` | string | Exactly three uppercase letters |
| `destination_iata` | string | Exactly three uppercase letters and different from origin |
| `departure_date` | date | `YYYY-MM-DD` |
| `departure_period` | enum | `Day` or `Night` |
| `passenger_count` | integer | Greater than zero |

Example:

```csv
flight_id,flight_number,origin_iata,destination_iata,departure_date,departure_period,passenger_count
FRA-HND-2026-07-04-GE101,GE101,FRA,HND,2026-07-04,Day,238
```

FSAIR derives direction as `origin_iata` + `-` + `destination_iata`. Flights with the same direction form a Comparable Flight Group for recommendation evidence.

### 4.2 `menu_items.csv`

One row represents one catalog item.

| Column | Type | Requirement |
|---|---|---|
| `item_id` | string | Unique lowercase snake-case key |
| `display_name` | string | Unique non-empty label |
| `category` | enum | Defined FSAIR food or beverage category |
| `portion_mass_kg` | decimal | Greater than zero |
| `unit_cost_eur` | decimal | Zero or greater |
| `binary_consumption` | boolean | Lowercase `true` or `false` |

Example:

```csv
item_id,display_name,category,portion_mass_kg,unit_cost_eur,binary_consumption
fish_rice_vegetables,Fish–Rice–Vegetables,Main Course,0.33,5.8,false
```

Binary-consumption items accept only 0% or 100% Consumption Estimates. In the current catalog, Beverage, Accompaniment, and Snack items are binary. Binary items cannot receive portion-size recommendations.

### 4.3 `flight_item_service.csv`

One row represents the loading and service outcome for one item on one Flight Service.

| Column | Type | Requirement |
|---|---|---|
| `flight_id` | string | Must reference `flights.csv` |
| `item_id` | string | Must reference `menu_items.csv` |
| `loaded_quantity` | integer | Zero or greater |
| `served_quantity` | integer | Zero or greater and not greater than `loaded_quantity` |

Example:

```csv
flight_id,item_id,loaded_quantity,served_quantity
FRA-HND-2026-07-04-GE101,fish_rice_vegetables,90,55
```

The composite key `(flight_id, item_id)` MUST be unique. Every flight and every catalog item MUST have one row, even when both quantities are zero. `served_quantity` is the number of fulfilled passenger item selections; it does not describe the consumed fraction.

### 4.4 `consumption_observations.csv`

One row represents one model-produced Consumption Observation for one identified Served Item.

| Column | Type | Requirement |
|---|---|---|
| `observation_id` | string | Globally unique |
| `flight_id` | string | Must reference `flights.csv` |
| `item_id` | string | Must reference `menu_items.csv` |
| `source_image_id` | string | Non-empty Consumption Image traceability label |
| `reference_image_id` | string | Non-empty reusable Reference Image label |
| `consumption_estimate_pct` | decimal | Between 0 and 100 inclusive |

Example:

```csv
observation_id,flight_id,item_id,source_image_id,reference_image_id,consumption_estimate_pct
OBS-01-fish_rice_vegetables-001,FRA-HND-2026-07-04-GE101,fish_rice_vegetables,IMG-01-001,REF-fish_rice_vegetables-01,28
```

For every `(flight_id, item_id)`, the number of observation rows MUST equal the corresponding `served_quantity`. A Reference Image MAY support multiple observations and is not interpreted as the physical earlier state of each Consumption Image.

### 4.5 `assumptions.csv`

This file stores configurable planning and simulation assumptions. Its composite key is `(assumption_key, scope)`.

| Assumption | Default | Purpose |
|---|---:|---|
| Quantity safety buffer | 10% | Added to expected served demand when recommending a load |
| Service-rate reduction threshold | 80% | Quantity reduction is considered below this rate |
| Low consumption threshold | 50% | Below this value, a 25% portion reduction is considered |
| Moderate consumption threshold | 75% | Up to and including this value, a 10% reduction is considered |
| Maximum simulated portion reduction | 90% | Prototype arithmetic scenario bound; not an operationally validated minimum portion |
| Minimum observations | 10 | Evidence gate for continuous portion recommendations |
| Fuel price | 0.80 EUR/L | Converts estimated fuel effect to simulated cost effect |
| Directional fuel factor | 0.35 or 0.33 L/kg | Converts avoidable carried mass to estimated fuel effect |
| ICAO direct CO₂ factor v1 | 2.528 kg CO2/L fuel | Converts estimated fuel savings to a simulated direct fuel-combustion CO₂ effect |

The exact required keys, scopes, units, and valid ranges are defined in the project's data dictionary. The low consumption threshold MUST be lower than the moderate threshold. `maximum_simulated_portion_reduction_pct` MUST use `%`, MUST be an integer from 1 through 99, and MUST be at least both configured recommendation reductions. It is visible in the dashboard assumptions panel.

`icao_corsia_jet_a_direct_co2_v1` is a versioned global assumption sourced from
ICAO Annex 16, Volume IV, second edition (July 2023), Part II, Chapter 2,
2.2.3. Its `2.528 kg CO2/L fuel` value is `3.16 kg CO2/kg` for Jet-A/Jet-A1
multiplied by ICAO's `0.8 kg/L` standard density. FSAIR applies it only after
the direction-specific fuel calculation. The resulting indicator covers direct
fuel-combustion CO₂ (tank-to-wake) only. It is not lifecycle CO₂e and excludes
fuel production and distribution, non-CO₂ effects, and catering production or
disposal. The versioned value, exact unit, ICAO source, direct scope, and lifecycle
exclusion are blocking validation rules. A changed factor or scope requires a new
versioned assumption. The supporting source assessment is in
`docs/research/CO2_EMISSION_FACTOR.md`.

Scenario-planner bounds describe prototype arithmetic possibilities, not operationally validated catering scenarios. Nutritional requirements, packaging constraints, minimum viable portions, service standards, and catering contracts are not modeled. The configured maximum therefore MUST NOT be interpreted as an approved operational reduction or minimum viable portion. Its below-100% range prevents a zero-mass portion. Binary-consumption items always retain their current portion mass and expose no enabled portion-reduction control.

## 5. Upstream AI integration contract

The AI bridge is not implemented in the current prototype. A future bridge is responsible for translating item-level model results into `consumption_observations.csv` without changing their meaning.

### 5.1 Required processing sequence

1. Associate each Consumption Image with a valid `flight_id`.
2. Run item detection and classification for every visible tray item.
3. Map the detected class to a valid FSAIR `item_id`.
4. Select or record the reusable Reference Image used for comparison.
5. Estimate the consumed percentage for each detected item.
6. Create a globally unique `observation_id` for each result.
7. Write one CSV row per detected item.
8. Reconcile observation counts with served quantities before starting FSAIR.

### 5.2 Field mapping

| Upstream result | FSAIR target |
|---|---|
| Flight or processing-batch association | `flight_id` |
| Normalized detected item class | `item_id` |
| Unique result identifier | `observation_id` |
| Consumption Image identifier | `source_image_id` |
| Comparison baseline identifier | `reference_image_id` |
| Estimated consumed percentage | `consumption_estimate_pct` |

The upstream adapter MUST normalize model class labels to the catalog's stable `item_id` values. It MUST NOT use display names as join keys. It SHOULD reject or quarantine unmapped classes instead of silently assigning a different item.

### 5.3 Confidence and provenance

The current input schema contains neither detector confidence nor consumption-estimation confidence. FSAIR therefore assumes that upstream results have already passed applicable quality thresholds. YOLO detection confidence is distinct from uncertainty in the consumed-percentage estimate and MUST NOT be presented as if it measured both.

A future interface SHOULD retain, at minimum, detector confidence, estimator confidence or uncertainty where available, detector and estimator model versions, processing time, and review status. These values may be stored in a staging dataset even if the present dashboard does not display them.

### 5.4 Incomplete observations

The current one-to-one reconciliation rule assumes complete image coverage and successful processing for every Served Item. Real operation may contain missing images, missed detections, rejected low-confidence results, or processing failures. Until the schema supports explicit coverage status, an adapter MUST NOT fabricate observations merely to satisfy reconciliation. Such a dataset is incompatible with the current prototype and should fail validation.

A production extension SHOULD support partial observation coverage and display the resulting evidence limitation to the Catering Planner.

## 6. Cabin-simulator integration concept

No cabin-simulator interface is available in the current project. The following section defines a technology-neutral extension concept rather than a completed integration.

The simulator adapter would provide Flight Service metadata and catering-flow data, while the image-analysis adapter would provide Consumption Observations. Both sources would use the same `flight_id` and `item_id` namespace. The adapter layer would then produce the five-table FSAIR contract or an equivalent future API payload.

Minimum simulator-side information:

- stable Flight Service identifier;
- flight number, direction, date, departure period, and passenger count;
- menu-item catalog identifiers;
- loaded quantity per item;
- served quantity per item.

Potential FSAIR outputs for the simulator environment:

- current and recommended loaded quantity;
- current and recommended portion mass;
- recommendation status and explanation;
- Comparable Group Flight Count, Observation-Contributing Flight Count, and Consumption Observation count;
- estimated avoidable carried mass;
- simulated fuel and fuel-cost effects;
- optional simulated planning estimate of direct fuel-combustion CO₂ effect, with its non-lifecycle scope.

The first simulator integration SHOULD use an adapter rather than embedding simulator-specific logic inside the analytics package. Depending on the future simulator interface, the adapter MAY exchange CSV files, call an API, query a database, or consume messages. Regardless of transport, the semantic rules in Section 4 should remain stable.

Before implementation, the simulator team must define identifier ownership, update frequency, execution trigger, error reporting, data provenance, incomplete-flight handling, and whether FSAIR recommendations are returned synchronously or stored for later review.

## 7. Installation and operation

Python 3.11 or newer is recommended.

Create and activate a virtual environment, then install the pinned dependency ranges:

```text
python -m venv .venv
python -m pip install -r requirements.txt
```

Start the application from the repository root:

```text
streamlit run app.py
```

After startup, the interface should display the simulated-data notice and open the Command Center. The five available workspaces are Command Center, Flight Detail, Item Analysis, Consumption Detail, and Recommendations.

The application runs offline after dependencies are installed. It does not upload source data, modify the five input files, or save scenario decisions.

The scenario planner is read-only and applies mass savings sequentially: quantity savings use the current portion mass, then portion savings apply only to the planned loaded quantity. Planned load is bounded by the selected flight's served and loaded quantities. Portion reduction is bounded by the explicit simulated maximum described in Section 4.5. The sidebar's optional **Show simulated direct CO₂ effect** control reveals the direct-combustion estimate beside fuel effects without changing calculations or exports. Every displayed CO₂ value is labeled as a simulated planning estimate, not a measured or realized reduction.

## 8. Output management

FSAIR provides three user-initiated CSV exports:

1. **Filtered item analysis:** `fsair_<flight_id>_items.csv`
2. **Full recommendations:** `fsair_<flight_id>_recommendations.csv`
3. **Consumption observations:** `fsair_<flight_id>_<item_id>_observations.csv`

The item-analysis export reflects the active category and item filters. It includes loading and service quantities, service rate, average Consumption Estimate, observation count, Unserved Mass, Consumption Waste, and Food Value Waste.

The Consumption Detail export contains the currently inspected item's observation-level records for the primary flight and, when selected, the comparison flight. It includes flight role, observation ID, Consumption Estimate, source-image ID, and reference-image ID.

The recommendation export contains the complete recommendation result for the selected flight, including evidence flags, current and recommended quantities and portion masses, estimated weight and fuel effects, the rounded `simulated_planning_direct_co2_effect_kg`, its `direct_co2_effect_scope`, and a plain-language rule explanation. The CO₂ fields are always exported even when the optional UI indicator is hidden. They describe a simulated planning estimate of direct fuel combustion, never a measured or realized emissions reduction or lifecycle estimate. `comparable_group_flight_count` reports the complete Comparable Flight Group size. `observation_contributing_flight_count` reports the distinct group Flight Services that supplied at least one Consumption Observation for that item. `observation_count` reports the individual observations. These fields MUST NOT be collapsed into one generic evidence-flight count. Exported recommendations remain decision-support information and MUST NOT be interpreted as approved catering instructions.

Calculations use full precision. Rounding occurs only for display and export.

## 9. Verification procedure

An integration is successful only when all applicable checks below pass:

- [ ] All five required CSV files exist in `data/`.
- [ ] Files use UTF-8, comma delimiters, headers, and period decimal separators.
- [ ] Required columns are present and non-empty.
- [ ] Primary and composite identifiers are unique.
- [ ] Every referenced flight and item exists.
- [ ] Every flight/item service pair exists exactly once.
- [ ] `served_quantity` never exceeds `loaded_quantity`.
- [ ] Every continuous Consumption Estimate is between 0 and 100.
- [ ] Every binary Consumption Estimate is exactly 0 or 100.
- [ ] Observation counts equal served quantities in the current prototype.
- [ ] All required assumption keys, scopes, and units exist.
- [ ] The maximum simulated portion reduction is an integer percentage from 1 through 99 and is not below either recommendation reduction.
- [ ] The versioned ICAO direct CO₂ factor is 2.528 `kg CO2/L fuel`, and its description states the ICAO source, direct-combustion scope, and lifecycle exclusion.
- [ ] Direction-specific fuel factors are applied before the global direct CO₂ factor; zero fuel saving gives zero CO₂ effect.
- [ ] The optional CO₂ display and recommendation export label results as simulated planning estimates, not measured or realized reductions.
- [ ] Scenario boundaries cover zero and maximum reduction, binary items, served-quantity load minimum, and loaded-quantity load maximum.
- [ ] FSAIR starts without a blocking validation error.
- [ ] Changing the selected flight updates metrics, charts, recommendations, and exports.
- [ ] A manually selected observation can be traced to its flight, item, Consumption Image, and Reference Image.

Automated verification can be run from the repository root with:

```text
python -m pytest -q
```

## 10. Troubleshooting

| Symptom | Likely cause | Corrective action |
|---|---|---|
| Required file is missing | Incorrect filename or data directory | Restore all five exact filenames under `data/` |
| Required column is missing | Adapter emitted an incompatible schema | Add the exact column name and regenerate the file |
| Foreign key does not resolve | Flight or item ID differs between files | Normalize IDs and use machine keys consistently |
| Served quantity exceeds loaded quantity | Source mapping or unit error | Correct the operational record before ingestion |
| Observation count differs from served quantity | Missing, duplicate, or failed item results | Reconcile source coverage; do not fabricate observations |
| Binary estimate is not 0 or 100 | Incompatible estimator output | Apply a documented upstream binary rule or reject the result |
| New flight or menu item is rejected | Prototype is locked to demonstration constants | Extend constants and validation deliberately, then add tests |
| Dashboard opens but an item lacks a portion recommendation | Binary item or insufficient observation evidence | Inspect item type, group coverage, and minimum observation count |

## 11. Production-extension priorities

Before using FSAIR with operational or simulator data, the following changes are recommended:

1. Replace fixed demonstration-flight and menu-catalog checks with configurable contracts.
2. Add a staging layer for model confidence, model version, provenance, and processing status.
3. Support incomplete observation coverage without treating missing estimates as zero consumption.
4. Add an explicit adapter or API boundary and integration tests.
5. Introduce persistent dataset and schema versioning.
6. Add authentication, authorization, audit history, and recommendation review if decisions are stored.
7. Validate the recommendation thresholds and simulated fuel factors with domain experts before operational interpretation.

These extensions do not change the purpose of the current prototype: demonstrating how item-level consumption evidence can be transformed into transparent catering decision support.
