"""Item-level consumption distributions behind one pure analysis interface."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import DataBundle


BAND_LABELS = (
    "0%",
    ">0–10%",
    ">10–20%",
    ">20–30%",
    ">30–40%",
    ">40–50%",
    ">50–60%",
    ">60–70%",
    ">70–80%",
    ">80–90%",
    ">90–<100%",
    "100%",
)


@dataclass(frozen=True)
class ConsumptionProfile:
    """Analysis-ready observations, item summaries, and normalized bands."""

    observations: pd.DataFrame
    summary: pd.DataFrame
    bands: pd.DataFrame


def _band(value: float) -> str:
    if value == 0:
        return BAND_LABELS[0]
    if value == 100:
        return BAND_LABELS[-1]
    if value > 90:
        return BAND_LABELS[-2]
    # Exact upper edges belong to the interval ending at that edge.
    return BAND_LABELS[int(np.ceil(value / 10))]


def consumption_profile(bundle: DataBundle, flight_id: str) -> ConsumptionProfile:
    """Return the complete consumption profile for one Flight Service.

    Unknown flights raise ``KeyError``. Valid flights with no observations return
    all catalog items with zero counts and shares rather than failing.
    """
    flights = bundle.flights[bundle.flights.flight_id == flight_id]
    if flights.empty:
        raise KeyError(f"Unknown Flight Service: {flight_id}")

    catalog = bundle.menu_items[
        ["item_id", "display_name", "category", "binary_consumption"]
    ].copy()
    observations = bundle.observations[bundle.observations.flight_id == flight_id].copy()
    observations = observations.merge(catalog, on="item_id", how="left", validate="many_to_one")
    observations["consumption_band"] = pd.Categorical(
        observations.consumption_estimate_pct.map(_band),
        categories=BAND_LABELS,
        ordered=True,
    )
    observations = observations.sort_values(
        ["category", "display_name", "observation_id"]
    ).reset_index(drop=True)

    def summarize(group: pd.Series) -> pd.Series:
        count = int(group.size)
        if not count:
            return pd.Series({
                "observation_count": 0, "mean_pct": np.nan, "median_pct": np.nan,
                "q1_pct": np.nan, "q3_pct": np.nan, "iqr_pct": np.nan,
                "share_at_or_below_10_pct": np.nan,
                "share_at_or_above_75_pct": np.nan, "share_exact_100_pct": np.nan,
            })
        q1, q3 = group.quantile([.25, .75])
        return pd.Series({
            "observation_count": count,
            "mean_pct": group.mean(),
            "median_pct": group.median(),
            "q1_pct": q1,
            "q3_pct": q3,
            "iqr_pct": q3 - q1,
            "share_at_or_below_10_pct": group.le(10).mean() * 100,
            "share_at_or_above_75_pct": group.ge(75).mean() * 100,
            "share_exact_100_pct": group.eq(100).mean() * 100,
        })

    statistic_columns = [
        "observation_count", "mean_pct", "median_pct", "q1_pct", "q3_pct",
        "iqr_pct", "share_at_or_below_10_pct", "share_at_or_above_75_pct",
        "share_exact_100_pct",
    ]
    statistics = (
        observations.groupby("item_id", observed=True).consumption_estimate_pct
        .apply(summarize).unstack()
        if not observations.empty else pd.DataFrame(columns=statistic_columns)
    )
    summary = catalog.merge(statistics, left_on="item_id", right_index=True, how="left")
    summary["observation_count"] = pd.to_numeric(
        summary.observation_count, errors="coerce"
    ).fillna(0).astype(int)
    summary = summary.sort_values(["category", "display_name"]).reset_index(drop=True)

    grid = pd.MultiIndex.from_product(
        [catalog.item_id, BAND_LABELS], names=["item_id", "consumption_band"]
    ).to_frame(index=False)
    counts = (
        observations.groupby(["item_id", "consumption_band"], observed=False)
        .size().rename("observation_count").reset_index()
    )
    bands = grid.merge(counts, how="left", on=["item_id", "consumption_band"])
    bands["observation_count"] = bands.observation_count.fillna(0).astype(int)
    totals = bands.groupby("item_id").observation_count.transform("sum")
    bands["share_pct"] = np.where(totals > 0, bands.observation_count / totals * 100, 0.0)
    bands = bands.merge(catalog, on="item_id", validate="many_to_one")
    bands["consumption_band"] = pd.Categorical(
        bands.consumption_band, categories=BAND_LABELS, ordered=True
    )
    bands = bands.sort_values(["category", "display_name", "consumption_band"]).reset_index(drop=True)
    return ConsumptionProfile(observations=observations, summary=summary, bands=bands)
