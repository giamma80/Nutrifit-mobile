"""Tests for MealAnalysisService display_name preservation.

Test suite per verificare che il display_name sia preservato
durante la pipeline di normalizzazione.
"""

import pytest

from domain.meal.application.meal_analysis_service import MealAnalysisService
from domain.meal.model import MealItem
from domain.meal.pipeline.normalizer import MealNormalizationPipeline


class TestMealAnalysisServiceDisplayName:
    """Test per verificare preservazione display_name nella pipeline."""

    def setup_method(self):
        """Setup del test con service mock."""
        self.pipeline = MealNormalizationPipeline(debug_enabled=False)
        self.service = MealAnalysisService(
            legacy_adapter=None,  # Non necessario per test conversioni
            normalization_pipeline=self.pipeline,
        )

    def test_display_name_preservation_through_normalization(self):
        """Test che display_name sia preservato durante conversione."""
        # Arrange - MealItem con display_name in italiano
        original_item = MealItem(
            label="chicken breast",
            confidence=0.95,
            display_name="Petto di pollo grigliato",
            quantity_g=150.0,
            calories=200,
            protein=30.0,
            carbs=0.0,
            fat=5.0,
        )

        # Act - Conversione andata e ritorno
        normalized_item = self.service._convert_to_normalized_item(
            original_item
        )
        converted_back = self.service._convert_from_normalized_item(
            normalized_item
        )

        # Assert - display_name deve essere identico
        assert converted_back.display_name == original_item.display_name
        assert converted_back.display_name == "Petto di pollo grigliato"
        assert normalized_item.display_name == "Petto di pollo grigliato"

    def test_display_name_none_handling(self):
        """Test gestione display_name None."""
        # Arrange
        item_without_display_name = MealItem(
            label="rice",
            confidence=0.8,
            display_name=None,
            quantity_g=100.0,
            calories=130,
        )

        # Act
        normalized = self.service._convert_to_normalized_item(
            item_without_display_name
        )
        back = self.service._convert_from_normalized_item(normalized)

        # Assert
        assert back.display_name is None
        assert normalized.display_name is None

    def test_display_name_different_from_label(self):
        """Test display_name diverso da label."""
        # Arrange
        original_item = MealItem(
            label="grilled_salmon",  # Label per USDA
            confidence=0.92,
            display_name="Salmone alla griglia",  # Display name italiano
            quantity_g=120.0,
            calories=180,
        )

        # Act
        normalized = self.service._convert_to_normalized_item(original_item)
        back = self.service._convert_from_normalized_item(normalized)

        # Assert - display_name preservato, diverso da label
        assert back.display_name == "Salmone alla griglia"
        assert back.label == "grilled_salmon"
        assert back.display_name != back.label