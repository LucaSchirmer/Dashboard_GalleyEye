"""CSV loading and complete contract validation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import pandas as pd

from .constants import BINARY_CATEGORIES, CATALOG, CATEGORIES, DATA_FILES, EXPECTED_FLIGHT_ROWS


class DataValidationError(ValueError):
    """A blocking, actionable dataset contract violation."""


@dataclass(frozen=True)
class DataBundle:
    flights: pd.DataFrame
    menu_items: pd.DataFrame
    service: pd.DataFrame
    observations: pd.DataFrame
    assumptions: pd.DataFrame


SCHEMAS = {
    "flights.csv": ["flight_id","flight_number","origin_iata","destination_iata","departure_date","departure_period","passenger_count"],
    "menu_items.csv": ["item_id","display_name","category","portion_mass_kg","unit_cost_eur","binary_consumption"],
    "flight_item_service.csv": ["flight_id","item_id","loaded_quantity","served_quantity"],
    "consumption_observations.csv": ["observation_id","flight_id","item_id","source_image_id","reference_image_id","consumption_estimate_pct"],
    "assumptions.csv": ["assumption_key","scope","value","unit","description"],
}

ASSUMPTION_SPEC = {
    ("quantity_safety_buffer_pct","global"):("%",0,100,False),
    ("service_rate_reduction_threshold_pct","global"):("%",0,100,False),
    ("low_consumption_threshold_pct","global"):("%",0,100,False),
    ("moderate_consumption_threshold_pct","global"):("%",0,100,False),
    ("low_consumption_portion_reduction_pct","global"):("%",0,100,False),
    ("moderate_consumption_portion_reduction_pct","global"):("%",0,100,False),
    ("maximum_simulated_portion_reduction_pct","global"):("%",1,99,True),
    ("minimum_consumption_observations","global"):("count",1,None,True),
    ("fuel_price_eur_per_liter","global"):("EUR/L",0,None,False),
    ("fuel_liters_per_kg_carried","FRA-HND"):("L/kg",0,None,False),
    ("fuel_liters_per_kg_carried","HND-FRA"):("L/kg",0,None,False),
    ("icao_corsia_jet_a_direct_co2_v1","global"):("kg CO2/L fuel",0,None,False),
}

def _fail(file: str, rule: str, identifier: str | None = None) -> None:
    where = f" (row/identifier: {identifier})" if identifier is not None else ""
    raise DataValidationError(f"{file}{where}: {rule}")

def _nonempty(df, file, columns):
    for col in columns:
        bad = df[col].isna() | df[col].astype(str).str.strip().eq("")
        if bad.any(): _fail(file, f"required value '{col}' is empty", str(df.index[bad][0] + 2))

def _unique(df, file, columns):
    bad = df.duplicated(columns, keep=False)
    if bad.any(): _fail(file, f"key {columns} must be unique", " / ".join(str(df.loc[bad].iloc[0][c]) for c in columns))

def _numeric(df, file, col, integer=False, minimum=None, maximum=None):
    values = pd.to_numeric(df[col], errors="coerce")
    bad = values.isna()
    if integer: bad |= values.mod(1).ne(0)
    if minimum is not None: bad |= values.lt(minimum)
    if maximum is not None: bad |= values.gt(maximum)
    if bad.any(): _fail(file, f"'{col}' has an invalid type or range", str(df.index[bad][0] + 2))
    df[col] = values.astype("int64" if integer else "float64")

def load_data(data_dir: str | Path) -> DataBundle:
    """Load five CSVs and either return a fully valid bundle or one blocking error."""
    path = Path(data_dir)
    frames = {}
    for name in DATA_FILES:
        file = path / name
        if not file.is_file(): _fail(name, f"required file is missing at {file}")
        try: df = pd.read_csv(file, encoding="utf-8", dtype=str, keep_default_na=False)
        except Exception as exc: _fail(name, f"cannot parse UTF-8 comma-delimited CSV: {exc}")
        missing = [c for c in SCHEMAS[name] if c not in df.columns]
        if missing: _fail(name, f"missing required column(s): {', '.join(missing)}")
        df = df[SCHEMAS[name]].copy()
        _nonempty(df, name, SCHEMAS[name])
        frames[name] = df

    f, m, s, o, a = (frames[n] for n in DATA_FILES)
    _unique(f,"flights.csv",["flight_id"])
    for col in ("origin_iata","destination_iata"):
        bad = ~f[col].str.fullmatch(r"[A-Z]{3}")
        if bad.any(): _fail("flights.csv",f"'{col}' must be exactly 3 uppercase letters",f.loc[bad,"flight_id"].iloc[0])
    bad = f.origin_iata.eq(f.destination_iata)
    if bad.any(): _fail("flights.csv","origin and destination must differ",f.loc[bad,"flight_id"].iloc[0])
    bad = ~f.departure_period.isin(["Day","Night"])
    if bad.any(): _fail("flights.csv","departure_period must be Day or Night",f.loc[bad,"flight_id"].iloc[0])
    parsed_dates = pd.to_datetime(f.departure_date, format="%Y-%m-%d", errors="coerce")
    bad = parsed_dates.isna() | parsed_dates.dt.strftime("%Y-%m-%d").ne(f.departure_date)
    if bad.any(): _fail("flights.csv","departure_date must be YYYY-MM-DD",f.loc[bad,"flight_id"].iloc[0])
    f["departure_date"] = parsed_dates
    _numeric(f,"flights.csv","passenger_count",True,1)
    if set(f.flight_id) != set(EXPECTED_FLIGHT_ROWS):
        _fail("flights.csv","must contain exactly the four Product Specification Flight Services")
    seed_columns = (
        "flight_number", "origin_iata", "destination_iata", "departure_date",
        "departure_period", "passenger_count",
    )
    for row in f.itertuples(index=False):
        actual = (
            row.flight_number, row.origin_iata, row.destination_iata,
            row.departure_date.strftime("%Y-%m-%d"), row.departure_period,
            row.passenger_count,
        )
        if actual != EXPECTED_FLIGHT_ROWS[row.flight_id]:
            _fail(
                "flights.csv",
                f"seed flight fields {seed_columns} must match the Product Specification",
                row.flight_id,
            )

    _unique(m,"menu_items.csv",["item_id"]); _unique(m,"menu_items.csv",["display_name"])
    bad = ~m.item_id.str.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
    if bad.any(): _fail("menu_items.csv","item_id must be snake_case",m.loc[bad,"item_id"].iloc[0])
    bad = ~m.category.isin(CATEGORIES)
    if bad.any(): _fail("menu_items.csv","invalid category",m.loc[bad,"item_id"].iloc[0])
    _numeric(m,"menu_items.csv","portion_mass_kg",False,0); _numeric(m,"menu_items.csv","unit_cost_eur",False,0)
    if (m.portion_mass_kg <= 0).any(): _fail("menu_items.csv","portion_mass_kg must be greater than zero",m.loc[m.portion_mass_kg <= 0,"item_id"].iloc[0])
    bad = ~m.binary_consumption.isin(["true","false"])
    if bad.any(): _fail("menu_items.csv","binary_consumption must be true or false",m.loc[bad,"item_id"].iloc[0])
    m["binary_consumption"] = m.binary_consumption.eq("true")
    expected = {(k,*v) for k,v in CATALOG.items()}
    actual = set(m[["item_id","display_name","category"]].itertuples(index=False,name=None))
    if actual != expected: _fail("menu_items.csv","must contain exactly the thesis meal catalog with documented names and categories")
    bad = m.binary_consumption.ne(m.category.isin(BINARY_CATEGORIES))
    if bad.any(): _fail("menu_items.csv","binary_consumption must be true exactly for Beverage, Accompaniment, and Snack",m.loc[bad,"item_id"].iloc[0])

    _unique(s,"flight_item_service.csv",["flight_id","item_id"])
    _numeric(s,"flight_item_service.csv","loaded_quantity",True,0); _numeric(s,"flight_item_service.csv","served_quantity",True,0)
    bad = s.served_quantity.gt(s.loaded_quantity)
    if bad.any(): _fail("flight_item_service.csv","served_quantity cannot exceed loaded_quantity",f"{s.loc[bad].iloc[0].flight_id}/{s.loc[bad].iloc[0].item_id}")
    for col, valid in (("flight_id",set(f.flight_id)),("item_id",set(m.item_id))):
        bad = ~s[col].isin(valid)
        if bad.any(): _fail("flight_item_service.csv",f"foreign key '{col}' does not resolve",s.loc[bad,col].iloc[0])
    expected_pairs = pd.MultiIndex.from_product([f.flight_id,m.item_id])
    actual_pairs = pd.MultiIndex.from_frame(s[["flight_id","item_id"]])
    missing = expected_pairs.difference(actual_pairs)
    if len(missing): _fail("flight_item_service.csv","every flight/catalog item pair must occur exactly once",f"{missing[0][0]}/{missing[0][1]}")

    _unique(o,"consumption_observations.csv",["observation_id"])
    _numeric(o,"consumption_observations.csv","consumption_estimate_pct",False,0,100)
    for col, valid in (("flight_id",set(f.flight_id)),("item_id",set(m.item_id))):
        bad = ~o[col].isin(valid)
        if bad.any(): _fail("consumption_observations.csv",f"foreign key '{col}' does not resolve",o.loc[bad,"observation_id"].iloc[0])
    binary_ids = set(m.loc[m.binary_consumption,"item_id"])
    bad = o.item_id.isin(binary_ids) & ~o.consumption_estimate_pct.isin([0,100])
    if bad.any(): _fail("consumption_observations.csv","binary item estimate must be exactly 0 or 100",o.loc[bad,"observation_id"].iloc[0])
    counts = o.groupby(["flight_id","item_id"]).size().rename("observed").reset_index()
    reconciled = s.merge(counts,how="left",on=["flight_id","item_id"]).fillna({"observed":0})
    bad = reconciled.observed.ne(reconciled.served_quantity)
    if bad.any(): _fail("consumption_observations.csv","observation count must equal served_quantity",f"{reconciled.loc[bad].iloc[0].flight_id}/{reconciled.loc[bad].iloc[0].item_id}")

    _unique(a,"assumptions.csv",["assumption_key","scope"]); _numeric(a,"assumptions.csv","value")
    actual_keys = set(a[["assumption_key","scope"]].itertuples(index=False,name=None))
    if actual_keys != set(ASSUMPTION_SPEC): _fail("assumptions.csv","required assumption keys and scopes must exist exactly once")
    for idx,row in a.iterrows():
        unit,lo,hi,integer = ASSUMPTION_SPEC[(row.assumption_key,row.scope)]
        if row.unit != unit: _fail("assumptions.csv",f"unit must be '{unit}'",f"{row.assumption_key}/{row.scope}")
        if row.value < lo or (hi is not None and row.value > hi) or (integer and row.value % 1):
            _fail("assumptions.csv","value violates its documented constraint",f"{row.assumption_key}/{row.scope}")
    direct_co2 = a[a.assumption_key.eq("icao_corsia_jet_a_direct_co2_v1")].iloc[0]
    if not math.isclose(direct_co2.value, 2.528, rel_tol=0, abs_tol=1e-12):
        _fail("assumptions.csv","versioned ICAO direct CO2 factor v1 must equal 2.528",direct_co2.assumption_key)
    source_description = direct_co2.description.lower()
    if not all(term in source_description for term in ("icao", "direct fuel combustion", "lifecycle")):
        _fail("assumptions.csv","direct CO2 factor description must identify its ICAO source, direct-combustion scope, and lifecycle exclusion",direct_co2.assumption_key)
    vals = a.set_index(["assumption_key","scope"]).value
    if vals[("low_consumption_threshold_pct","global")] >= vals[("moderate_consumption_threshold_pct","global")]:
        _fail("assumptions.csv","low consumption threshold must be less than moderate threshold")
    maximum_reduction = vals[("maximum_simulated_portion_reduction_pct","global")]
    for key in ("low_consumption_portion_reduction_pct", "moderate_consumption_portion_reduction_pct"):
        if vals[(key,"global")] > maximum_reduction:
            _fail("assumptions.csv",f"{key} cannot exceed maximum simulated portion reduction")
    return DataBundle(f,m,s,o,a)

def assumption(bundle: DataBundle, key: str, scope: str = "global") -> float:
    row = bundle.assumptions[(bundle.assumptions.assumption_key == key) & (bundle.assumptions.scope == scope)]
    return float(row.value.iloc[0])
