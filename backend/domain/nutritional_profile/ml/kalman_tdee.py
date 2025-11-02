"""Kalman Filter-based adaptive TDEE tracking.

This module implements a Kalman filter to adaptively estimate a user's
True Daily Energy Expenditure (TDEE) based on observed weight changes
and reported calorie intake.

The Kalman filter provides:
- Adaptive TDEE estimation that responds to actual weight changes
- Noise reduction in daily measurements
- Confidence intervals for estimates
- Automatic handling of measurement uncertainty

Theory:
- TDEE is modeled as a slowly-changing hidden state
- Weight changes reveal the true energy balance (intake - TDEE)
- Kalman filter fuses measurements with process model for optimal estimate

Usage:
    kalman = KalmanTDEEService(initial_tdee=2000.0)
    
    # Update daily with weight and calories
    for day in progress_history:
        tdee_estimate = kalman.update(
            weight_kg=day.weight,
            consumed_calories=day.consumed_calories
        )
    
    # Get current estimate with confidence
    tdee, std_dev = kalman.get_estimate()
    confidence_95 = (tdee - 2*std_dev, tdee + 2*std_dev)
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


@dataclass
class KalmanState:
    """Kalman filter state for TDEE tracking.
    
    Attributes:
        tdee: Current TDEE estimate (kcal/day)
        variance: Uncertainty in TDEE estimate (variance)
        previous_weight: Last observed weight (kg)
    """
    tdee: float  # kcal/day
    variance: float  # variance in TDEE estimate
    previous_weight: Optional[float] = None  # kg
    
    def confidence_interval(
        self, z_score: float = 1.96
    ) -> Tuple[float, float]:
        """Calculate confidence interval for TDEE estimate.
        
        Args:
            z_score: Z-score for confidence level (default 1.96 = 95%)
        
        Returns:
            Tuple of (lower_bound, upper_bound) in kcal/day
        """
        std_dev = np.sqrt(self.variance)
        margin = z_score * std_dev
        return (self.tdee - margin, self.tdee + margin)


class KalmanTDEEService:
    """Kalman filter service for adaptive TDEE tracking.
    
    This service uses a Kalman filter to estimate the user's true TDEE
    by observing weight changes and reported calorie intake over time.
    
    The filter assumes:
    - TDEE changes slowly over time (process noise)
    - Weight measurements have some error (measurement noise)
    - Energy balance: weight_change = (intake - TDEE) / 7700 kcal/kg
    
    Attributes:
        state: Current Kalman filter state
        process_noise: How much TDEE can change day-to-day (variance)
        measurement_noise: Uncertainty in weight measurements (variance)
    """
    
    # Default noise parameters (tuned for typical use cases)
    DEFAULT_PROCESS_NOISE = 50.0  # TDEE variance day-to-day (kcal²)
    DEFAULT_MEASUREMENT_NOISE = 0.01  # Weight measurement variance (kg²)
    # 0.01 kg² = 0.1 kg std dev (modern scale accuracy)
    KCAL_PER_KG = 7700.0  # Energy equivalent of 1kg body weight
    
    def __init__(
        self,
        initial_tdee: float,
        initial_variance: float = 10000.0,  # Initial uncertainty (kcal²)
        process_noise: float = DEFAULT_PROCESS_NOISE,
        measurement_noise: float = DEFAULT_MEASUREMENT_NOISE,
    ) -> None:
        """Initialize Kalman TDEE filter.
        
        Args:
            initial_tdee: Initial TDEE estimate (kcal/day)
            initial_variance: Initial uncertainty in TDEE (variance)
            process_noise: Daily TDEE variance (how much it can change)
            measurement_noise: Weight measurement variance
        """
        if initial_tdee <= 0:
            raise ValueError("Initial TDEE must be positive")
        if initial_variance < 0:
            raise ValueError("Initial variance must be non-negative")
        if process_noise < 0:
            raise ValueError("Process noise must be non-negative")
        if measurement_noise <= 0:
            raise ValueError("Measurement noise must be positive")
            
        self.state = KalmanState(
            tdee=initial_tdee,
            variance=initial_variance,
            previous_weight=None,
        )
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        
    def predict(self) -> None:
        """Predict step: TDEE stays roughly constant, but add uncertainty.
        
        This step increases uncertainty (variance) to account for the fact
        that TDEE can change slowly over time (metabolism adaptation,
        activity level changes, etc.).
        """
        # TDEE prediction: assume constant
        # (no change in predicted value, just increase uncertainty)
        self.state.variance += self.process_noise
        
    def update(
        self,
        weight_kg: float,
        consumed_calories: float,
    ) -> float:
        """Update filter with new measurement.
        
        This is the core Kalman update step. It uses the observed weight
        change and reported calorie intake to update the TDEE estimate.
        
        Energy balance model:
            weight_change = (consumed - TDEE) / KCAL_PER_KG
            
        Args:
            weight_kg: Current weight measurement (kg)
            consumed_calories: Reported calorie intake (kcal)
            
        Returns:
            Updated TDEE estimate (kcal/day)
            
        Raises:
            ValueError: If inputs are invalid
        """
        if weight_kg <= 0:
            raise ValueError("Weight must be positive")
        if consumed_calories < 0:
            raise ValueError("Consumed calories cannot be negative")
            
        # First update: just store weight, no update yet
        if self.state.previous_weight is None:
            self.state.previous_weight = weight_kg
            return self.state.tdee
            
        # Calculate observed weight change
        weight_change = weight_kg - self.state.previous_weight  # kg
        
        # Calculate expected weight change based on current TDEE estimate
        # energy_balance = consumed - tdee (kcal)
        # weight_change = energy_balance / KCAL_PER_KG (kg)
        expected_balance = consumed_calories - self.state.tdee
        expected_weight_change = expected_balance / self.KCAL_PER_KG
        
        # Innovation: difference between observed and expected
        innovation = weight_change - expected_weight_change  # kg
        
        # Predict step: add process noise to variance
        predicted_variance = self.state.variance + self.process_noise
        
        # Innovation variance (uncertainty in innovation)
        # Convert from kcal² to kg² using KCAL_PER_KG scaling
        innovation_variance = (
            predicted_variance / (self.KCAL_PER_KG ** 2) +
            self.measurement_noise
        )
        
        # Kalman gain: how much to trust the measurement vs prediction
        # High gain = trust measurement more
        # Low gain = trust prediction more
        kalman_gain = (
            (predicted_variance / (self.KCAL_PER_KG ** 2)) /
            innovation_variance
        )
        
        # Update TDEE estimate
        # If weight decreased more than expected: TDEE was underestimated
        # If weight increased more than expected: TDEE was overestimated
        tdee_correction = -innovation * kalman_gain * self.KCAL_PER_KG
        self.state.tdee += tdee_correction
        
        # Update variance (reduce uncertainty after measurement)
        self.state.variance = predicted_variance * (1.0 - kalman_gain)
        
        # Store current weight for next update
        self.state.previous_weight = weight_kg
        
        # Enforce reasonable bounds (TDEE should be positive)
        if self.state.tdee < 500:
            self.state.tdee = 500.0  # Minimum viable TDEE
        if self.state.tdee > 10000:
            self.state.tdee = 10000.0  # Maximum reasonable TDEE
            
        return self.state.tdee
        
    def get_estimate(self) -> Tuple[float, float]:
        """Get current TDEE estimate with uncertainty.
        
        Returns:
            Tuple of (tdee_estimate, standard_deviation) in kcal/day
        """
        std_dev = np.sqrt(self.state.variance)
        return (self.state.tdee, std_dev)
        
    def get_confidence_interval(
        self,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """Get confidence interval for TDEE estimate.
        
        Args:
            confidence_level: Confidence level (0.0-1.0), default 0.95
            
        Returns:
            Tuple of (lower_bound, upper_bound) in kcal/day
        """
        if not 0 < confidence_level < 1:
            raise ValueError("Confidence level must be between 0 and 1")
            
        # Z-score for confidence level (normal distribution)
        from scipy import stats
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        
        return self.state.confidence_interval(z_score)
        
    def reset(self, new_tdee: float, new_variance: float = 10000.0) -> None:
        """Reset filter with new initial values.
        
        Useful when user makes major lifestyle changes (e.g., new training
        program, diet change) that invalidate previous estimates.
        
        Args:
            new_tdee: New TDEE estimate (kcal/day)
            new_variance: New initial uncertainty (variance)
        """
        if new_tdee <= 0:
            raise ValueError("TDEE must be positive")
        if new_variance < 0:
            raise ValueError("Variance must be non-negative")
            
        self.state = KalmanState(
            tdee=new_tdee,
            variance=new_variance,
            previous_weight=None,
        )
