from dataclasses import replace
from io import BytesIO
import math
import numpy as np
import pandas as pd
from galleyeye.analytics import (flight_comparison, flight_summary, item_comparison,
                                 item_metrics, priority_recommendations,
                                 recommendations, scenario_impact)
from galleyeye.presentation import export_csv

FID="FRA-HND-2026-07-04-GE101"

def test_item_formulas(bundle):
    row=item_metrics(bundle,FID).set_index("item_id").loc["fish_rice_vegetables"]
    assert row.service_rate_pct==row.served_quantity/row.loaded_quantity*100
    assert row.unserved_mass_kg==(row.loaded_quantity-row.served_quantity)*row.portion_mass_kg
    assert row.consumption_waste_kg==row.served_quantity*row.portion_mass_kg*(1-row.average_consumed_pct/100)
    expected=(row.loaded_quantity-row.served_quantity)*row.unit_cost_eur+row.served_quantity*row.unit_cost_eur*(1-row.average_consumed_pct/100)
    assert row.food_value_waste_eur==expected

def test_flight_service_rate_is_ratio_of_totals(bundle):
    rows=item_metrics(bundle,FID); summary=flight_summary(bundle,FID)
    assert summary["service_rate_pct"]==rows.served_quantity.sum()/rows.loaded_quantity.sum()*100
    assert not math.isclose(summary["service_rate_pct"],rows.service_rate_pct.mean())

def test_zero_denominators_are_not_available(bundle):
    rows=item_metrics(bundle,"FRA-HND-2026-07-18-GE101").set_index("item_id")
    assert np.isnan(rows.loc["coffee","service_rate_pct"])
    assert np.isnan(rows.loc["coffee","average_consumed_pct"])
    assert np.isnan(rows.loc["coffee","consumption_waste_kg"])

def test_required_demonstration_statuses(bundle):
    r=recommendations(bundle,FID).set_index("display_name")
    expected={"Chicken–Rice–Vegetables":"Maintain","Fish–Rice–Vegetables":"Consider both",
              "Wrap":"Reduce portion size","Standard Side Salad":"Reduce loaded quantity","Coffee":"Insufficient evidence"}
    assert r.status.loc[list(expected)].to_dict()==expected

def test_binary_items_never_change_portion(bundle):
    r=recommendations(bundle,FID); binary=set(bundle.menu_items.loc[bundle.menu_items.binary_consumption,"item_id"])
    assert (r[r.item_id.isin(binary)].portion_reduction_pct==0).all()
    assert (r[r.item_id.isin(binary)].recommended_portion_mass_kg==r[r.item_id.isin(binary)].current_portion_mass_kg).all()

def test_quantity_formula_clamp_and_threshold(bundle):
    r=recommendations(bundle,FID).set_index("item_id").loc["standard_side_salad"]
    assert r.recommended_loaded_quantity>=bundle.service.query("flight_id==@FID and item_id=='standard_side_salad'").served_quantity.iloc[0]
    assert r.recommended_loaded_quantity<r.current_loaded_quantity
    assert r.group_service_rate_pct<80

def test_portion_threshold_rules(bundle):
    r=recommendations(bundle,FID).set_index("item_id")
    assert r.loc["fish_rice_vegetables","portion_reduction_pct"]==25
    assert r.loc["wrap","portion_reduction_pct"]==10
    assert r.loc["chicken_rice_vegetables","portion_reduction_pct"]==0

def test_sequential_savings_identity(bundle):
    r=recommendations(bundle,FID)
    original=r.current_loaded_quantity*r.current_portion_mass_kg
    assert np.allclose(original-r.proposed_loaded_mass_kg,r.combined_weight_saving_kg)
    assert np.allclose(r.combined_weight_saving_kg,r.quantity_saving_kg+r.portion_saving_kg)

def test_fuel_effects(bundle):
    r=recommendations(bundle,FID)
    assert np.allclose(r.estimated_fuel_saving_l,r.combined_weight_saving_kg*.35)
    assert np.allclose(r.estimated_fuel_cost_saving_eur,r.estimated_fuel_saving_l*.80)

def test_direct_co2_uses_direction_specific_fuel_before_global_emission_factor(bundle):
    outbound=recommendations(bundle,FID)
    inbound=recommendations(bundle,"HND-FRA-2026-07-08-GE102")
    assert np.allclose(outbound.estimated_fuel_saving_l,outbound.combined_weight_saving_kg*.35)
    assert np.allclose(inbound.estimated_fuel_saving_l,inbound.combined_weight_saving_kg*.33)
    assert np.allclose(
        outbound.simulated_planning_direct_co2_effect_kg,
        outbound.estimated_fuel_saving_l*2.528,
    )
    assert np.allclose(
        inbound.simulated_planning_direct_co2_effect_kg,
        inbound.estimated_fuel_saving_l*2.528,
    )

def test_zero_savings_produces_zero_direct_co2_effect(bundle):
    maintained=recommendations(bundle,FID).query("combined_weight_saving_kg == 0")
    assert not maintained.empty
    assert (maintained.estimated_fuel_saving_l==0).all()
    assert (maintained.simulated_planning_direct_co2_effect_kg==0).all()

def test_combined_quantity_and_portion_change_has_sequential_direct_co2_effect(bundle):
    both=recommendations(bundle,FID).set_index("item_id").loc["fish_rice_vegetables"]
    assert both.status=="Consider both"
    assert both.quantity_saving_kg>0 and both.portion_saving_kg>0
    expected=(both.quantity_saving_kg+both.portion_saving_kg)*.35*2.528
    assert math.isclose(both.simulated_planning_direct_co2_effect_kg,expected)
    assert both.direct_co2_effect_scope.startswith("Direct fuel combustion only")

def test_normalized_comparison_and_rate_points(bundle):
    other="FRA-HND-2026-07-18-GE101"; comp=flight_comparison(bundle,FID,other).set_index("metric")
    s=flight_summary(bundle,FID); c=flight_summary(bundle,other)
    assert comp.loc["loaded_items","delta"]==s["loaded_items"]/s["passengers"]*100-c["loaded_items"]/c["passengers"]*100
    assert comp.loc["service_rate_pct","delta"]==s["service_rate_pct"]-c["service_rate_pct"]
    assert comp.loc["service_rate_pct","unit"]=="percentage points"

def test_item_comparison_changes_with_selection(bundle):
    a=item_comparison(bundle,FID,"FRA-HND-2026-07-18-GE101")
    b=item_comparison(bundle,"HND-FRA-2026-07-08-GE102",FID)
    assert not a.loaded_quantity_delta_per_100.equals(b.loaded_quantity_delta_per_100)

def test_group_consumption_is_unweighted_observation_mean(bundle):
    r=recommendations(bundle,FID).set_index("item_id").loc["wrap"]
    ids={"FRA-HND-2026-07-04-GE101","FRA-HND-2026-07-18-GE101"}
    raw=bundle.observations.query("flight_id in @ids and item_id=='wrap'").consumption_estimate_pct.mean()
    assert r.group_average_consumed_pct==raw

def test_evidence_gates_are_separate(bundle):
    r=recommendations(bundle,FID).set_index("item_id")
    assert not r.loc["coffee","quantity_evidence_sufficient"]
    assert not r.loc["coffee","portion_evidence_applicable"]
    assert r.loc["coffee","portion_evidence_sufficient"]
    assert r.loc["wrap","quantity_evidence_sufficient"] and r.loc["wrap","portion_evidence_sufficient"]

def test_complete_portion_evidence_reports_group_and_contributing_flight_counts(bundle):
    recommendations_table=recommendations(bundle,FID)
    wrap=recommendations_table.set_index("item_id").loc["wrap"]
    assert wrap.comparable_group_flight_count==2
    assert wrap.observation_contributing_flight_count==2
    assert "2 of 2 comparable flights contributed observations." in wrap.explanation
    assert "evidence_flight_count" not in recommendations_table.columns

def test_incomplete_observation_coverage_reports_distinct_contributing_flights(bundle):
    other="FRA-HND-2026-07-18-GE101"
    observations=bundle.observations[
        ~(bundle.observations.flight_id.eq(other) & bundle.observations.item_id.eq("wrap"))
    ].copy()
    incomplete=replace(bundle,observations=observations)
    wrap=recommendations(incomplete,FID).set_index("item_id").loc["wrap"]
    assert wrap.comparable_group_flight_count==2
    assert wrap.observation_contributing_flight_count==1
    assert not wrap.portion_evidence_sufficient
    assert "1 of 2 comparable flights contributed observations." in wrap.explanation

def test_binary_item_counts_observation_contributors_without_changing_evidence_rules(bundle):
    coffee=recommendations(bundle,FID).set_index("item_id").loc["coffee"]
    assert coffee.comparable_group_flight_count==2
    assert coffee.observation_contributing_flight_count==1
    assert not coffee.portion_evidence_applicable
    assert coffee.portion_evidence_sufficient
    assert coffee.portion_reduction_pct==0

def test_recommendation_csv_exports_both_flight_counts(bundle):
    exported=pd.read_csv(BytesIO(export_csv(recommendations(bundle,FID))))
    assert "comparable_group_flight_count" in exported.columns
    assert "observation_contributing_flight_count" in exported.columns
    assert "evidence_flight_count" not in exported.columns
    wrap=exported.set_index("item_id").loc["wrap"]
    assert wrap.comparable_group_flight_count==2
    assert wrap.observation_contributing_flight_count==2

def test_recommendation_csv_exports_rounded_labeled_direct_co2_effect(bundle):
    raw=recommendations(bundle,FID)
    exported=pd.read_csv(BytesIO(export_csv(raw)))
    column="simulated_planning_direct_co2_effect_kg"
    assert column in exported.columns
    assert "direct_co2_effect_scope" in exported.columns
    assert np.allclose(exported[column],raw[column].round(1))
    assert exported.direct_co2_effect_scope.str.contains("excludes lifecycle").all()

def test_priorities_are_actionable_and_ranked_by_weight(bundle):
    priorities=priority_recommendations(bundle,FID)
    assert priorities.priority_rank.tolist()==[1,2,3]
    assert priorities.status.isin({"Consider both","Reduce loaded quantity","Reduce portion size"}).all()
    assert priorities.combined_weight_saving_kg.is_monotonic_decreasing

def test_scenario_zero_reduction_boundary(bundle):
    current=item_metrics(bundle,FID).set_index("item_id").loc["wrap"]
    result=scenario_impact(bundle,FID,"wrap",current.loaded_quantity,0)
    assert result["planned_load"]==current.loaded_quantity
    assert result["applied_portion_reduction_pct"]==0
    assert result["planned_portion_mass_kg"]==current.portion_mass_kg
    assert result["combined_weight_saving_kg"]==0
    assert result["simulated_planning_direct_co2_effect_kg"]==0

def test_scenario_maximum_reduction_boundary_prevents_zero_mass(bundle):
    current=item_metrics(bundle,FID).set_index("item_id").loc["wrap"]
    result=scenario_impact(bundle,FID,"wrap",current.loaded_quantity,100)
    assert result["applied_portion_reduction_pct"]==90
    assert math.isclose(result["planned_portion_mass_kg"],current.portion_mass_kg*.10)
    assert result["planned_portion_mass_kg"]>0

def test_scenario_binary_item_disables_portion_reduction_in_calculation(bundle):
    current=item_metrics(bundle,FID).set_index("item_id").loc["cola"]
    result=scenario_impact(bundle,FID,"cola",current.loaded_quantity,90)
    assert result["applied_portion_reduction_pct"]==0
    assert result["planned_portion_mass_kg"]==current.portion_mass_kg
    assert result["portion_saving_kg"]==0

def test_scenario_load_minimum_is_served_quantity(bundle):
    current=item_metrics(bundle,FID).set_index("item_id").loc["wrap"]
    result=scenario_impact(bundle,FID,"wrap",0,0)
    assert result["planned_load"]==current.served_quantity
    expected=(current.loaded_quantity-current.served_quantity)*current.portion_mass_kg
    assert math.isclose(result["combined_weight_saving_kg"],expected)
    assert math.isclose(result["estimated_fuel_saving_l"],expected*.35)

def test_scenario_load_maximum_is_loaded_quantity_and_savings_remain_sequential(bundle):
    current=item_metrics(bundle,FID).set_index("item_id").loc["wrap"]
    result=scenario_impact(bundle,FID,"wrap",current.loaded_quantity+100,10)
    assert result["planned_load"]==current.loaded_quantity
    expected=current.loaded_quantity*current.portion_mass_kg*.10
    assert math.isclose(result["combined_weight_saving_kg"],expected)
    assert math.isclose(result["combined_weight_saving_kg"],result["quantity_saving_kg"]+result["portion_saving_kg"])
