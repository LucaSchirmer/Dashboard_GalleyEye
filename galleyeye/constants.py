"""Contract constants shared by generation and validation."""

EXPECTED_FLIGHT_ROWS = {
    "FRA-HND-2026-07-04-GE101": ("GE101", "FRA", "HND", "2026-07-04", "Day", 714),
    "FRA-HND-2026-07-18-GE101": ("GE101", "FRA", "HND", "2026-07-18", "Night", 756),
    "HND-FRA-2026-07-08-GE102": ("GE102", "HND", "FRA", "2026-07-08", "Day", 732),
    "HND-FRA-2026-07-22-GE102": ("GE102", "HND", "FRA", "2026-07-22", "Night", 687),
}
EXPECTED_FLIGHTS = set(EXPECTED_FLIGHT_ROWS)

CATALOG = {
    "chicken_rice_vegetables": ("Chicken–Rice–Vegetables", "Main Course"),
    "fish_rice_vegetables": ("Fish–Rice–Vegetables", "Main Course"),
    "salad": ("Salad", "Main Course"),
    "wrap": ("Wrap", "Main Course"),
    "bread_roll": ("Bread Roll", "Side Dish"),
    "standard_side_salad": ("Standard Side Salad", "Side Dish"),
    "chocolate_cake": ("Chocolate Cake", "Dessert"),
    "vanilla_pudding_fruit": ("Vanilla Pudding with Fruit", "Dessert"),
    "fruit_salad": ("Fruit Salad", "Dessert"),
    "cola": ("Cola", "Beverage"),
    "orange_juice": ("Orange Juice", "Beverage"),
    "water": ("Water", "Beverage"),
    "coffee": ("Coffee", "Beverage"),
    "tea": ("Tea", "Beverage"),
    "butter": ("Butter", "Accompaniment"),
    "cherry_jam": ("Cherry Jam", "Accompaniment"),
    "plum_jam": ("Plum Jam", "Accompaniment"),
    "honey": ("Honey", "Accompaniment"),
    "cookie": ("Cookie", "Snack"),
}

CATEGORIES = {"Main Course", "Side Dish", "Dessert", "Beverage", "Accompaniment", "Snack"}
BINARY_CATEGORIES = {"Beverage", "Accompaniment", "Snack"}
DATA_FILES = ("flights.csv", "menu_items.csv", "flight_item_service.csv", "consumption_observations.csv", "assumptions.csv")
