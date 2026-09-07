"""Deep Streamlit dashboard module; callers only need ``render_dashboard``."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from galleyeye.analytics import (
    flight_comparison as calculate_flight_comparison,
    flight_record,
    flight_summary as calculate_flight_summary,
    item_comparison as calculate_item_comparison,
    item_metrics as calculate_item_metrics,
    priority_recommendations as calculate_priority_recommendations,
    recommendations as calculate_recommendations,
    scenario_impact,
)
from galleyeye.consumption import BAND_LABELS, consumption_profile
from galleyeye.data import DataBundle, assumption
from galleyeye.presentation import display_number_format, export_csv

NAVY, BLUE, SKY, TEAL, AMBER, RED, INK, MUTED, BG = (
    "#1E3A5F", "#2563EB", "#DBEAFE", "#3B6FB6", "#64748B", "#475569",
    "#172033", "#64748B", "#F8FAFC",
)
SIDEBAR_BLUE = "#0F172A"
SIDEBAR_HOVER = "#1E293B"
SIDEBAR_SELECTED = "#1D4ED8"
SIDEBAR_FOREGROUND = "#F8FAFC"
STATUS_COLORS = {"Consider both": NAVY, "Reduce loaded quantity": BLUE,
                 "Reduce portion size": TEAL, "Maintain": MUTED,
                 "Insufficient evidence": RED}


def table_column_config(columns, labels=None, formats=None):
    """Build consistent display-only formats without rounding source values."""
    labels = labels or {}
    formats = formats or {}
    config = {}
    for column in columns:
        number_format = formats.get(column, display_number_format(column))
        label = labels.get(column)
        if number_format:
            config[column] = st.column_config.NumberColumn(label, format=number_format)
        elif label:
            config[column] = label
    return config

DASHBOARD_STYLES = f"""
<style>
.fsair-kicker {{color:{BLUE};font-size:.78rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}}
.fsair-hero {{background:white;border:1px solid #E2E8F0;border-left:5px solid {BLUE};padding:22px 26px;border-radius:10px;margin-bottom:18px;overflow:hidden;position:relative}}
.fsair-hero h1 {{margin:0;color:{INK};font-size:2rem}} .fsair-hero p {{margin:.35rem 0 0;color:{MUTED}}}
.fsair-route {{position:absolute;right:28px;top:14px;color:{BLUE};font-size:4rem;opacity:.10;transform:rotate(-8deg)}}
.priority-rank {{width:36px;height:36px;border-radius:50%;background:{BLUE};color:white;display:flex;align-items:center;justify-content:center;font-weight:800}}
.priority-title {{color:{NAVY};font-size:1.25rem;font-weight:800;margin:.7rem 0 .15rem}}
.priority-action {{color:{INK};min-height:2.9rem;font-size:.96rem}}
.flight-card-title {{color:{NAVY};font-size:1.2rem;font-weight:800}}
.flight-card-route {{color:{BLUE};font-size:1.55rem;font-weight:700;margin:.2rem 0 .6rem}}
.status-chip {{display:inline-block;padding:4px 9px;color:white;border-radius:999px;font-size:.74rem;font-weight:700}}
[data-testid="stColumn"]:has(.flight-panel-primary),
[data-testid="stColumn"]:has(.flight-panel-secondary) {{
  border:1px solid #D8E2EC;border-radius:14px;padding:1.15rem;
  box-shadow:0 5px 18px rgba(30,58,95,.08)
}}
[data-testid="stColumn"]:has(.flight-panel-primary) {{
  background:#EFF6FF;border-top:5px solid {BLUE}
}}
[data-testid="stColumn"]:has(.flight-panel-secondary) {{
  background:#ECFDF5;border-top:5px solid #0F766E
}}
.flight-panel-primary,.flight-panel-secondary {{height:0;overflow:hidden}}
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {{
  background:{SIDEBAR_BLUE};border-right:1px solid rgba(148,163,184,.18);
  color:{SIDEBAR_FOREGROUND};box-shadow:12px 0 30px rgba(15,23,42,.12)
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] svg,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{color:{SIDEBAR_FOREGROUND}}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > p {{color:{SIDEBAR_FOREGROUND}}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{opacity:.72}}
[data-testid="stSidebar"] hr {{border-color:rgba(255,255,255,.16)}}
.st-key-nav [role="radiogroup"] {{gap:7px}}
.st-key-nav [role="radiogroup"] label {{
  position:relative;padding:11px 13px;border:1px solid transparent;border-radius:9px;
  transition:background-color .16s ease,border-color .16s ease,transform .16s ease,box-shadow .16s ease;
  cursor:pointer
}}
.st-key-nav [role="radiogroup"] label p {{color:{SIDEBAR_FOREGROUND};font-weight:600}}
.st-key-nav [role="radiogroup"] label:hover {{
  background:{SIDEBAR_HOVER};border-color:rgba(147,197,253,.28);transform:translateX(4px);
  box-shadow:0 5px 14px rgba(0,0,0,.22)
}}
.st-key-nav [role="radiogroup"] label:has(input:checked),
.st-key-nav [role="radiogroup"] label:has([aria-checked="true"]) {{
  background:{SIDEBAR_SELECTED};border-color:rgba(191,219,254,.4);
  box-shadow:inset 4px 0 0 #93C5FD,0 7px 18px rgba(0,0,0,.28);transform:translateX(2px)
}}
.st-key-nav [role="radiogroup"] label:has(input:checked) p,
.st-key-nav [role="radiogroup"] label:has([aria-checked="true"]) p {{color:#FFFFFF;font-weight:800}}
.st-key-nav [role="radiogroup"] label:focus-within {{outline:3px solid #93C5FD;outline-offset:2px}}
[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] [data-baseweb="tag"] * {{color:{INK}}}
.st-key-nav label[data-baseweb="radio"] > div:first-child,
.st-key-nav label[data-baseweb="radio"] input[type="radio"] + div {{display:none}}
@media (max-width: 900px) {{
  [data-testid="stHorizontalBlock"] {{flex-wrap:wrap;gap:1rem}}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    flex:1 1 100%;min-width:100%;width:100%
  }}
}}
</style>
"""


def apply_dashboard_styles() -> None:
    """Emit dashboard CSS on every Streamlit rerun."""
    st.markdown(DASHBOARD_STYLES, unsafe_allow_html=True)


def flight_label(flights, fid):
    row = flights.set_index("flight_id").loc[fid]
    return f"{row.flight_number} · {row.direction} · {row.departure_date} · {row.departure_period}"


def open_flight(fid):
    st.session_state.selected_flight = fid
    st.session_state.nav = "Flight Detail"


def analysis_context(flights, eligible, include_comparison=False):
    """Keep the active and comparison flights together in the analysis workspace."""
    with st.container(border=True):
        st.markdown('<div class="fsair-kicker">Analysis context</div>', unsafe_allow_html=True)
        primary_col, comparison_col = st.columns(2) if include_comparison else (st.container(), None)
        with primary_col:
            selected_id = st.selectbox(
                "Primary Flight Service",
                eligible.flight_id.tolist(),
                format_func=lambda fid: flight_label(flights, fid),
                key="selected_flight",
            )
        comparison_id = None
        if include_comparison:
            if st.session_state.get("comparison_flight") == selected_id:
                st.session_state.comparison_flight = None
                st.info("Comparison cleared because it is now the primary Flight Service.")
            choices = [None] + [fid for fid in flights.flight_id if fid != selected_id]
            with comparison_col:
                comparison_id = st.selectbox(
                    "Compare with (optional)",
                    choices,
                    format_func=lambda x: "Choose a flight…" if x is None else flight_label(flights, x),
                    key="comparison_flight",
                    help="Totals are normalized to 100 passengers before differences are calculated.",
                )
        if include_comparison:
            st.caption("Deltas are Primary − Comparison; positive values mean the primary flight is higher.")
    return selected_id, comparison_id


def styled_figure(fig, height=370):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
                      font=dict(family="Inter, sans-serif", color=INK), margin=dict(l=20, r=20, t=45, b=20),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E8EFF5")
    return fig


def hero(title, subtitle, route=False):
    st.markdown(f'<div class="fsair-hero"><div class="fsair-route">{"✈" if route else "◈"}</div>'
                f'<div class="fsair-kicker">FSAIR · decision support</div>'
                f'<h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def assumptions_panel(bundle):
    with st.expander("Planning assumptions · simulated"):
        shown = bundle.assumptions.copy()
        shown["value"] = shown.value.map(lambda x: f"{x:g}")
        st.dataframe(shown[["assumption_key", "scope", "value", "unit", "description"]],
                     hide_index=True, width="stretch")


def priority_cards(bundle, fid, limit=3, show_co2_effect=False):
    priorities = calculate_priority_recommendations(bundle, fid, limit)
    st.markdown('<div class="fsair-kicker">Act first</div>', unsafe_allow_html=True)
    st.subheader("Top 3 priorities to change")
    st.caption("Ranked by projected avoidable carried mass. Suggestions inform a planner; they do not authorize a catering change.")
    if priorities.empty:
        st.success("No actionable changes meet the current evidence rules.")
        return priorities
    cols = st.columns(len(priorities))
    for col, row in zip(cols, priorities.itertuples(index=False)):
        with col:
            with st.container(border=True):
                color = STATUS_COLORS[row.status]
                st.markdown(f'<div class="priority-rank">{row.priority_rank}</div>'
                            f'<div class="priority-title">{row.display_name}</div>'
                            f'<span class="status-chip" style="background:{color}">{row.status}</span>',
                            unsafe_allow_html=True)
                actions = []
                if row.quantity_reduction_units:
                    actions.append(f"Load <b>{row.quantity_reduction_units} fewer</b> units")
                if row.portion_reduction_pct:
                    actions.append(f"Reduce portion by <b>{row.portion_reduction_pct:.0f}%</b>")
                st.markdown(f'<div class="priority-action">{" · ".join(actions)}</div>', unsafe_allow_html=True)
                effect_columns = st.columns(3 if show_co2_effect else 2)
                effect_columns[0].metric("Weight effect", f"{row.combined_weight_saving_kg:.1f} kg")
                effect_columns[1].metric("Fuel effect", f"{row.estimated_fuel_saving_l:.1f} L")
                if show_co2_effect:
                    effect_columns[2].metric(
                        "Simulated direct CO₂ effect",
                        f"{row.simulated_planning_direct_co2_effect_kg:.1f} kg",
                        help="Planning estimate for direct jet-fuel combustion only; not measured or realized and not a lifecycle estimate.",
                    )
                st.caption(
                    f"{row.evidence_strength} evidence · "
                    f"{row.comparable_group_flight_count} comparable flights · "
                    f"{row.observation_contributing_flight_count} observation-contributing flights · "
                    f"{row.observation_count} observations"
                )
                with st.expander("Why this priority?"):
                    st.write(row.explanation)
    if show_co2_effect:
        st.caption("CO₂ effects are simulated planning estimates of direct fuel combustion only, not measured or realized reductions; lifecycle and non-CO₂ effects are excluded.")
    return priorities


def flight_panel_heading(bundle, fid, role):
    flight = flight_record(bundle, fid)
    st.markdown(f'<div class="fsair-kicker">{role} flight</div>', unsafe_allow_html=True)
    st.subheader(f"{flight.flight_number} · {flight.origin_iata} → {flight.destination_iata}")
    st.caption(f"{flight.departure_date:%d %B %Y} · {flight.departure_period} · {flight.passenger_count:,} passengers")


def flight_panel_marker(role):
    """Provide a stable hook for styling the two comparison columns."""
    panel_class = "flight-panel-primary" if role == "Primary" else "flight-panel-secondary"
    st.markdown(f'<div class="{panel_class}" aria-hidden="true"></div>', unsafe_allow_html=True)


def render_flight_detail(bundle, fid, role, show_co2_effect=False):
    flight_panel_heading(bundle, fid, role)
    items = calculate_item_metrics(bundle, fid)
    summary = calculate_flight_summary(bundle, fid)
    labels = [("Passengers", f"{summary['passengers']:,}"), ("Loaded items", f"{summary['loaded_items']:,}"),
              ("Service rate", f"{summary['service_rate_pct']:.1f}%"), ("Consumption waste", f"{summary['consumption_waste_kg']:.1f} kg")]
    for start in range(0, len(labels), 2):
        for col, (name, value) in zip(st.columns(2), labels[start:start + 2]):
            col.metric(name, value)
    impact_labels = [("Food value waste", f"€{summary['food_value_waste_eur']:.2f}"),
                     ("Avoidable fuel effect", f"{summary['estimated_fuel_attributable_l']:.1f} L")]
    if show_co2_effect:
        impact_labels.append(("Simulated direct CO₂ effect", f"{summary['simulated_planning_direct_co2_effect_kg']:.1f} kg"))
    for col, (name, value) in zip(st.columns(len(impact_labels)), impact_labels):
        col.metric(name, value)
    if show_co2_effect:
        st.caption("CO₂ effect: simulated planning estimate of direct fuel combustion only; not measured, realized, lifecycle CO₂e, or total climate impact.")
    tab_summary, tab_catering, tab_consumption, tab_impact = st.tabs(["Summary", "Catering flow", "Consumption", "Waste & impact"])
    with tab_summary:
        priority_cards(bundle, fid, show_co2_effect=show_co2_effect)
    with tab_catering:
        totals = pd.DataFrame({"Stage": ["Loaded", "Served", "Estimated consumed"],
                               "Units": [items.loaded_quantity.sum(), items.served_quantity.sum(),
                                         (items.served_quantity * items.average_consumed_pct.fillna(0) / 100).sum()]})
        fig = go.Figure(go.Funnel(y=totals.Stage, x=totals.Units, textinfo="value+percent initial", marker=dict(color=[NAVY, BLUE, TEAL])))
        st.plotly_chart(styled_figure(fig, 390), width="stretch", key=f"flow_{fid}")
        st.caption("Estimated consumed units are an analytical equivalent derived from Consumption Estimates; they are not physical item counts.")
    with tab_consumption:
        consume = items.dropna(subset=["average_consumed_pct"]).sort_values("average_consumed_pct")
        fig = px.bar(consume, x="average_consumed_pct", y="display_name", orientation="h", color="average_consumed_pct",
                     color_continuous_scale=[RED, AMBER, TEAL], labels={"average_consumed_pct": "Average consumed (%)", "display_name": ""})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(styled_figure(fig, 540), width="stretch", key=f"consumption_{fid}")
    with tab_impact:
        waste = items.assign(total_waste_kg=lambda d: d.unserved_mass_kg + d.consumption_waste_kg.fillna(0)).sort_values("total_waste_kg", ascending=False)
        waste["Cumulative share"] = waste.total_waste_kg.cumsum() / waste.total_waste_kg.sum() * 100
        fig = go.Figure()
        fig.add_bar(x=waste.display_name, y=waste.total_waste_kg, name="Waste mass", marker_color=BLUE)
        fig.add_scatter(x=waste.display_name, y=waste["Cumulative share"], name="Cumulative share", yaxis="y2", line=dict(color=AMBER, width=3))
        fig.update_layout(yaxis_title="Waste mass (kg)", yaxis2=dict(title="Cumulative share (%)", overlaying="y", side="right", range=[0, 105]))
        st.plotly_chart(styled_figure(fig, 430), width="stretch", key=f"pareto_{fid}")


def render_item_analysis(bundle, fid, role):
    flight_panel_heading(bundle, fid, role)
    items = calculate_item_metrics(bundle, fid)
    categories = st.multiselect("Categories", sorted(items.category.unique()), default=sorted(items.category.unique()), key=f"categories_{fid}")
    available = items[items.category.isin(categories) & items.served_quantity.gt(0)]
    names = st.multiselect("Served items", available.display_name.tolist(), default=available.display_name.tolist(), key=f"items_{fid}")
    filtered = available[available.display_name.isin(names)].copy()
    if filtered.empty:
        st.info("No items match the current filters.")
        return
    load = filtered.melt("display_name", value_vars=["loaded_quantity", "served_quantity"], var_name="Series", value_name="Units")
    load.Series = load.Series.map({"loaded_quantity": "Loaded", "served_quantity": "Served"})
    st.plotly_chart(styled_figure(px.bar(load, x="display_name", y="Units", color="Series", barmode="group", color_discrete_sequence=[NAVY, BLUE])), width="stretch", key=f"item_load_{fid}")
    matrix = filtered.dropna(subset=["average_consumed_pct", "service_rate_pct"])
    fig = px.scatter(matrix, x="service_rate_pct", y="average_consumed_pct", size="food_value_waste_eur", color="category", hover_name="display_name",
                     labels={"service_rate_pct": "Service rate (%)", "average_consumed_pct": "Average consumed (%)"})
    service_threshold = assumption(bundle, "service_rate_reduction_threshold_pct")
    low_threshold = assumption(bundle, "low_consumption_threshold_pct")
    moderate_threshold = assumption(bundle, "moderate_consumption_threshold_pct")
    fig.add_vline(x=service_threshold, line_dash="dash", line_color=MUTED,
                  annotation_text=f"Service {service_threshold:g}%")
    fig.add_hline(y=low_threshold, line_dash="dot", line_color=MUTED,
                  annotation_text=f"Low {low_threshold:g}%")
    fig.add_hline(y=moderate_threshold, line_dash="dash", line_color=MUTED,
                  annotation_text=f"Moderate {moderate_threshold:g}%")
    st.plotly_chart(styled_figure(fig), width="stretch", key=f"matrix_{fid}")
    st.caption("Bottom-left items warrant the closest review: relatively low service and low consumption.")
    table_cols = ["display_name", "category", "loaded_quantity", "served_quantity", "service_rate_pct", "average_consumed_pct", "observation_count", "unserved_mass_kg", "consumption_waste_kg", "food_value_waste_eur"]
    st.dataframe(
        filtered[table_cols], column_config=table_column_config(table_cols),
        hide_index=True, width="stretch",
    )
    st.download_button("Download filtered analysis (CSV)", export_csv(filtered[table_cols]), f"fsair_{fid}_items.csv", "text/csv", key=f"download_items_{fid}")


def render_consumption_detail(bundle, primary_id, comparison_id):
    primary = consumption_profile(bundle, primary_id)
    categories = sorted(primary.summary.category.unique())
    selected_categories = st.multiselect(
        "Categories", categories, default=categories, key="consumption_categories"
    )
    served_item_ids = set(primary.summary.loc[primary.summary.observation_count.gt(0), "item_id"])
    overview = primary.bands[
        primary.bands.category.isin(selected_categories)
        & primary.bands.item_id.isin(served_item_ids)
    ].copy()
    if overview.empty:
        st.info("No observations match the current category filter.")
        return

    st.subheader("Distribution across served items")
    heatmap = overview.pivot(index="display_name", columns="consumption_band", values="share_pct")
    heatmap = heatmap.reindex(columns=BAND_LABELS)
    counts = overview.pivot(index="display_name", columns="consumption_band", values="observation_count").reindex(columns=BAND_LABELS)
    fig = go.Figure(go.Heatmap(
        z=heatmap.values, x=list(BAND_LABELS), y=heatmap.index,
        text=np.char.add(np.round(heatmap.values, 1).astype(str), "%"), texttemplate="%{text}",
        customdata=counts.values,
        hovertemplate="%{y}<br>%{x}<br>%{z:.1f}% · %{customdata} observations<extra></extra>",
        colorscale=[[0, "#F8FAFC"], [1, BLUE]], zmin=0,
    ))
    st.plotly_chart(styled_figure(fig, max(390, 32 * len(heatmap))), width="stretch", key="consumption_heatmap")
    with st.expander("Accessible distribution table"):
        overview_columns = ["display_name", "consumption_band", "share_pct", "observation_count"]
        st.dataframe(
            overview[overview_columns], column_config=table_column_config(overview_columns),
            hide_index=True, width="stretch",
        )

    available = primary.summary[
        primary.summary.category.isin(selected_categories)
        & primary.summary.observation_count.gt(0)
    ]
    if available.empty:
        st.info("No served items are available for inspection.")
        return
    item_ids = available.item_id.tolist()
    default = item_ids.index("wrap") if "wrap" in item_ids else 0
    item_id = st.selectbox(
        "Served item", item_ids, index=default,
        format_func=lambda value: available.set_index("item_id").loc[value, "display_name"],
        key="consumption_item",
    )
    selected = available.set_index("item_id").loc[item_id]
    label = "Binary item · valid observations are 0% or 100%" if selected.binary_consumption else "Continuous Consumption Estimate"
    st.caption(label)
    if selected.observation_count == 0:
        st.info("No observations are available for this served item.")
        return

    st.subheader(f"{selected.display_name} detail")
    metrics = [
        ("Observations", f"{selected.observation_count:,}"),
        ("Mean", f"{selected.mean_pct:.1f}%"),
        ("Median", f"{selected.median_pct:.1f}%"),
        ("Interquartile range", f"{selected.iqr_pct:.1f} pp"),
        ("≤ 10%", f"{selected.share_at_or_below_10_pct:.1f}%"),
        ("≥ 75%", f"{selected.share_at_or_above_75_pct:.1f}%"),
        ("Exact 100%", f"{selected.share_exact_100_pct:.1f}%"),
    ]
    for start in range(0, len(metrics), 4):
        for col, (name, value) in zip(st.columns(min(4, len(metrics) - start)), metrics[start:start + 4]):
            col.metric(name, value)

    distributions = [primary.bands[primary.bands.item_id == item_id].assign(flight_role="Primary")]
    summaries = [("Primary", selected)]
    if comparison_id:
        comparison = consumption_profile(bundle, comparison_id)
        distributions.append(comparison.bands[comparison.bands.item_id == item_id].assign(flight_role="Comparison"))
        comparison_row = comparison.summary.set_index("item_id").loc[item_id]
        summaries.append(("Comparison", comparison_row))
    distribution = pd.concat(distributions, ignore_index=True)
    fig = px.bar(
        distribution, x="consumption_band", y="share_pct", color="flight_role",
        barmode="group", category_orders={"consumption_band": list(BAND_LABELS)},
        custom_data=["observation_count"], color_discrete_sequence=[BLUE, "#0F766E"],
        labels={"consumption_band": "Consumption band", "share_pct": "Observations (%)", "flight_role": "Flight role"},
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:.1f}% · %{customdata[0]} observations<extra>%{fullData.name}</extra>")
    st.plotly_chart(styled_figure(fig, 410), width="stretch", key="consumption_distribution")
    if comparison_id:
        other = summaries[1][1]
        if other.observation_count == 0:
            st.info("No comparison observations are available for this served item; summary deltas are unavailable.")
        else:
            delta_cols = st.columns(3)
            delta_cols[0].metric("Mean delta", f"{selected.mean_pct - other.mean_pct:+.1f} pp")
            delta_cols[1].metric("≤ 10% delta", f"{selected.share_at_or_below_10_pct - other.share_at_or_below_10_pct:+.1f} pp")
            delta_cols[2].metric("≥ 75% delta", f"{selected.share_at_or_above_75_pct - other.share_at_or_above_75_pct:+.1f} pp")
            st.caption("Deltas are Primary − Comparison. Bars show percentages, so flights with different observation counts remain comparable.")

    observations = []
    for role, profile in [("Primary", primary)] + ([("Comparison", comparison)] if comparison_id else []):
        rows = profile.observations[profile.observations.item_id == item_id].copy()
        rows.insert(0, "flight_role", role)
        observations.append(rows)
    detail = pd.concat(observations, ignore_index=True)
    detail = detail[["flight_role", "observation_id", "consumption_estimate_pct", "source_image_id", "reference_image_id"]]
    with st.expander("Observation-level records"):
        st.dataframe(
            detail, column_config=table_column_config(detail.columns),
            hide_index=True, width="stretch",
        )
        st.download_button(
            "Download observations (CSV)", export_csv(detail),
            f"fsair_{primary_id}_{item_id}_observations.csv", "text/csv", key="download_consumption_observations",
        )


def render_recommendations(bundle, fid, role, show_co2_effect=False):
    flight_panel_heading(bundle, fid, role)
    items = calculate_item_metrics(bundle, fid)
    priorities = priority_cards(bundle, fid, show_co2_effect=show_co2_effect)
    st.divider()
    st.subheader("Scenario planner")
    st.caption("Prototype arithmetic bounds · Explore a reversible what-if scenario. Values below do not modify the source data or approve a recommendation.")
    scenario_ids = items.loc[items.served_quantity > 0, "item_id"].tolist()
    preferred_item = priorities.item_id.iloc[0] if not priorities.empty else scenario_ids[0]
    scenario_item = st.selectbox(
        "Served item", scenario_ids, index=scenario_ids.index(preferred_item),
        format_func=lambda iid: items.set_index("item_id").loc[iid, "display_name"],
        key=f"scenario_item_{fid}",
    )
    current = items.set_index("item_id").loc[scenario_item]
    recommended = calculate_recommendations(bundle, fid).set_index("item_id").loc[scenario_item]
    planned_load = st.slider("Planned loaded quantity", int(current.served_quantity), int(current.loaded_quantity), int(recommended.recommended_loaded_quantity), key=f"planned_load_{fid}")
    simulated_max_reduction = int(assumption(bundle, "maximum_simulated_portion_reduction_pct"))
    binary_item = bool(current.binary_consumption)
    portion_reduction = st.slider(
        "Portion reduction", 0, simulated_max_reduction,
        0 if binary_item else int(recommended.portion_reduction_pct),
        format="%d%%", disabled=binary_item, key=f"portion_reduction_{fid}",
    )
    impact = scenario_impact(bundle, fid, scenario_item, planned_load, portion_reduction)
    scenario_effects = [('Weight effect', f"{impact['combined_weight_saving_kg']:.1f} kg"),
                        ('Fuel effect', f"{impact['estimated_fuel_saving_l']:.1f} L")]
    if show_co2_effect:
        scenario_effects.append(('Simulated direct CO₂ effect', f"{impact['simulated_planning_direct_co2_effect_kg']:.1f} kg"))
    scenario_effects.append(('Fuel-cost effect', f"€{impact['estimated_fuel_cost_saving_eur']:.2f}"))
    for values in [[('Planned load', f"{impact['planned_load']} units"), ('New portion', f"{impact['planned_portion_mass_kg']:.2f} kg")],
                   scenario_effects]:
        for col, (label, value) in zip(st.columns(len(values)), values):
            col.metric(label, value)
    if show_co2_effect:
        st.caption("CO₂ effect: simulated planning estimate of direct fuel combustion only; not measured, realized, or lifecycle CO₂e.")
    st.divider()
    st.subheader("All recommendation evidence")
    recs = calculate_recommendations(bundle, fid)
    status_order = ["Consider both", "Reduce loaded quantity", "Reduce portion size", "Insufficient evidence", "Maintain"]
    selected_status = st.multiselect("Status", status_order, default=status_order, key=f"status_{fid}")
    shown = recs[recs.status.isin(selected_status)]
    shown_columns = ["display_name", "status", "current_loaded_quantity", "recommended_loaded_quantity",
                        "current_portion_mass_kg", "recommended_portion_mass_kg",
                        "comparable_group_flight_count", "observation_contributing_flight_count",
                        "observation_count", "group_service_rate_pct", "group_average_consumed_pct",
                        "quantity_saving_kg", "portion_saving_kg", "combined_weight_saving_kg",
                        "estimated_fuel_saving_l"]
    if show_co2_effect:
        shown_columns.append("simulated_planning_direct_co2_effect_kg")
    shown_columns.extend(["estimated_fuel_cost_saving_eur", "explanation"])
    recommendation_labels = {
        "comparable_group_flight_count": "Comparable group flights",
        "observation_contributing_flight_count": "Observation-contributing flights",
        "observation_count": "Consumption observations",
    }
    st.dataframe(shown[shown_columns],
                 column_config=table_column_config(shown_columns, recommendation_labels),
                 hide_index=True, width="stretch")
    st.download_button("Download full recommendations (CSV)", export_csv(recs), f"fsair_{fid}_recommendations.csv", "text/csv", key=f"download_recs_{fid}")


def render_dashboard(bundle: DataBundle) -> None:
    """Render all five workspaces for a validated, read-only data bundle."""
    apply_dashboard_styles()
    flights = bundle.flights.assign(direction=lambda x: x.origin_iata + "–" + x.destination_iata)
    if "selected_flight" not in st.session_state:
        st.session_state.selected_flight = flights.flight_id.iloc[0]
    if "nav" not in st.session_state:
        st.session_state.nav = "Command Center"

    with st.sidebar:
        st.markdown("# ✈ FSAIR")
        st.caption("AI-assisted airline catering insights")
        page = st.radio("Workspace", ["Command Center", "Flight Detail", "Item Analysis", "Consumption Detail", "Recommendations"], key="nav")
        st.divider()
        directions = st.multiselect("Direction", sorted(flights.direction.unique()), default=sorted(flights.direction.unique()))
        periods = st.multiselect("Departure period", ["Day", "Night"], default=["Day", "Night"])
        show_co2_effect = st.checkbox(
            "Show simulated direct CO₂ effect",
            value=False,
            help="Optional planning indicator for direct jet-fuel combustion only. It is not measured, realized, or a lifecycle estimate.",
        )
        eligible = flights[flights.direction.isin(directions) & flights.departure_period.isin(periods)]
        if eligible.empty:
            st.warning("No matching flights; showing all Flight Services.")
            eligible = flights
        if st.session_state.selected_flight not in eligible.flight_id.tolist():
            st.session_state.selected_flight = eligible.flight_id.iloc[0]
        st.divider()
        st.caption("Simulated thesis dataset · Offline and read-only · Consumption Estimates are model-produced planning inputs.")
    
    selected_id = st.session_state.selected_flight
    
    
    if page == "Command Center":
        hero("Catering command center", "See the fleet picture, identify the largest opportunities, and move from insight to action.")
        priority_cards(bundle, selected_id, show_co2_effect=show_co2_effect)
        st.divider()
        st.markdown('<div class="fsair-kicker">Flight services</div>', unsafe_allow_html=True)
        st.subheader("Overview grid")
        for start in range(0, len(eligible), 3):
            cols = st.columns(3)
            for col, row in zip(cols, eligible.iloc[start:start + 3].itertuples(index=False)):
                fs = calculate_flight_summary(bundle, row.flight_id)
                with col:
                    with st.container(border=True):
                        st.markdown(f'<div class="flight-card-title">{row.flight_number}</div><div class="flight-card-route">{row.direction}</div>', unsafe_allow_html=True)
                        st.caption(f"{row.departure_date:%d %b %Y} · {row.departure_period} · {row.passenger_count} passengers")
                        a, b = st.columns(2)
                        a.metric("Service rate", f"{fs['service_rate_pct']:.1f}%")
                        b.metric("Consumption waste", f"{fs['consumption_waste_kg']:.1f} kg")
                        st.button("Open flight detail", key=f"open_{row.flight_id}", type="primary", width="stretch",
                                  on_click=open_flight, args=(row.flight_id,))
        st.subheader("Cross-flight trend")
        trend_rows = []
        for row in eligible.sort_values("departure_date").itertuples(index=False):
            fs = calculate_flight_summary(bundle, row.flight_id)
            trend_rows.append({"Date": row.departure_date, "Flight": row.flight_number,
                               "Service rate (%)": fs["service_rate_pct"],
                               "Consumption waste per 100 passengers (kg)": fs["consumption_waste_kg"] / row.passenger_count * 100})
        trend = pd.DataFrame(trend_rows)
        fig = go.Figure()
        fig.add_scatter(x=trend.Date, y=trend["Service rate (%)"], mode="lines+markers", name="Service rate", line=dict(color=BLUE, width=3))
        fig.add_scatter(x=trend.Date, y=trend["Consumption waste per 100 passengers (kg)"], mode="lines+markers", name="Consumption waste / 100 passengers",
                        yaxis="y2", line=dict(color=AMBER, width=3))
        fig.update_layout(yaxis=dict(title="Service rate (%)"), yaxis2=dict(title="Consumption waste / 100 passengers (kg)", overlaying="y", side="right"))
        st.plotly_chart(styled_figure(fig, 330), width="stretch", key="trend")
        st.caption("Four simulated Flight Services provide only an illustrative trend; more history is required for seasonality or forecasting.")
    
    elif page == "Flight Detail":
        flight = flight_record(bundle, selected_id)
        hero(f"{flight.flight_number} · {flight.origin_iata} → {flight.destination_iata}",
             f"{flight.departure_date:%d %B %Y} · {flight.departure_period} service · {flight.passenger_count:,} passengers", route=True)
        selected_id, comparison_id = analysis_context(flights, eligible, include_comparison=True)
        panel_ids = [(selected_id, "Primary")]
        if comparison_id:
            panel_ids.append((comparison_id, "Secondary"))
        for col, (fid, role) in zip(st.columns(len(panel_ids)), panel_ids):
            with col:
                flight_panel_marker(role)
                render_flight_detail(bundle, fid, role, show_co2_effect=show_co2_effect)
        if comparison_id:
            st.subheader("Normalized flight comparison")
            st.caption("Primary − Comparison; additive metrics are normalized per 100 passengers and rates use percentage points.")
            comparison = calculate_flight_comparison(bundle, selected_id, comparison_id)
            if not show_co2_effect:
                comparison = comparison[comparison.metric.ne("simulated_planning_direct_co2_effect_kg")]
            st.dataframe(
                comparison,
                column_config=table_column_config(comparison.columns, formats={"delta": "%.1f"}),
                hide_index=True, width="stretch",
            )
        assumptions_panel(bundle)
    
    elif page == "Item Analysis":
        flight = flight_record(bundle, selected_id)
        hero("Item analysis", f"Explore loading, service, and Consumption Estimates for {flight.flight_number}.")
        selected_id, comparison_id = analysis_context(flights, eligible, include_comparison=True)
        panel_ids = [(selected_id, "Primary")]
        if comparison_id:
            panel_ids.append((comparison_id, "Secondary"))
        for col, (fid, role) in zip(st.columns(len(panel_ids)), panel_ids):
            with col:
                flight_panel_marker(role)
                render_item_analysis(bundle, fid, role)
        if comparison_id:
            st.subheader("Selected-versus-comparison item deltas")
            st.caption("Primary − Comparison; quantities and impacts are per 100 passengers and rates use percentage points.")
            item_comparison = calculate_item_comparison(bundle, selected_id, comparison_id)
            st.dataframe(
                item_comparison, column_config=table_column_config(item_comparison.columns),
                hide_index=True, width="stretch",
            )
    
    elif page == "Consumption Detail":
        flight = flight_record(bundle, selected_id)
        hero("Consumption detail", f"Inspect observation distributions for {flight.flight_number}.")
        selected_id, comparison_id = analysis_context(flights, eligible, include_comparison=True)
        render_consumption_detail(bundle, selected_id, comparison_id)

    else:
        hero("Recommendations", "Review the strongest opportunities, test a scenario, and inspect the evidence behind every suggestion.")
        selected_id, comparison_id = analysis_context(flights, eligible, include_comparison=True)
        st.warning(
            "Prototype arithmetic scenarios are not operationally validated. Nutritional requirements, "
            "packaging constraints, minimum viable portions, service standards, and catering contracts "
            "are not modeled."
        )
        panel_ids = [(selected_id, "Primary")]
        if comparison_id:
            panel_ids.append((comparison_id, "Secondary"))
        for col, (fid, role) in zip(st.columns(len(panel_ids)), panel_ids):
            with col:
                flight_panel_marker(role)
                render_recommendations(bundle, fid, role, show_co2_effect=show_co2_effect)
        assumptions_panel(bundle)
