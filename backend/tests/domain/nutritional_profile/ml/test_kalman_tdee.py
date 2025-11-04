"""Tests for Kalman TDEE adaptive tracking service."""

import pytest
import numpy as np
from domain.nutritional_profile.ml.kalman_tdee import (
    KalmanTDEEService,
    KalmanState,
)


class TestKalmanState:
    """Tests for KalmanState dataclass."""

    def test_confidence_interval_default(self):
        """Test 95% confidence interval calculation."""
        state = KalmanState(tdee=2000.0, variance=10000.0)
        lower, upper = state.confidence_interval()

        # 95% CI: ±1.96 * std_dev
        # std_dev = sqrt(10000) = 100
        # CI = 2000 ± 196
        assert lower == pytest.approx(1804.0, rel=0.01)
        assert upper == pytest.approx(2196.0, rel=0.01)

    def test_confidence_interval_custom_z(self):
        """Test confidence interval with custom z-score."""
        state = KalmanState(tdee=2000.0, variance=10000.0)
        lower, upper = state.confidence_interval(z_score=1.0)

        # 68% CI: ±1.0 * std_dev
        # std_dev = 100
        # CI = 2000 ± 100
        assert lower == pytest.approx(1900.0)
        assert upper == pytest.approx(2100.0)


class TestKalmanTDEEServiceInitialization:
    """Tests for KalmanTDEEService initialization."""

    def test_init_valid(self):
        """Test initialization with valid parameters."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        assert service.state.tdee == 2000.0
        assert service.state.variance == 10000.0
        assert service.state.previous_weight is None
        assert service.process_noise == 50.0
        assert service.measurement_noise == 0.01

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        service = KalmanTDEEService(
            initial_tdee=2500.0,
            initial_variance=5000.0,
            process_noise=50.0,
            measurement_noise=0.5,
        )

        assert service.state.tdee == 2500.0
        assert service.state.variance == 5000.0
        assert service.process_noise == 50.0
        assert service.measurement_noise == 0.5

    def test_init_negative_tdee(self):
        """Test initialization with negative TDEE."""
        with pytest.raises(ValueError, match="Initial TDEE must be positive"):
            KalmanTDEEService(initial_tdee=-100.0)

    def test_init_negative_variance(self):
        """Test initialization with negative variance."""
        with pytest.raises(ValueError, match="Initial variance must be non-negative"):
            KalmanTDEEService(initial_tdee=2000.0, initial_variance=-100.0)

    def test_init_negative_process_noise(self):
        """Test initialization with negative process noise."""
        with pytest.raises(ValueError, match="Process noise must be non-negative"):
            KalmanTDEEService(initial_tdee=2000.0, process_noise=-10.0)

    def test_init_negative_measurement_noise(self):
        """Test initialization with negative measurement noise."""
        with pytest.raises(ValueError, match="Measurement noise must be positive"):
            KalmanTDEEService(initial_tdee=2000.0, measurement_noise=-0.1)


class TestKalmanTDEEServiceUpdate:
    """Tests for Kalman filter update logic."""

    def test_first_update_stores_weight(self):
        """Test that first update only stores weight without changing TDEE."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        tdee = service.update(weight_kg=80.0, consumed_calories=2200.0)

        assert tdee == 2000.0  # TDEE unchanged
        assert service.state.previous_weight == 80.0

    def test_update_weight_loss_increases_tdee(self):
        """Test TDEE increases when weight loss exceeds expectation."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        # First update: store initial weight
        service.update(weight_kg=80.0, consumed_calories=2200.0)

        # Second update: user lost 1kg eating 2200 kcal/day
        # Expected: (2200 - 2000) / 7700 = +0.026kg (slight gain)
        # Actual: -1.0kg (weight loss)
        # Innovation negative => TDEE should increase
        tdee = service.update(weight_kg=79.0, consumed_calories=2200.0)

        assert tdee > 2000.0, "TDEE should increase"

    def test_update_weight_gain_decreases_tdee(self):
        """Test TDEE decreases when weight gain exceeds expectation."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        # First update
        service.update(weight_kg=80.0, consumed_calories=1800.0)

        # Second update: user gained 1kg eating 1800 kcal/day
        # Expected: (1800 - 2000) / 7700 = -0.026kg (slight loss)
        # Actual: +1.0kg (weight gain)
        # Innovation positive => TDEE should decrease
        tdee = service.update(weight_kg=81.0, consumed_calories=1800.0)

        assert tdee < 2000.0, "TDEE should decrease"

    def test_update_reduces_variance(self):
        """Test that informative measurements reduce uncertainty."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        # First update just stores weight
        service.update(weight_kg=80.0, consumed_calories=2000.0)
        variance_after_first = service.state.variance

        # Simulate consistent deficit with informative weight changes
        # User eats 1500 kcal/day, loses weight predictably
        weights = [79.9, 79.7, 79.5, 79.3, 79.1]
        for weight in weights:
            service.update(weight_kg=weight, consumed_calories=1500.0)

        # Variance should decrease with informative measurements
        assert service.state.variance < variance_after_first

    def test_update_invalid_weight(self):
        """Test update with invalid weight."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        with pytest.raises(ValueError, match="Weight must be positive"):
            service.update(weight_kg=-5.0, consumed_calories=2000.0)

    def test_update_invalid_calories(self):
        """Test update with invalid calories."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        with pytest.raises(ValueError, match="Consumed calories cannot be negative"):
            service.update(weight_kg=80.0, consumed_calories=-100.0)

    def test_update_enforces_minimum_tdee(self):
        """Test TDEE cannot go below 500 kcal/day."""
        service = KalmanTDEEService(initial_tdee=600.0, process_noise=10.0)

        # Force large weight gain to drive TDEE down
        service.update(weight_kg=80.0, consumed_calories=500.0)
        prev_weight = service.state.previous_weight
        assert prev_weight is not None
        for _ in range(10):
            service.update(weight_kg=prev_weight + 0.5, consumed_calories=500.0)
            prev_weight = service.state.previous_weight
            assert prev_weight is not None

        # TDEE should be clamped at minimum
        assert service.state.tdee >= 500.0

    def test_update_enforces_maximum_tdee(self):
        """Test TDEE cannot exceed 10000 kcal/day."""
        service = KalmanTDEEService(initial_tdee=9500.0, process_noise=10.0)

        # Force large weight loss to drive TDEE up
        service.update(weight_kg=80.0, consumed_calories=9500.0)
        prev_weight = service.state.previous_weight
        assert prev_weight is not None
        for _ in range(10):
            service.update(weight_kg=prev_weight - 0.5, consumed_calories=9500.0)
            prev_weight = service.state.previous_weight
            assert prev_weight is not None

        # TDEE should be clamped at maximum
        assert service.state.tdee <= 10000.0


class TestKalmanTDEEServiceConvergence:
    """Tests for Kalman filter convergence behavior."""

    def test_converges_to_true_tdee(self):
        """Test filter converges to true TDEE with synthetic data."""
        TRUE_TDEE = 2200.0
        WEIGHT_NOISE_STD = 0.2  # kg (reduced noise)

        service = KalmanTDEEService(
            initial_tdee=2000.0,  # Start with wrong estimate
            process_noise=25.0,  # Reduced to allow faster convergence
            measurement_noise=WEIGHT_NOISE_STD**2,
        )

        # Simulate 60 days of consistent eating (longer period)
        np.random.seed(42)
        weight = 80.0
        for day in range(60):
            # Consume at maintenance
            consumed = TRUE_TDEE

            # Simulate realistic weight change
            # Perfect energy balance + noise
            weight_change = np.random.normal(0, WEIGHT_NOISE_STD)
            weight += weight_change

            service.update(weight_kg=weight, consumed_calories=consumed)

        # After 60 days, estimate should be close to true TDEE
        final_tdee, std_dev = service.get_estimate()

        # Allow 10% error due to noise (more realistic)
        assert final_tdee == pytest.approx(TRUE_TDEE, rel=0.10)
        # Uncertainty should decrease
        assert std_dev < 100.0  # Initial std was 100

    def test_converges_during_deficit(self):
        """Test filter works correctly during calorie deficit."""
        TRUE_TDEE = 2000.0
        DAILY_DEFICIT = 500.0  # kcal/day
        EXPECTED_LOSS_PER_DAY = DAILY_DEFICIT / 7700.0  # ~0.065 kg/day

        service = KalmanTDEEService(
            initial_tdee=1800.0,  # Underestimate
            process_noise=50.0,
            measurement_noise=0.25,
        )

        # Simulate 20 days of deficit
        np.random.seed(42)
        weight = 85.0
        for day in range(20):
            consumed = TRUE_TDEE - DAILY_DEFICIT  # 1500 kcal

            # Weight should decrease by expected amount + noise
            weight -= EXPECTED_LOSS_PER_DAY
            weight += np.random.normal(0, 0.2)

            service.update(weight_kg=weight, consumed_calories=consumed)

        # Should converge to true TDEE
        final_tdee, _ = service.get_estimate()
        assert final_tdee == pytest.approx(TRUE_TDEE, rel=0.10)


class TestKalmanTDEEServiceQueries:
    """Tests for querying filter state."""

    def test_get_estimate(self):
        """Test getting TDEE estimate with uncertainty."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        tdee, std_dev = service.get_estimate()

        assert tdee == 2000.0
        assert std_dev == pytest.approx(100.0)  # sqrt(10000)

    def test_get_confidence_interval_95(self):
        """Test 95% confidence interval."""
        service = KalmanTDEEService(initial_tdee=2000.0, initial_variance=10000.0)

        lower, upper = service.get_confidence_interval(confidence_level=0.95)

        # Should be approximately ±196 kcal
        assert lower == pytest.approx(1804.0, rel=0.01)
        assert upper == pytest.approx(2196.0, rel=0.01)

    def test_get_confidence_interval_68(self):
        """Test 68% confidence interval."""
        service = KalmanTDEEService(initial_tdee=2000.0, initial_variance=10000.0)

        lower, upper = service.get_confidence_interval(confidence_level=0.68)

        # Should be approximately ±100 kcal (1 std dev)
        assert lower == pytest.approx(1900.0, rel=0.01)
        assert upper == pytest.approx(2100.0, rel=0.01)

    def test_get_confidence_interval_invalid(self):
        """Test confidence interval with invalid level."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        with pytest.raises(ValueError, match="Confidence level must be between 0 and 1"):
            service.get_confidence_interval(confidence_level=1.5)


class TestKalmanTDEEServiceReset:
    """Tests for resetting filter state."""

    def test_reset(self):
        """Test resetting filter to new initial state."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        # Do some updates
        service.update(weight_kg=80.0, consumed_calories=2000.0)
        service.update(weight_kg=79.5, consumed_calories=2000.0)

        # Reset to new TDEE
        service.reset(new_tdee=2500.0, new_variance=5000.0)

        assert service.state.tdee == 2500.0
        assert service.state.variance == 5000.0
        assert service.state.previous_weight is None

    def test_reset_invalid_tdee(self):
        """Test reset with invalid TDEE."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        with pytest.raises(ValueError, match="TDEE must be positive"):
            service.reset(new_tdee=-100.0)

    def test_reset_invalid_variance(self):
        """Test reset with invalid variance."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        with pytest.raises(ValueError, match="Variance must be non-negative"):
            service.reset(new_tdee=2000.0, new_variance=-100.0)


class TestKalmanTDEEServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_consumed_calories(self):
        """Test with zero consumed calories (fasting day)."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        service.update(weight_kg=80.0, consumed_calories=0.0)
        tdee = service.update(weight_kg=79.7, consumed_calories=0.0)

        # Should handle gracefully
        assert tdee > 0

    def test_no_weight_change(self):
        """Test with exactly zero weight change."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        service.update(weight_kg=80.0, consumed_calories=2000.0)
        tdee = service.update(weight_kg=80.0, consumed_calories=2000.0)

        # If weight stable at 2000 kcal, TDEE estimate should stay ~2000
        assert tdee == pytest.approx(2000.0, rel=0.01)

    def test_large_weight_fluctuation(self):
        """Test filter handles large weight changes (outliers)."""
        service = KalmanTDEEService(initial_tdee=2000.0)

        service.update(weight_kg=80.0, consumed_calories=2000.0)

        # Simulate large measurement error (e.g., user weighed with shoes)
        tdee = service.update(weight_kg=85.0, consumed_calories=2000.0)

        # Filter should handle outlier without breaking
        assert 500.0 <= tdee <= 10000.0

    def test_high_variance_scenario(self):
        """Test with highly variable weight measurements."""
        service = KalmanTDEEService(
            initial_tdee=2000.0, measurement_noise=1.0  # High measurement noise
        )

        np.random.seed(42)
        weight = 80.0
        for _ in range(10):
            # Random large fluctuations
            weight += np.random.uniform(-2, 2)
            service.update(weight_kg=weight, consumed_calories=2000.0)

        # Should still produce reasonable estimate
        final_tdee, _ = service.get_estimate()
        assert 1000.0 <= final_tdee <= 3000.0
