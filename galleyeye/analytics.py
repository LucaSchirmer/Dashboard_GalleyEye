"""Pure dataframe calculations defined by docs/CALCULATIONS.md."""

from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .data import DataBundle, assumption

DIRECT_CO2_FACTOR_KEY = "icao_corsia_jet_a_direct_co2_v1"
DIRECT_CO2_SCOPE = "Direct fuel combustion only; excludes lifecycle emissions and non-CO2 effects."


def flight_record(bundle: DataBundle, flight_id: str) -> pd.Series:
    rows = bundle.flights[bundle.flights.flight_id == flight_id]
    if rows.empty: raise KeyError(f"Unknown Flight Service: {flight_id}")
    row = rows.iloc[0].copy()
    row["direction"] = f"{row.origin_iata}-{row.destination_iata}"
    return row

def item_metrics(bundle: DataBundle, flight_id: str) -> pd.DataFrame:
    """Return all catalog items and their selected-flight operational metrics."""
    service = bundle.service[bundle.service.flight_id == flight_id]
    df = service.merge(bundle.menu_items,on="item_id",validate="one_to_one")
    obs = (bundle.observations[bundle.observations.flight_id == flight_id]
           .groupby("item_id").consumption_estimate_pct.agg([("observation_count","size"),("average_consumed_pct","mean")]).reset_index())
    df = df.merge(obs,on="item_id",how="left")
    df["observation_count"] = df.observation_count.fillna(0).astype(int)
    df["service_rate_pct"] = np.where(df.loaded_quantity > 0, df.served_quantity / df.loaded_quantity * 100, np.nan)
    df["unserved_quantity"] = df.loaded_quantity - df.served_quantity
    df["unserved_mass_kg"] = df.unserved_quantity * df.portion_mass_kg
    df["consumption_waste_kg"] = np.where(df.served_quantity > 0,
        df.served_quantity * df.portion_mass_kg * (1 - df.average_consumed_pct / 100), np.nan)
    df["food_value_waste_eur"] = ((df.loaded_quantity-df.served_quantity)*df.unit_cost_eur +
        np.where(df.served_quantity > 0,df.served_quantity*df.unit_cost_eur*(1-df.average_consumed_pct/100),0))
    return df.sort_values(["category","display_name"]).reset_index(drop=True)

def recommendations(bundle: DataBundle, selected_flight_id: str) -> pd.DataFrame:
    selected = flight_record(bundle,selected_flight_id)
    direction = selected.direction
    group_flights = bundle.flights[(bundle.flights.origin_iata == selected.origin_iata) &
                                    (bundle.flights.destination_iata == selected.destination_iata)]
    group_ids = set(group_flights.flight_id)
    group_service = bundle.service[bundle.service.flight_id.isin(group_ids)]
    group_obs = bundle.observations[bundle.observations.flight_id.isin(group_ids)]
    current = item_metrics(bundle,selected_flight_id).set_index("item_id")
    buffer = assumption(bundle,"quantity_safety_buffer_pct")/100
    sr_threshold = assumption(bundle,"service_rate_reduction_threshold_pct")
    low = assumption(bundle,"low_consumption_threshold_pct")
    moderate = assumption(bundle,"moderate_consumption_threshold_pct")
    low_reduction = assumption(bundle,"low_consumption_portion_reduction_pct")/100
    moderate_reduction = assumption(bundle,"moderate_consumption_portion_reduction_pct")/100
    minimum_obs = int(assumption(bundle,"minimum_consumption_observations"))
    fuel_factor = assumption(bundle,"fuel_liters_per_kg_carried",direction)
    fuel_price = assumption(bundle,"fuel_price_eur_per_liter")
    direct_co2_factor = assumption(bundle,DIRECT_CO2_FACTOR_KEY)
    total_passengers = int(group_flights.passenger_count.sum())
    rows=[]
    for item in bundle.menu_items.itertuples(index=False):
        gs = group_service[group_service.item_id == item.item_id]
        go = group_obs[group_obs.item_id == item.item_id]
        cur = current.loc[item.item_id]
        loaded, served = int(gs.loaded_quantity.sum()), int(gs.served_quantity.sum())
        group_rate = served/loaded*100 if loaded else np.nan
        avg = float(go.consumption_estimate_pct.mean()) if len(go) else np.nan
        per_flight_rows = gs.set_index("flight_id").reindex(group_flights.flight_id)
        quantity_evidence = len(per_flight_rows)==len(group_flights) and per_flight_rows.loaded_quantity.notna().all() and (per_flight_rows.loaded_quantity>0).all()
        obs_flights = set(go.flight_id)
        comparable_group_flight_count = len(group_flights)
        observation_contributing_flight_count = len(obs_flights)
        portion_applicable = not item.binary_consumption
        portion_evidence = len(go)>=minimum_obs and group_ids.issubset(obs_flights) if portion_applicable else True

        rec_load = int(cur.loaded_quantity)
        if quantity_evidence:
            raw = math.ceil((served/total_passengers)*int(selected.passenger_count)*(1+buffer))
            candidate = max(int(cur.served_quantity),min(int(cur.loaded_quantity),raw))
            if group_rate < sr_threshold and candidate < int(cur.loaded_quantity): rec_load=candidate
        quantity_change = rec_load < int(cur.loaded_quantity)

        reduction=0.0
        if portion_applicable and portion_evidence:
            if avg < low: reduction=low_reduction
            elif avg <= moderate: reduction=moderate_reduction
        rec_mass = float(item.portion_mass_kg)*(1-reduction)
        portion_change = reduction>0
        applicable_sufficient = quantity_evidence and (portion_evidence if portion_applicable else True)
        if quantity_change and portion_change: status="Consider both"
        elif quantity_change: status="Reduce loaded quantity"
        elif portion_change: status="Reduce portion size"
        elif applicable_sufficient: status="Maintain"
        else: status="Insufficient evidence"

        quantity_saving=(int(cur.loaded_quantity)-rec_load)*float(item.portion_mass_kg)
        portion_saving=rec_load*(float(item.portion_mass_kg)-rec_mass)
        combined=quantity_saving+portion_saving
        explanations=[]
        if quantity_evidence:
            explanations.append(f"Quantity evidence: {len(group_flights)} flights; group service rate {group_rate:.1f}% versus {sr_threshold:.1f}% threshold.")
        else:
            explanations.append(f"Quantity evidence insufficient: each of {len(group_flights)} group flights must have a positive load.")
        if not portion_applicable:
            explanations.append("Portion rule not applicable because consumption is binary.")
        elif portion_evidence:
            explanations.append(
                f"Portion evidence: {len(go)} observations; "
                f"{observation_contributing_flight_count} of {comparable_group_flight_count} comparable flights contributed observations. "
                f"Average consumed {avg:.1f}% (thresholds {low:.1f}% and {moderate:.1f}%)."
            )
        else:
            explanations.append(
                f"Portion evidence insufficient: {len(go)} observations; "
                f"{observation_contributing_flight_count} of {comparable_group_flight_count} comparable flights contributed observations. "
                f"Minimum {minimum_obs} observations and every comparable flight required."
            )
        estimated_fuel_saving_l=combined*fuel_factor
        rows.append({
            "item_id":item.item_id,"display_name":item.display_name,"category":item.category,"status":status,
            "current_loaded_quantity":int(cur.loaded_quantity),"recommended_loaded_quantity":rec_load,
            "current_portion_mass_kg":float(item.portion_mass_kg),"recommended_portion_mass_kg":rec_mass,
            "comparable_group_flight_count":comparable_group_flight_count,
            "observation_contributing_flight_count":observation_contributing_flight_count,
            "observation_count":len(go),
            "quantity_evidence_sufficient":bool(quantity_evidence),"portion_evidence_applicable":bool(portion_applicable),
            "portion_evidence_sufficient":bool(portion_evidence),"group_service_rate_pct":group_rate,
            "group_average_consumed_pct":avg,"quantity_reduction_units":int(cur.loaded_quantity)-rec_load,
            "portion_reduction_pct":reduction*100,"quantity_saving_kg":quantity_saving,
            "portion_saving_kg":portion_saving,"combined_weight_saving_kg":combined,
            "proposed_loaded_mass_kg":rec_load*rec_mass,"estimated_fuel_saving_l":estimated_fuel_saving_l,
            "estimated_fuel_cost_saving_eur":estimated_fuel_saving_l*fuel_price,
            "simulated_planning_direct_co2_effect_kg":estimated_fuel_saving_l*direct_co2_factor,
            "direct_co2_effect_scope":DIRECT_CO2_SCOPE,"explanation":" ".join(explanations)
        })
    return pd.DataFrame(rows).sort_values(["category","display_name"]).reset_index(drop=True)

def priority_recommendations(bundle: DataBundle, selected_flight_id: str, limit: int = 3) -> pd.DataFrame:
    """Rank actionable suggestions by avoidable mass, with evidence as a guardrail."""
    recs = recommendations(bundle, selected_flight_id).copy()
    actionable = recs[recs.status.isin([
        "Consider both", "Reduce loaded quantity", "Reduce portion size"
    ])].copy()
    actionable["evidence_strength"] = np.where(
        actionable.quantity_evidence_sufficient
        & (~actionable.portion_evidence_applicable | actionable.portion_evidence_sufficient),
        "Strong", "Limited"
    )
    actionable["priority_score"] = actionable.combined_weight_saving_kg
    actionable = actionable.sort_values(
        ["priority_score", "estimated_fuel_saving_l", "display_name"],
        ascending=[False, False, True],
    ).head(limit).reset_index(drop=True)
    actionable.insert(0, "priority_rank", range(1, len(actionable) + 1))
    return actionable

def scenario_impact(bundle: DataBundle, selected_flight_id: str, item_id: str,
                    planned_load: int, portion_reduction_pct: float) -> dict:
    """Calculate a planner-entered arithmetic scenario without changing source data."""
    current = item_metrics(bundle, selected_flight_id).set_index("item_id").loc[item_id]
    flight = flight_record(bundle, selected_flight_id)
    load = max(int(current.served_quantity), min(int(current.loaded_quantity), int(planned_load)))
    maximum_reduction = assumption(bundle, "maximum_simulated_portion_reduction_pct")
    requested_reduction = 0.0 if bool(current.binary_consumption) else float(portion_reduction_pct)
    reduction_pct = max(0.0, min(maximum_reduction, requested_reduction))
    reduction = reduction_pct / 100
    new_mass = float(current.portion_mass_kg) * (1 - reduction)
    quantity_saving = (int(current.loaded_quantity) - load) * float(current.portion_mass_kg)
    portion_saving = load * (float(current.portion_mass_kg) - new_mass)
    weight = quantity_saving + portion_saving
    factor = assumption(bundle, "fuel_liters_per_kg_carried", flight.direction)
    price = assumption(bundle, "fuel_price_eur_per_liter")
    direct_co2_factor = assumption(bundle, DIRECT_CO2_FACTOR_KEY)
    fuel_saving = weight * factor
    return {
        "planned_load": load,
        "applied_portion_reduction_pct": reduction_pct,
        "planned_portion_mass_kg": new_mass,
        "quantity_saving_kg": quantity_saving,
        "portion_saving_kg": portion_saving,
        "combined_weight_saving_kg": weight,
        "estimated_fuel_saving_l": fuel_saving,
        "estimated_fuel_cost_saving_eur": fuel_saving * price,
        "simulated_planning_direct_co2_effect_kg": fuel_saving * direct_co2_factor,
        "direct_co2_effect_scope": DIRECT_CO2_SCOPE,
    }

def flight_summary(bundle: DataBundle, flight_id: str) -> dict:
    items=item_metrics(bundle,flight_id); flight=flight_record(bundle,flight_id)
    loaded=int(items.loaded_quantity.sum()); served=int(items.served_quantity.sum())
    recs=recommendations(bundle,flight_id)
    avoidable=float(recs.combined_weight_saving_kg.sum())
    direction=flight.direction
    factor=assumption(bundle,"fuel_liters_per_kg_carried",direction)
    fuel_effect=avoidable*factor
    direct_co2_factor=assumption(bundle,DIRECT_CO2_FACTOR_KEY)
    return {"passengers":int(flight.passenger_count),"loaded_items":loaded,
            "served_items":served,"service_rate_pct":served/loaded*100 if loaded else np.nan,
            "unserved_mass_kg":float(items.unserved_mass_kg.sum()),
            "consumption_waste_kg":float(items.consumption_waste_kg.sum(skipna=True)),
            "food_value_waste_eur":float(items.food_value_waste_eur.sum()),
            "avoidable_carried_mass_kg":avoidable,"estimated_fuel_attributable_l":fuel_effect,
            "simulated_planning_direct_co2_effect_kg":fuel_effect*direct_co2_factor}

ADDITIVE = ["loaded_items","served_items","unserved_mass_kg","consumption_waste_kg","food_value_waste_eur","avoidable_carried_mass_kg","estimated_fuel_attributable_l","simulated_planning_direct_co2_effect_kg"]

def flight_comparison(bundle: DataBundle, selected_id: str, comparison_id: str) -> pd.DataFrame:
    """Selected minus comparison, normalized per 100 passengers; rates in points."""
    selected, comparison = flight_summary(bundle,selected_id), flight_summary(bundle,comparison_id)
    rows=[]
    for metric in ADDITIVE:
        s=selected[metric]/selected["passengers"]*100; c=comparison[metric]/comparison["passengers"]*100
        rows.append({"metric":metric,"selected_per_100":s,"comparison_per_100":c,"delta":s-c,"unit":"per 100 passengers"})
    rows.append({"metric":"service_rate_pct","selected_per_100":selected["service_rate_pct"],
                 "comparison_per_100":comparison["service_rate_pct"],"delta":selected["service_rate_pct"]-comparison["service_rate_pct"],"unit":"percentage points"})
    return pd.DataFrame(rows)

def item_comparison(bundle: DataBundle, selected_id: str, comparison_id: str) -> pd.DataFrame:
    """Item deltas normalized per 100 passengers; service rates in points."""
    sf=flight_record(bundle,selected_id); cf=flight_record(bundle,comparison_id)
    s=item_metrics(bundle,selected_id); c=item_metrics(bundle,comparison_id)
    cols=["item_id","display_name","loaded_quantity","served_quantity","unserved_mass_kg","consumption_waste_kg","food_value_waste_eur","service_rate_pct","average_consumed_pct"]
    x=s[cols].merge(c[cols],on="item_id",suffixes=("_selected","_comparison"))
    out=pd.DataFrame({"item_id":x.item_id,"display_name":x.display_name_selected})
    for col in ["loaded_quantity","served_quantity","unserved_mass_kg","consumption_waste_kg","food_value_waste_eur"]:
        out[f"{col}_delta_per_100"] = x[f"{col}_selected"]/sf.passenger_count*100-x[f"{col}_comparison"]/cf.passenger_count*100
    out["service_rate_delta_pp"]=x.service_rate_pct_selected-x.service_rate_pct_comparison
    out["average_consumed_delta_pp"]=x.average_consumed_pct_selected-x.average_consumed_pct_comparison
    return out
