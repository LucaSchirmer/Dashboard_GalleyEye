# FSAIR Product Specification

## Product outcome

FSAIR is an offline thesis prototype that demonstrates how item-level Consumption Observations can support airline catering planning. A Catering Planner selects one simulated Flight Service, examines loading and consumption outcomes, optionally compares another flight, and receives transparent suggestions for future loading quantities and portion sizes.

The application is decision support. It explains calculated suggestions and never presents them as automatic catering decisions.

## Audience and decisions

The primary user is a Catering Planner deciding:

- how many units of each menu item to load for a comparable future flight;
- whether a served item's portion size merits reduction;
- which outcomes require more evidence before action.

## Scope

### Included

- English Streamlit application titled **FSAIR · Airline Catering Intelligence**.
- Four repository-bundled simulated Flight Services.
- One selected flight and one optional comparison flight.
- Flight-level and item-level loading, serving, consumption, waste, value, and fuel metrics.
- Recommendations based on a Comparable Flight Group.
- CSV exports of the current analysis and recommendation tables.
- Desktop-first layout targeting approximately 1440×900.
- Persistent **Simulated thesis dataset** hint and an assumptions panel.
- Offline execution with `streamlit run app.py`.

### Excluded

- Real airline or passenger data.
- Passenger nationality, age, sex, gender, or other sensitive demographics.
- Authentication, permissions, databases, and saved user decisions.
- Runtime APIs and live model inference.
- Image display, segmentation overlays, and model-quality evaluation.
- User-supplied CSV upload.
- Automatic catering decisions and claims that passengers dislike an item.
- Mobile-specific layouts and PDF report generation.

See [FUTURE_ENHANCEMENTS.md](./FUTURE_ENHANCEMENTS.md) for deferred ideas.

## Demonstration scenario

The dataset contains these fictional economy-class Flight Services:

| Flight ID | Flight number | Direction | Date | Period | Passengers |
|---|---|---|---|---|---:|
| `FRA-HND-2026-07-04-GE101` | GE101 | FRA–HND | 2026-07-04 | Day | 714 |
| `FRA-HND-2026-07-18-GE101` | GE101 | FRA–HND | 2026-07-18 | Night | 756 |
| `HND-FRA-2026-07-08-GE102` | GE102 | HND–FRA | 2026-07-08 | Day | 732 |
| `HND-FRA-2026-07-22-GE102` | GE102 | HND–FRA | 2026-07-22 | Night | 687 |

Flights with the same direction form a Comparable Flight Group. Departure period is displayed and filterable but does not determine group membership.

The simulated values deliberately create these examples:

| Item | Expected status |
|---|---|
| Chicken–Rice–Vegetables | Maintain |
| Fish–Rice–Vegetables | Consider both |
| Wrap | Reduce portion size |
| Standard Side Salad | Reduce loaded quantity |
| Coffee | Insufficient evidence |

Other menu items may resolve to any status consistent with the documented calculations. Generated data must be deterministic. The generator applies a threefold data-volume multiplier to passenger, loaded, and served quantities, producing more than 20,000 item-level Consumption Observations without adding Flight Services.

## Meal catalog

The mock data uses only the thesis catalog:

- Main Course: Chicken–Rice–Vegetables, Fish–Rice–Vegetables, Salad, Wrap
- Side Dish: Bread Roll, Standard Side Salad
- Dessert: Chocolate Cake, Vanilla Pudding with Fruit, Fruit Salad
- Beverage: Cola, Orange Juice, Water, Coffee, Tea
- Accompaniment: Butter, Cherry Jam, Plum Jam, Honey
- Snack: Cookie

The application models flexible meal composition. The mock generator alone follows the experimental tray constraints: zero or one main course, side dish, dessert, and beverage; exactly one Cookie; accompaniments only with Bread Roll. These constraints are not presented as an airline-industry standard.

## Navigation and workflows

The sidebar contains five workspaces. Analysis workspaces provide a primary Flight
Service selector and an optional comparison selector. Comparison options exclude
the primary flight. Changing either selection updates every visible metric and export.

### Command Center

Show a grid of Flight Service cards and the selected flight's three highest-impact actionable suggestions. Each priority card displays its rank, concrete change, projected mass and fuel effect, evidence strength, and an expandable explanation. Rank actionable suggestions by projected Avoidable Carried Mass.

### Flight Detail

Show flight number, direction, date, departure period, and passenger count, followed by six KPI cards:

1. Passengers
2. Loaded Items
3. Service Rate
4. Consumption Waste
5. Food Value Waste
6. Estimated Fuel Attributable to Avoidable Mass

Organize the analysis into Summary, Catering flow, Consumption, and Waste & impact tabs. Show a loaded-to-served-to-estimated-consumed funnel, Consumption Estimates, and a waste Pareto chart. When a comparison flight is selected, show normalized differences per 100 passengers. Rate differences use percentage points.

### Item Analysis

Provide category and item filters. Show:

- an item table with loaded quantity, served quantity, service rate, average consumed percentage, observation count, Unserved Mass, Consumption Waste, and Food Value Waste;
- a loaded-versus-served bar chart;
- a service-rate-versus-consumption recommendation matrix;
- a selected-versus-comparison delta table when applicable;
- a CSV download of the filtered item table.

Binary-consumption items display estimates of either 0% or 100%. Empty filter results show a neutral message rather than an exception.

### Consumption Detail

Show a Served Items × consumption-band heatmap for the primary Flight Service,
filtered by category and labeled with observation percentages. Counts remain
available in hover and an accessible table. Bands are exact `0%`, ten-percentage-
point intervals through `90%`, `>90–<100%`, and exact `100%`.

Allow one Served Item to be inspected in a full-width drill-down, defaulting to
Wrap when available. Show observation count, mean, median, interquartile range,
share at or below 10%, share at or above 75%, and exact 100%. If a comparison
Flight Service is selected, show normalized grouped distribution bars and Primary
minus Comparison summary deltas in percentage points. Raw observation counts stay
in hover. An expandable table and CSV export contain flight role, observation ID,
Consumption Estimate, source-image ID, and reference-image ID. Binary items remain
visible and are labeled as valid 0%/100% distributions. Empty states are neutral.

### Recommendations

Calculate evidence from the selected flight's Comparable Flight Group and scale quantity recommendations to the selected flight's passenger count. Show one row or card per item with:

- status;
- current and recommended loaded quantity;
- current and recommended portion mass;
- Comparable Group Flight Count, Observation-Contributing Flight Count, and Consumption Observation count;
- service rate and average consumed percentage used;
- quantity, portion, and combined weight effects;
- estimated fuel and fuel-cost effects;
- a plain-language explanation of the triggered rules.

Statuses are **Reduce loaded quantity**, **Reduce portion size**, **Consider both**, **Maintain**, and **Insufficient evidence**. A CSV download exports the full recommendation table.

The Recommendations workspace also provides a reversible scenario planner. A planner may vary loaded quantity and portion reduction within **prototype arithmetic bounds** and immediately see projected portion mass, weight, and fuel effects. These bounds describe arithmetic possibilities, not operationally validated scenarios. Scenarios never modify source data or approve a recommendation.

The workspace persistently states that nutritional requirements, packaging constraints, minimum viable portions, service standards, and catering contracts are not modeled. The maximum simulated portion reduction is an explicit `assumptions.csv` value, is shown in the assumptions panel, and is not an operational minimum-portion rule. It must remain below 100%, so a scenario cannot produce a zero-mass portion. Binary-consumption items keep portion reduction disabled.

## Presentation and interaction rules

- Use accessible colors and never rely on color alone to communicate a status.
- Use one decimal place for percentages, total kilograms, and liters; two decimals for euros and individual portion kilograms; whole units for quantities.
- Calculate with full precision and round only for display and export.
- Label operational values, costs, and fuel assumptions as simulated.
- Call model values Consumption Estimates, not ground truth.
- Refer to item-level records as observations, never people or passengers; the data contract has no passenger or complete-meal identifier.
- Call passenger-facing item counts served, not ordered.
- Prefer bar charts to pie or donut charts.
- Tables remain readable without horizontal scrolling at the target resolution where practical.

## Startup and validation

The application loads the five CSV files documented in [DATA_DICTIONARY.md](./DATA_DICTIONARY.md). Validation completes before dashboard calculations run. A validation failure produces a blocking, actionable error naming the file, row or identifier when available, and violated rule.

## Acceptance criteria

Implementation is complete when all of the following are true:

- `streamlit run app.py` starts without a network connection and loads the default flight.
- The UI contains the five specified workspaces and the simulated-data hint is always visible.
- All four specified Flight Services and only the thesis meal catalog are present.
- Selecting a flight updates all cards, charts, tables, recommendations, and downloads.
- Optional comparison excludes the selected flight and reports normalized differences correctly.
- Consumption bands cover every edge exactly once, counts reconcile to Served Items, and non-empty item shares total 100%.
- Consumption comparisons use observation percentages and keep raw counts available.
- Wrap shows low and intermediate modes, has no exact 100% observations, and remains in the moderate recommendation band.
- The five expected demonstration items produce their specified statuses.
- Quantity and portion savings are calculated sequentially without double counting.
- Binary items never receive portion-size recommendations.
- Scenario-planner results are identified as arithmetic prototypes rather than operationally validated scenarios, and no scenario produces a zero-mass portion.
- Recommendation evidence distinguishes the full Comparable Flight Group from the distinct flights that contributed observations for each item.
- Every displayed number is reproducible from the CSVs and [CALCULATIONS.md](./CALCULATIONS.md).
- Invalid fixture files exercise every blocking validation rule.
- Automated tests cover validation, formulas, thresholds, evidence gates, normalization, comparison behavior, and observation reconciliation.
- A smoke test imports or starts the Streamlit application successfully.
