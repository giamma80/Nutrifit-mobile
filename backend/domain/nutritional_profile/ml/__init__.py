"""ML services for nutritional profile domain.

This module provides machine learning-powered features:
- Kalman TDEE: Adaptive Total Daily Energy Expenditure tracking
- Weight Forecasting: Predictive weight trajectory modeling
"""

from domain.nutritional_profile.ml.kalman_tdee import KalmanTDEEService

__all__ = ["KalmanTDEEService"]
