"""Nutrition plan adapter - stub implementation.

Per ora implementazione stub per completare l'integrazione.
In futuro: persistenza in database, integrazione con user preferences.
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from domain.nutrition.model import (
    NutritionPlan,
    UserPhysicalData,
    ActivityLevel,
    GoalStrategy,
    MacroTargets,
)
from domain.nutrition.ports import NutritionPlanPort


logger = logging.getLogger("domain.nutrition.adapters.nutrition_plan")


class NutritionPlanAdapter(NutritionPlanPort):
    """Stub adapter per nutrition plans - in-memory storage."""
    
    def __init__(self):
        # In-memory storage per testing/demo
        self._plans: dict[str, NutritionPlan] = {}
    
    def get_by_user_id(self, user_id: str) -> Optional[NutritionPlan]:
        """Recupera piano utente (stub)."""
        return self._plans.get(user_id)
    
    def save(self, plan: NutritionPlan) -> NutritionPlan:
        """Salva piano (stub in-memory)."""
        self._plans[plan.user_id] = plan
        logger.info(f"Saved nutrition plan for user {plan.user_id}")
        return plan
    
    def create_default_plan(
        self,
        user_id: str,
        physical_data: UserPhysicalData,
    ) -> NutritionPlan:
        """Crea piano default per nuovo utente."""
        
        # Default values per demo
        default_targets = MacroTargets(
            calories=2000,
            protein_g=150.0,
            carbs_g=200.0,
            fat_g=67.0,
            fiber_g=28.0,
        )
        
        plan = NutritionPlan(
            user_id=user_id,
            strategy=GoalStrategy.MAINTAIN,
            macro_targets=default_targets,
            physical_data=physical_data,
            bmr=1600.0,  # Will be calculated properly by service
            tdee=2000.0,  # Will be calculated properly by service
            updated_at=datetime.now(),
        )
        
        return self.save(plan)


__all__ = ["NutritionPlanAdapter"]