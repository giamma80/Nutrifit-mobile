"""Unit tests for BarcodeProduct entity.

Tests validation, business logic, and invariants.
"""

import pytest

from domain.meal.barcode.entities import BarcodeProduct
from domain.meal.nutrition.entities import NutrientProfile


class TestBarcodeProduct:
    """Test suite for BarcodeProduct entity."""

    def test_creates_barcode_product_with_required_fields(self) -> None:
        """Test creating barcode product with required fields."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.95,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Galletti Biscuits",
            brand="Mulino Bianco",
            nutrients=nutrients,
        )

        assert product.barcode == "8001505005707"
        assert product.name == "Galletti Biscuits"
        assert product.brand == "Mulino Bianco"
        assert product.nutrients.calories == 450
        assert product.image_url is None
        assert product.serving_size_g is None

    def test_creates_barcode_product_with_optional_fields(self) -> None:
        """Test creating barcode product with all optional fields."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Galletti Biscuits",
            brand="Mulino Bianco",
            nutrients=nutrients,
            image_url="https://images.openfoodfacts.org/product.jpg",
            serving_size_g=25.0,
        )

        assert product.image_url == "https://images.openfoodfacts.org/product.jpg"
        assert product.serving_size_g == 25.0

    def test_raises_if_barcode_empty(self) -> None:
        """Test that empty barcode raises ValueError."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        with pytest.raises(ValueError, match="Barcode cannot be empty"):
            BarcodeProduct(
                barcode="",
                name="Product",
                brand="Brand",
                nutrients=nutrients,
            )

        with pytest.raises(ValueError, match="Barcode cannot be empty"):
            BarcodeProduct(
                barcode="   ",
                name="Product",
                brand="Brand",
                nutrients=nutrients,
            )

    def test_raises_if_barcode_not_alphanumeric(self) -> None:
        """Test that non-alphanumeric barcode raises ValueError."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        # Special characters not allowed (except - and space which are cleaned)
        with pytest.raises(ValueError, match="must be alphanumeric"):
            BarcodeProduct(
                barcode="800#150@500",
                name="Product",
                brand="Brand",
                nutrients=nutrients,
            )

    def test_raises_if_name_empty(self) -> None:
        """Test that empty name raises ValueError."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        with pytest.raises(ValueError, match="name cannot be empty"):
            BarcodeProduct(
                barcode="8001505005707",
                name="",
                brand="Brand",
                nutrients=nutrients,
            )

        with pytest.raises(ValueError, match="name cannot be empty"):
            BarcodeProduct(
                barcode="8001505005707",
                name="   ",
                brand="Brand",
                nutrients=nutrients,
            )

    def test_raises_if_serving_size_not_positive(self) -> None:
        """Test that non-positive serving size raises ValueError."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        with pytest.raises(ValueError, match="Serving size must be positive"):
            BarcodeProduct(
                barcode="8001505005707",
                name="Product",
                brand="Brand",
                nutrients=nutrients,
                serving_size_g=0.0,
            )

        with pytest.raises(ValueError, match="Serving size must be positive"):
            BarcodeProduct(
                barcode="8001505005707",
                name="Product",
                brand="Brand",
                nutrients=nutrients,
                serving_size_g=-10.0,
            )

    def test_has_image_returns_true_when_image_url_set(self) -> None:
        """Test that has_image returns True when image_url is set."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
            image_url="https://example.com/image.jpg",
        )

        assert product.has_image() is True

    def test_has_image_returns_false_when_no_image_url(self) -> None:
        """Test that has_image returns False when image_url is None or empty."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product_no_url = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
            image_url=None,
        )

        product_empty_url = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
            image_url="   ",
        )

        assert product_no_url.has_image() is False
        assert product_empty_url.has_image() is False

    def test_has_brand_returns_true_when_brand_set(self) -> None:
        """Test that has_brand returns True when brand is set."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Mulino Bianco",
            nutrients=nutrients,
        )

        assert product.has_brand() is True

    def test_has_brand_returns_false_when_no_brand(self) -> None:
        """Test that has_brand returns False when brand is None or empty."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product_no_brand = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand=None,
            nutrients=nutrients,
        )

        product_empty_brand = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="   ",
            nutrients=nutrients,
        )

        assert product_no_brand.has_brand() is False
        assert product_empty_brand.has_brand() is False

    def test_display_name_includes_brand_when_available(self) -> None:
        """Test that display_name includes brand when available."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Galletti Biscuits",
            brand="Mulino Bianco",
            nutrients=nutrients,
        )

        assert product.display_name() == "Mulino Bianco - Galletti Biscuits"

    def test_display_name_only_name_when_no_brand(self) -> None:
        """Test that display_name returns only name when no brand."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Generic Crackers",
            brand=None,
            nutrients=nutrients,
        )

        assert product.display_name() == "Generic Crackers"

    def test_scale_nutrients_scales_correctly(self) -> None:
        """Test that scale_nutrients scales to target quantity."""
        # Nutrients per 100g
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            quantity_g=100.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        # Scale to 50g
        scaled = product.scale_nutrients(50.0)

        assert scaled.calories == 225  # 450 * 0.5
        assert scaled.protein == 3.25  # 6.5 * 0.5
        assert scaled.carbs == 34.0  # 68.0 * 0.5
        assert scaled.fat == 8.0  # 16.0 * 0.5
        assert scaled.quantity_g == 50.0

    def test_scale_nutrients_raises_if_quantity_not_positive(self) -> None:
        """Test that scale_nutrients raises ValueError for invalid quantity."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            product.scale_nutrients(0.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            product.scale_nutrients(-10.0)

    def test_is_high_quality_returns_true_for_barcode_db_source(self) -> None:
        """Test that is_high_quality returns True for BARCODE_DB source."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.95,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        assert product.is_high_quality() is True

    def test_is_high_quality_returns_false_for_low_confidence(self) -> None:
        """Test that is_high_quality returns False for low confidence."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="AI_ESTIMATE",
            confidence=0.6,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        assert product.is_high_quality() is False
