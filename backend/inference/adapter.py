"""Inference Adapter abstraction per Meal Photo Analysis (Fase 1 groundwork).

Obiettivo: isolare la generazione delle predictions (oggi stub) dal repository
e futura orchestrazione. Permette di:
* Inserire heuristic / remote model senza refactor repository
* Aggiungere metriche e timing attorno all'adapter
* Selezionare implementazione via feature flag ambientale

API minimale per Fase 0→1. Potrà estendersi (portion inference, nutrient
enrichment, fallback chain).
"""

from __future__ import annotations

from typing import List, Optional, Protocol
import os
import hashlib

from ai_models.meal_photo_models import MealPhotoItemPredictionRecord


class InferenceAdapter(Protocol):
    def name(self) -> str:  # identificatore adapter per logging/metrics
        ...

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        """Produce lista di predictions (stub/heuristic/model).
            Requisiti baseline:
        * Non sollevare eccezioni per input vuoti (fallback interno)
        * Restituire ≥1 item (se nessun rilevamento usare placeholder generico)
            * Confidence in range [0,1]
        """
        ...


class StubAdapter:
    """Adapter deterministico che replica lo stub fisso attuale."""

    _ITEMS = [
        MealPhotoItemPredictionRecord(
            label="Insalata mista",
            confidence=0.92,
            quantity_g=150.0,
            calories=60,
            protein=2.0,
            carbs=8.0,
            fat=2.0,
            fiber=3.0,
        ),
        MealPhotoItemPredictionRecord(
            label="Petto di pollo",
            confidence=0.88,
            quantity_g=120.0,
            calories=198,
            protein=35.0,
            carbs=0.0,
            fat=4.0,
        ),
    ]

    def name(self) -> str:
        return "stub"

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        return list(self._ITEMS)


class HeuristicAdapter:
    """Adapter semplice heuristic (fase 1 minimale).

    Regole:
    - Se photo_id termina con numero pari → aumenta porzione del secondo item
    - Aggiunge un terzo item "Acqua" se url contiene 'water'
    Confidence calcolata in base a semplici pesi.
    """

    def name(self) -> str:  # pragma: no cover (semplice)
        return "heuristic"

    def analyze(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        now_iso: str,
    ) -> List[MealPhotoItemPredictionRecord]:
        base = StubAdapter().analyze(
            user_id=user_id,
            photo_id=photo_id,
            photo_url=photo_url,
            now_iso=now_iso,
        )
        items = list(base)
        even = False
        if photo_id and photo_id[-1].isdigit():
            even = int(photo_id[-1]) % 2 == 0
        if even and len(items) > 1 and items[1].quantity_g:
            # aumenta porzione secondo item
            items[1].quantity_g = items[1].quantity_g * 1.15  # tipo euristica
            items[1].confidence = min(1.0, items[1].confidence + 0.03)
        if photo_url and "water" in photo_url.lower():
            items.append(
                MealPhotoItemPredictionRecord(
                    label="Acqua",
                    confidence=0.75,
                    quantity_g=200.0,
                    calories=0,
                )
            )
        return items


# Feature flag (futura estensione: se definito ADAPTER=heuristic, ecc.)
_ENV_FLAG = os.getenv("AI_HEURISTIC_ENABLED", "0")


def get_active_adapter() -> InferenceAdapter:
    if _ENV_FLAG in {"1", "true", "TRUE", "on"}:
        return HeuristicAdapter()
    return StubAdapter()


def hash_photo_reference(photo_id: Optional[str], photo_url: Optional[str]) -> str:
    """Hash stabile (sha256 trunc) di riferimenti foto per caching/idempotenza.
    Non usato ancora per la chiave principale (compat mantenuta) ma pronto.
    """
    basis = f"{photo_id or ''}|{photo_url or ''}".encode("utf-8")
    return hashlib.sha256(basis).hexdigest()[:16]
