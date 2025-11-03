"""
Integration tests for ML weight forecasting.

Tests complete workflow from GraphQL to domain services.
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData
from infrastructure.ml_adapters import WeightForecastAdapter


@pytest.fixture
def profile_with_progress():
    """Create profile with realistic progress history."""
    profile_id = ProfileId.generate()
    user_data = UserData(
        weight=85.0,
        height=175.0,
        age=35,
        sex="M",
        activity_level=ActivityLevel.MODERATE,
    )

    profile = NutritionalProfile(
        profile_id=profile_id,
        user_id="integration_test_user",
        user_data=user_data,
        goal=Goal.CUT,
        bmr=BMR(1750.0),
        tdee=TDEE(2275.0),
        calories_target=1800.0,  # 475 kcal deficit
        macro_split=MacroSplit(protein_g=170, carbs_g=135, fat_g=60),
        progress_history=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Add realistic deficit progress (losing ~0.5 kg/week)
    start_weight = 85.0
    for i in range(30):
        record_date = date.today() - timedelta(days=29 - i)
        # Realistic weight loss with daily variance
        expected_loss = i * 0.5 / 7  # ~0.5 kg per week
        daily_noise = (-1) ** i * 0.1  # Daily fluctuation
        weight = start_weight - expected_loss + daily_noise

        record = ProgressRecord(
            record_id=uuid4(),
            profile_id=profile_id,
            date=record_date,
            weight=weight,
            consumed_calories=1800.0,
        )
        profile.progress_history.append(record)

    return profile


@pytest.mark.integration
class TestWeightForecastIntegration:
    """Integration tests for weight forecasting workflow."""

    def test_forecast_with_sufficient_data(self, profile_with_progress):
        """Test complete forecast flow with 30 days of data."""
        # Create adapter (service created internally)
        adapter = WeightForecastAdapter()

        # Execute forecast
        forecast = adapter.forecast_from_progress(
            profile_with_progress.progress_history, days_ahead=30
        )

        # Verify forecast structure
        assert forecast is not None
        assert len(forecast.predictions) == 30
        assert len(forecast.dates) == 30
        assert len(forecast.lower_bound) == 30
        assert len(forecast.upper_bound) == 30
        assert forecast.model_used in [
            "ARIMA",
            "ExponentialSmoothing",
            "LinearRegression",
        ]
        assert forecast.confidence_level == 0.95

        # Verify predictions make sense
        first_pred = forecast.predictions[0]
        last_pred = forecast.predictions[-1]

        assert first_pred > 0
        assert last_pred > 0

        # Weight should trend downward (deficit scenario)
        current_weight = profile_with_progress.progress_history[-1].weight
        assert last_pred < current_weight

        # Confidence bounds should be valid
        assert (
            forecast.lower_bound[0] < first_pred < forecast.upper_bound[0]
        )

    def test_forecast_with_minimal_data(self, profile_with_progress):
        """Test forecast with only 7 days of data."""
        # Keep only first 7 records
        limited_progress = profile_with_progress.progress_history[:7]

        adapter = WeightForecastAdapter()

        forecast = adapter.forecast_from_progress(
            limited_progress, days_ahead=14
        )

        # Should use simple model for short history
        assert forecast.model_used in ["LinearRegression", "SimpleTrend"]
        assert len(forecast.predictions) == 14

    def test_forecast_with_custom_confidence(self, profile_with_progress):
        """Test forecast with custom confidence level."""
        adapter = WeightForecastAdapter()

        forecast = adapter.forecast_from_progress(
            profile_with_progress.progress_history,
            days_ahead=30,
            confidence_level=0.68,
        )

        assert forecast.confidence_level == 0.68

        # Narrower confidence bounds for 68% vs 95%
        bound_range = forecast.upper_bound[0] - forecast.lower_bound[0]

        # 68% CI should be narrower than typical 95% CI
        # (roughly half the range)
        assert bound_range < 2.0  # Reasonable range for 68% CI

    def test_forecast_insufficient_data_raises_error(self):
        """Test forecast fails with insufficient data."""
        profile_id = ProfileId.generate()

        # Only 1 record
        single_record = [
            ProgressRecord(
                record_id=uuid4(),
                profile_id=profile_id,
                date=date.today(),
                weight=80.0,
                consumed_calories=2000.0,
            )
        ]

        adapter = WeightForecastAdapter()

        with pytest.raises(ValueError, match="at least 2 data points"):
            adapter.forecast_from_progress(single_record, days_ahead=30)

    def test_forecast_invalid_days_ahead_raises_error(
        self, profile_with_progress
    ):
        """Test forecast fails with invalid days_ahead."""
        adapter = WeightForecastAdapter()

        with pytest.raises(ValueError, match="must be positive"):
            adapter.forecast_from_progress(
                profile_with_progress.progress_history, days_ahead=0
            )

        # Note: Upper limit validation happens in GraphQL layer (90 days)
        # Service itself allows any positive value

    def test_forecast_realistic_weight_loss_scenario(self):
        """Test forecast with realistic 12-week weight loss data."""
        profile_id = ProfileId.generate()
        progress = []

        # Realistic 12-week cut: 90 kg → 84 kg (6 kg loss, 0.5 kg/week)
        start_weight = 90.0
        weeks = 12

        for week in range(weeks):
            for day in range(7):
                days_elapsed = week * 7 + day
                days_from_today = weeks * 7 - days_elapsed
                record_date = date.today() - timedelta(days=days_from_today)

                # Weight loss curve with plateaus
                if week < 4:
                    weekly_loss = 0.7  # Initial fast loss
                elif week < 8:
                    weekly_loss = 0.5  # Steady loss
                else:
                    weekly_loss = 0.3  # Slower as approaching goal

                daily_loss = day * weekly_loss / 7
                weight = start_weight - (week * weekly_loss) - daily_loss
                weight += (-1) ** day * 0.15  # Daily fluctuation

                progress.append(
                    ProgressRecord(
                        record_id=uuid4(),
                        profile_id=profile_id,
                        date=record_date,
                        weight=weight,
                        consumed_calories=1900.0,
                    )
                )

        adapter = WeightForecastAdapter()

        # Forecast next 4 weeks
        forecast = adapter.forecast_from_progress(progress, days_ahead=28)

        # Should use advanced model (ARIMA or ExponentialSmoothing)
        assert forecast.model_used in ["ARIMA", "ExponentialSmoothing"]

        # Verify trend continues downward but slows
        current_weight = progress[-1].weight
        final_weight = forecast.predictions[-1]

        assert final_weight < current_weight
        assert current_weight - final_weight < 2.0  # Less than 2 kg/4wk

    def test_forecast_plateau_scenario(self):
        """Test forecast with weight maintenance plateau."""
        profile_id = ProfileId.generate()
        progress = []

        # 4 weeks of stable weight (plateau)
        stable_weight = 75.0

        for i in range(28):
            record_date = date.today() - timedelta(days=27 - i)
            weight = stable_weight + (-1) ** i * 0.2  # Minor fluctuation

            progress.append(
                ProgressRecord(
                    record_id=uuid4(),
                    profile_id=profile_id,
                    date=record_date,
                    weight=weight,
                    consumed_calories=2200.0,
                )
            )

        adapter = WeightForecastAdapter()

        forecast = adapter.forecast_from_progress(progress, days_ahead=14)

        # Predictions should stay near stable weight
        avg_prediction = sum(forecast.predictions) / len(forecast.predictions)

        assert abs(avg_prediction - stable_weight) < 1.0

    def test_forecast_with_missing_calorie_data(self, profile_with_progress):
        """Test forecast handles missing consumed_calories gracefully."""
        # Set some calories to None
        for i, record in enumerate(profile_with_progress.progress_history):
            if i % 3 == 0:
                record.consumed_calories = None

        adapter = WeightForecastAdapter()

        # Should still work (forecast only uses weight and dates)
        forecast = adapter.forecast_from_progress(
            profile_with_progress.progress_history, days_ahead=14
        )

        assert forecast is not None
        assert len(forecast.predictions) == 14
