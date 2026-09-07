from dataclasses import replace

import numpy as np
import pandas as pd

from galleyeye.consumption import BAND_LABELS, consumption_profile


def test_every_distribution_band_edge_is_unambiguous(bundle):
    values = [0, .01, 10, 10.01, 20, 30, 40, 50, 60, 70, 80, 90, 90.01, 99.99, 100]
    expected = [
        "0%", ">0–10%", ">0–10%", ">10–20%", ">10–20%", ">20–30%",
        ">30–40%", ">40–50%", ">50–60%", ">60–70%", ">70–80%",
        ">80–90%", ">90–<100%", ">90–<100%", "100%",
    ]
    observations = pd.DataFrame({
        "observation_id": [f"edge-{i}" for i in range(len(values))],
        "flight_id": [bundle.flights.flight_id.iloc[0]] * len(values),
        "item_id": ["wrap"] * len(values),
        "source_image_id": [f"image-{i}" for i in range(len(values))],
        "reference_image_id": ["reference"] * len(values),
        "consumption_estimate_pct": values,
    })
    profile = consumption_profile(replace(bundle, observations=observations), bundle.flights.flight_id.iloc[0])
    actual = profile.observations.assign(
        edge_number=lambda frame: frame.observation_id.str.removeprefix("edge-").astype(int)
    ).sort_values("edge_number").consumption_band.astype(str).tolist()
    assert actual == expected
    assert tuple(profile.bands.consumption_band.cat.categories) == BAND_LABELS


def test_counts_shares_and_statistics_reconcile(bundle):
    flight_id = bundle.flights.flight_id.iloc[0]
    profile = consumption_profile(bundle, flight_id)
    served = bundle.service[bundle.service.flight_id.eq(flight_id)].set_index("item_id").served_quantity
    counts = profile.bands.groupby("item_id", observed=True).observation_count.sum()
    pd.testing.assert_series_equal(counts.sort_index(), served.sort_index(), check_names=False)
    totals = profile.bands.groupby("item_id", observed=True).share_pct.sum()
    assert np.allclose(totals[served.gt(0)], 100)

    wrap = bundle.observations[(bundle.observations.flight_id.eq(flight_id)) & (bundle.observations.item_id.eq("wrap"))].consumption_estimate_pct
    summary = profile.summary.set_index("item_id").loc["wrap"]
    assert summary.mean_pct == wrap.mean()
    assert summary.median_pct == wrap.median()
    assert summary.iqr_pct == wrap.quantile(.75) - wrap.quantile(.25)


def test_zero_observation_profile_is_safe(bundle):
    empty = bundle.observations.iloc[0:0].copy()
    profile = consumption_profile(replace(bundle, observations=empty), bundle.flights.flight_id.iloc[0])
    assert profile.observations.empty
    assert profile.summary.observation_count.eq(0).all()
    assert profile.summary.mean_pct.isna().all()
    assert profile.bands.observation_count.eq(0).all()
    assert profile.bands.share_pct.eq(0).all()


def test_wrap_pattern_and_normalized_comparison(bundle):
    profiles = [consumption_profile(bundle, fid) for fid in bundle.flights.flight_id]
    for profile in profiles:
        wrap = profile.observations[profile.observations.item_id.eq("wrap")].consumption_estimate_pct
        assert {10, 35, 55, 65, 80}.issubset(set(wrap))
        assert not wrap.eq(100).any()
        assert 50 <= wrap.mean() <= 75
        shares = profile.bands[profile.bands.item_id.eq("wrap")].share_pct
        assert np.isclose(shares.sum(), 100)
    assert profiles[0].summary.set_index("item_id").loc["wrap", "observation_count"] != profiles[1].summary.set_index("item_id").loc["wrap", "observation_count"]


def test_continuous_observations_have_realistic_variation(bundle):
    continuous_ids = set(bundle.menu_items.loc[~bundle.menu_items.binary_consumption, "item_id"])
    groups = bundle.observations[bundle.observations.item_id.isin(continuous_ids)].groupby(
        ["flight_id", "item_id"]
    ).consumption_estimate_pct
    assert (groups.nunique() >= 15).all()
