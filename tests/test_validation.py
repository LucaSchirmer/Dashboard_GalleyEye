import pandas as pd
import pytest
from galleyeye.constants import CATALOG, EXPECTED_FLIGHTS
from galleyeye.data import DataValidationError, load_data

def mutate(path,file,fn):
    p=path/file; df=pd.read_csv(p); fn(df); df.to_csv(p,index=False)

def rejected(path, text):
    with pytest.raises(DataValidationError,match=text): load_data(path)

def test_valid_seed_contract(bundle):
    assert set(bundle.flights.flight_id)==EXPECTED_FLIGHTS
    assert set(bundle.menu_items.item_id)==set(CATALOG)
    assert len(bundle.service)==4*len(CATALOG)

def test_missing_file(data_copy):
    (data_copy/"flights.csv").unlink(); rejected(data_copy,"required file is missing")

def test_missing_column(data_copy):
    mutate(data_copy,"flights.csv",lambda d:d.drop(columns="flight_number",inplace=True)); rejected(data_copy,"missing required column")

@pytest.mark.parametrize("file,mutation,match",[
 ("flights.csv",lambda d:d.__setitem__("flight_id",[d.flight_id.iloc[0]]*len(d)),"must be unique"),
 ("flights.csv",lambda d:d.__setitem__("origin_iata",["fra"]+d.origin_iata.iloc[1:].tolist()),"uppercase"),
 ("flights.csv",lambda d:d.__setitem__("destination_iata",[d.origin_iata.iloc[0]]+d.destination_iata.iloc[1:].tolist()),"must differ"),
 ("flights.csv",lambda d:d.__setitem__("departure_period",["Dawn"]+d.departure_period.iloc[1:].tolist()),"Day or Night"),
 ("flights.csv",lambda d:d.__setitem__("departure_date",["07/04/26"]+d.departure_date.iloc[1:].tolist()),"YYYY-MM-DD"),
 ("flights.csv",lambda d:d.__setitem__("passenger_count",[0]+d.passenger_count.iloc[1:].tolist()),"type or range"),
 ("menu_items.csv",lambda d:d.__setitem__("item_id",["Bad ID"]+d.item_id.iloc[1:].tolist()),"snake_case"),
 ("menu_items.csv",lambda d:d.__setitem__("display_name",[d.display_name.iloc[0]]*len(d)),"must be unique"),
 ("menu_items.csv",lambda d:d.__setitem__("category",["Starter"]+d.category.iloc[1:].tolist()),"invalid category"),
 ("menu_items.csv",lambda d:d.__setitem__("portion_mass_kg",[0]+d.portion_mass_kg.iloc[1:].tolist()),"greater than zero"),
 ("menu_items.csv",lambda d:d.__setitem__("unit_cost_eur",[-1]+d.unit_cost_eur.iloc[1:].tolist()),"type or range"),
 ("menu_items.csv",lambda d:d.__setitem__("binary_consumption",["yes"]+d.binary_consumption.iloc[1:].tolist()),"true or false"),
 ("flight_item_service.csv",lambda d:d.__setitem__("served_quantity",[int(d.loaded_quantity.iloc[0])+1]+d.served_quantity.iloc[1:].tolist()),"cannot exceed"),
 ("flight_item_service.csv",lambda d:d.__setitem__("loaded_quantity",[-1]+d.loaded_quantity.iloc[1:].tolist()),"type or range"),
 ("consumption_observations.csv",lambda d:d.__setitem__("consumption_estimate_pct",[101]+d.consumption_estimate_pct.iloc[1:].tolist()),"type or range"),
 ("consumption_observations.csv",lambda d:d.__setitem__("observation_id",[d.observation_id.iloc[0]]*len(d)),"must be unique"),
 ("assumptions.csv",lambda d:d.__setitem__("description",[""]+d.description.iloc[1:].tolist()),"is empty"),
])
def test_scalar_validation_rules(data_copy,file,mutation,match):
    mutate(data_copy,file,mutation); rejected(data_copy,match)

@pytest.mark.parametrize("column,value", [
    ("flight_number", "XX1"),
    ("origin_iata", "MUC"),
    ("destination_iata", "NRT"),
    ("departure_date", "2026-07-05"),
    ("departure_period", "Night"),
    ("passenger_count", 715),
])
def test_flight_catalog_validates_complete_seed_rows(data_copy, column, value):
    def wrong(d):
        d.loc[0, column] = value
    mutate(data_copy, "flights.csv", wrong)
    rejected(data_copy, "seed flight fields")


def test_flight_catalog_rejects_unknown_id(data_copy):
    mutate(data_copy,"flights.csv",lambda d:d.__setitem__("flight_id",["OTHER"]+d.flight_id.iloc[1:].tolist()))
    rejected(data_copy,"four Product")

def test_catalog_exact_and_binary_categories(data_copy):
    def wrong(d):
        d["binary_consumption"]=d.binary_consumption.astype(str).str.lower()
        d.loc[d.item_id=="coffee","binary_consumption"]="false"
    mutate(data_copy,"menu_items.csv",wrong); rejected(data_copy,"binary_consumption must be true")

def test_service_foreign_keys(data_copy):
    mutate(data_copy,"flight_item_service.csv",lambda d:d.__setitem__("flight_id",["UNKNOWN"]+d.flight_id.iloc[1:].tolist())); rejected(data_copy,"foreign key")

def test_observation_foreign_keys(data_copy):
    mutate(data_copy,"consumption_observations.csv",lambda d:d.__setitem__("item_id",["unknown"]+d.item_id.iloc[1:].tolist())); rejected(data_copy,"foreign key")

def test_service_pair_completeness(data_copy):
    p=data_copy/"flight_item_service.csv"; pd.read_csv(p).iloc[:-1].to_csv(p,index=False); rejected(data_copy,"every flight/catalog item pair")

def test_service_pair_composite_key_is_unique(data_copy):
    p=data_copy/"flight_item_service.csv"
    rows=pd.read_csv(p)
    pd.concat([rows,rows.iloc[[0]]],ignore_index=True).to_csv(p,index=False)
    rejected(data_copy,"must be unique")

def test_observation_reconciliation(data_copy):
    p=data_copy/"consumption_observations.csv"; pd.read_csv(p).iloc[:-1].to_csv(p,index=False); rejected(data_copy,"observation count must equal")

def test_binary_estimate(data_copy):
    def wrong(d): d.loc[d.item_id=="coffee","consumption_estimate_pct"]=50
    mutate(data_copy,"consumption_observations.csv",wrong); rejected(data_copy,"binary item estimate")

@pytest.mark.parametrize("column",["source_image_id","reference_image_id"])
def test_observation_traceability_ids_are_required(data_copy,column):
    def empty(d): d.loc[0,column]=""
    mutate(data_copy,"consumption_observations.csv",empty)
    rejected(data_copy,rf"required value '{column}' is empty")

@pytest.mark.parametrize("change,match",[
 (lambda d:d.drop(index=0,inplace=True),"required assumption keys"),
 (lambda d:d.__setitem__("unit",["wrong"]+d.unit.iloc[1:].tolist()),"unit must"),
 (lambda d:d.__setitem__("value",[-1]+d.value.iloc[1:].tolist()),"constraint"),
])
def test_assumption_contract(data_copy,change,match):
    mutate(data_copy,"assumptions.csv",change); rejected(data_copy,match)

def test_assumption_threshold_order(data_copy):
    def wrong(d): d.loc[d.assumption_key=="low_consumption_threshold_pct","value"]=90
    mutate(data_copy,"assumptions.csv",wrong); rejected(data_copy,"low consumption threshold")

@pytest.mark.parametrize("value",[100,0,-1,90.5])
def test_maximum_simulated_portion_reduction_range(data_copy,value):
    def wrong(d): d.loc[d.assumption_key=="maximum_simulated_portion_reduction_pct","value"]=value
    mutate(data_copy,"assumptions.csv",wrong); rejected(data_copy,"constraint")

def test_maximum_simulated_portion_reduction_unit(data_copy):
    def wrong(d): d.loc[d.assumption_key=="maximum_simulated_portion_reduction_pct","unit"]="kg"
    mutate(data_copy,"assumptions.csv",wrong); rejected(data_copy,"unit must be '%'")

def test_recommendation_reduction_cannot_exceed_simulated_maximum(data_copy):
    def wrong(d): d.loc[d.assumption_key=="maximum_simulated_portion_reduction_pct","value"]=20
    mutate(data_copy,"assumptions.csv",wrong); rejected(data_copy,"cannot exceed maximum simulated")

def test_assumption_composite_key_is_unique(data_copy):
    p=data_copy/"assumptions.csv"
    rows=pd.read_csv(p)
    pd.concat([rows,rows.iloc[[0]]],ignore_index=True).to_csv(p,index=False)
    rejected(data_copy,"must be unique")

def test_versioned_direct_co2_assumption_value_is_fixed(data_copy):
    def wrong(d): d.loc[d.assumption_key=="icao_corsia_jet_a_direct_co2_v1","value"]=2.7
    mutate(data_copy,"assumptions.csv",wrong)
    rejected(data_copy,"versioned ICAO direct CO2 factor v1 must equal 2.528")

def test_direct_co2_assumption_unit_is_validated(data_copy):
    def wrong(d): d.loc[d.assumption_key=="icao_corsia_jet_a_direct_co2_v1","unit"]="kg CO2e/L"
    mutate(data_copy,"assumptions.csv",wrong)
    rejected(data_copy,"unit must be 'kg CO2/L fuel'")

def test_direct_co2_assumption_requires_source_and_scope_description(data_copy):
    def wrong(d): d.loc[d.assumption_key=="icao_corsia_jet_a_direct_co2_v1","description"]="Generic factor."
    mutate(data_copy,"assumptions.csv",wrong)
    rejected(data_copy,"must identify its ICAO source")
