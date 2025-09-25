"""Definizione centralizzata dei nutrient field names utilizzati nel backend.

Evitare duplicazioni di liste hard-coded in più moduli.
"""

from __future__ import annotations

from typing import Final, List

NUTRIENT_FIELDS: Final[List[str]] = [
    "calories",
    "protein",
    "carbs",
    "fat",
    "fiber",
    "sugar",
    "sodium",
]

__all__ = ["NUTRIENT_FIELDS"]
