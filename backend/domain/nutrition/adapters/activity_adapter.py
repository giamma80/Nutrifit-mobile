"""
Activity Data Adapter per il dominio nutrition.

Implementa l'interfaccia ActivityDataPort utilizzando il repository esistente.
"""

from __future__ import annotations

import logging
from typing import Dict

from domain.nutrition.ports import ActivityDataPort
from repository.health_totals import health_totals_repo


logger = logging.getLogger("domain.nutrition.adapters.activity")


class ActivityDataAdapter(ActivityDataPort):
    """Adapter che utilizza health_totals_repo esistente."""

    def get_daily_activity(self, user_id: str, date: str) -> Dict[str, float]:
        """Recupera dati attività giornalieri."""
        try:
            # Use existing health_totals_repo logic da app.py
            steps_tot, cal_out_tot = health_totals_repo.daily_totals(
                user_id=user_id,
                date=date,
            )

            return {
                "steps": float(steps_tot),
                "calories_out": float(cal_out_tot),
            }

        except Exception as e:
            logger.error(f"Error fetching daily activity: {e}")
            return {"steps": 0.0, "calories_out": 0.0}

    def get_weekly_activity_avg(
        self,
        user_id: str,
        end_date: str,
    ) -> Dict[str, float]:
        """Media attività ultimi 7 giorni (placeholder per ora)."""
        # TODO: Implement proper 7-day average logic
        # Per ora restituisce i dati del giorno finale
        try:
            daily = self.get_daily_activity(user_id, end_date)
            return {
                "avg_steps": daily["steps"],
                "avg_calories_out": daily["calories_out"],
            }

        except Exception as e:
            logger.error(f"Error calculating weekly activity avg: {e}")
            return {"avg_steps": 0.0, "avg_calories_out": 0.0}


__all__ = ["ActivityDataAdapter"]
