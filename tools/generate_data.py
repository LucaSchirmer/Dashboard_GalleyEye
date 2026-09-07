"""Generate the deterministic, simulated thesis dataset."""

from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
DATA_VOLUME_MULTIPLIER = 3

FLIGHTS = [
    ("FRA-HND-2026-07-04-GE101", "GE101", "FRA", "HND", "2026-07-04", "Day", 238),
    ("FRA-HND-2026-07-18-GE101", "GE101", "FRA", "HND", "2026-07-18", "Night", 252),
    ("HND-FRA-2026-07-08-GE102", "GE102", "HND", "FRA", "2026-07-08", "Day", 244),
    ("HND-FRA-2026-07-22-GE102", "GE102", "HND", "FRA", "2026-07-22", "Night", 229),
]

ITEMS = [
    ("chicken_rice_vegetables", "Chicken–Rice–Vegetables", "Main Course", .34, 5.20, False),
    ("fish_rice_vegetables", "Fish–Rice–Vegetables", "Main Course", .33, 5.80, False),
    ("salad", "Salad", "Main Course", .25, 4.10, False),
    ("wrap", "Wrap", "Main Course", .24, 3.80, False),
    ("bread_roll", "Bread Roll", "Side Dish", .06, .65, False),
    ("standard_side_salad", "Standard Side Salad", "Side Dish", .12, 1.50, False),
    ("chocolate_cake", "Chocolate Cake", "Dessert", .10, 1.80, False),
    ("vanilla_pudding_fruit", "Vanilla Pudding with Fruit", "Dessert", .13, 1.65, False),
    ("fruit_salad", "Fruit Salad", "Dessert", .12, 1.70, False),
    ("cola", "Cola", "Beverage", .33, 1.10, True),
    ("orange_juice", "Orange Juice", "Beverage", .25, 1.05, True),
    ("water", "Water", "Beverage", .50, .55, True),
    ("coffee", "Coffee", "Beverage", .20, .70, True),
    ("tea", "Tea", "Beverage", .20, .65, True),
    ("butter", "Butter", "Accompaniment", .01, .18, True),
    ("cherry_jam", "Cherry Jam", "Accompaniment", .02, .22, True),
    ("plum_jam", "Plum Jam", "Accompaniment", .02, .22, True),
    ("honey", "Honey", "Accompaniment", .02, .25, True),
    ("cookie", "Cookie", "Snack", .04, .60, True),
]

# Base loaded/served quantities for the four flights. Directional evidence intentionally
# demonstrates every recommendation status. Coffee has no load on the second flight in
# each direction, exercising the clarified quantity-evidence rule.
Q = {
    "chicken_rice_vegetables": [(105,100),(112,107),(108,102),(101,96)],
    "fish_rice_vegetables": [(90,55),(96,59),(92,57),(86,53)],
    "salad": [(30,27),(32,29),(31,28),(29,26)],
    "wrap": [(35,32),(37,34),(36,33),(34,31)],
    "bread_roll": [(210,190),(222,201),(216,195),(203,183)],
    "standard_side_salad": [(180,115),(190,121),(184,118),(173,110)],
    "chocolate_cake": [(90,82),(95,87),(92,84),(86,79)],
    "vanilla_pudding_fruit": [(75,67),(79,71),(77,69),(72,65)],
    "fruit_salad": [(70,64),(74,68),(72,66),(68,62)],
    "cola": [(110,98),(116,104),(113,101),(106,95)],
    "orange_juice": [(85,76),(90,81),(87,78),(82,73)],
    "water": [(230,220),(243,232),(235,224),(221,211)],
    "coffee": [(80,65),(0,0),(82,66),(0,0)],
    "tea": [(75,62),(79,65),(77,64),(72,60)],
    "butter": [(145,120),(153,127),(148,123),(139,115)],
    "cherry_jam": [(45,35),(48,37),(46,36),(43,33)],
    "plum_jam": [(42,32),(44,34),(43,33),(40,31)],
    "honey": [(40,31),(42,33),(41,32),(38,30)],
    "cookie": [(238,230),(252,244),(244,236),(229,221)],
}

# Beta distributions produce varied but bounded estimates around an item-specific
# average. Lower concentration means more passenger-to-passenger variation. The
# fixed seed in continuous_estimates keeps the simulated dataset reproducible.
CONTINUOUS_DISTRIBUTIONS = {
    "chicken_rice_vegetables": (.86, 14),
    "fish_rice_vegetables": (.39, 10),
    "salad": (.78, 12),
    "bread_roll": (.84, 14),
    "standard_side_salad": (.88, 16),
    "chocolate_cake": (.73, 11),
    "vanilla_pudding_fruit": (.68, 10),
    "fruit_salad": (.85, 14),
}
BINARY_CONSUMED_RATE = {"cola":.82,"orange_juice":.86,"water":.94,"coffee":.70,"tea":.76,
                        "butter":.72,"cherry_jam":.65,"plum_jam":.62,"honey":.70,"cookie":.90}

ASSUMPTIONS = [
    ("quantity_safety_buffer_pct","global",10,"%","Simulated buffer above expected demand."),
    ("service_rate_reduction_threshold_pct","global",80,"%","Service-rate threshold for quantity review."),
    ("low_consumption_threshold_pct","global",50,"%","Consumption Estimate threshold for a larger portion reduction."),
    ("moderate_consumption_threshold_pct","global",75,"%","Upper threshold for a moderate portion reduction."),
    ("low_consumption_portion_reduction_pct","global",25,"%","Suggested reduction when average consumption is low."),
    ("moderate_consumption_portion_reduction_pct","global",10,"%","Suggested reduction when average consumption is moderate."),
    ("maximum_simulated_portion_reduction_pct","global",90,"%","Prototype simulation bound only; not an operationally validated minimum portion."),
    ("minimum_consumption_observations","global",10,"count","Minimum group observations for portion evidence."),
    ("fuel_price_eur_per_liter","global",.80,"EUR/L","Simulated planning fuel price."),
    ("fuel_liters_per_kg_carried","FRA-HND",.35,"L/kg","Simulated fuel factor for FRA–HND."),
    ("fuel_liters_per_kg_carried","HND-FRA",.33,"L/kg","Simulated fuel factor for HND–FRA."),
    ("icao_corsia_jet_a_direct_co2_v1","global",2.528,"kg CO2/L fuel","ICAO Annex 16 Vol IV (2nd ed., July 2023): 3.16 kg CO2/kg Jet-A times ICAO standard density 0.8 kg/L; direct fuel combustion only, excluding lifecycle and non-CO2 effects."),
]

def write(name, header, rows):
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def continuous_estimates(item_id, flight_index, count):
    """Return realistic, reproducible observation-level percentages."""
    rng = random.Random(f"fsair-v2:{item_id}:{flight_index}")
    flight_shift = (-.015, .012, -.008, .018)[flight_index]

    if item_id == "wrap":
        # Wrap intentionally has both a mostly-consumed and a partly-consumed
        # population. Anchors keep its documented modes visible in every flight.
        modes = ((.80, .55), (.35, .25), (.55, .10), (.10, .05), (.65, .05))
        values = [80, 35, 55, 10, 65]
        for _ in range(max(0, count - len(values))):
            draw = rng.random()
            cumulative = 0.0
            mode = modes[-1][0]
            for candidate, weight in modes:
                cumulative += weight
                if draw < cumulative:
                    mode = candidate
                    break
            concentration = 28 if mode >= .65 else 20
            shifted = min(.97, max(.03, mode + flight_shift))
            estimate = rng.betavariate(shifted * concentration, (1 - shifted) * concentration)
            values.append(round(estimate * 100))
        rng.shuffle(values)
        return values[:count]

    mean, concentration = CONTINUOUS_DISTRIBUTIONS[item_id]
    mean = min(.97, max(.03, mean + flight_shift))
    return [round(rng.betavariate(mean * concentration, (1 - mean) * concentration) * 100)
            for _ in range(count)]

def main():
    OUT.mkdir(exist_ok=True)
    scaled_flights = [(*flight[:-1], flight[-1] * DATA_VOLUME_MULTIPLIER) for flight in FLIGHTS]
    write("flights.csv", ["flight_id","flight_number","origin_iata","destination_iata","departure_date","departure_period","passenger_count"], scaled_flights)
    write("menu_items.csv", ["item_id","display_name","category","portion_mass_kg","unit_cost_eur","binary_consumption"],
          [(*row[:-1], str(row[-1]).lower()) for row in ITEMS])
    service_rows, obs_rows = [], []
    binary = {r[0] for r in ITEMS if r[-1]}
    for fi, flight in enumerate(FLIGHTS):
        flight_id = flight[0]
        for item_id, *_ in ITEMS:
            loaded, served = (
                value * DATA_VOLUME_MULTIPLIER for value in Q[item_id][fi]
            )
            service_rows.append((flight_id,item_id,loaded,served))
            continuous = None if item_id in binary else continuous_estimates(item_id, fi, served)
            for n in range(served):
                if item_id in binary:
                    # Even distribution approximation, deterministically shifted by flight.
                    pct = 100 if ((n * 37 + fi * 11) % 100) < BINARY_CONSUMED_RATE[item_id] * 100 else 0
                else:
                    pct = continuous[n]
                obs_rows.append((f"OBS-{fi+1:02d}-{item_id}-{n+1:03d}",flight_id,item_id,
                                 f"IMG-{fi+1:02d}-{n+1:03d}",f"REF-{item_id}-01",pct))
    write("flight_item_service.csv", ["flight_id","item_id","loaded_quantity","served_quantity"], service_rows)
    write("consumption_observations.csv", ["observation_id","flight_id","item_id","source_image_id","reference_image_id","consumption_estimate_pct"], obs_rows)
    write("assumptions.csv", ["assumption_key","scope","value","unit","description"], ASSUMPTIONS)

if __name__ == "__main__":
    main()
