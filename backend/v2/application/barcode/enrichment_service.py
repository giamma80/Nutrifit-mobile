"""
Barcode enrichment service.

Orchestrates barcode lookup across USDA and OpenFoodFacts with
intelligent data merging and confidence scoring.
"""

import time
from typing import Optional

import structlog

from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    BarcodeQuality,
    OFFProduct,
)
from backend.v2.domain.meal.barcode.openfoodfacts_mapper import (
    OpenFoodFactsMapper,
)
from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.domain.shared.errors import BarcodeNotFoundError
from backend.v2.infrastructure.usda.api_client import USDAApiClient
from backend.v2.infrastructure.openfoodfacts.api_client import (
    OpenFoodFactsClient,
)

logger = structlog.get_logger(__name__)


class BarcodeEnrichmentResult:
    """Result of barcode enrichment with metadata."""

    def __init__(
        self,
        profile: NutrientProfile,
        quality: BarcodeQuality,
        product_name: Optional[str] = None,
        brand: Optional[str] = None,
        image_url: Optional[str] = None,
        barcode_value: Optional[str] = None,
    ) -> None:
        """Initialize enrichment result.

        Args:
            profile: Nutrient profile
            quality: Quality metrics
            product_name: Product name
            brand: Brand name
            image_url: Product image URL
            barcode_value: Barcode value
        """
        self.profile = profile
        self.quality = quality
        self.product_name = product_name
        self.brand = brand
        self.image_url = image_url
        self.barcode_value = barcode_value


class BarcodeEnrichmentService:
    """Orchestrates barcode-based nutrition enrichment.

    Flow:
    1. Query OpenFoodFacts (faster, more barcodes)
    2. Query USDA (higher quality, fewer barcodes)
    3. Merge data if both found
    4. Calculate confidence score
    """

    def __init__(
        self,
        usda_client: USDAApiClient,
        off_client: OpenFoodFactsClient,
    ) -> None:
        """Initialize service.

        Args:
            usda_client: USDA API client
            off_client: OpenFoodFacts API client
        """
        self.usda_client = usda_client
        self.off_client = off_client

    async def enrich(self, barcode: Barcode) -> BarcodeEnrichmentResult:
        """Enrich nutrition data by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Enrichment result with profile, quality, and metadata

        Raises:
            BarcodeNotFoundError: If barcode not found in any DB

        Example:
            >>> async def test():
            ...     async with USDAApiClient(api_key="test") as usda:
            ...         async with OpenFoodFactsClient() as off:
            ...             service = BarcodeEnrichmentService(usda, off)
            ...             barcode = Barcode(value="3017620422003")
            ...             result = await service.enrich(barcode)
            ...             return result
        """
        start_time = time.time()

        logger.info(
            "Starting barcode enrichment",
            barcode=barcode.value,
        )

        # Try OpenFoodFacts first (faster, more coverage)
        off_product: Optional[OFFProduct] = None
        off_time_ms = 0.0

        try:
            off_start = time.time()
            off_result = await self.off_client.get_product(barcode)
            off_time_ms = (time.time() - off_start) * 1000

            if off_result and off_result.product:
                off_product = off_result.product
                logger.info(
                    "Found in OpenFoodFacts",
                    barcode=barcode.value,
                    name=off_result.product.product_name or "Unknown",
                    brand=off_result.product.brands or "Unknown",
                    time_ms=round(off_time_ms, 2),
                )
        except BarcodeNotFoundError:
            logger.debug(
                "Not found in OpenFoodFacts",
                barcode=barcode.value,
                time_ms=round(off_time_ms, 2),
            )
        except Exception as e:
            logger.warning(
                "OpenFoodFacts lookup failed",
                barcode=barcode.value,
                error=str(e),
                time_ms=round(off_time_ms, 2),
            )

        # Try USDA (higher quality, less coverage)
        usda_profile: Optional[NutrientProfile] = None
        usda_time_ms = 0.0

        try:
            from backend.v2.domain.meal.nutrition.usda_mapper import (
                USDAMapper,
            )

            usda_start = time.time()
            usda_result = await self.usda_client.search_by_barcode(barcode)
            usda_time_ms = (time.time() - usda_start) * 1000

            if usda_result and usda_result.foods:
                usda_profile = USDAMapper.to_nutrient_profile(usda_result.foods[0])
                logger.info(
                    "Found in USDA",
                    barcode=barcode.value,
                    description=usda_result.foods[0].description,
                    time_ms=round(usda_time_ms, 2),
                )
        except Exception as e:
            logger.warning(
                "USDA lookup failed",
                barcode=barcode.value,
                error=str(e),
                time_ms=round(usda_time_ms, 2),
            )

        total_time_ms = (time.time() - start_time) * 1000

        # Merge data if both found
        if off_product and usda_profile:
            result = self._merge_data(off_product, usda_profile, barcode)
            logger.info(
                "Barcode enrichment completed (merged)",
                barcode=barcode.value,
                total_time_ms=round(total_time_ms, 2),
                off_time_ms=round(off_time_ms, 2),
                usda_time_ms=round(usda_time_ms, 2),
            )
            return result

        # Use OpenFoodFacts only
        if off_product:
            result = self._use_off_only(off_product, barcode)
            logger.info(
                "Barcode enrichment completed (OFF only)",
                barcode=barcode.value,
                total_time_ms=round(total_time_ms, 2),
                off_time_ms=round(off_time_ms, 2),
            )
            return result

        # Use USDA only
        if usda_profile:
            result = self._use_usda_only(usda_profile, barcode)
            logger.info(
                "Barcode enrichment completed (USDA only)",
                barcode=barcode.value,
                total_time_ms=round(total_time_ms, 2),
                usda_time_ms=round(usda_time_ms, 2),
            )
            return result

        # Not found anywhere
        logger.error(
            "Barcode not found in any database",
            barcode=barcode.value,
            total_time_ms=round(total_time_ms, 2),
        )
        raise BarcodeNotFoundError(f"Barcode {barcode.value} not found in any database")

    def _merge_data(
        self,
        off_product: OFFProduct,
        usda_profile: NutrientProfile,
        barcode: Barcode,
    ) -> BarcodeEnrichmentResult:
        """Merge OpenFoodFacts and USDA data.

        Strategy:
        - Use USDA for macros (higher quality)
        - Fill gaps with OpenFoodFacts
        - Use OFF for additional metadata (name, brand, image)

        Args:
            off_product: OpenFoodFacts product
            usda_profile: USDA nutrient profile
            barcode: Product barcode

        Returns:
            Enrichment result with merged data
        """
        logger.info("Merging USDA + OpenFoodFacts data", barcode=barcode.value)

        off_profile = OpenFoodFactsMapper.to_nutrient_profile(off_product)

        # Prefer USDA for main nutrients (higher quality)
        # But validate that values are reasonable
        merged = NutrientProfile(
            calories=self._choose_best_value(
                usda_profile.calories, off_profile.calories, "calories"
            ),
            protein=self._choose_best_value(usda_profile.protein, off_profile.protein, "protein"),
            carbs=self._choose_best_value(usda_profile.carbs, off_profile.carbs, "carbs"),
            fat=self._choose_best_value(usda_profile.fat, off_profile.fat, "fat"),
            # Fill gaps with OpenFoodFacts
            fiber=usda_profile.fiber or off_profile.fiber,
            sugar=usda_profile.sugar or off_profile.sugar,
            sodium=usda_profile.sodium or off_profile.sodium,
            source=NutrientSource.BARCODE_DB,  # Merged source
        )

        # Calculate quality
        completeness = self._calculate_completeness(merged)
        quality = BarcodeQuality(
            completeness=completeness,
            source_reliability=0.95,  # USDA + OFF is very reliable
            data_freshness=0.90,  # Both sources are recent
        )

        # Extract metadata from OpenFoodFacts
        return BarcodeEnrichmentResult(
            profile=merged,
            quality=quality,
            product_name=off_product.product_name,
            brand=off_product.brands,
            image_url=off_product.image_url,
            barcode_value=barcode.value,
        )

    def _use_off_only(self, off_product: OFFProduct, barcode: Barcode) -> BarcodeEnrichmentResult:
        """Use OpenFoodFacts data only.

        Args:
            off_product: OpenFoodFacts product
            barcode: Product barcode

        Returns:
            Enrichment result
        """
        logger.info("Using OpenFoodFacts only", barcode=barcode.value)

        profile = OpenFoodFactsMapper.to_nutrient_profile(off_product)

        completeness = OpenFoodFactsMapper.calculate_completeness(off_product)
        quality = BarcodeQuality(
            completeness=completeness,
            source_reliability=0.80,  # OFF is good but varies
            data_freshness=0.85,
        )

        return BarcodeEnrichmentResult(
            profile=profile,
            quality=quality,
            product_name=off_product.product_name,
            brand=off_product.brands,
            image_url=off_product.image_url,
            barcode_value=barcode.value,
        )

    def _use_usda_only(
        self, usda_profile: NutrientProfile, barcode: Barcode
    ) -> BarcodeEnrichmentResult:
        """Use USDA data only.

        Args:
            usda_profile: USDA nutrient profile
            barcode: Product barcode

        Returns:
            Enrichment result
        """
        logger.info("Using USDA only", barcode=barcode.value)

        completeness = self._calculate_completeness(usda_profile)
        quality = BarcodeQuality(
            completeness=completeness,
            source_reliability=0.95,  # USDA is very reliable
            data_freshness=0.80,  # May be older data
        )

        return BarcodeEnrichmentResult(
            profile=usda_profile,
            quality=quality,
            product_name=None,  # USDA doesn't have brand names
            brand=None,
            image_url=None,  # USDA doesn't have images
            barcode_value=barcode.value,
        )

    def _choose_best_value(
        self,
        usda_value: Optional[float],
        off_value: Optional[float],
        nutrient_name: str,
    ) -> float:
        """Choose best value between USDA and OFF.

        Strategy:
        - Prefer USDA if available (higher quality)
        - Use OFF as fallback
        - Log significant discrepancies

        Args:
            usda_value: USDA nutrient value
            off_value: OpenFoodFacts value
            nutrient_name: Name of nutrient (for logging)

        Returns:
            Best value to use
        """
        if usda_value is None or usda_value == 0:
            return off_value or 0.0

        if off_value is None or off_value == 0:
            return usda_value

        # Both have values - check for significant discrepancy
        diff_pct = abs(usda_value - off_value) / usda_value * 100
        if diff_pct > 20:  # More than 20% difference
            logger.warning(
                "Significant nutrient discrepancy",
                nutrient=nutrient_name,
                usda_value=round(usda_value, 2),
                off_value=round(off_value, 2),
                diff_percent=round(diff_pct, 1),
            )

        # Prefer USDA
        return usda_value

    def _calculate_completeness(self, profile: NutrientProfile) -> float:
        """Calculate nutrient profile completeness.

        Args:
            profile: Nutrient profile

        Returns:
            Completeness score (0-1)
        """
        fields_to_check = [
            profile.calories,
            profile.protein,
            profile.carbs,
            profile.fat,
            profile.fiber,
            profile.sugar,
            profile.sodium,
        ]

        filled = sum(1 for field in fields_to_check if field is not None and field > 0)
        return round(filled / len(fields_to_check), 2)
