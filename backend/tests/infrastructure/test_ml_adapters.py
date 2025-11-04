"""Tests for ML infrastructure adapters."""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from infrastructure.ml_adapters import (
    KalmanTDEEAdapter,
    WeightForecastAdapter,
)
from domain.nutritional_profile.core.entities import ProgressRecord
from domain.nutritional_profile.core.value_objects import ProfileId


def create_progress_record(
    record_date: date,
    weight: float,
    consumed_calories: float,
) -> ProgressRecord:
    """Helper to create progress record for testing."""
    return ProgressRecord(
        record_id=uuid4(),
        profile_id=ProfileId(uuid4()),
        date=record_date,
        weight=weight,
        consumed_calories=consumed_calories,
    )


class TestKalmanTDEEAdapter:
    """Tests for Kalman TDEE adapter."""

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = KalmanTDEEAdapter(initial_tdee=2000.0)

        tdee, std_dev = adapter.get_current_estimate()
        assert tdee == 2000.0
        assert std_dev > 0

    def test_update_with_progress(self):
        """Test updating TDEE with progress record."""
        adapter = KalmanTDEEAdapter(initial_tdee=2000.0)

        # First progress record
        progress1 = create_progress_record(
            record_date=date(2025, 1, 1),
            weight=80.0,
            consumed_calories=2000.0,
        )
        tdee1 = adapter.update_with_progress(progress1)
        assert tdee1 == 2000.0  # No update on first record

        # Second progress record (weight decreased)
        progress2 = create_progress_record(
            record_date=date(2025, 1, 2),
            weight=79.7,
            consumed_calories=2000.0,
        )
        tdee2 = adapter.update_with_progress(progress2)

        # TDEE should update based on weight change
        assert tdee2 > 0

    def test_update_batch(self):
        """Test batch update with multiple records."""
        adapter = KalmanTDEEAdapter(initial_tdee=2000.0)

        records = [
            create_progress_record(
                record_date=date(2025, 1, i),
                weight=80.0 - 0.1 * i,
                consumed_calories=1800.0,
            )
            for i in range(1, 11)
        ]

        final_tdee = adapter.update_batch(records)

        # Should have processed all records
        assert final_tdee > 0
        assert final_tdee != 2000.0  # Should have updated

    def test_get_current_estimate(self):
        """Test getting current estimate."""
        adapter = KalmanTDEEAdapter(initial_tdee=2500.0)

        tdee, std_dev = adapter.get_current_estimate()

        assert tdee == 2500.0
        assert std_dev == pytest.approx(100.0)  # sqrt(10000)

    def test_get_confidence_interval(self):
        """Test getting confidence interval."""
        adapter = KalmanTDEEAdapter(initial_tdee=2000.0)

        lower, upper = adapter.get_confidence_interval(confidence_level=0.95)

        assert lower < 2000.0 < upper
        assert (upper - lower) > 0

    def test_reset(self):
        """Test resetting adapter state."""
        adapter = KalmanTDEEAdapter(initial_tdee=2000.0)

        # Do some updates
        for i in range(5):
            progress = create_progress_record(
                record_date=date(2025, 1, i + 1),
                weight=80.0 - 0.1 * i,
                consumed_calories=1800.0,
            )
            adapter.update_with_progress(progress)

        # Reset to new TDEE
        adapter.reset(new_tdee=2500.0)

        tdee, _ = adapter.get_current_estimate()
        assert tdee == 2500.0

    def test_custom_noise_parameters(self):
        """Test initialization with custom noise parameters."""
        adapter = KalmanTDEEAdapter(
            initial_tdee=2000.0,
            process_noise=100.0,
            measurement_noise=0.05,
        )

        tdee, _ = adapter.get_current_estimate()
        assert tdee == 2000.0


class TestWeightForecastAdapter:
    """Tests for weight forecast adapter."""

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = WeightForecastAdapter()
        assert adapter is not None

    def test_forecast_from_progress(self):
        """Test forecasting from progress records."""
        adapter = WeightForecastAdapter()

        # Create progress history
        records = [
            create_progress_record(
                record_date=date(2025, 1, i),
                weight=80.0 - 0.1 * i,
                consumed_calories=2000.0,
            )
            for i in range(1, 16)
        ]

        forecast = adapter.forecast_from_progress(
            progress_records=records,
            days_ahead=14,
        )

        assert len(forecast.predictions) == 14
        assert len(forecast.dates) == 14
        assert forecast.model_used in [
            "SimpleTrend",
            "LinearRegression",
            "ExponentialSmoothing",
            "ARIMA(1,1,1)",
        ]

    def test_forecast_from_progress_with_confidence(self):
        """Test forecast confidence intervals."""
        adapter = WeightForecastAdapter()

        records = [
            create_progress_record(
                record_date=date(2025, 1, i),
                weight=75.0 + 0.05 * i,
                consumed_calories=2200.0,
            )
            for i in range(1, 11)
        ]

        forecast = adapter.forecast_from_progress(
            progress_records=records,
            confidence_level=0.68,
        )

        assert forecast.confidence_level == 0.68

        # All predictions should be within bounds
        for lower, pred, upper in zip(
            forecast.lower_bound,
            forecast.predictions,
            forecast.upper_bound,
        ):
            assert lower <= pred <= upper

    def test_forecast_from_data(self):
        """Test forecasting from raw data."""
        adapter = WeightForecastAdapter()

        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(20)]
        weights = [80.0 - 0.15 * i for i in range(20)]

        forecast = adapter.forecast_from_data(
            dates=dates,
            weights=weights,
            days_ahead=7,
        )

        assert len(forecast.predictions) == 7
        # Should predict continued weight loss
        assert forecast.predictions[-1] < weights[-1]

    def test_forecast_different_horizons(self):
        """Test forecasting with different time horizons."""
        adapter = WeightForecastAdapter()

        records = [
            create_progress_record(
                record_date=date(2025, 1, i),
                weight=80.0,
                consumed_calories=2000.0,
            )
            for i in range(1, 31)
        ]

        # Short forecast
        forecast_7 = adapter.forecast_from_progress(
            progress_records=records,
            days_ahead=7,
        )
        assert len(forecast_7.predictions) == 7

        # Long forecast
        forecast_30 = adapter.forecast_from_progress(
            progress_records=records,
            days_ahead=30,
        )
        assert len(forecast_30.predictions) == 30

    def test_forecast_validation(self):
        """Test forecast validates input data."""
        adapter = WeightForecastAdapter()

        # Insufficient data
        with pytest.raises(ValueError):
            adapter.forecast_from_progress(
                progress_records=[
                    create_progress_record(
                        record_date=date(2025, 1, 1),
                        weight=80.0,
                        consumed_calories=2000.0,
                    )
                ],
            )


class TestAdapterIntegration:
    """Integration tests for adapters working together."""

    def test_kalman_and_forecast_together(self):
        """Test using both adapters on same data."""
        kalman_adapter = KalmanTDEEAdapter(initial_tdee=2000.0)
        forecast_adapter = WeightForecastAdapter()

        # Create progress history
        records = [
            create_progress_record(
                record_date=date(2025, 1, i),
                weight=80.0 - 0.1 * i,
                consumed_calories=1800.0,
            )
            for i in range(1, 31)
        ]

        # Update TDEE estimate
        final_tdee = kalman_adapter.update_batch(records)
        tdee, std_dev = kalman_adapter.get_current_estimate()

        assert final_tdee > 0
        assert std_dev < 100.0  # Uncertainty should have decreased

        # Generate weight forecast
        forecast = forecast_adapter.forecast_from_progress(
            progress_records=records,
            days_ahead=14,
        )

        assert len(forecast.predictions) == 14
        # With consistent deficit, weight should continue decreasing
        assert forecast.predictions[-1] < records[-1].weight

    def test_realistic_weight_loss_scenario(self):
        """Test realistic weight loss with both adapters."""
        kalman_adapter = KalmanTDEEAdapter(initial_tdee=2200.0)
        forecast_adapter = WeightForecastAdapter()

        # User starts at 85kg, loses ~0.5kg/week for 8 weeks
        import numpy as np

        np.random.seed(42)

        records = [
            create_progress_record(
                record_date=date(2025, 1, 1) + timedelta(days=i),
                weight=85.0 - 0.5 * (i / 7) + np.random.normal(0, 0.2),
                consumed_calories=1700.0,
            )
            for i in range(56)
        ]

        # TDEE should adapt to actual results
        final_tdee = kalman_adapter.update_batch(records)

        # With 500 kcal deficit and 0.5kg/week loss, TDEE ≈ 2200
        assert 2000.0 < final_tdee < 2400.0

        # Forecast should predict continued loss
        forecast = forecast_adapter.forecast_from_progress(
            progress_records=records,
            days_ahead=28,
        )

        # After 56 days: ~81kg, forecast +28 days: ~79kg
        expected_final = 81.0 - 0.5 * 4
        assert forecast.predictions[-1] == pytest.approx(expected_final, abs=2.0)
