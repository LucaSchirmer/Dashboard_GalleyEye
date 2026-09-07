from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_streamlit_app_loads_default_flight():
    app=Path(__file__).resolve().parents[1]/"app.py"
    at=AppTest.from_file(str(app),default_timeout=45).run()
    assert not at.exception
    assert any("FSAIR" in x.value for x in at.markdown)
    assert any("Simulated thesis dataset" in x.value for x in at.caption)
    assert any("Top 3 priorities to change" in x.value for x in at.subheader)
    assert len(at.metric)>=6
    overview_buttons=[button for button in at.button if button.label=="Open flight detail"]
    assert len(overview_buttons)==4

def test_analysis_pages_render_primary_and_secondary_flights_side_by_side():
    app=Path(__file__).resolve().parents[1]/"app.py"
    at=AppTest.from_file(str(app),default_timeout=45).run()
    assert not at.selectbox

    at.radio[0].set_value("Flight Detail").run()
    primary=next(box for box in at.selectbox if box.label=="Primary Flight Service")
    comparison=next(box for box in at.selectbox if box.label=="Compare with (optional)")
    original_primary=primary.value
    other="FRA-HND-2026-07-18-GE101"
    assert len(comparison.options)==4  # None plus every non-primary flight
    comparison.set_value(other).run()
    assert not at.exception
    assert any("Primary flight" in x.value for x in at.markdown)
    assert any("Secondary flight" in x.value for x in at.markdown)
    assert any(x.value=="Normalized flight comparison" for x in at.subheader)
    comparison_table=next(frame.value for frame in at.dataframe if "metric" in frame.value.columns)
    assert {"selected_per_100","comparison_per_100","delta","unit"} <= set(comparison_table.columns)
    detail_headings=[x.value for x in at.subheader if "→" in x.value]
    assert len(detail_headings)==2
    assert next(box for box in at.selectbox if box.label=="Primary Flight Service").value != next(
        box for box in at.selectbox if box.label=="Compare with (optional)").value
    next(box for box in at.selectbox if box.label=="Primary Flight Service").set_value(other).run()
    assert next(box for box in at.selectbox if box.label=="Compare with (optional)").value is None
    assert any("Comparison cleared" in message.value for message in at.info)

    at.radio[0].set_value("Item Analysis").run()
    assert not at.exception
    assert next(box for box in at.selectbox if box.label=="Primary Flight Service").value==other
    comparison=next(box for box in at.selectbox if box.label=="Compare with (optional)")
    comparison.set_value(original_primary).run()
    assert not at.exception
    assert len([x for x in at.multiselect if x.label=="Categories"])==2
    assert len([x for x in at.download_button if x.label=="Download filtered analysis (CSV)"])==2
    assert any(x.value=="Selected-versus-comparison item deltas" for x in at.subheader)
    item_delta=next(frame.value for frame in at.dataframe if "service_rate_delta_pp" in frame.value.columns)
    assert "loaded_quantity_delta_per_100" in item_delta.columns

    at.radio[0].set_value("Recommendations").run()
    assert not at.exception
    assert [box.label for box in at.selectbox].count("Compare with (optional)")==1
    assert [box.label for box in at.selectbox].count("Served item")==2
    assert len([x for x in at.subheader if x.value=="Scenario planner"])==2
    assert len([x for x in at.download_button if x.label=="Download full recommendations (CSV)"])==2
    portion_sliders=[slider for slider in at.slider if slider.label=="Portion reduction" and not slider.disabled]
    assert portion_sliders and all(slider.max==90 for slider in portion_sliders)
    assert any("Prototype arithmetic bounds" in x.value for x in at.caption)
    assert any("Nutritional requirements" in x.value and "catering contracts" in x.value for x in at.warning)
    scenario_item=next(box for box in at.selectbox if box.label=="Served item")
    assert "Cola" in scenario_item.options
    scenario_item.set_value("cola").run()
    assert any(slider.label=="Portion reduction" and slider.disabled for slider in at.slider)
    assert any(metric.label=="Fuel-cost effect" for metric in at.metric)
    co2_toggle=next(box for box in at.checkbox if box.label=="Show simulated direct CO₂ effect")
    assert not co2_toggle.value
    co2_toggle.set_value(True).run()
    assert any(metric.label=="Simulated direct CO₂ effect" for metric in at.metric)
    assert any("not measured" in caption.value and "lifecycle" in caption.value for caption in at.caption)
    assumptions_table=next(frame.value for frame in at.dataframe if "assumption_key" in frame.value.columns)
    maximum_assumption=assumptions_table.set_index("assumption_key").loc["maximum_simulated_portion_reduction_pct"]
    assert maximum_assumption["unit"]=="%"
    assert "not an operationally validated minimum portion" in maximum_assumption["description"]
    recommendation_table=next(
        frame.value for frame in at.dataframe
        if "recommended_loaded_quantity" in frame.value.columns
    )
    assert {
        "current_portion_mass_kg","recommended_portion_mass_kg","group_service_rate_pct",
        "comparable_group_flight_count","observation_contributing_flight_count",
        "group_average_consumed_pct","quantity_saving_kg","portion_saving_kg",
        "combined_weight_saving_kg","estimated_fuel_saving_l","estimated_fuel_cost_saving_eur",
        "simulated_planning_direct_co2_effect_kg",
    } <= set(recommendation_table.columns)

def test_consumption_detail_renders_filters_comparison_binary_and_export():
    app=Path(__file__).resolve().parents[1]/"app.py"
    at=AppTest.from_file(str(app),default_timeout=60).run()
    at.radio[0].set_value("Consumption Detail").run()
    assert not at.exception
    assert next(box for box in at.selectbox if box.label=="Served item").value=="wrap"
    assert len(at.get("plotly_chart"))==2
    assert any(metric.label=="Observations" for metric in at.metric)
    assert any(button.label=="Download observations (CSV)" for button in at.download_button)

    comparison=next(box for box in at.selectbox if box.label=="Compare with (optional)")
    comparison.set_value("FRA-HND-2026-07-18-GE101").run()
    assert not at.exception
    assert any(metric.label=="Mean delta" for metric in at.metric)

    item=next(box for box in at.selectbox if box.label=="Served item")
    item.set_value("cola").run()
    assert not at.exception
    assert any("Binary item" in caption.value for caption in at.caption)


def test_consumption_comparison_without_observations_has_neutral_deltas():
    app=Path(__file__).resolve().parents[1]/"app.py"
    at=AppTest.from_file(str(app),default_timeout=60).run()
    at.radio[0].set_value("Consumption Detail").run()
    comparison=next(box for box in at.selectbox if box.label=="Compare with (optional)")
    comparison.set_value("FRA-HND-2026-07-18-GE101").run()
    item=next(box for box in at.selectbox if box.label=="Served item")
    item.set_value("coffee").run()

    assert not at.exception
    assert any(
        "No comparison observations" in message.value and "deltas are unavailable" in message.value
        for message in at.info
    )
    assert not any("nan" in str(metric.value).lower() for metric in at.metric)
