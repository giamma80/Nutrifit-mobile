"""Domain ports per meal analysis service.

Interfacce che definiscono i contratti tra il domain layer e
l'infrastructure layer per l'analisi delle foto dei pasti.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, List, Optional, Protocol

if TYPE_CHECKING:
    from domain.meal.model import MealAnalysisResult


class MealPhotoAnalyzer(Protocol):
    """Port per analisi foto pasti tramite AI."""

    @abstractmethod
    async def analyze_async(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> MealAnalysisResult:
        """Analizza foto pasto e restituisce predizioni nutrizionali."""
        ...


class MealNormalizationService(Protocol):
    """Port per normalizzazione dati nutrizionali."""

    @abstractmethod
    def normalize(
        self,
        items: List[object],
        mode: str,
    ) -> object:
        """Normalizza dati nutrizionali secondo modalità specificata."""
        ...


__all__ = [
    "MealPhotoAnalyzer",
    "MealNormalizationService",
]
