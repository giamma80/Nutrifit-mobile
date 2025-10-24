"""USDA FoodData Central API client."""

from infrastructure.external_apis.usda.client import USDAClient, normalize_food_label

__all__ = [
    "USDAClient",
    "normalize_food_label",
]
