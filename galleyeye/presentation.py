"""Display-only formatting helpers; domain values stay full precision."""

from __future__ import annotations

import pandas as pd


def display_number_format(column: str) -> str | None:
    """Return the product-spec display format for a numeric table column."""
    if column.endswith(("_quantity", "_count")) or column in {
        "loaded_quantity", "served_quantity", "observation_count",
        "quantity_reduction_units",
    }:
        return "%d"
    if column.endswith("_eur"):
        return "%.2f"
    if column.endswith("_kg") and "portion" in column:
        return "%.2f"
    if column.endswith(("_pct", "_kg", "_l", "_pp", "_per_100")):
        return "%.1f"
    return None

def export_csv(df: pd.DataFrame) -> bytes:
    out=df.copy()
    for col in out.columns:
        if col.endswith("_quantity") or col.endswith("_count") or col in {"loaded_quantity","served_quantity","observation_count","quantity_reduction_units"}:
            continue
        if col.endswith("_eur"): out[col]=pd.to_numeric(out[col]).round(2)
        elif col.endswith("_kg") and "portion" in col: out[col]=pd.to_numeric(out[col]).round(2)
        elif col.endswith(("_pct","_kg","_l","_pp","_per_100")): out[col]=pd.to_numeric(out[col]).round(1)
    return out.to_csv(index=False).encode("utf-8")
