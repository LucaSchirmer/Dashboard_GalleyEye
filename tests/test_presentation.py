import pandas as pd

from galleyeye.presentation import display_number_format, export_csv


def test_display_number_formats_follow_product_contract():
    assert display_number_format("observation_count") == "%d"
    assert display_number_format("service_rate_pct") == "%.1f"
    assert display_number_format("combined_weight_saving_kg") == "%.1f"
    assert display_number_format("estimated_fuel_saving_l") == "%.1f"
    assert display_number_format("estimated_fuel_cost_saving_eur") == "%.2f"
    assert display_number_format("recommended_portion_mass_kg") == "%.2f"
    assert display_number_format("display_name") is None


def test_export_rounding_does_not_mutate_calculation_values():
    source = pd.DataFrame({"service_rate_pct": [71.666667]})
    assert export_csv(source).decode("utf-8").splitlines()[1] == "71.7"
    assert source.loc[0, "service_rate_pct"] == 71.666667
