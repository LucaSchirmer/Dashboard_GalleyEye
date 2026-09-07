# GalleyEye Calculations

## Conventions

All calculations use full-precision numeric values. Rounding occurs only for display and CSV export. Percent inputs are converted to fractions before multiplication. Empty denominators produce `not available`, never zero.

Selected-flight metrics use the selected Flight Service. Recommendation evidence uses its Comparable Flight Group: all Flight Services with the same origin and destination.

## Item metrics for one flight

For an item with loaded quantity `L`, served quantity `S`, portion mass `M` kg, unit cost `C` EUR, and Consumption Estimates `p_i` expressed as fractions:

```text
service_rate = S / L
average_consumed = mean(p_i)
unserved_quantity = L - S
unserved_mass_kg = (L - S) × M
consumption_waste_kg = S × M × (1 - average_consumed)
food_value_waste_eur = ((L - S) × C) + (S × C × (1 - average_consumed))
```

When `L = 0`, service rate is not available. When `S = 0`, average consumption and Consumption Waste are not available; unserved metrics remain calculable.

Flight totals sum item-level masses, values, and quantities. The flight service rate is `sum(S) / sum(L)`, not the mean of item rates.

## Consumption distribution profile

Consumption Detail analyzes one model-produced observation per Served Item. It
does not infer a person, passenger, or complete meal. Estimates use these fixed,
ordered bands:

```text
0%, >0–10%, >10–20%, >20–30%, >30–40%, >40–50%, >50–60%,
>60–70%, >70–80%, >80–90%, >90–<100%, 100%
```

Exact interval endpoints belong to the interval ending at that endpoint; exact
zero and exact 100 have their own bands. For item `j` and band `b`:

```text
band_share_pct(j,b) = observations_in_band(j,b) / all_observations(j) × 100
```

Shares sum to 100% for every item with observations. Items with no observations
retain zero counts and zero band shares, while their summary statistics are not
available. The item summary reports observation count, mean, median, quartiles,
interquartile range (`Q3 - Q1`), and shares at or below 10%, at or above 75%, and
exactly 100%. Comparison bars use observation percentages, not raw counts;
summary deltas are Primary minus Comparison in percentage points.

## Passenger normalization

For an additive flight metric `X`:

```text
X_per_100_passengers = X / passenger_count × 100
X_per_passenger = X / passenger_count
```

Comparison deltas are `selected normalized value - comparison normalized value`. Rate deltas are percentage-point differences. The UI labels the sign and unit explicitly.

## Comparable-group evidence

For each item, sum loaded and served quantities over every flight in the selected direction. Compute the group service rate from summed quantities. Compute group average consumption as the unweighted mean of individual Consumption Estimates, not a mean of flight averages.

Report two separate flight counts for each item:

- `comparable_group_flight_count` is the number of Flight Services in the selected direction's Comparable Flight Group;
- `observation_contributing_flight_count` is the number of distinct Flight Services in that group with at least one Consumption Observation for the item.

The second count can be lower than the first, including when a flight has a valid zero-served row for an item. `observation_count` remains the total number of individual Consumption Observations across contributing flights.

Quantity evidence is sufficient when load/service rows exist and loaded quantity is greater than zero for every flight in the group. A zero-load row preserves schema completeness but does not provide evidence about demand. Portion evidence is sufficient when:

- at least `minimum_consumption_observations` exist across the group; and
- each flight in the group contributes at least one observation.

An evidence failure affects only its corresponding recommendation type.

## Quantity recommendation

Let `P_g` be total passengers across the group, `S_g` total served quantity for the item, `P_t` the selected flight's passenger count, and `B` the quantity safety buffer fraction.

```text
expected_served_for_target = (S_g / P_g) × P_t
recommended_loaded_quantity = ceil(expected_served_for_target × (1 + B))
```

A quantity reduction is a candidate only when group service rate is below the configured 80% threshold and `recommended_loaded_quantity` is below the selected flight's current loaded quantity. Clamp the recommendation to the interval from the selected flight's served quantity through its current loaded quantity.

```text
recommended_loaded_quantity = max(selected_served_quantity,
                                  min(selected_loaded_quantity,
                                      recommended_loaded_quantity))
quantity_reduction_units = selected_loaded_quantity - recommended_loaded_quantity
```

## Portion recommendation

Continuous-consumption items use group average consumption:

| Average consumed | Portion action |
|---|---|
| Below 50% | Reduce by 25% |
| 50% through 75%, inclusive | Reduce by 10% |
| Above 75% | Maintain |

The exact thresholds and reductions come from `assumptions.csv`. Binary-consumption items always maintain portion size. Insufficient portion evidence yields no portion change.

```text
recommended_portion_mass_kg = current_portion_mass_kg × (1 - portion_reduction_fraction)
```

## Status precedence

Derive the displayed status from actionable changes and evidence:

| Quantity change | Portion change | Status |
|---:|---:|---|
| yes | yes | Consider both |
| yes | no | Reduce loaded quantity |
| no | yes | Reduce portion size |
| no | no, all applicable evidence sufficient | Maintain |
| no actionable change and any applicable evidence insufficient | Insufficient evidence |

For a binary item, portion evidence is not applicable and cannot cause Insufficient evidence. A plain-language explanation lists every evaluated rule, evidence count, and threshold.
When portion evidence is insufficient, its explanation reports coverage as “X of Y comparable flights contributed observations,” where X is `observation_contributing_flight_count` and Y is `comparable_group_flight_count`.

## Sequential savings

Let original load be `L`, recommended load `L_r`, original portion mass `M`, and recommended portion mass `M_r`.

```text
original_loaded_mass_kg = L × M
quantity_saving_kg = (L - L_r) × M
portion_saving_kg = L_r × (M - M_r)
combined_weight_saving_kg = quantity_saving_kg + portion_saving_kg
proposed_loaded_mass_kg = L_r × M_r
```

The identity `original_loaded_mass_kg - proposed_loaded_mass_kg = combined_weight_saving_kg` must hold within numeric tolerance. Applying portion savings only to the remaining recommended load prevents double counting.

## Fuel and direct-combustion CO₂ effects

For direction-specific factor `F` in liters per kilogram carried, fuel price `R`
in EUR per liter, and versioned global direct-combustion factor `E = 2.528 kg
CO2/L fuel`:

```text
estimated_fuel_saving_l = combined_weight_saving_kg × F
estimated_fuel_cost_saving_eur = estimated_fuel_saving_l × R
simulated_planning_direct_co2_effect_kg = estimated_fuel_saving_l × E
```

Apply `E` only after the direction-specific fuel calculation. Thus route direction
changes fuel savings and consequently the CO₂ effect, while combustion chemistry
uses one global factor. Zero fuel saving produces exactly zero CO₂ effect. Combined
quantity and portion changes continue to use the sequential mass-saving formula before
either effect is calculated.

`icao_corsia_jet_a_direct_co2_v1` derives `2.528 kg CO2/L fuel` from the ICAO
Jet-A/Jet-A1 fuel conversion factor `3.16 kg CO2/kg fuel` and ICAO standard
density `0.8 kg/L`. The normative reference is ICAO Annex 16, Volume IV,
second edition (July 2023), Part II, Chapter 2, 2.2.3. The source and academic
cross-check are documented in [CO2_EMISSION_FACTOR.md](./research/CO2_EMISSION_FACTOR.md).

The result is direct fuel-combustion CO₂ (tank-to-wake) only. It is not CO₂e
and excludes fuel production/distribution, lifecycle effects, non-CO₂ gases and
aviation effects, and catering production/disposal. The Flight Detail uses the same
formula with total Avoidable Carried Mass. Fuel and CO₂ results are simulated
planning estimates, not measured fuel burn or measured/realized emissions reductions.

## Priority ranking and scenarios

The Top 3 contains only actionable statuses: **Consider both**, **Reduce loaded quantity**, and **Reduce portion size**. Rank these by `combined_weight_saving_kg` descending, then fuel effect descending, with display name as the deterministic final tie-breaker. Ranking adds presentation priority but does not change recommendation rules.

The scenario planner applies the same sequential-savings identity to planner-entered values. Planned load is clamped between the selected flight's served and loaded quantities. For continuous-consumption items, portion reduction is clamped from 0% through `maximum_simulated_portion_reduction_pct`. The bundled prototype value is 90%; the validated range is an integer 1–99%, ensuring that a positive current portion mass remains positive. This is a simulated arithmetic bound, not an operationally validated minimum portion. Binary-consumption items always apply 0% reduction, and the UI disables their portion slider.

These scenarios model none of the nutritional requirements, packaging constraints, minimum viable portions, service standards, or catering contracts that would be needed to validate a real catering change. Scenarios are temporary, apply quantity savings before portion savings to avoid double counting, and never change recommendation or CSV data.

## Display precision

| Value | Display precision |
|---|---|
| Percentages and rates | 1 decimal place |
| Total mass | 1 decimal kg |
| Individual portion mass | 2 decimal kg |
| Money | 2 decimal EUR |
| Fuel | 1 decimal L |
| Simulated direct-combustion CO₂ effect | 1 decimal kg CO₂ |
| Quantities and observation counts | Whole units |
