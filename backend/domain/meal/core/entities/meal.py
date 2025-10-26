"""Meal aggregate root - complete meal with multiple dishes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from .meal_entry import MealEntry


@dataclass
class Meal:
    """
    Aggregate Root: Complete meal with multiple dishes.

    A Meal represents a complete eating occasion (breakfast, lunch, etc.)
    and contains one or more MealEntry items (individual dishes).

    Example:
        Meal = "Pranzo del 22 Ottobre"
        ├─ MealEntry 1 = "Pasta al pomodoro" (150g)
        ├─ MealEntry 2 = "Insalata mista" (100g)
        └─ MealEntry 3 = "Pane integrale" (50g)

    Invariants:
    - Must have at least one entry
    - Totals must equal sum of entries
    - Timestamp cannot be in the future

    Identity: Defined by unique ID (UUID)
    Mutability: Can be modified (entries can be added/removed/updated)
    """

    id: UUID
    user_id: str
    timestamp: datetime
    meal_type: str  # BREAKFAST | LUNCH | DINNER | SNACK

    # Recognition metadata (from analysis)
    dish_name: str = "Meal"  # Recognized dish name (e.g., "Spaghetti Carbonara")
    image_url: Optional[str] = None  # Photo/barcode image URL
    source: str = "manual"  # Analysis source: "gpt4v_v2", "barcode", "manual", "text"
    confidence: float = 1.0  # Average confidence (0.0-1.0)

    # Aggregate content
    entries: List[MealEntry] = field(default_factory=list)

    # Aggregated totals (calculated from entries)
    total_calories: int = 0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    total_sugar: float = 0.0
    total_sodium: float = 0.0

    # Metadata
    analysis_id: Optional[str] = None
    notes: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (use UTC)")

        if self.meal_type not in ["BREAKFAST", "LUNCH", "DINNER", "SNACK"]:
            raise ValueError(f"Invalid meal_type: {self.meal_type}")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (use UTC)")

        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware (use UTC)")

    def add_entry(self, entry: MealEntry) -> None:
        """
        Add entry to meal and recalculate totals.

        Args:
            entry: MealEntry to add

        Raises:
            ValueError: If entry.meal_id doesn't match this meal's id
        """
        if entry.meal_id != self.id:
            raise ValueError(f"Entry meal_id {entry.meal_id} doesn't match Meal id {self.id}")

        self.entries.append(entry)
        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)

    def remove_entry(self, entry_id: UUID) -> None:
        """
        Remove entry from meal and recalculate totals.

        Args:
            entry_id: ID of entry to remove

        Raises:
            ValueError: If meal would have no entries after removal
        """
        self.entries = [e for e in self.entries if e.id != entry_id]

        if not self.entries:
            raise ValueError("Meal must have at least one entry")

        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)

    def update_entry(self, entry_id: UUID, **updates: float | str | None) -> None:
        """
        Update an entry and recalculate totals.

        Args:
            entry_id: ID of entry to update
            **updates: Field updates (e.g., quantity_g=200)

        Raises:
            ValueError: If entry not found or invalid field
        """
        for entry in self.entries:
            if entry.id == entry_id:
                # Update fields
                for key, value in updates.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                    else:
                        raise ValueError(f"Invalid field: {key}")

                # Re-validate entry
                entry.__post_init__()
                break
        else:
            raise ValueError(f"Entry {entry_id} not found in meal {self.id}")

        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)

    def _recalculate_totals(self) -> None:
        """Recalculate aggregated totals from entries."""
        self.total_calories = sum(e.calories for e in self.entries)
        self.total_protein = sum(e.protein for e in self.entries)
        self.total_carbs = sum(e.carbs for e in self.entries)
        self.total_fat = sum(e.fat for e in self.entries)
        self.total_fiber = sum(e.fiber or 0.0 for e in self.entries)
        self.total_sugar = sum(e.sugar or 0.0 for e in self.entries)
        self.total_sodium = sum(e.sodium or 0.0 for e in self.entries)

    def validate_invariants(self) -> None:
        """
        Validate all meal invariants.

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.entries:
            raise ValueError("Meal must have at least one entry")

        if self.timestamp > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")

        # Verify totals match entries
        expected_calories = sum(e.calories for e in self.entries)
        if abs(self.total_calories - expected_calories) > 1:  # Allow 1 cal rounding
            raise ValueError(
                f"Total calories mismatch: {self.total_calories} != {expected_calories}"
            )

    def get_nutrient_distribution(self) -> dict[str, float]:
        """
        Get macronutrient distribution as percentages.

        Returns:
            Dict with protein_pct, carbs_pct, fat_pct
        """
        total_cals_from_macros = (
            self.total_protein * 4  # 4 cal/g protein
            + self.total_carbs * 4  # 4 cal/g carbs
            + self.total_fat * 9  # 9 cal/g fat
        )

        if total_cals_from_macros == 0:
            return {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

        return {
            "protein_pct": (self.total_protein * 4 / total_cals_from_macros) * 100,
            "carbs_pct": (self.total_carbs * 4 / total_cals_from_macros) * 100,
            "fat_pct": (self.total_fat * 9 / total_cals_from_macros) * 100,
        }

    def is_high_protein(self) -> bool:
        """Check if meal is high protein (>30% calories from protein)."""
        distribution = self.get_nutrient_distribution()
        return distribution["protein_pct"] > 30

    def average_confidence(self) -> float:
        """Calculate average confidence across all entries."""
        if not self.entries:
            return 0.0
        return sum(e.confidence for e in self.entries) / len(self.entries)
