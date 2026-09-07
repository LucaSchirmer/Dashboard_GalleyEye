# FSAIR

FSAIR (FSR + AI + air) is an offline thesis prototype demonstrating how visually estimated aircraft-meal consumption could support airline catering planning. It analyzes simulated loaded, served, and consumed quantities for selectable flights and produces transparent quantity and portion-size suggestions with projected weight, fuel, and cost effects.

The five workspaces provide a flight overview, Flight Detail, Item Analysis,
observation-level Consumption Detail, and Recommendations with a reversible
scenario planner. “GalleyEye” remains the name of the underlying analytics package.

All operational flight, quantity, cost, and fuel data in the prototype is simulated. The optional CO₂ indicator is a simulated planning estimate of direct jet-fuel combustion only, not a measured or realized reduction and not a lifecycle estimate. Scenario-planner bounds are prototype arithmetic possibilities, not operationally validated catering scenarios. Nutritional requirements, packaging constraints, minimum viable portions, service standards, and catering contracts are not modeled. The dashboard is decision support, not an automatic catering system.

## Documentation

- [Domain language](./CONTEXT.md)
- [Product specification](./docs/PRODUCT_SPEC.md)
- [CSV data dictionary](./docs/DATA_DICTIONARY.md)
- [Calculations and recommendation rules](./docs/CALCULATIONS.md)
- [CO₂ emission-factor source assessment](./docs/research/CO2_EMISSION_FACTOR.md)
- [Future enhancements](./docs/FUTURE_ENHANCEMENTS.md)

These documents are the implementation contract. Calculation rules belong in `docs/CALCULATIONS.md`; CSV schemas and validation rules belong in `docs/DATA_DICTIONARY.md`.

## Implementation

The finished application uses Python, Streamlit, pandas, and Plotly. Five validated,
read-only CSV datasets contain four deterministic simulated Flight Services. Domain
calculations and validation live outside the Streamlit presentation layer and are
covered by automated tests.

The deterministic dataset contains more than 20,000 item-level Consumption
Observations across the existing four Flight Services.

## Project structure

```text
app.py                         Thin Streamlit entry point and validated data loading
galleyeye/
  analytics.py                Flight metrics, comparisons, and recommendations
  consumption.py              Observation distributions and item summaries
  constants.py                Required seed flights and thesis catalog
  dashboard.py                Navigation, styling, charts, and five workspaces
  data.py                     CSV loader and blocking validation
  presentation.py             Display/export rounding
data/                          Five repository-bundled simulated CSV datasets
docs/                          Product, schema, calculation, and scope contracts
tests/                         Validation, calculation, behavior, and smoke tests
tools/generate_data.py         Deterministic dataset generator
requirements.txt               Runtime and test dependencies
```

## Install

The supported and verified interpreter is CPython 3.12 in WSL. The readable direct
dependency ranges remain in `requirements.txt`; `constraints-py312.txt` pins the
complete tested dependency set. Always let pip obtain platform-appropriate wheels.
Do not copy or install packages from `.test-deps`.

```bash
python -m venv .venv
```

In WSL:

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
python -m pip install -r requirements.txt -c constraints-py312.txt
```

## Test

```bash
python -m pytest -q
```

From Windows PowerShell in the repository, this single command uses WSL to create
an isolated CPython 3.12 environment in `/tmp`, installs the exact constrained
dependency set, checks it, runs the entire test suite, and removes the environment:

```powershell
wsl.exe bash ./tools/verify_wsl.sh
```

## Launch

```bash
streamlit run app.py
```

The dashboard runs offline after installation. It does not upload data, call runtime
APIs, save decisions, or modify the bundled CSV files.
