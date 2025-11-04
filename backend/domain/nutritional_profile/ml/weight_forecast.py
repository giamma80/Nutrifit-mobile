"""Weight forecasting service using time series analysis.

This module provides weight forecasting capabilities using statistical
time series models (ARIMA) or simpler exponential smoothing methods.

The forecast predicts future weight trajectory based on historical data,
providing point estimates and confidence intervals for planning purposes.

Features:
- 30-day ahead forecasting
- Confidence intervals (95% default)
- Automatic model selection based on data length
- Fallback to simple methods for short histories

Models:
- ARIMA: For long histories (30+ data points)
- Exponential Smoothing: For medium histories (14-29 points)
- Linear Regression: For short histories (7-13 points)
- Mean projection: For very short histories (<7 points)

Usage:
    forecaster = WeightForecastService()

    # Provide historical data
    dates = [date(2025, 1, 1), date(2025, 1, 2), ...]
    weights = [80.5, 80.3, 80.1, ...]

    # Get 30-day forecast
    forecast = forecaster.forecast(
        dates=dates,
        weights=weights,
        days_ahead=30
    )

    # Access predictions
    for date, weight, lower, upper in zip(
        forecast.dates,
        forecast.predictions,
        forecast.lower_bound,
        forecast.upper_bound
    ):
        print(f"{date}: {weight:.1f} kg ({lower:.1f} - {upper:.1f})")
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List
import numpy as np


@dataclass
class WeightForecast:
    """Weight forecast result with confidence intervals.

    Attributes:
        dates: Forecasted dates
        predictions: Predicted weights (kg)
        lower_bound: Lower confidence bound (kg)
        upper_bound: Upper confidence bound (kg)
        model_used: Name of the model used for forecasting
        confidence_level: Confidence level used (0.0-1.0)
        trend_direction: Overall trend ("decreasing", "increasing", "stable")
        trend_magnitude: Magnitude of change (kg) from first to last prediction
    """

    dates: List[date]
    predictions: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    model_used: str
    confidence_level: float
    trend_direction: str = "stable"
    trend_magnitude: float = 0.0

    def __post_init__(self) -> None:
        """Validate forecast data consistency."""
        n = len(self.dates)
        if not (
            len(self.predictions) == n and len(self.lower_bound) == n and len(self.upper_bound) == n
        ):
            raise ValueError("All forecast arrays must have the same length")


class WeightForecastService:
    """Time series forecasting service for weight predictions.

    This service automatically selects the appropriate forecasting method
    based on the amount of historical data available:

    - 30+ points: ARIMA model (best accuracy)
    - 14-29 points: Exponential smoothing
    - 7-13 points: Linear regression
    - <7 points: Mean with trend extrapolation

    All methods provide confidence intervals for uncertainty quantification.
    """

    # Minimum data points for each method
    MIN_POINTS_ARIMA = 30
    MIN_POINTS_EXP_SMOOTHING = 14
    MIN_POINTS_LINEAR = 7

    # Default forecast parameters
    DEFAULT_CONFIDENCE_LEVEL = 0.95
    DEFAULT_FORECAST_DAYS = 30

    # Threshold for considering weight change as "stable" (kg)
    STABLE_THRESHOLD = 0.5

    @staticmethod
    def _calculate_trend(predictions: List[float]) -> tuple[str, float]:
        """Calculate trend direction and magnitude from predictions.

        Args:
            predictions: List of predicted weights

        Returns:
            Tuple of (trend_direction, trend_magnitude)
            - trend_direction: "decreasing", "increasing", or "stable"
            - trend_magnitude: Change in kg from first to last prediction
        """
        if len(predictions) < 2:
            return ("stable", 0.0)

        magnitude = predictions[-1] - predictions[0]

        # Classify based on threshold
        if abs(magnitude) < WeightForecastService.STABLE_THRESHOLD:
            direction = "stable"
        elif magnitude < 0:
            direction = "decreasing"
        else:
            direction = "increasing"

        return (direction, magnitude)

    def forecast(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int = DEFAULT_FORECAST_DAYS,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> WeightForecast:
        """Generate weight forecast with confidence intervals.

        Automatically selects the best forecasting method based on
        available data length.

        Args:
            dates: Historical dates (sorted, ascending)
            weights: Historical weights in kg
            days_ahead: Number of days to forecast ahead
            confidence_level: Confidence level for intervals (0.0-1.0)

        Returns:
            WeightForecast with predictions and confidence bounds

        Raises:
            ValueError: If inputs are invalid or insufficient data
        """
        # Validate inputs
        if len(dates) != len(weights):
            raise ValueError("Dates and weights must have same length")
        if len(dates) < 2:
            raise ValueError("Need at least 2 data points for forecasting")
        if days_ahead < 1:
            raise ValueError("days_ahead must be positive")
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        if any(w <= 0 for w in weights):
            raise ValueError("All weights must be positive")

        # Check dates are sorted
        if dates != sorted(dates):
            raise ValueError("Dates must be sorted in ascending order")

        # Select forecasting method based on data length
        n_points = len(dates)

        if n_points >= self.MIN_POINTS_ARIMA:
            return self._forecast_arima(dates, weights, days_ahead, confidence_level)
        elif n_points >= self.MIN_POINTS_EXP_SMOOTHING:
            return self._forecast_exponential_smoothing(
                dates, weights, days_ahead, confidence_level
            )
        elif n_points >= self.MIN_POINTS_LINEAR:
            return self._forecast_linear(dates, weights, days_ahead, confidence_level)
        else:
            return self._forecast_simple(dates, weights, days_ahead, confidence_level)

    def _forecast_arima(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int,
        confidence_level: float,
    ) -> WeightForecast:
        """Forecast using ARIMA model.

        ARIMA (AutoRegressive Integrated Moving Average) is a powerful
        statistical model for time series forecasting. It captures:
        - Trend (through differencing)
        - Autocorrelation (through AR terms)
        - Moving average effects (through MA terms)

        We use auto_arima to automatically select optimal parameters.
        """
        from statsmodels.tsa.arima.model import ARIMA

        # Convert weights to numpy array
        y = np.array(weights)

        # Fit ARIMA model with auto-selected order
        # Using (1,1,1) as a good default for weight data
        # p=1: one lag of autoregression
        # d=1: first-order differencing (removes trend)
        # q=1: one lag of moving average
        try:
            model = ARIMA(y, order=(1, 1, 1))
            fitted_model = model.fit()

            # Get forecast with confidence intervals
            forecast_obj = fitted_model.get_forecast(steps=days_ahead)

            # Get predictions
            predictions = forecast_obj.predicted_mean

            # Get confidence intervals
            conf_int = forecast_obj.conf_int(alpha=1 - confidence_level)

            lower_bound = conf_int.iloc[:, 0].tolist()
            upper_bound = conf_int.iloc[:, 1].tolist()

        except Exception:
            # If ARIMA fails, fallback to exponential smoothing
            return self._forecast_exponential_smoothing(
                dates, weights, days_ahead, confidence_level
            )

        # Generate future dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i + 1) for i in range(days_ahead)]

        # Calculate trend
        trend_direction, trend_magnitude = self._calculate_trend(predictions.tolist())

        return WeightForecast(
            dates=future_dates,
            predictions=predictions.tolist(),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            model_used="ARIMA(1,1,1)",
            confidence_level=confidence_level,
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude,
        )

    def _forecast_exponential_smoothing(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int,
        confidence_level: float,
    ) -> WeightForecast:
        """Forecast using exponential smoothing.

        Exponential smoothing gives more weight to recent observations,
        making it adaptive to recent trends while still considering
        historical patterns.
        """
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        y = np.array(weights)

        try:
            # Simple exponential smoothing (no trend, no seasonality)
            model = ExponentialSmoothing(
                y,
                trend="add",  # Additive trend for weight changes
                seasonal=None,  # No seasonality in daily weights
            )
            fitted_model = model.fit()

            # Generate forecast
            forecast_result = fitted_model.forecast(steps=days_ahead)
            predictions = forecast_result.tolist()

            # Estimate prediction intervals using residual std
            residuals = fitted_model.fittedvalues - y[: len(fitted_model.fittedvalues)]
            std_error = np.std(residuals)

            # Z-score for confidence level
            from scipy import stats

            z_score = stats.norm.ppf((1 + confidence_level) / 2)

            # Expanding confidence intervals over time
            margin = [z_score * std_error * np.sqrt(i + 1) for i in range(days_ahead)]
            lower_bound = [pred - m for pred, m in zip(predictions, margin)]
            upper_bound = [pred + m for pred, m in zip(predictions, margin)]

        except Exception:
            # Fallback to linear regression
            return self._forecast_linear(dates, weights, days_ahead, confidence_level)

        # Generate future dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i + 1) for i in range(days_ahead)]

        # Calculate trend
        trend_direction, trend_magnitude = self._calculate_trend(predictions)

        return WeightForecast(
            dates=future_dates,
            predictions=predictions,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            model_used="ExponentialSmoothing",
            confidence_level=confidence_level,
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude,
        )

    def _forecast_linear(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int,
        confidence_level: float,
    ) -> WeightForecast:
        """Forecast using simple linear regression.

        Fits a straight line to historical data and extrapolates.
        Good for short-term predictions with clear linear trends.
        """
        from scipy import stats as scipy_stats

        # Convert dates to days since first date
        days = np.array([(d - dates[0]).days for d in dates])
        y = np.array(weights)

        # Fit linear regression
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(days, y)

        # Generate future days
        last_day = days[-1]
        future_days = np.array([last_day + i + 1 for i in range(days_ahead)])

        # Predictions
        predictions = slope * future_days + intercept

        # Confidence intervals
        # Standard error increases with distance from data
        residuals = y - (slope * days + intercept)
        residual_std = np.std(residuals)

        from scipy import stats

        z_score = stats.norm.ppf((1 + confidence_level) / 2)

        # Expanding margins for extrapolation uncertainty
        margin = [z_score * residual_std * (1 + 0.1 * i) for i in range(days_ahead)]
        lower_bound = predictions - margin
        upper_bound = predictions + margin

        # Generate future dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i + 1) for i in range(days_ahead)]

        # Calculate trend
        trend_direction, trend_magnitude = self._calculate_trend(predictions.tolist())

        return WeightForecast(
            dates=future_dates,
            predictions=predictions.tolist(),
            lower_bound=lower_bound.tolist(),
            upper_bound=upper_bound.tolist(),
            model_used="LinearRegression",
            confidence_level=confidence_level,
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude,
        )

    def _forecast_simple(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int,
        confidence_level: float,
    ) -> WeightForecast:
        """Simple forecast for very short histories.

        Uses mean weight with linear trend from first to last point.
        Wide confidence intervals to reflect high uncertainty.
        """
        y = np.array(weights)

        # Calculate simple trend
        trend_per_day = (weights[-1] - weights[0]) / (len(weights) - 1)

        # Project forward
        last_weight = weights[-1]
        predictions = [last_weight + trend_per_day * (i + 1) for i in range(days_ahead)]

        # Wide confidence intervals (±2 std of historical data)
        std = np.std(y)
        from scipy import stats

        z_score = stats.norm.ppf((1 + confidence_level) / 2)

        # Very wide margins due to limited data
        margin = [z_score * std * (1 + 0.2 * i) for i in range(days_ahead)]
        lower_bound = [pred - m for pred, m in zip(predictions, margin)]
        upper_bound = [pred + m for pred, m in zip(predictions, margin)]

        # Generate future dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i + 1) for i in range(days_ahead)]

        # Calculate trend
        trend_direction, trend_magnitude = self._calculate_trend(predictions)

        return WeightForecast(
            dates=future_dates,
            predictions=predictions,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            model_used="SimpleTrend",
            confidence_level=confidence_level,
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude,
        )
