"""Factory for creating Meal aggregates.

This factory encapsulates the complex creation logic for Meal aggregates,
ensuring all invariants are satisfied and totals are correctly calculated.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from domain.meal.core.entities.meal import Meal
from domain.meal.core.entities.meal_entry import MealEntry


class MealFactory:
    """Factory for creating Meal aggregates with proper initialization."""

    @staticmethod
    def create_from_analysis(
        user_id: str,
        items: list[tuple[dict[str, Any], dict[str, Any]]],
        source: str,
        timestamp: Optional[datetime] = None,
        meal_type: str = "SNACK",
        photo_url: Optional[str] = None,
        analysis_id: Optional[str] = None,
    ) -> Meal:
        """
        Create Meal from AI analysis results.

        This method is used when creating meals from photo recognition,
        barcode scanning, or text description analysis.

        Args:
            user_id: User ID who owns the meal
            items: List of (recognized_food, nutrients) tuples where:
                   - recognized_food: dict with keys: label, display_name, quantity_g,
                     confidence, source, category?, barcode?, image_url?
                   - nutrients: dict with keys: calories, protein, carbs, fat,
                     fiber?, sugar?, sodium?
            source: Source of the analysis (PHOTO | BARCODE | DESCRIPTION)
            timestamp: Meal timestamp (default: now UTC)
            meal_type: Type of meal (BREAKFAST | LUNCH | DINNER | SNACK)
            photo_url: Optional URL of the meal photo
            analysis_id: Optional ID linking to the analysis record

        Returns:
            New Meal aggregate with all entries and calculated totals

        Raises:
            ValueError: If items is empty or contains invalid data

        Example:
            >>> items = [
            ...     (
            ...         {
            ...             "label": "pasta",
            ...             "display_name": "Pasta al Pomodoro",
            ...             "quantity_g": 150.0,
            ...             "confidence": 0.95,
            ...             "source": "PHOTO",
            ...         },
            ...         {
            ...             "calories": 200,
            ...             "protein": 7.0,
            ...             "carbs": 40.0,
            ...             "fat": 2.0,
            ...         }
            ...     )
            ... ]
            >>> meal = MealFactory.create_from_analysis(
            ...     user_id="user123",
            ...     items=items,
            ...     source="PHOTO",
            ...     meal_type="LUNCH"
            ... )
        """
        if not items:
            raise ValueError("Cannot create meal with no items")

        meal_id = uuid4()
        timestamp = timestamp or datetime.now(timezone.utc)

        # Create entries from analysis
        entries = []
        for recognized, nutrients in items:
            entry = MealEntry(
                id=uuid4(),
                meal_id=meal_id,
                name=recognized["label"],
                display_name=recognized["display_name"],
                quantity_g=recognized["quantity_g"],
                calories=nutrients["calories"],
                protein=nutrients["protein"],
                carbs=nutrients["carbs"],
                fat=nutrients["fat"],
                fiber=nutrients.get("fiber"),
                sugar=nutrients.get("sugar"),
                sodium=nutrients.get("sodium"),
                source=source,
                confidence=recognized.get("confidence", 1.0),
                category=recognized.get("category"),
                barcode=recognized.get("barcode"),
                image_url=photo_url or recognized.get("image_url"),
            )
            entries.append(entry)

        # Calculate average confidence from entries
        avg_confidence = sum(e.confidence or 0.0 for e in entries) / len(entries)

        # Generate dish name from first entry or all entries
        if len(entries) == 1:
            dish_name = entries[0].display_name
        else:
            # Use first entry as primary, add count if multiple
            dish_name = f"{entries[0].display_name} (+{len(entries)-1} altri)"

        # Image URL: prioritize photo_url, fallback to entry image_url (barcode case)
        image_url = photo_url
        if not image_url and entries:
            # Check first entry for barcode image (OpenFoodFacts)
            image_url = entries[0].image_url

        # Create meal with entries
        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp,
            meal_type=meal_type,
            dish_name=dish_name,
            image_url=image_url,
            source=source,
            confidence=avg_confidence,
            entries=entries,
            analysis_id=analysis_id,
        )

        # Calculate totals from entries
        meal._recalculate_totals()

        return meal

    @staticmethod
    def create_manual(
        user_id: str,
        name: str,
        quantity_g: float,
        calories: int,
        protein: float,
        carbs: float,
        fat: float,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None,
        fiber: Optional[float] = None,
        sugar: Optional[float] = None,
        sodium: Optional[float] = None,
    ) -> Meal:
        """
        Create Meal from manual entry.

        This method is used when users manually enter nutritional data
        without AI analysis.

        Args:
            user_id: User ID who owns the meal
            name: Food name (used for both name and display_name)
            quantity_g: Quantity in grams
            calories: Total calories
            protein: Protein in grams
            carbs: Carbohydrates in grams
            fat: Fat in grams
            meal_type: Type of meal (BREAKFAST | LUNCH | DINNER | SNACK)
            timestamp: Meal timestamp (default: now UTC)
            fiber: Optional fiber in grams
            sugar: Optional sugar in grams
            sodium: Optional sodium in milligrams

        Returns:
            New Meal aggregate with single manual entry

        Raises:
            ValueError: If any validation fails

        Example:
            >>> meal = MealFactory.create_manual(
            ...     user_id="user123",
            ...     name="Banana",
            ...     quantity_g=120.0,
            ...     calories=105,
            ...     protein=1.3,
            ...     carbs=27.0,
            ...     fat=0.4,
            ...     meal_type="SNACK"
            ... )
        """
        meal_id = uuid4()
        timestamp = timestamp or datetime.now(timezone.utc)

        # Create single manual entry
        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name=name,
            display_name=name,
            quantity_g=quantity_g,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            sugar=sugar,
            sodium=sodium,
            source="MANUAL",
            confidence=1.0,  # Manual entries have full confidence
        )

        # Create meal with single entry
        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp,
            meal_type=meal_type,
            entries=[entry],
        )

        # Calculate totals from entry
        meal._recalculate_totals()

        return meal

    @staticmethod
    def create_empty(
        user_id: str,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None,
    ) -> tuple[Meal, UUID]:
        """
        Create an empty meal template ready to receive entries.

        This is useful for creating a meal container before adding entries
        one by one (e.g., during interactive meal building).

        Note: The returned meal has one placeholder entry that should be
        replaced with actual food items. The meal_id is returned separately
        so callers can create properly-linked entries.

        Args:
            user_id: User ID who owns the meal
            meal_type: Type of meal (BREAKFAST | LUNCH | DINNER | SNACK)
            timestamp: Meal timestamp (default: now UTC)

        Returns:
            Tuple of (Meal with placeholder entry, meal_id for creating entries)

        Example:
            >>> meal, meal_id = MealFactory.create_empty("user123", "BREAKFAST")
            >>> # Later, replace placeholder with real entries
        """
        meal_id = uuid4()
        timestamp = timestamp or datetime.now(timezone.utc)

        # Create placeholder entry (will be replaced)
        placeholder_entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="placeholder",
            display_name="Placeholder - Add Food Items",
            quantity_g=1.0,
            calories=0,
            protein=0.0,
            carbs=0.0,
            fat=0.0,
            source="MANUAL",
            confidence=0.0,
        )

        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp,
            meal_type=meal_type,
            entries=[placeholder_entry],
        )

        meal._recalculate_totals()

        return meal, meal_id
