"""
Category-based nutrient profiles for fallback.

Used when USDA lookup fails to provide reasonable estimates.
"""

from backend.v2.domain.meal.nutrition.usda_models import (
    CategoryProfile,
    FoodCategory,
)


# Default nutrient profiles by category (per 100g)
CATEGORY_PROFILES: dict[FoodCategory, CategoryProfile] = {
    FoodCategory.FRUIT: CategoryProfile(
        category=FoodCategory.FRUIT,
        calories_per_100g=52.0,
        protein_per_100g=0.5,
        carbs_per_100g=14.0,
        fat_per_100g=0.2,
        fiber_per_100g=2.4,
        sugar_per_100g=10.0,
        sodium_per_100g=1.0,
    ),
    FoodCategory.VEGETABLE: CategoryProfile(
        category=FoodCategory.VEGETABLE,
        calories_per_100g=25.0,
        protein_per_100g=2.0,
        carbs_per_100g=5.0,
        fat_per_100g=0.3,
        fiber_per_100g=2.0,
        sugar_per_100g=2.0,
        sodium_per_100g=20.0,
    ),
    FoodCategory.PROTEIN: CategoryProfile(
        category=FoodCategory.PROTEIN,
        calories_per_100g=165.0,
        protein_per_100g=25.0,
        carbs_per_100g=0.0,
        fat_per_100g=7.0,
        fiber_per_100g=0.0,
        sugar_per_100g=0.0,
        sodium_per_100g=70.0,
    ),
    FoodCategory.GRAIN: CategoryProfile(
        category=FoodCategory.GRAIN,
        calories_per_100g=350.0,
        protein_per_100g=10.0,
        carbs_per_100g=75.0,
        fat_per_100g=2.0,
        fiber_per_100g=3.0,
        sugar_per_100g=1.0,
        sodium_per_100g=5.0,
    ),
    FoodCategory.DAIRY: CategoryProfile(
        category=FoodCategory.DAIRY,
        calories_per_100g=60.0,
        protein_per_100g=3.3,
        carbs_per_100g=4.8,
        fat_per_100g=3.0,
        fiber_per_100g=0.0,
        sugar_per_100g=4.8,
        sodium_per_100g=50.0,
    ),
    FoodCategory.FAT: CategoryProfile(
        category=FoodCategory.FAT,
        calories_per_100g=720.0,
        protein_per_100g=0.0,
        carbs_per_100g=0.0,
        fat_per_100g=80.0,
        fiber_per_100g=0.0,
        sugar_per_100g=0.0,
        sodium_per_100g=2.0,
    ),
    FoodCategory.BEVERAGE: CategoryProfile(
        category=FoodCategory.BEVERAGE,
        calories_per_100g=40.0,
        protein_per_100g=0.0,
        carbs_per_100g=10.0,
        fat_per_100g=0.0,
        fiber_per_100g=0.0,
        sugar_per_100g=10.0,
        sodium_per_100g=10.0,
    ),
    FoodCategory.SNACK: CategoryProfile(
        category=FoodCategory.SNACK,
        calories_per_100g=500.0,
        protein_per_100g=6.0,
        carbs_per_100g=60.0,
        fat_per_100g=25.0,
        fiber_per_100g=2.0,
        sugar_per_100g=20.0,
        sodium_per_100g=400.0,
    ),
    FoodCategory.DESSERT: CategoryProfile(
        category=FoodCategory.DESSERT,
        calories_per_100g=300.0,
        protein_per_100g=4.0,
        carbs_per_100g=45.0,
        fat_per_100g=12.0,
        fiber_per_100g=1.0,
        sugar_per_100g=35.0,
        sodium_per_100g=150.0,
    ),
    FoodCategory.UNKNOWN: CategoryProfile(
        category=FoodCategory.UNKNOWN,
        calories_per_100g=200.0,
        protein_per_100g=8.0,
        carbs_per_100g=25.0,
        fat_per_100g=8.0,
        fiber_per_100g=2.0,
        sugar_per_100g=5.0,
        sodium_per_100g=100.0,
    ),
}


def get_category_profile(category: FoodCategory) -> CategoryProfile:
    """Get fallback profile for category.

    Args:
        category: Food category

    Returns:
        Nutrient profile for category

    Example:
        >>> profile = get_category_profile(FoodCategory.FRUIT)
        >>> assert profile.calories_per_100g == 52.0
        >>> assert profile.category == FoodCategory.FRUIT
    """
    return CATEGORY_PROFILES.get(category, CATEGORY_PROFILES[FoodCategory.UNKNOWN])


def infer_category(description: str) -> FoodCategory:
    """Infer food category from description.

    Args:
        description: Food description

    Returns:
        Inferred category

    Example:
        >>> category = infer_category("Apple juice")
        >>> assert category == FoodCategory.BEVERAGE

        >>> category = infer_category("Grilled chicken breast")
        >>> assert category == FoodCategory.PROTEIN

        >>> category = infer_category("Unknown food item")
        >>> assert category == FoodCategory.UNKNOWN
    """
    desc_lower = description.lower()

    # Beverage keywords (check first as they override)
    beverage_keywords = [
        "juice",
        "drink",
        "soda",
        "tea",
        "coffee",
        "smoothie",
        "milk",
        "water",
        "beer",
        "wine",
    ]
    if any(kw in desc_lower for kw in beverage_keywords):
        return FoodCategory.BEVERAGE

    # Fruit keywords
    fruit_keywords = [
        "apple",
        "banana",
        "orange",
        "berry",
        "grape",
        "melon",
        "peach",
        "pear",
        "plum",
        "fruit",
    ]
    if any(kw in desc_lower for kw in fruit_keywords):
        return FoodCategory.FRUIT

    # Vegetable keywords
    veg_keywords = [
        "lettuce",
        "tomato",
        "carrot",
        "broccoli",
        "spinach",
        "cabbage",
        "pepper",
        "cucumber",
        "vegetable",
        "salad",
    ]
    if any(kw in desc_lower for kw in veg_keywords):
        return FoodCategory.VEGETABLE

    # Protein keywords
    protein_keywords = [
        "chicken",
        "beef",
        "pork",
        "fish",
        "turkey",
        "egg",
        "meat",
        "salmon",
        "tuna",
        "tofu",
    ]
    if any(kw in desc_lower for kw in protein_keywords):
        return FoodCategory.PROTEIN

    # Grain keywords
    grain_keywords = [
        "bread",
        "rice",
        "pasta",
        "cereal",
        "oat",
        "wheat",
        "grain",
        "flour",
        "noodle",
    ]
    if any(kw in desc_lower for kw in grain_keywords):
        return FoodCategory.GRAIN

    # Dairy keywords
    dairy_keywords = [
        "cheese",
        "yogurt",
        "cream",
        "butter",
        "dairy",
    ]
    if any(kw in desc_lower for kw in dairy_keywords):
        return FoodCategory.DAIRY

    # Fat/Oil keywords
    fat_keywords = ["oil", "fat", "mayo", "margarine"]
    if any(kw in desc_lower for kw in fat_keywords):
        return FoodCategory.FAT

    # Dessert keywords
    dessert_keywords = [
        "cake",
        "cookie",
        "ice cream",
        "chocolate",
        "candy",
        "dessert",
        "brownie",
        "pie",
    ]
    if any(kw in desc_lower for kw in dessert_keywords):
        return FoodCategory.DESSERT

    # Snack keywords
    snack_keywords = [
        "chip",
        "cracker",
        "popcorn",
        "pretzel",
        "nut",
        "snack",
    ]
    if any(kw in desc_lower for kw in snack_keywords):
        return FoodCategory.SNACK

    return FoodCategory.UNKNOWN
