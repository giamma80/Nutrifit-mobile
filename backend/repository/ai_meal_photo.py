"""In-memory repository per analisi foto pasto (stub Fase 0).

Responsabilità (Fase 0):
* Registrare un'analisi generata in modo deterministico (no vera AI)
* Supportare idempotenza tramite idempotency_key
    (auto-derivata da photoId|photoUrl|user)
* Restituire sempre stato COMPLETED con predictions statiche
* Fornire conferma che genera MealRecord a partire dagli indici accettati

Fasi future potranno introdurre stati PENDING/FAILED e aggiornamenti asincroni.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import hashlib
import uuid


@dataclass(slots=True)
class MealPhotoItemPredictionRecord:
    label: str
    confidence: float
    quantity_g: Optional[float] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None


@dataclass(slots=True)
class MealPhotoAnalysisRecord:
    id: str
    user_id: str
    status: str  # PENDING | COMPLETED | FAILED
    created_at: str
    items: List[MealPhotoItemPredictionRecord]
    raw_json: Optional[str] = None
    idempotency_key_used: Optional[str] = None


class InMemoryMealPhotoAnalysisRepository:
    def __init__(self) -> None:
        # (user_id, analysis_id)
        self._analyses: Dict[Tuple[str, str], MealPhotoAnalysisRecord] = {}
        # (user_id, idempotency_key) -> analysis_id
        self._idemp: Dict[Tuple[str, str], str] = {}

    def _auto_key(
        self,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
    ) -> str:
        basis = f"{user_id}|{photo_id or ''}|{photo_url or ''}".encode("utf-8")
        return "auto-" + hashlib.sha256(basis).hexdigest()[:16]

    def create_or_get(
        self,
        *,
        user_id: str,
        photo_id: Optional[str],
        photo_url: Optional[str],
        idempotency_key: Optional[str],
        now_iso: str,
    ) -> MealPhotoAnalysisRecord:
        if idempotency_key is None:
            idempotency_key = self._auto_key(user_id, photo_id, photo_url)
        key = (user_id, idempotency_key)
        existing_id = self._idemp.get(key)
        if existing_id:
            return self._analyses[(user_id, existing_id)]
        # Stub predictions statiche (2 items)
        items = [
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
        analysis_id = uuid.uuid4().hex
        rec = MealPhotoAnalysisRecord(
            id=analysis_id,
            user_id=user_id,
            status="COMPLETED",
            created_at=now_iso,
            items=items,
            raw_json=None,
            idempotency_key_used=idempotency_key,
        )
        self._analyses[(user_id, analysis_id)] = rec
        self._idemp[key] = analysis_id
        return rec

    def get(self, user_id: str, analysis_id: str) -> Optional[MealPhotoAnalysisRecord]:
        return self._analyses.get((user_id, analysis_id))


meal_photo_repo = InMemoryMealPhotoAnalysisRepository()
