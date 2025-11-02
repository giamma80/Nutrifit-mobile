"""Tests for weight forecasting service."""

import pytest
import numpy as np
from datetime import date, timedelta
from domain.nutritional_profile.ml.weight_forecast import (
    WeightForecastService,
    WeightForecast,
)


class TestWeightForecast:
    """Tests for WeightForecast dataclass."""

    def test_valid_forecast(self):
        """Test creating valid forecast."""
        dates = [date(2025, 1, i) for i in range(1, 6)]
        predictions = [80.0, 79.8, 79.6, 79.4, 79.2]
        lower = [79.5, 79.2, 78.9, 78.6, 78.3]
        upper = [80.5, 80.4, 80.3, 80.2, 80.1]

        forecast = WeightForecast(
            dates=dates,
            predictions=predictions,
            lower_bound=lower,
            upper_bound=upper,
            model_used="TestModel",
            confidence_level=0.95,
        )

        assert len(forecast.dates) == 5
        assert forecast.model_used == "TestModel"
        assert forecast.confidence_level == 0.95

    def test_inconsistent_lengths(self):
        """Test validation catches inconsistent array lengths."""
        with pytest.raises(ValueError, match="All forecast arrays must have the same length"):
            WeightForecast(
                dates=[date(2025, 1, 1)],
                predictions=[80.0, 79.8],  # Wrong length
                lower_bound=[79.0],
                upper_bound=[81.0],
                model_used="Test",
                confidence_level=0.95,
            )


class TestWeightForecastServiceValidation:
    """Tests for input validation."""

    def test_mismatched_lengths(self):
        """Test error on mismatched dates/weights lengths."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="Dates and weights must have same length"):
            service.forecast(
                dates=[date(2025, 1, 1), date(2025, 1, 2)],
                weights=[80.0],  # Wrong length
            )

    def test_insufficient_data(self):
        """Test error on insufficient data points."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="Need at least 2 data points"):
            service.forecast(
                dates=[date(2025, 1, 1)],
                weights=[80.0],
            )

    def test_negative_days_ahead(self):
        """Test error on negative forecast horizon."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="days_ahead must be positive"):
            service.forecast(
                dates=[date(2025, 1, 1), date(2025, 1, 2)],
                weights=[80.0, 79.8],
                days_ahead=-5,
            )

    def test_invalid_confidence_level(self):
        """Test error on invalid confidence level."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="confidence_level must be between 0 and 1"):
            service.forecast(
                dates=[date(2025, 1, 1), date(2025, 1, 2)],
                weights=[80.0, 79.8],
                confidence_level=1.5,
            )

    def test_negative_weights(self):
        """Test error on negative weights."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="All weights must be positive"):
            service.forecast(
                dates=[date(2025, 1, 1), date(2025, 1, 2)],
                weights=[80.0, -5.0],
            )

    def test_unsorted_dates(self):
        """Test error on unsorted dates."""
        service = WeightForecastService()

        with pytest.raises(ValueError, match="Dates must be sorted in ascending order"):
            service.forecast(
                dates=[date(2025, 1, 2), date(2025, 1, 1)],
                weights=[80.0, 79.8],
            )


class TestWeightForecastServiceSimple:
    """Tests for simple forecasting method (<7 points)."""

    def test_simple_forecast_very_short_history(self):
        """Test simple trend forecast with minimal data."""
        service = WeightForecastService()

        # 3 data points showing weight loss
        dates = [date(2025, 1, i) for i in range(1, 4)]
        weights = [80.0, 79.5, 79.0]  # -0.5 kg/day

        forecast = service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=7,
            confidence_level=0.95,
        )

        assert forecast.model_used == "SimpleTrend"
        assert len(forecast.predictions) == 7
        assert len(forecast.dates) == 7

        # Should continue downward trend
        assert forecast.predictions[0] < weights[-1]
        assert forecast.predictions[-1] < forecast.predictions[0]

        # Confidence intervals should be wide
        margin_day1 = (forecast.upper_bound[0] - forecast.lower_bound[0]) / 2
        margin_day7 = (forecast.upper_bound[-1] - forecast.lower_bound[-1]) / 2
        assert margin_day7 > margin_day1  # Expanding uncertainty

    def test_simple_forecast_dates_are_correct(self):
        """Test forecast generates correct future dates."""
        service = WeightForecastService()

        dates = [date(2025, 1, 1), date(2025, 1, 2)]
        weights = [80.0, 79.8]

        forecast = service.forecast(dates=dates, weights=weights)

        expected_dates = [date(2025, 1, 3) + timedelta(days=i) for i in range(30)]
        assert forecast.dates == expected_dates


class TestWeightForecastServiceLinear:
    """Tests for linear regression method (7-13 points)."""

    def test_linear_forecast_medium_history(self):
        """Test linear regression with medium history."""
        service = WeightForecastService()

        # 10 data points with clear linear trend
        dates = [date(2025, 1, i) for i in range(1, 11)]
        # Losing 0.2 kg/day
        weights = [80.0 - 0.2 * i for i in range(10)]

        forecast = service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=7,
        )

        assert forecast.model_used == "LinearRegression"
        assert len(forecast.predictions) == 7

        # Should continue linear trend
        # After 10 days at -0.2 kg/day: 78.0 kg
        # Day 11 should be ~77.8 kg
        assert forecast.predictions[0] == pytest.approx(77.8, abs=0.5)

        # Confidence intervals should exist
        assert all(
            l < p < u
            for l, p, u in zip(
                forecast.lower_bound,
                forecast.predictions,
                forecast.upper_bound,
            )
        )

    def test_linear_forecast_upward_trend(self):
        """Test linear forecast with weight gain."""
        service = WeightForecastService()

        dates = [date(2025, 1, i) for i in range(1, 9)]
        # Gaining 0.1 kg/day
        weights = [70.0 + 0.1 * i for i in range(8)]

        forecast = service.forecast(dates=dates, weights=weights)

        # Should predict continued gain
        assert forecast.predictions[0] > weights[-1]
        assert forecast.predictions[-1] > forecast.predictions[0]


class TestWeightForecastServiceExponentialSmoothing:
    """Tests for exponential smoothing (14-29 points)."""

    def test_exp_smoothing_medium_long_history(self):
        """Test exponential smoothing with adequate data."""
        service = WeightForecastService()

        # 20 data points with trend + noise
        np.random.seed(42)
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(20)]
        # Trend: -0.15 kg/day + noise
        weights = [80.0 - 0.15 * i + np.random.normal(0, 0.2) for i in range(20)]

        forecast = service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=14,
        )

        assert forecast.model_used == "ExponentialSmoothing"
        assert len(forecast.predictions) == 14

        # Should predict continued weight loss
        assert forecast.predictions[-1] < weights[-1]

        # Confidence intervals should expand over time
        margin_start = forecast.upper_bound[0] - forecast.lower_bound[0]
        margin_end = forecast.upper_bound[-1] - forecast.lower_bound[-1]
        assert margin_end > margin_start


class TestWeightForecastServiceARIMA:
    """Tests for ARIMA model (30+ points)."""

    def test_arima_long_history(self):
        """Test ARIMA or fallback with sufficient data."""
        service = WeightForecastService()

        # 40 data points with realistic pattern
        np.random.seed(42)
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(40)]
        # Weight loss with decreasing rate (plateau effect)
        weights = [
            85.0 - 5.0 * (1 - np.exp(-i / 20)) + np.random.normal(0, 0.15) for i in range(40)
        ]

        forecast = service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=30,
        )

        # ARIMA may fall back to ExponentialSmoothing if convergence fails
        assert forecast.model_used in ["ARIMA(1,1,1)", "ExponentialSmoothing"]
        assert len(forecast.predictions) == 30

        # Should have reasonable predictions
        assert all(60 < w < 90 for w in forecast.predictions)

        # Confidence intervals should be reasonable
        for lower, pred, upper in zip(
            forecast.lower_bound,
            forecast.predictions,
            forecast.upper_bound,
        ):
            assert lower < pred < upper
            # Margin shouldn't be crazy wide
            assert (upper - lower) < 10.0

    def test_arima_stable_weight(self):
        """Test ARIMA with stable weight (maintenance)."""
        service = WeightForecastService()

        # 35 points oscillating around 75 kg
        np.random.seed(42)
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(35)]
        weights = [75.0 + np.random.normal(0, 0.3) for _ in range(35)]

        forecast = service.forecast(dates=dates, weights=weights)

        # Should predict stable weight
        mean_pred = np.mean(forecast.predictions)
        assert mean_pred == pytest.approx(75.0, abs=1.0)

        # Predictions should not drift far
        assert all(73.0 < w < 77.0 for w in forecast.predictions)


class TestWeightForecastServiceFallback:
    """Tests for fallback behavior when models fail."""

    def test_fallback_on_edge_case(self):
        """Test service falls back gracefully on edge cases."""
        service = WeightForecastService()

        # Constant weight (edge case for ARIMA)
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(30)]
        weights = [80.0] * 30  # Perfectly constant

        # Should not crash, should fall back to simpler method
        forecast = service.forecast(dates=dates, weights=weights)

        assert len(forecast.predictions) == 30
        # With constant weight, predictions should be near 80
        assert all(79.0 < w < 81.0 for w in forecast.predictions)


class TestWeightForecastServiceConfidence:
    """Tests for confidence interval behavior."""

    def test_different_confidence_levels(self):
        """Test different confidence levels produce different intervals."""
        service = WeightForecastService()

        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(30)]
        np.random.seed(42)
        weights = [80.0 - 0.1 * i + np.random.normal(0, 0.2) for i in range(30)]

        # 95% confidence
        forecast_95 = service.forecast(
            dates=dates,
            weights=weights,
            confidence_level=0.95,
        )

        # 68% confidence
        forecast_68 = service.forecast(
            dates=dates,
            weights=weights,
            confidence_level=0.68,
        )

        # 95% intervals should be wider than 68%
        margin_95 = forecast_95.upper_bound[0] - forecast_95.lower_bound[0]
        margin_68 = forecast_68.upper_bound[0] - forecast_68.lower_bound[0]

        assert margin_95 > margin_68

    def test_confidence_intervals_contain_predictions(self):
        """Test predictions are within confidence bounds."""
        service = WeightForecastService()

        dates = [date(2025, 1, i) for i in range(1, 16)]
        weights = [80.0 - 0.1 * i for i in range(15)]

        forecast = service.forecast(dates=dates, weights=weights)

        # All predictions should be within bounds
        for lower, pred, upper in zip(
            forecast.lower_bound,
            forecast.predictions,
            forecast.upper_bound,
        ):
            assert lower <= pred <= upper


class TestWeightForecastServiceRealWorld:
    """Tests with realistic scenarios."""

    def test_realistic_deficit_scenario(self):
        """Test realistic weight loss scenario."""
        service = WeightForecastService()

        # User starts at 85kg, loses ~0.5kg/week for 8 weeks
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(56)]
        np.random.seed(42)
        weights = [85.0 - 0.5 * (i / 7) + np.random.normal(0, 0.3) for i in range(56)]

        forecast = service.forecast(dates=dates, weights=weights, days_ahead=30)

        # After 56 days: ~81 kg
        # After 30 more days: ~79 kg (4 more weeks)
        expected_final = 81.0 - 0.5 * 4
        assert forecast.predictions[-1] == pytest.approx(expected_final, abs=2.0)

    def test_realistic_plateau_scenario(self):
        """Test realistic plateau after initial loss."""
        service = WeightForecastService()

        # 30 days of loss, then 14 days of plateau
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(44)]
        np.random.seed(42)

        weights = []
        for i in range(30):
            # Initial loss
            weights.append(80.0 - 0.2 * i + np.random.normal(0, 0.2))
        for i in range(14):
            # Plateau around 74 kg
            weights.append(74.0 + np.random.normal(0, 0.3))

        forecast = service.forecast(dates=dates, weights=weights, days_ahead=14)

        # Should predict continued plateau (not continued loss)
        mean_forecast = np.mean(forecast.predictions)
        assert mean_forecast == pytest.approx(74.0, abs=1.5)
